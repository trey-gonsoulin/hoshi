"""Tests for planetary return (cycle completion) computation."""

from datetime import datetime, timezone

from hoshi.chart import Chart
from hoshi.cycles import (
    CycleReturn,
    ORBITAL_PERIODS,
    format_period,
    next_cycles,
)
from hoshi.store import ChartInput


_FROM_DT = datetime(2026, 1, 1, tzinfo=timezone.utc)

# A natal chart with a modern birth date (within DE421 ephemeris range 1899-2053).
_CI = ChartInput(
    name="test",
    date="1990-06-15",
    time="12:00",
    tz="UTC",
    lat=40.7,
    lon=-74.0,
)


def _chart() -> Chart:
    return Chart.from_input(_CI)


class TestOrbitalPeriods:
    def test_sun_period_is_roughly_one_year(self):
        assert 360 < ORBITAL_PERIODS["sun"] < 367

    def test_moon_period_is_roughly_27_days(self):
        assert 27 < ORBITAL_PERIODS["moon"] < 28

    def test_saturn_period_in_expected_range(self):
        # ~29.5 years in days
        assert 10_500 < ORBITAL_PERIODS["saturn"] < 11_000


class TestFormatPeriod:
    def test_days_under_one_year(self):
        assert format_period(88) == "88d"

    def test_years_for_long_periods(self):
        label = format_period(365.25)
        assert "y" in label

    def test_nan_returns_dash(self):
        import math

        assert format_period(math.nan) == "—"


class TestNextCycles:
    def test_returns_one_entry_per_planet(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        assert len(results) == len(chart.planets)

    def test_all_results_are_cycle_return(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        for r in results:
            assert isinstance(r, CycleReturn)

    def test_skyfield_bodies_have_exact_dates(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        skyfield_ids = {"sun", "moon", "mercury", "venus", "mars", "jupiter"}
        for r in results:
            if r.body_pid in skyfield_ids:
                assert r.available, f"{r.body_pid} should be available"
                assert len(r.exact) >= 1, f"{r.body_pid} should have at least one return date"

    def test_horizons_bodies_not_available(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        horizons_ids = {"chiron", "ceres", "eris"}
        for r in results:
            if r.body_pid in horizons_ids:
                assert not r.available
                assert r.note is not None
                assert len(r.exact) == 0

    def test_return_dates_are_after_from_dt(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        for r in results:
            if r.available and r.exact:
                for dt in r.exact:
                    assert dt > _FROM_DT, (
                        f"{r.body_pid} return {dt} should be after {_FROM_DT}"
                    )

    def test_return_dates_are_utc(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        for r in results:
            for dt in r.exact:
                assert dt.tzinfo is not None

    def test_sun_return_within_one_year(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        sun = next(r for r in results if r.body_pid == "sun")
        assert sun.available
        assert len(sun.exact) == 1
        # Solar return should be within ~1 year of from_dt
        delta = sun.exact[0] - _FROM_DT
        assert delta.days < 400, f"Solar return too far: {delta.days} days"

    def test_moon_return_within_one_month(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        moon = next(r for r in results if r.body_pid == "moon")
        assert moon.available
        assert len(moon.exact) >= 1
        # Lunar return should be within ~28 days
        delta = moon.exact[0] - _FROM_DT
        assert delta.days < 30, f"Lunar return too far: {delta.days} days"

    def test_natal_sign_is_set(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        for r in results:
            assert r.natal_sign, f"{r.body_pid} should have natal_sign"

    def test_period_days_is_positive(self):
        chart = _chart()
        results = next_cycles(chart, _FROM_DT)
        for r in results:
            # period_days may be nan for unknown bodies, skip those
            if r.available:
                assert r.period_days > 0, f"{r.body_pid} period should be positive"

    def test_mode_affects_natal_sign(self):
        chart = _chart()
        results_realsky = next_cycles(chart, _FROM_DT, mode="realsky")
        results_tropical = next_cycles(chart, _FROM_DT, mode="tropical")
        # Signs may differ between modes; just ensure both return valid data
        assert len(results_realsky) == len(results_tropical)
        for r in results_tropical:
            assert r.natal_sign  # tropical sign is always set
