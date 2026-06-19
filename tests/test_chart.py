from datetime import datetime, timezone

import pytest

from hoshi.chart import Chart, HouseSystem, Placed
from hoshi.ephemeris import PlanetPosition
from hoshi.houses import Angles
from hoshi.points import LunarElements
from hoshi.zodiac import Placement


class TestPlacedForLongitude:
    def test_basic(self):
        p = Placed.for_longitude(45.0, ayanamsa=23.85, precession=0.0)
        assert p.lon == pytest.approx(45.0)
        assert isinstance(p.realsky, Placement)
        assert isinstance(p.tropical, Placement)
        assert isinstance(p.vedic, Placement)

    def test_tropical_matches(self):
        p = Placed.for_longitude(45.0, ayanamsa=23.85, precession=0.0)
        direct = Placement.tropical(45.0)
        assert p.tropical.name == direct.name
        assert p.tropical.deg == pytest.approx(direct.deg)

    def test_vedic_matches(self):
        p = Placed.for_longitude(45.0, ayanamsa=23.85, precession=0.0)
        direct = Placement.vedic(45.0, 23.85)
        assert p.vedic.name == direct.name
        assert p.vedic.deg == pytest.approx(direct.deg)

    def test_realsky_matches(self):
        p = Placed.for_longitude(250.0, ayanamsa=23.85, precession=0.5)
        direct = Placement.realsky(250.0, 0.5)
        assert p.realsky.name == direct.name
        assert p.realsky.deg == pytest.approx(direct.deg)


class TestChartBuild:
    @pytest.fixture
    def mock_deps(self, monkeypatch):
        fake_positions = {
            pid: PlanetPosition(lon=i * 30.0, lat=0.0, retrograde=False)
            for i, pid in enumerate([
                "sun", "moon", "mercury", "venus", "mars",
                "jupiter", "saturn", "uranus", "neptune", "pluto", "chiron",
            ])
        }
        angles = Angles(asc=0.0, mc=270.0, ic=90.0, dsc=180.0, vertex=200.0, antivertex=20.0)
        lunar = LunarElements(om=125.0, w=45.0)

        monkeypatch.setattr("hoshi.chart.positions", lambda _: fake_positions)
        monkeypatch.setattr("hoshi.chart.lahiri_ayanamsa", lambda _: 23.85)
        monkeypatch.setattr("hoshi.chart.ecliptic_precession", lambda _: 0.0)
        monkeypatch.setattr("hoshi.chart.Angles.compute", classmethod(lambda cls, *a, **kw: angles))
        monkeypatch.setattr("hoshi.chart.LunarElements.at", classmethod(lambda cls, _: lunar))
        return {"angles": angles, "lunar": lunar}

    def test_planet_count(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert len(chart.planets) == 11

    def test_angle_count(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert len(chart.angles) == 6

    def test_point_count(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert len(chart.points) == 3
        names = {p.name for p in chart.points}
        assert names == {"N.Node", "S.Node", "Lilith"}

    def test_lot_count(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert len(chart.lots) == 7

    def test_houses_in_range_porphyry(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        for p in chart.planets:
            assert 1 <= p.house <= 12

    def test_houses_in_range_arc13(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "arc13")
        for p in chart.planets:
            assert 1 <= p.house <= 13

    def test_cusps_porphyry(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert len(chart.cusps) == 12
        assert chart.house_system == "porphyry"

    def test_cusps_equal(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "equal")
        assert len(chart.cusps) == 12

    def test_cusps_arc13(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "arc13")
        assert len(chart.cusps) == 13

    def test_cusps_placidus(self, mock_deps, monkeypatch):
        monkeypatch.setattr("hoshi.houses._julian_day_ut", lambda _: 2451545.0)
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 41.88, -87.65, "placidus")
        assert len(chart.cusps) == 12
