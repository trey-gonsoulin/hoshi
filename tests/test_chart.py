from datetime import datetime, timezone

import pytest

from hoshi.chart import BodyRef, Chart, Placed, _midpoint_lon, uncertain_signs
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
                "ceres",
                "eris",
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
        assert len(chart.planets) == 13

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


# ---------------------------------------------------------------------------
# _midpoint_lon
# ---------------------------------------------------------------------------


class TestMidpointLon:
    def test_simple(self):
        assert _midpoint_lon(10.0, 30.0) == pytest.approx(20.0)

    def test_wrap_around(self):
        # 350° and 10° — shorter arc midpoint is 0°
        assert _midpoint_lon(350.0, 10.0) == pytest.approx(0.0)

    def test_exactly_180_apart(self):
        # At exactly 180° diff the shorter arc is ambiguous; formula picks one deterministically
        result = _midpoint_lon(0.0, 180.0)
        assert 0.0 <= result < 360.0

    def test_same_point(self):
        assert _midpoint_lon(90.0, 90.0) == pytest.approx(90.0)

    def test_result_in_range(self):
        for a, b in [(355.0, 5.0), (0.0, 270.0), (100.0, 300.0)]:
            r = _midpoint_lon(a, b)
            assert 0.0 <= r < 360.0


# ---------------------------------------------------------------------------
# Chart.composite
# ---------------------------------------------------------------------------


def _make_two_charts(mock_deps):
    """Build two minimal offline charts using the mock_deps fixture."""
    angles_a = Angles(
        asc=10.0, mc=280.0, ic=100.0, dsc=190.0, vertex=210.0, antivertex=30.0
    )
    angles_b = Angles(
        asc=50.0, mc=320.0, ic=140.0, dsc=230.0, vertex=250.0, antivertex=70.0
    )
    lunar_a = LunarElements(om=100.0, w=30.0)
    lunar_b = LunarElements(om=120.0, w=50.0)

    PIDS = [
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
        "ceres",
        "eris",
    ]

    pos_a = {
        pid: PlanetPosition(lon=i * 20.0 % 360, lat=0.0, retrograde=True)
        for i, pid in enumerate(PIDS)
    }
    pos_b = {
        pid: PlanetPosition(lon=(i * 20.0 + 10.0) % 360, lat=0.0, retrograde=False)
        for i, pid in enumerate(PIDS)
    }

    ci_a = ChartInput(
        name="person_a", date="1990-01-01", time="12:00", tz="UTC", lat=40.0, lon=-74.0
    )
    ci_b = ChartInput(
        name="person_b", date="1995-06-15", time="18:00", tz="UTC", lat=51.5, lon=-0.13
    )

    # Build charts from known positions without hitting Horizons
    from hoshi.chart import Chart, Placed
    from hoshi.houses import porphyry_cusps

    def _build_offline(pos, angles, lunar, ci):
        from hoshi.chart import _build_planets, _build_points
        from hoshi.houses import house_from_cusps
        from hoshi.points import HERMETIC_LOT_NAMES, hermetic_lots

        ayan = 23.85
        prec = 0.0
        cusps = porphyry_cusps(angles)

        def house_of(lon):
            return house_from_cusps(lon, cusps)

        planets = _build_planets(pos, ayan, prec, house_of)
        points = _build_points(lunar, ayan, prec, house_of)
        angle_charts = [
            __import__("hoshi.chart", fromlist=["AngleChart"]).AngleChart(
                name=name,
                placed=Placed.for_longitude(getattr(angles, name), ayan, prec),
                house=house_of(getattr(angles, name)),
            )
            for name in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
        ]
        lot_lons = hermetic_lots(
            angles.asc,
            pos["sun"].lon,
            pos["moon"].lon,
            pos["mercury"].lon,
            pos["venus"].lon,
            pos["mars"].lon,
            pos["jupiter"].lon,
            pos["saturn"].lon,
        )
        lot_charts = [
            __import__("hoshi.chart", fromlist=["PointChart"]).PointChart(
                name=name,
                placed=Placed.for_longitude(lot_lons[name], ayan, prec),
                house=house_of(lot_lons[name]),
            )
            for name in HERMETIC_LOT_NAMES
        ]
        when_dt = ci.to_datetime().astimezone(__import__("datetime").timezone.utc)
        return Chart(
            when=when_dt,
            lat=ci.lat if ci.lat is not None else 0.001,
            lon=ci.lon if ci.lon is not None else 0.0,
            ayanamsa=ayan,
            house_system="porphyry",
            angles=angle_charts,
            planets=planets,
            points=points,
            lots=lot_charts,
            cusps=cusps,
            location_known=ci.location_known,
            time_known=ci.time_known,
        )

    chart_a = _build_offline(pos_a, angles_a, lunar_a, ci_a)
    chart_b = _build_offline(pos_b, angles_b, lunar_b, ci_b)
    return ci_a, ci_b, chart_a, chart_b


