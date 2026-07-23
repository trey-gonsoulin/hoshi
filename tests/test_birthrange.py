"""Tests for birth date range estimation."""

from datetime import datetime, timezone

import pytest

from hoshi.birthrange import (
    BirthDateRange,
    Constraint,
    SCANNABLE_ANGLES,
    SCANNABLE_PLANETS,
    _min_sign_width,
    _step_hours,
    find_birth_date_ranges,
    valid_signs,
)
from hoshi.zodiac import ZodiacMode


class TestValidSigns:
    def test_realsky_includes_ophiuchus(self):
        signs = valid_signs(ZodiacMode.realsky)
        assert "Ophiuchus" in signs
        assert len(signs) == 13

    def test_tropical_excludes_ophiuchus(self):
        signs = valid_signs(ZodiacMode.tropical)
        assert "Ophiuchus" not in signs
        assert len(signs) == 12

    def test_vedic_excludes_ophiuchus(self):
        signs = valid_signs(ZodiacMode.vedic)
        assert "Ophiuchus" not in signs
        assert len(signs) == 12


class TestMinSignWidth:
    def test_realsky_narrowest_is_scorpio(self):
        # Scorpio in realsky IAU table is ~6.71°
        width = _min_sign_width(ZodiacMode.realsky)
        assert 6.0 < width < 8.0

    def test_tropical_is_30(self):
        assert _min_sign_width(ZodiacMode.tropical) == 30.0

    def test_vedic_is_30(self):
        assert _min_sign_width(ZodiacMode.vedic) == 30.0


class TestStepHours:
    def test_moon_realsky_gives_small_step(self):
        # Moon in realsky: ~1h step (narrowest sign / fastest planet / 10 samples)
        step = _step_hours(["moon"], ZodiacMode.realsky)
        assert step <= 2.0

    def test_pluto_gives_large_step(self):
        step = _step_hours(["pluto"], ZodiacMode.tropical)
        assert step > 24.0

    def test_mixed_uses_fastest(self):
        # Moon + Saturn: step should be small (Moon dominates)
        step_mixed = _step_hours(["moon", "saturn"], ZodiacMode.tropical)
        step_saturn_only = _step_hours(["saturn"], ZodiacMode.tropical)
        assert step_mixed < step_saturn_only

    def test_floor_is_one_hour(self):
        step = _step_hours(["moon"], ZodiacMode.realsky)
        assert step >= 1.0

    def test_angle_body_returns_fixed_one_minute(self):
        step = _step_hours(["asc"], ZodiacMode.realsky)
        assert step == pytest.approx(1.0 / 60.0)

    def test_angle_overrides_planet_step(self):
        # Even combined with a slow planet, angle drives the step to 1 min.
        step = _step_hours(["saturn", "asc"], ZodiacMode.tropical)
        assert step == pytest.approx(1.0 / 60.0)

    def test_ceiling_is_168_hours(self):
        step = _step_hours(["pluto"], ZodiacMode.realsky)
        assert step <= 168.0


class TestFindBirthDateRanges:
    def test_sun_in_aries_tropical_finds_windows(self):
        # Sun is in tropical Aries ~Mar 20 – Apr 19 every year.
        # Search one year and expect at least one window.
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        end = datetime(2000, 12, 31, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("sun", "Aries")],
            start,
            end,
            ZodiacMode.tropical,
        )
        assert len(windows) >= 1
        # The window should fall around March–April
        w = windows[0]
        assert w.start.month in (3, 4)
        assert w.end.month in (3, 4)

    def test_windows_are_ordered(self):
        start = datetime(1990, 1, 1, tzinfo=timezone.utc)
        end = datetime(1991, 12, 31, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("sun", "Leo")],
            start,
            end,
            ZodiacMode.tropical,
        )
        for i in range(len(windows) - 1):
            assert windows[i].end <= windows[i + 1].start

    def test_impossible_constraints_return_empty(self):
        # Sun can't be in both Aries and Taurus simultaneously
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        end = datetime(2000, 12, 31, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("sun", "Aries"), Constraint("sun", "Taurus")],
            start,
            end,
            ZodiacMode.tropical,
        )
        assert windows == []

    def test_duration_is_positive(self):
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        end = datetime(2000, 12, 31, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("sun", "Cancer")],
            start,
            end,
            ZodiacMode.tropical,
        )
        assert all(w.duration_days > 0 for w in windows)

    def test_requires_at_least_one_constraint(self):
        with pytest.raises(ValueError, match="At least one constraint"):
            find_birth_date_ranges(
                [],
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2000, 12, 31, tzinfo=timezone.utc),
            )

    def test_rejects_horizons_bodies(self):
        with pytest.raises(ValueError, match="not a scannable body"):
            find_birth_date_ranges(
                [Constraint("chiron", "Aries")],
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2000, 12, 31, tzinfo=timezone.utc),
            )

    def test_rejects_invalid_sign_for_mode(self):
        with pytest.raises(ValueError, match="not a valid sign"):
            find_birth_date_ranges(
                [Constraint("sun", "Ophiuchus")],
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2000, 12, 31, tzinfo=timezone.utc),
                ZodiacMode.tropical,
            )

    def test_empty_search_window_returns_empty(self):
        start = datetime(2051, 1, 1, tzinfo=timezone.utc)
        end = datetime(2052, 1, 1, tzinfo=timezone.utc)
        # Entirely outside DE421 coverage — clipped to empty window
        windows = find_birth_date_ranges(
            [Constraint("sun", "Aries")],
            start,
            end,
            ZodiacMode.tropical,
        )
        assert windows == []

    def test_scannable_planets_set(self):
        assert "sun" in SCANNABLE_PLANETS
        assert "moon" in SCANNABLE_PLANETS
        assert "chiron" not in SCANNABLE_PLANETS
        assert "ceres" not in SCANNABLE_PLANETS
        assert "eris" not in SCANNABLE_PLANETS

    def test_birth_date_range_duration(self):
        start = datetime(2000, 3, 21, tzinfo=timezone.utc)
        end = datetime(2000, 4, 19, tzinfo=timezone.utc)
        r = BirthDateRange(start=start, end=end)
        assert r.duration_days == pytest.approx(29.0, abs=1.0)


