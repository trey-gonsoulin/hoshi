"""Tests for hoshi/events.py sky event detection.

All tests use Skyfield with the bundled de421.bsp — no Horizons network calls.
Seed-cache bodies (Chiron/Ceres/Eris) are not tested here since they require
the Lambda seed-path environment variable.
"""

from datetime import datetime, timezone

import numpy as np
import pytest

from hoshi.events import (
    BODY_DISPLAY,
    SIGN_SYMBOL,
    SkyEvent,
    _ayanamsa_from_jd,
    _body_directions,
    _body_lons,
    _datetime_to_jd,
    _find_exact_aspects,
    _find_ingresses_skyfield,
    _find_moon_phases,
    _find_stations_skyfield,
    _find_voc_windows,
    _jd_to_utc,
    _moon_sun_elongation,
    _phase_bucket,
    _precession_from_jd,
    _sign_idx_realsky,
    _sign_idx_tropical,
    _sign_idx_vedic,
    _sign_name,
    sky_events,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

# J2000.0 epoch as a UTC datetime
J2000 = datetime(2000, 1, 1, 11, 58, 56, tzinfo=timezone.utc)

# Mercury retrograde periods in 2026 (verified from de421):
#   Feb 26 – Mar 20  |  Jun 29 – Jul 23  |  Oct 24 – Nov 13
MERCURY_RX_START = datetime(2026, 6, 15, tzinfo=timezone.utc)  # bracket Jun 29 station
MERCURY_RX_END = datetime(2026, 8, 1, tzinfo=timezone.utc)
MERCURY_MID_RX = datetime(2026, 7, 10, tzinfo=timezone.utc)  # mid-retrograde

# Known Moon New Moon in 2026 (approx 2026-01-29)
NEW_MOON_2026_JAN = datetime(2026, 1, 29, tzinfo=timezone.utc)

# A 30-day window for integration tests
WINDOW_START = datetime(2026, 7, 1, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 7, 31, tzinfo=timezone.utc)


# ── Unit tests ────────────────────────────────────────────────────────────────


class TestJdConversion:
    def test_roundtrip(self):
        dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        jd = _datetime_to_jd(dt)
        recovered = _jd_to_utc(jd)
        # Allow 1-second tolerance for floating-point roundtrip
        assert abs((recovered - dt).total_seconds()) < 1.0

    def test_j2000_epoch(self):
        # J2000.0 = JD 2451545.0
        jd = _datetime_to_jd(J2000)
        assert abs(jd - 2451545.0) < 0.01


class TestPrecession:
    def test_j2000_zero_precession(self):
        jd = np.array([2451545.0])
        prec = _precession_from_jd(jd)
        assert abs(prec[0]) < 0.001

    def test_precession_increases_with_time(self):
        jd_past = np.array([2451545.0 - 365.25 * 10])  # 10 years before J2000
        jd_future = np.array([2451545.0 + 365.25 * 10])  # 10 years after
        prec_past = _precession_from_jd(jd_past)
        prec_future = _precession_from_jd(jd_future)
        assert prec_past[0] < 0
        assert prec_future[0] > 0

    def test_ayanamsa_near_j2000(self):
        jd = np.array([2451545.0])
        ayn = _ayanamsa_from_jd(jd)
        assert abs(ayn[0] - 23.85) < 0.01


class TestSignIndices:
    def test_tropical_aries_0_30(self):
        lons = np.array([0.0, 15.0, 29.99])
        idxs = _sign_idx_tropical(lons)
        assert all(idx == 0 for idx in idxs)  # Aries

    def test_tropical_boundaries(self):
        lons = np.array([0.0, 30.0, 60.0, 90.0, 150.0, 180.0, 270.0, 330.0])
        idxs = _sign_idx_tropical(lons)
        assert list(idxs) == [0, 1, 2, 3, 5, 6, 9, 11]

    def test_vedic_offset(self):
        # Vedic = tropical - ayanamsa (~24°); so tropical Aries (0-30) is
        # vedic Pisces (12) for most of Aries
        ayn = np.array([23.85])
        lons = np.array([5.0])  # tropical 5° Aries
        idxs = _sign_idx_vedic(lons, ayn)
        assert idxs[0] == 11  # Pisces (0-based index 11)

    def test_realsky_sagittarius(self):
        # IAU Sagittarius: ~266.55 – 299.71 in J2000 (no precession shift)
        prec = np.zeros(1)
        lons = np.array([280.0])
        idxs = _sign_idx_realsky(lons, prec)
        from hoshi.zodiac import IAU

        assert IAU[int(idxs[0])].name == "Sagittarius"

    def test_realsky_ophiuchus(self):
        # IAU Ophiuchus: ~247.74 – 266.55
        prec = np.zeros(1)
        lons = np.array([255.0])
        idxs = _sign_idx_realsky(lons, prec)
        from hoshi.zodiac import IAU

        assert IAU[int(idxs[0])].name == "Ophiuchus"


class TestSignName:
    def test_realsky_sign_name(self):
        assert _sign_name(8, "realsky") == "Ophiuchus"  # IAU index 8

    def test_tropical_sign_name(self):
        assert _sign_name(0, "tropical") == "Aries"
        assert _sign_name(11, "tropical") == "Pisces"


class TestMoonSunElongation:
    def test_elongation_in_range(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        t_arr = np.linspace(start_jd, start_jd + 7, 10)
        elong = _moon_sun_elongation(t_arr)
        assert elong.shape == (10,)
        assert all(0.0 <= e < 360.0 for e in elong)

    def test_phase_bucket(self):
        # 0° elongation → new moon (bucket 0)
        # 90° → first quarter (bucket 1)
        # 180° → full moon (bucket 2)
        # 270° → last quarter (bucket 3)
        elong = np.array([10.0, 95.0, 185.0, 275.0])
        buckets = _phase_bucket(elong)
        assert list(buckets) == [0, 1, 2, 3]


class TestBodyLongitudes:
    def test_sun_lon_in_range(self):
        jd = np.array([_datetime_to_jd(WINDOW_START)])
        lons = _body_lons("sun", jd)
        assert 0.0 <= lons[0] < 360.0

    def test_vectorized(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        jd_arr = np.linspace(start_jd, start_jd + 30, 30)
        lons = _body_lons("jupiter", jd_arr)
        assert lons.shape == (30,)
        assert all(0.0 <= lon < 360.0 for lon in lons)

    def test_sun_moves_forward(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        jd_arr = np.array([start_jd, start_jd + 10.0])
        lons = _body_lons("sun", jd_arr)
        # Sun moves ~1°/day eastward (ignoring wrap-around)
        diff = (lons[1] - lons[0] + 360) % 360
        assert 5.0 < diff < 15.0


class TestBodyDirections:
    def test_jupiter_direction(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        jd_arr = np.array([start_jd])
        dirs = _body_directions("jupiter", jd_arr)
        assert dirs[0] in (-1, 1)

    def test_retrograde_detection(self):
        # Mercury is retrograde Jul 10 2026 (between Jun 29 RX and Jul 23 D stations)
        mid_rx = _datetime_to_jd(MERCURY_MID_RX)
        dirs = _body_directions("mercury", np.array([mid_rx]))
        assert dirs[0] == -1, "Mercury should be retrograde on 2026-07-10"


# ── Integration tests (require de421.bsp, no network) ────────────────────────


class TestStations:
    def test_mercury_station_in_2026_summer(self):
        """Mercury stations retrograde Jun 29 and direct Jul 23, 2026."""
        start_jd = _datetime_to_jd(MERCURY_RX_START)
        end_jd = _datetime_to_jd(MERCURY_RX_END)
        stations = _find_stations_skyfield("mercury", start_jd, end_jd)
        # Should find at least one station (RX around Jul 18)
        assert len(stations) >= 1
        # First station should be a retrograde station
        rx_stations = [s for s in stations if s[1] is True]
        assert len(rx_stations) >= 1

    def test_station_within_range(self):
        start_jd = _datetime_to_jd(MERCURY_RX_START)
        end_jd = _datetime_to_jd(MERCURY_RX_END)
        stations = _find_stations_skyfield("mercury", start_jd, end_jd)
        for jd, _ in stations:
            assert start_jd <= jd <= end_jd

    def test_no_moon_stations(self):
        # Moon is not in _STATION_BODIES — this tests external code, but we can
        # verify that scanning "sun" gives no stations either (Sun doesn't retrograde)
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        stations = _find_stations_skyfield("sun", start_jd, end_jd)
        assert len(stations) == 0


class TestIngresses:
    def test_moon_makes_multiple_ingresses_in_a_month(self):
        """Moon changes sign ~13 times per month."""
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        ingresses = _find_ingresses_skyfield("moon", start_jd, end_jd, "realsky")
        assert len(ingresses) >= 10
        assert len(ingresses) <= 16  # at most ~13 per month

    def test_ingress_times_ordered(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        ingresses = _find_ingresses_skyfield("moon", start_jd, end_jd, "realsky")
        jds = [jd for jd, _ in ingresses]
        assert jds == sorted(jds)

    def test_ingress_sign_indices_valid(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        ingresses = _find_ingresses_skyfield("moon", start_jd, end_jd, "realsky")
        for _, sign_idx in ingresses:
            assert 0 <= sign_idx <= 12

    def test_sun_ingresses_fewer_than_moon(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        moon_ingresses = _find_ingresses_skyfield("moon", start_jd, end_jd, "realsky")
        sun_ingresses = _find_ingresses_skyfield("sun", start_jd, end_jd, "realsky")
        # Moon changes sign ~13x/month; Sun changes ~1x/month
        assert len(sun_ingresses) <= 2
        assert len(moon_ingresses) > len(sun_ingresses)


class TestMoonPhases:
    def test_finds_four_phases_per_month(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        phases = _find_moon_phases(start_jd, end_jd)
        # A calendar month should have 3–5 lunar phase milestones
        assert 3 <= len(phases) <= 5

    def test_phase_buckets_valid(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        phases = _find_moon_phases(start_jd, end_jd)
        for _, bucket in phases:
            assert 0 <= bucket <= 3

    def test_phases_in_chronological_order(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        phases = _find_moon_phases(start_jd, end_jd)
        jds = [jd for jd, _ in phases]
        assert jds == sorted(jds)

    def test_phase_buckets_cycle(self):
        """Phase buckets should follow the cycle 0→1→2→3→0→…"""
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        phases = _find_moon_phases(start_jd, end_jd)
        buckets = [b for _, b in phases]
        for i in range(1, len(buckets)):
            expected = (buckets[i - 1] + 1) % 4
            assert buckets[i] == expected, (
                f"Phase sequence broken at index {i}: "
                f"{buckets[i - 1]} → {buckets[i]}, expected {expected}"
            )


class TestVoC:
    def test_finds_voc_windows(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        windows = _find_voc_windows(start_jd, end_jd, "realsky")
        # A month should have ~13 VoC windows
        assert len(windows) >= 8

    def test_voc_window_order(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        windows = _find_voc_windows(start_jd, end_jd, "realsky")
        starts = [v[0] for v in windows]
        assert starts == sorted(starts)

    def test_voc_start_before_end(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        windows = _find_voc_windows(start_jd, end_jd, "realsky")
        for voc_start, voc_end, _ in windows:
            assert voc_start <= voc_end

    def test_voc_entering_sign_is_string(self):
        start_jd = _datetime_to_jd(WINDOW_START)
        end_jd = _datetime_to_jd(WINDOW_END)
        windows = _find_voc_windows(start_jd, end_jd, "realsky")
        for _, _, entering in windows:
            assert isinstance(entering, str)
            assert len(entering) > 0


class TestExactAspects:
    def test_finds_some_aspects_in_year(self):
        """A full year should contain multiple exact outer-planet aspects."""
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 12, 31, tzinfo=timezone.utc)
        start_jd = _datetime_to_jd(start)
        end_jd = _datetime_to_jd(end)
        aspects = _find_exact_aspects(start_jd, end_jd)
        assert len(aspects) > 0

    def test_aspect_tuple_structure(self):
        start_jd = _datetime_to_jd(datetime(2026, 1, 1, tzinfo=timezone.utc))
        end_jd = _datetime_to_jd(datetime(2026, 12, 31, tzinfo=timezone.utc))
        aspects = _find_exact_aspects(start_jd, end_jd)
        for jd, body_a, body_b, name, symbol in aspects:
            assert isinstance(jd, float)
            assert isinstance(body_a, str)
            assert isinstance(body_b, str)
            assert isinstance(name, str)
            assert isinstance(symbol, str)

    def test_aspects_in_range(self):
        start_jd = _datetime_to_jd(datetime(2026, 1, 1, tzinfo=timezone.utc))
        end_jd = _datetime_to_jd(datetime(2026, 12, 31, tzinfo=timezone.utc))
        aspects = _find_exact_aspects(start_jd, end_jd)
        for jd, _, _, _, _ in aspects:
            assert start_jd <= jd <= end_jd


class TestSkyEvents:
    def test_sky_events_returns_sorted_list(self):
        events = sky_events(WINDOW_START, WINDOW_END)
        whens = [e.when for e in events]
        assert whens == sorted(whens)

    def test_sky_event_types_valid(self):
        valid_types = {
            "retrograde_station",
            "direct_station",
            "ingress",
            "moon_new",
            "moon_first_quarter",
            "moon_full",
            "moon_last_quarter",
            "voc_start",
            "voc_end",
            "exact_aspect",
        }
        events = sky_events(WINDOW_START, WINDOW_END)
        for e in events:
            assert e.event_type in valid_types, f"Unknown event type: {e.event_type}"

    def test_sky_events_aware_utc(self):
        events = sky_events(WINDOW_START, WINDOW_END)
        for e in events:
            assert e.when.tzinfo is not None

    def test_sky_events_require_aware_datetimes(self):
        with pytest.raises(ValueError):
            sky_events(
                datetime(2026, 7, 1),  # naive — should raise
                WINDOW_END,
            )

    def test_sky_events_include_flags(self):
        events_no_stations = sky_events(
            WINDOW_START, WINDOW_END, include_stations=False
        )
        events_no_ingresses = sky_events(
            WINDOW_START, WINDOW_END, include_ingresses=False
        )
        all_events = sky_events(WINDOW_START, WINDOW_END)

        station_types = {"retrograde_station", "direct_station"}
        assert not any(e.event_type in station_types for e in events_no_stations)
        assert not any(e.event_type == "ingress" for e in events_no_ingresses)
        assert len(all_events) >= len(events_no_stations)

    def test_sky_events_body_symbol_populated(self):
        events = sky_events(WINDOW_START, WINDOW_END)
        # Events should have non-empty body_symbol for known bodies
        for e in events:
            if e.event_type != "exact_aspect":
                assert e.body_symbol, (
                    f"Missing body_symbol for {e.body} ({e.event_type})"
                )


class TestDisplayTables:
    def test_body_display_covers_all_skyfield_targets(self):
        from hoshi.ephemeris import SKYFIELD_TARGETS

        for key in SKYFIELD_TARGETS:
            assert key in BODY_DISPLAY

    def test_sign_symbol_covers_all_iau_signs(self):
        from hoshi.zodiac import IAU

        for sign in IAU:
            assert sign.name in SIGN_SYMBOL, f"Missing sign symbol for {sign.name}"

    def test_sky_event_ordering(self):
        """SkyEvents should sort by when (UTC)."""
        e1 = SkyEvent(
            when=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
            event_type="ingress",
            body="Moon",
        )
        e2 = SkyEvent(
            when=datetime(2026, 7, 2, 6, 0, tzinfo=timezone.utc),
            event_type="moon_full",
            body="Moon",
        )
        assert e1 < e2
        assert sorted([e2, e1]) == [e1, e2]
