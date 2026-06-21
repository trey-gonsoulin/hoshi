from datetime import datetime, timezone

import pytest

from hoshi.chart import BodyRef, Chart, Placed, uncertain_signs
from hoshi.ephemeris import PlanetPosition
from hoshi.houses import Angles
from hoshi.points import LunarElements
from hoshi.store import ChartInput
from hoshi.zodiac import Placement, ZodiacMode

from tests.conftest import make_angle, make_chart, make_planet, make_point


@pytest.fixture
def mock_deps(monkeypatch):
    """Stub ephemeris/Horizons deps so `Chart.build` runs offline."""
    fake_positions = {
        pid: PlanetPosition(lon=i * 30.0, lat=0.0, retrograde=False)
        for i, pid in enumerate(
            [
                "sun",
                "moon",
                "mercury",
                "venus",
                "mars",
                "jupiter",
                "saturn",
                "uranus",
                "neptune",
                "pluto",
                "chiron",
            ]
        )
    }
    angles = Angles(
        asc=0.0, mc=270.0, ic=90.0, dsc=180.0, vertex=200.0, antivertex=20.0
    )
    lunar = LunarElements(om=125.0, w=45.0)
    monkeypatch.setattr("hoshi.chart.positions", lambda _: fake_positions)
    monkeypatch.setattr("hoshi.chart.lahiri_ayanamsa", lambda _: 23.85)
    monkeypatch.setattr("hoshi.chart.ecliptic_precession", lambda _: 0.0)
    monkeypatch.setattr(
        "hoshi.chart.Angles.compute", classmethod(lambda cls, *a, **kw: angles)
    )
    monkeypatch.setattr(
        "hoshi.chart.LunarElements.at", classmethod(lambda cls, _: lunar)
    )
    return {"angles": angles, "lunar": lunar}


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

    def test_placement_selects_mode(self):
        p = Placed.for_longitude(45.0, ayanamsa=23.85, precession=0.0)
        assert p.placement("realsky") is p.realsky
        assert p.placement("tropical") is p.tropical
        assert p.placement("vedic") is p.vedic

    def test_placement_unknown_mode_raises(self):
        p = Placed.for_longitude(45.0, ayanamsa=23.85, precession=0.0)
        with pytest.raises(ValueError, match="Unknown zodiac mode"):
            p.placement("bogus")

    def test_realsky_matches(self):
        p = Placed.for_longitude(250.0, ayanamsa=23.85, precession=0.5)
        direct = Placement.realsky(250.0, 0.5)
        assert p.realsky.name == direct.name
        assert p.realsky.deg == pytest.approx(direct.deg)


class TestChartBuild:
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

    def test_build_marks_location_and_time_known(self, mock_deps):
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        chart = Chart.build(when, 0.0, 0.0, "porphyry")
        assert chart.location_known is True
        assert chart.time_known is True


class TestChartBodies:
    def _chart(self):
        return make_chart(
            planets=[make_planet("sun", 10.0, retrograde=True)],
            angles=[make_angle("asc", 0.0), make_angle("mc", 270.0)],
            points=[make_point("N.Node", 125.0), make_point("Lilith", 350.0)],
            lots=[make_point("Fortune", 50.0)],
        )

    def test_yields_every_body_with_kinds(self):
        bodies = list(self._chart().bodies())
        assert [b.kind for b in bodies] == [
            "Planet",
            "Angle",
            "Angle",
            "Node",
            "Point",
            "Lot",
        ]

    def test_labels_and_ids(self):
        by_id = {b.id: b for b in self._chart().bodies()}
        assert by_id["sun"].label == "Sun"
        assert by_id["asc"].label == "Asc"
        assert by_id["mc"].label == "MC"
        assert by_id["N.Node"].label == "N.Node"

    def test_planet_retrograde_carried(self):
        sun = self._chart().body("sun")
        assert isinstance(sun, BodyRef)
        assert sun.retrograde is True

    def test_angle_has_no_retrograde(self):
        assert self._chart().body("asc").retrograde is None

    def test_body_lookup_missing_raises(self):
        with pytest.raises(KeyError, match="No body with id"):
            self._chart().body("nope")


class TestFromInput:
    def test_location_and_time_known(self, mock_deps):
        ci = ChartInput(name="x", date="2000-01-01", time="12:00", lat=40.0, lon=-70.0)
        chart = Chart.from_input(ci)
        assert chart.location_known is True
        assert chart.time_known is True

    def test_unknown_location_uses_placeholder(self, mock_deps):
        ci = ChartInput(name="x", date="2000-01-01", time="12:00")
        chart = Chart.from_input(ci)
        assert chart.location_known is False
        assert chart.time_known is True

    def test_unknown_time(self, mock_deps):
        ci = ChartInput(name="x", date="2000-01-01", lat=40.0, lon=-70.0)
        chart = Chart.from_input(ci)
        assert chart.location_known is True
        assert chart.time_known is False


class TestUncertainSigns:
    @pytest.fixture
    def crossing(self, monkeypatch):
        # Sun crosses the Aries→Taurus boundary across the day; others stable.
        def fake_positions(when, *, include_chiron=True):
            late = when.hour >= 12
            lons = {
                "sun": 31.0 if late else 29.5,  # Taurus vs Aries (tropical)
                "moon": 100.0,
                "mercury": 100.0,
                "venus": 100.0,
                "mars": 100.0,
            }
            return {
                pid: PlanetPosition(lon=lon, lat=0.0, retrograde=False)
                for pid, lon in lons.items()
            }

        monkeypatch.setattr("hoshi.chart.positions", fake_positions)
        monkeypatch.setattr("hoshi.chart.lahiri_ayanamsa", lambda _: 23.85)
        monkeypatch.setattr("hoshi.chart.ecliptic_precession", lambda _: 0.0)

    def test_detects_crossing(self, crossing):
        ci = ChartInput(name="x", date="2000-01-01")
        assert uncertain_signs(ci, ZodiacMode.tropical) == frozenset({"sun"})

    def test_accepts_string_mode(self, crossing):
        ci = ChartInput(name="x", date="2000-01-01")
        assert uncertain_signs(ci, "tropical") == frozenset({"sun"})