class TestChartComposite:
    def test_has_same_planet_count(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        assert len(comp.planets) == len(chart_a.planets)

    def test_planets_not_retrograde(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        assert all(not p.pos.retrograde for p in comp.planets)

    def test_sun_midpoint(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        sun_a = next(p for p in chart_a.planets if p.pid == "sun")
        sun_b = next(p for p in chart_b.planets if p.pid == "sun")
        sun_comp = next(p for p in comp.planets if p.pid == "sun")
        expected = _midpoint_lon(sun_a.pos.lon, sun_b.pos.lon)
        assert sun_comp.placed.lon == pytest.approx(expected)

    def test_location_known_true_when_both_known(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        assert chart_a.location_known and chart_b.location_known
        comp = Chart.composite(chart_a, chart_b)
        assert comp.location_known is True

    def test_location_known_false_suppresses_angles(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        # Mark one chart as no-location
        chart_b = chart_b.model_copy(update={"location_known": False})
        comp = Chart.composite(chart_a, chart_b)
        assert comp.location_known is False
        assert comp.angles == []
        assert comp.lots == []
        assert comp.cusps == []

    def test_angles_are_midpoints(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        asc_a = next(a.placed.lon for a in chart_a.angles if a.name == "asc")
        asc_b = next(a.placed.lon for a in chart_b.angles if a.name == "asc")
        comp_asc = next(a.placed.lon for a in comp.angles if a.name == "asc")
        assert comp_asc == pytest.approx(_midpoint_lon(asc_a, asc_b))

    def test_cusps_monotonic(self, mock_deps):
        """Cusps derived from composite angles must be monotonically ordered."""
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        # Force far-apart Ascendants (120°) to exercise the monotonicity concern
        angles_far_a = Angles(
            asc=0.0, mc=270.0, ic=90.0, dsc=180.0, vertex=200.0, antivertex=20.0
        )
        angles_far_b = Angles(
            asc=120.0, mc=30.0, ic=210.0, dsc=300.0, vertex=320.0, antivertex=140.0
        )
        chart_a2 = chart_a.model_copy(
            update={
                "angles": [
                    __import__("hoshi.chart", fromlist=["AngleChart"]).AngleChart(
                        name=n,
                        placed=Placed.for_longitude(
                            getattr(angles_far_a, n), 23.85, 0.0
                        ),
                        house=1,
                    )
                    for n in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
                ]
            }
        )
        chart_b2 = chart_b.model_copy(
            update={
                "angles": [
                    __import__("hoshi.chart", fromlist=["AngleChart"]).AngleChart(
                        name=n,
                        placed=Placed.for_longitude(
                            getattr(angles_far_b, n), 23.85, 0.0
                        ),
                        house=1,
                    )
                    for n in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
                ]
            }
        )
        comp = Chart.composite(chart_a2, chart_b2)
        assert len(comp.cusps) == 12
        # Each cusp must be reachable from the previous by going forward < 90°
        for i in range(12):
            a = comp.cusps[i]
            b = comp.cusps[(i + 1) % 12]
            arc = (b - a) % 360.0
            assert arc < 180.0, f"Cusps not monotonic at index {i}: {comp.cusps}"

    def test_composite_bodies_iterable(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        bodies = list(comp.bodies())
        assert len(bodies) > 0
        assert any(b.kind == "Planet" for b in bodies)
        assert any(b.kind == "Angle" for b in bodies)

    def test_time_known_and_of_both(self, mock_deps):
        _, _, chart_a, chart_b = _make_two_charts(mock_deps)
        chart_b_no_time = chart_b.model_copy(update={"time_known": False})
        comp = Chart.composite(chart_a, chart_b_no_time)
        assert comp.time_known is False


# ---------------------------------------------------------------------------
# CompositeOutput
# ---------------------------------------------------------------------------


class TestCompositeOutput:
    def test_build_basic(self, mock_deps):
        from hoshi.output import CompositeOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        output = CompositeOutput.build(ci_a, ci_b, comp, "tropical")
        assert output.header.name_a == "person_a"
        assert output.header.name_b == "person_b"
        assert len(output.bodies) > 0

    def test_render_shows_composite_header(self, mock_deps):
        from io import StringIO
        from rich.console import Console
        from hoshi.output import CompositeOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        output = CompositeOutput.build(ci_a, ci_b, comp, "tropical")
        buf = StringIO()
        console = Console(file=buf, width=120, no_color=True)
        output.render(console)
        text = buf.getvalue()
        assert "Composite" in text
        assert "person_a" in text.lower()
        assert "person_b" in text.lower()

    def test_no_angles_when_location_unknown(self, mock_deps):
        from hoshi.output import CompositeOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        chart_b_no_loc = chart_b.model_copy(update={"location_known": False})
        comp = Chart.composite(chart_a, chart_b_no_loc)
        ci_b_no_loc = ChartInput(name="person_b", date="1995-06-15")
        output = CompositeOutput.build(
            ci_a, ci_b_no_loc, comp, "tropical", details=True
        )
        angle_bodies = [b for b in output.bodies if b.kind == "Angle"]
        assert angle_bodies == []

    def test_aspects_populated_when_requested(self, mock_deps):
        from hoshi.output import CompositeOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        output = CompositeOutput.build(ci_a, ci_b, comp, "tropical", aspects=True)
        assert output.aspects is not None


# ---------------------------------------------------------------------------
# Composite transits / forecast output
# ---------------------------------------------------------------------------


class TestCompositeTransitsOutput:
    def test_basic_transits(self, mock_deps):
        from datetime import datetime, timezone

        from hoshi.cli import _composite_chart_input
        from hoshi.output import TransitsOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        ci_comp = _composite_chart_input(ci_a, ci_b, comp)

        assert "person_a" in ci_comp.name
        assert "person_b" in ci_comp.name
        assert ci_comp.time_known
        assert ci_comp.location_known

        transit_dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        output = TransitsOutput.build(ci_comp, comp, transit_dt, "tropical")
        assert output.header.name == ci_comp.name
        assert len(output.transit_bodies) > 0

    def test_no_location_suppresses_houses(self, mock_deps):
        from datetime import datetime, timezone

        from hoshi.cli import _composite_chart_input
        from hoshi.output import TransitsOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        chart_b_no_loc = chart_b.model_copy(update={"location_known": False})
        comp = Chart.composite(chart_a, chart_b_no_loc)
        ci_b_no_loc = ChartInput(name="person_b", date="1995-06-15")
        ci_comp = _composite_chart_input(ci_a, ci_b_no_loc, comp)

        assert not ci_comp.location_known
        transit_dt = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        output = TransitsOutput.build(ci_comp, comp, transit_dt, "tropical")
        assert any("location unknown" in w for w in output.warnings)


class TestCompositeForecastOutput:
    def test_basic_forecast(self, mock_deps):
        from datetime import datetime, timedelta, timezone

        from hoshi.cli import _composite_chart_input
        from hoshi.output import ForecastOutput

        ci_a, ci_b, chart_a, chart_b = _make_two_charts(mock_deps)
        comp = Chart.composite(chart_a, chart_b)
        ci_comp = _composite_chart_input(ci_a, ci_b, comp)

        from_dt = datetime(2024, 6, 1, tzinfo=timezone.utc)
        to_dt = from_dt + timedelta(days=30)
        output = ForecastOutput.build(
            ci_comp, comp, from_dt, to_dt, "tropical", tier="all"
        )
        assert output.header.name == ci_comp.name
        assert isinstance(output.aspects, list)
