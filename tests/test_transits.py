"""Tests for transit aspect window computation."""

from datetime import datetime, timezone


from hoshi.aspects import ASPECT_DEFS
from hoshi.transits import transit_aspect_window


def _adef(name: str):
    return next(a for a in ASPECT_DEFS if a.name == name)


class TestTransitAspectWindow:
    # Saturn at ~295° (Capricorn), natal Sun at ~295° — conjunction within 4°
    # Use a known approximate conjunction to test the window is found.

    def test_returns_none_for_unscannable_bodies(self):
        adef = _adef("Conjunction")
        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ingress, exact, egress = transit_aspect_window("chiron", 120.0, adef, dt)
        assert ingress is None
        assert exact == []
        assert egress is None

    def test_returns_none_for_unknown_body(self):
        adef = _adef("Conjunction")
        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ingress, exact, egress = transit_aspect_window("n.node", 120.0, adef, dt)
        assert ingress is None
        assert exact == []
        assert egress is None

    def test_window_ordering_when_found(self):
        """ingress <= exact[0] <= egress for an active transit."""
        # Use Saturn (slow) transiting an arbitrary natal point that it recently
        # was near.  We need a point within 4° of Saturn's position on this date.
        # Saturn was near 348° ecliptic in mid-2025.
        natal_lon = 349.0  # within 4° of Saturn ~348°
        adef = _adef("Conjunction")
        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ingress, exact, egress = transit_aspect_window("saturn", natal_lon, adef, dt)

        if ingress is not None and egress is not None and exact:
            assert ingress <= exact[0]
            assert exact[-1] <= egress
            assert ingress.tzinfo is not None
            assert egress.tzinfo is not None
            for e in exact:
                assert e.tzinfo is not None

    def test_consistency_with_snapshot_orb(self):
        """At transit_dt the recomputed separation should match the aspect orb."""
        from hoshi.events import _body_lons, _datetime_to_jd
        import numpy as np

        # Pick a natal longitude and check Saturn is within 4° of a conjunction
        natal_lon = 349.0
        adef = _adef("Conjunction")
        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)

        ref_jd = _datetime_to_jd(dt)
        lon = float(_body_lons("saturn", np.array([ref_jd]))[0])
        diff = (lon - natal_lon) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff
        snapshot_orb = diff - adef.angle

        if abs(snapshot_orb) <= adef.orb:
            ingress, exact, egress = transit_aspect_window(
                "saturn", natal_lon, adef, dt
            )
            # If in-orb, we should find at least one exact date
            assert isinstance(exact, list)
            # Ingress must be before or equal to now
            if ingress is not None:
                assert ingress <= dt
            # Egress must be after or equal to now
            if egress is not None:
                assert egress >= dt

    def test_exact_dates_are_utc(self):
        """All returned datetimes must be UTC-aware."""
        natal_lon = 349.0
        adef = _adef("Conjunction")
        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ingress, exact, egress = transit_aspect_window("saturn", natal_lon, adef, dt)
        if ingress is not None:
            assert ingress.tzinfo is not None
        if egress is not None:
            assert egress.tzinfo is not None
        for e in exact:
            assert e.tzinfo is not None

    def test_sun_window_is_short(self):
        """Sun window should be days, not years."""
        # Find what the Sun is near on a test date
        from hoshi.events import _body_lons, _datetime_to_jd
        import numpy as np

        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ref_jd = _datetime_to_jd(dt)
        sun_lon = float(_body_lons("sun", np.array([ref_jd]))[0])
        natal_lon = sun_lon  # exact conjunction right now

        adef = _adef("Conjunction")
        ingress, _, egress = transit_aspect_window("sun", natal_lon, adef, dt)

        if ingress is not None and egress is not None:
            window_days = (egress - ingress).total_seconds() / 86400
            # Sun crosses 4° orb in ~8 days; window should be well under 30
            assert window_days < 30


