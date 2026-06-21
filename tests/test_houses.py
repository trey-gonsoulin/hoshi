from datetime import datetime, timezone

import pytest

from hoshi.houses import (
    FIXED_ARCS,
    Angles,
    arc13_cusps,
    equal_cusps,
    house_13_arc,
    house_from_cusps,
    porphyry_cusps,
    placidus_cusps,
)


class TestEqualCusps:
    def test_asc_zero(self):
        cusps = equal_cusps(0.0)
        assert len(cusps) == 12
        for i, c in enumerate(cusps):
            assert c == pytest.approx(i * 30.0)

    def test_offset(self):
        cusps = equal_cusps(45.0)
        assert cusps[0] == pytest.approx(45.0)
        assert cusps[1] == pytest.approx(75.0)

    def test_wraps(self):
        cusps = equal_cusps(350.0)
        assert cusps[0] == pytest.approx(350.0)
        assert cusps[1] == pytest.approx(20.0)

    def test_always_twelve(self):
        for asc in [0, 90, 180, 270, 350]:
            assert len(equal_cusps(asc)) == 12


class TestPorphyryCusps:
    def test_cardinal_cusps_pinned(self):
        angles = Angles(
            asc=10.0, mc=280.0, ic=100.0, dsc=190.0, vertex=200.0, antivertex=20.0
        )
        cusps = porphyry_cusps(angles)
        assert cusps[0] == pytest.approx(10.0)  # asc
        assert cusps[3] == pytest.approx(100.0)  # ic
        assert cusps[6] == pytest.approx(190.0)  # dsc
        assert cusps[9] == pytest.approx(280.0)  # mc

    def test_twelve_cusps(self):
        angles = Angles(
            asc=0.0, mc=270.0, ic=90.0, dsc=180.0, vertex=200.0, antivertex=20.0
        )
        cusps = porphyry_cusps(angles)
        assert len(cusps) == 12

    def test_trisection(self):
        angles = Angles(
            asc=0.0, mc=270.0, ic=90.0, dsc=180.0, vertex=200.0, antivertex=20.0
        )
        cusps = porphyry_cusps(angles)
        # Q1: asc(0) to ic(90), trisected at 30 and 60
        assert cusps[1] == pytest.approx(30.0)
        assert cusps[2] == pytest.approx(60.0)


class TestArc13Cusps:
    def test_length(self):
        cusps = arc13_cusps(0.0)
        assert len(cusps) == 13

    def test_first_is_asc(self):
        cusps = arc13_cusps(45.0)
        assert cusps[0] == pytest.approx(45.0)

    def test_arcs_match_fixed(self):
        cusps = arc13_cusps(0.0)
        for i in range(12):
            gap = (cusps[i + 1] - cusps[i]) % 360.0
            assert gap == pytest.approx(FIXED_ARCS[i])


class TestHouseFromCusps:
    def test_first_house(self):
        cusps = equal_cusps(0.0)
        assert house_from_cusps(15.0, cusps) == 1

    def test_last_house(self):
        cusps = equal_cusps(0.0)
        assert house_from_cusps(345.0, cusps) == 12

    def test_exact_cusp(self):
        cusps = equal_cusps(0.0)
        assert house_from_cusps(30.0, cusps) == 2

    def test_wrap(self):
        cusps = equal_cusps(350.0)
        # House 1 is 350-20; lon=5 is inside
        assert house_from_cusps(5.0, cusps) == 1

    def test_all_twelve(self):
        cusps = equal_cusps(0.0)
        for i in range(12):
            lon = i * 30.0 + 15.0
            assert house_from_cusps(lon, cusps) == i + 1


class TestHouse13Arc:
    def test_first(self):
        assert house_13_arc(0.0, 0.0) == 1

    def test_last(self):
        # Last arc starts at sum of first 12 arcs
        total_12 = sum(FIXED_ARCS[:12])
        assert house_13_arc(total_12 + 1.0, 0.0) == 13

    def test_mid(self):
        # House 2 starts at FIXED_ARCS[0] = 24.41
        assert house_13_arc(25.0, 0.0) == 2

    def test_with_offset_asc(self):
        assert house_13_arc(100.0, 100.0) == 1


class TestAnglesCompute:
    def test_ic_dsc_opposites(self, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        angles = Angles.compute(when, lat=41.88, lon=-87.65)
        assert angles.ic == pytest.approx((angles.mc + 180.0) % 360.0)
        assert angles.dsc == pytest.approx((angles.asc + 180.0) % 360.0)

    def test_naive_raises(self, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        with pytest.raises(ValueError, match="timezone-aware"):
            Angles.compute(datetime(2000, 1, 1, 12, 0), lat=0.0, lon=0.0)

    def test_angles_in_range(self, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        angles = Angles.compute(when, lat=41.88, lon=-87.65)
        for name in ("asc", "mc", "ic", "dsc", "vertex", "antivertex"):
            val = getattr(angles, name)
            assert 0.0 <= val < 360.0, f"{name}={val} out of range"


class TestPlacidus:
    def test_cardinal_cusps_pinned(self, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        angles = Angles.compute(when, lat=41.88, lon=-87.65)
        cusps = placidus_cusps(when, 41.88, -87.65, angles)
        assert len(cusps) == 12
        assert cusps[0] == pytest.approx(angles.asc)
        assert cusps[3] == pytest.approx(angles.ic)
        assert cusps[6] == pytest.approx(angles.dsc)
        assert cusps[9] == pytest.approx(angles.mc)

    def test_naive_raises(self, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        angles = Angles(asc=0, mc=270, ic=90, dsc=180, vertex=200, antivertex=20)
        with pytest.raises(ValueError, match="timezone-aware"):
            placidus_cusps(datetime(2000, 1, 1), 0.0, 0.0, angles)
