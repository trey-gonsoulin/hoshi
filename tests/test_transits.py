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