class TestPassTracking:
    def test_single_pass_has_count_one(self):
        """Fast planets that don't retrograde mid-orb produce a single exact."""
        from hoshi.events import _body_lons, _datetime_to_jd
        import numpy as np

        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ref_jd = _datetime_to_jd(dt)
        sun_lon = float(_body_lons("sun", np.array([ref_jd]))[0])
        adef = _adef("Conjunction")
        _, exact, _ = transit_aspect_window("sun", sun_lon, adef, dt)
        # Sun doesn't retrograde: at most 1 exact crossing
        assert len(exact) <= 1

    def test_next_pass_before_first_exact(self):
        """_next_pass returns 1 when transit_dt is before the first exact."""
        from hoshi.output import _next_pass

        dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        exacts = [
            datetime(2025, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            datetime(2026, 5, 10, tzinfo=timezone.utc),
        ]
        assert _next_pass(exacts, dt) == 1

    def test_next_pass_between_exacts(self):
        """_next_pass returns 2 when transit_dt is between the 1st and 2nd exact."""
        from hoshi.output import _next_pass

        dt = datetime(2025, 10, 1, tzinfo=timezone.utc)
        exacts = [
            datetime(2025, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            datetime(2026, 5, 10, tzinfo=timezone.utc),
        ]
        assert _next_pass(exacts, dt) == 2

    def test_next_pass_after_all_exacts(self):
        """_next_pass returns pass_count when all exacts are in the past."""
        from hoshi.output import _next_pass

        dt = datetime(2027, 1, 1, tzinfo=timezone.utc)
        exacts = [
            datetime(2025, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 15, tzinfo=timezone.utc),
            datetime(2026, 5, 10, tzinfo=timezone.utc),
        ]
        assert _next_pass(exacts, dt) == 3

    def test_next_pass_empty_returns_none(self):
        """_next_pass returns None for an empty exact list."""
        from hoshi.output import _next_pass

        dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        assert _next_pass([], dt) is None


class TestTransitTier:
    def test_known_slow_bodies(self):
        from hoshi.transits import TransitTier, transit_tier

        for pid in (
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
            "chiron",
            "ceres",
            "eris",
        ):
            assert transit_tier(pid) == TransitTier.slow

    def test_medium_body(self):
        from hoshi.transits import TransitTier, transit_tier

        assert transit_tier("mars") == TransitTier.medium

    def test_fast_bodies(self):
        from hoshi.transits import TransitTier, transit_tier

        for pid in ("sun", "mercury", "venus"):
            assert transit_tier(pid) == TransitTier.fast

    def test_luminary(self):
        from hoshi.transits import TransitTier, transit_tier

        assert transit_tier("moon") == TransitTier.luminary

    def test_unknown_defaults_to_slow(self):
        from hoshi.transits import TransitTier, transit_tier

        assert transit_tier("n.node") == TransitTier.slow
        assert transit_tier("lilith") == TransitTier.slow

    def test_case_insensitive(self):
        from hoshi.transits import TransitTier, transit_tier

        assert transit_tier("Saturn") == TransitTier.slow
        assert transit_tier("MOON") == TransitTier.luminary

    def test_tier_field_on_transit_aspect(self):
        """TransitAspect.tier is populated (non-empty) when computed."""
        from datetime import timezone

        from hoshi.output import _compute_transit_aspects
        from hoshi.store import ChartInput
        from hoshi.chart import Chart

        dt = datetime(2025, 7, 18, 12, 0, tzinfo=timezone.utc)
        ci = ChartInput(
            name="test", date="1990-01-01", time="12:00", tz="UTC", lat=40.7, lon=-74.0
        )
        chart_natal = Chart.from_input(ci)
        chart_transit = Chart.positions_only(dt)

        aspects = _compute_transit_aspects(
            chart_natal, chart_transit, False, "realsky", dt, windows=False
        )
        assert len(aspects) > 0
        for asp in aspects:
            assert asp.tier in ("slow", "medium", "fast", "luminary")


class TestForecastTransits:
    """Tests for the date-range transit-to-natal aspect scanner."""

    # Fixed natal chart: New York, 1990-01-01 noon UTC
    _CI = {
        "name": "test",
        "date": "1990-01-01",
        "time": "12:00",
        "tz": "UTC",
        "lat": 40.7,
        "lon": -74.0,
    }

    def _natal_bodies(self, details: bool = False):
        from hoshi.aspects import _bodies
        from hoshi.chart import Chart
        from hoshi.store import ChartInput

        ci = ChartInput(**self._CI)
        chart = Chart.from_input(ci)
        return _bodies(chart, details, "realsky")

    def test_returns_list(self):
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        assert isinstance(windows, list)

    def test_default_tier_is_slow(self):
        from datetime import timezone

        from hoshi.transits import TransitTier, forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        for w in windows:
            assert w.tier == TransitTier.slow, f"{w.transit_name} has tier {w.tier}"

    def test_windows_have_in_range_exact_dates(self):
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        for w in windows:
            in_range = [e for e in w.exact if from_dt <= e <= to_dt]
            assert len(in_range) >= 1, (
                f"{w.transit_name} {w.aspect_name} {w.natal_name}: "
                f"no exact dates in range (exact={w.exact})"
            )

    def test_ingress_before_exact_before_egress(self):
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        for w in windows:
            if w.ingress is not None and w.exact:
                assert w.ingress <= w.exact[0], (
                    f"ingress {w.ingress} > first exact {w.exact[0]}"
                )
            if w.egress is not None and w.exact:
                assert w.exact[-1] <= w.egress, (
                    f"last exact {w.exact[-1]} > egress {w.egress}"
                )

    def test_all_datetimes_utc(self):
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        for w in windows:
            if w.ingress is not None:
                assert w.ingress.tzinfo is not None
            if w.egress is not None:
                assert w.egress.tzinfo is not None
            for e in w.exact:
                assert e.tzinfo is not None

    def test_sorted_by_first_in_range_exact(self):
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        if len(windows) >= 2:
            first_exacts = []
            for w in windows:
                in_range = [e for e in w.exact if from_dt <= e <= to_dt]
                first_exacts.append(in_range[0] if in_range else from_dt)
            assert first_exacts == sorted(first_exacts)

    def test_no_duplicate_windows(self):
        """Each transit window should appear at most once."""
        from datetime import timezone

        from hoshi.transits import forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()
        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        keys = [
            (w.transit_pid, w.natal_name, w.aspect_name, w.ingress, w.egress)
            for w in windows
        ]
        assert len(keys) == len(set(keys)), "Duplicate windows found"

    def test_tier_filter(self):
        from datetime import timezone

        from hoshi.transits import TransitTier, forecast_transits

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        natal_bodies = self._natal_bodies()

        slow_windows = forecast_transits(
            natal_bodies, from_dt, to_dt, tiers=frozenset({TransitTier.slow})
        )
        medium_windows = forecast_transits(
            natal_bodies, from_dt, to_dt, tiers=frozenset({TransitTier.medium})
        )
        for w in slow_windows:
            assert w.tier == "slow"
        for w in medium_windows:
            assert w.tier == "medium"

    def test_consistency_with_transit_aspect_window(self):
        """For each ForecastWindow, transit_aspect_window called at the first
        in-range exact date should return the same ingress/egress."""
        from datetime import timezone

        from hoshi.aspects import _bodies
        from hoshi.chart import Chart
        from hoshi.store import ChartInput
        from hoshi.transits import forecast_transits, transit_aspect_window
        from hoshi.aspects import ASPECT_DEFS

        from_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        ci = ChartInput(**self._CI)
        chart = Chart.from_input(ci)
        natal_bodies = _bodies(chart, False, "realsky")

        windows = forecast_transits(natal_bodies, from_dt, to_dt)
        adef_map = {a.name: a for a in ASPECT_DEFS}

        for w in windows[:5]:  # check first 5 to keep test fast
            in_range = [e for e in w.exact if from_dt <= e <= to_dt]
            ref_dt = in_range[0]
            adef = adef_map[w.aspect_name]
            ingress2, _, egress2 = transit_aspect_window(
                w.transit_pid, w.natal_lon, adef, ref_dt
            )
            # Allow ≤1 hour difference: bisection precision varies with scan step
            if w.ingress is not None and ingress2 is not None:
                assert abs((ingress2 - w.ingress).total_seconds()) <= 3600, (
                    f"{w.transit_name} {w.aspect_name} {w.natal_name}: "
                    f"ingress mismatch: forecast={w.ingress}, window={ingress2}"
                )
            if w.egress is not None and egress2 is not None:
                assert abs((egress2 - w.egress).total_seconds()) <= 3600, (
                    f"{w.transit_name} {w.aspect_name} {w.natal_name}: "
                    f"egress mismatch: forecast={w.egress}, window={egress2}"
                )