class TestAngleConstraints:
    # New York: lat=40.71, lon=-74.01
    LAT = 40.71
    LON = -74.01

    def test_scannable_angles_set(self):
        assert "asc" in SCANNABLE_ANGLES
        assert "mc" in SCANNABLE_ANGLES
        assert "ic" in SCANNABLE_ANGLES
        assert "dsc" in SCANNABLE_ANGLES

    def test_batch_angle_lons_matches_scalar(self):
        """Oracle test: vectorized result must equal Angles.compute at each time."""
        from hoshi.houses import Angles, batch_angle_lons

        times = [
            datetime(2000, 6, 15, h, 0, tzinfo=timezone.utc) for h in range(0, 24, 3)
        ]
        result = batch_angle_lons(times, self.LAT, self.LON)
        for i, dt in enumerate(times):
            scalar = Angles.compute(dt, self.LAT, self.LON)
            assert result["asc"][i] == pytest.approx(scalar.asc, abs=0.001)
            assert result["mc"][i] == pytest.approx(scalar.mc, abs=0.001)
            assert result["ic"][i] == pytest.approx((scalar.mc + 180) % 360, abs=0.001)
            assert result["dsc"][i] == pytest.approx(
                (scalar.asc + 180) % 360, abs=0.001
            )

    def test_missing_lat_lon_raises(self):
        with pytest.raises(ValueError, match="lat and lon are required"):
            find_birth_date_ranges(
                [Constraint("asc", "Aries")],
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2000, 6, 1, tzinfo=timezone.utc),
                ZodiacMode.tropical,
            )

    def test_span_too_large_raises(self):
        with pytest.raises(ValueError, match="too large"):
            find_birth_date_ranges(
                [Constraint("asc", "Aries")],
                datetime(2000, 1, 1, tzinfo=timezone.utc),
                datetime(2010, 1, 1, tzinfo=timezone.utc),
                ZodiacMode.tropical,
                lat=self.LAT,
                lon=self.LON,
            )

    def test_asc_tropical_finds_windows(self):
        # ASC passes through each tropical sign ~2h/day — many windows over a week.
        start = datetime(2000, 6, 1, tzinfo=timezone.utc)
        end = datetime(2000, 6, 8, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("asc", "Aries")],
            start,
            end,
            ZodiacMode.tropical,
            lat=self.LAT,
            lon=self.LON,
        )
        assert len(windows) >= 1
        for w in windows:
            assert w.duration_days < 1  # each window is ~2h, well under 1 day
            assert w.start >= start
            assert w.end <= end

    def test_sun_and_asc_tropical(self):
        # Sun in Cancer (late June–late July) + ASC in Aries.
        # Narrow window to keep the scan fast.
        start = datetime(2000, 7, 1, tzinfo=timezone.utc)
        end = datetime(2000, 7, 7, tzinfo=timezone.utc)
        windows = find_birth_date_ranges(
            [Constraint("sun", "Cancer"), Constraint("asc", "Aries")],
            start,
            end,
            ZodiacMode.tropical,
            lat=self.LAT,
            lon=self.LON,
        )
        assert len(windows) >= 1
        for w in windows:
            assert w.duration_days < 1  # ASC window dominates duration
