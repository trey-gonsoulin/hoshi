from io import StringIO

from rich.console import Console

from datetime import datetime, timezone

from hoshi.aspects import Aspect
from hoshi.output import (
    BodyEntry,
    CuspEntry,
    TransitAspect,
    _render_aspects,
    _render_by_house,
)
from hoshi.store import ChartInput


def _capture(fn):
    buf = StringIO()
    console = Console(file=buf, width=120, no_color=True)
    fn(console)
    return buf.getvalue()


def test_render_by_house_shows_sign_and_range():
    bodies = [
        BodyEntry(
            name="Sun",
            kind="Planet",
            sign="Aries",
            degree=10.5,
            lon=10.5,
            house=1,
        ),
    ]
    cusps = [
        CuspEntry(house=1, sign="Aries", degree=0.0, lon=0.0),
        CuspEntry(house=2, sign="Taurus", degree=0.0, lon=30.0),
        CuspEntry(house=3, sign="Gemini", degree=0.0, lon=60.0),
    ]
    text = _capture(lambda c: _render_by_house(c, bodies, cusps, asc_lon=0.0))

    assert "H1" in text
    assert "Aries" in text
    assert "00°00'" in text
    assert "30°00'" in text

    assert "H2" in text
    assert "Taurus" in text

    assert "Sun" in text


def test_render_by_house_empty_house():
    cusps = [
        CuspEntry(house=1, sign="Aries", degree=0.0, lon=0.0),
        CuspEntry(house=2, sign="Taurus", degree=0.0, lon=30.0),
    ]
    text = _capture(lambda c: _render_by_house(c, [], cusps, asc_lon=0.0))

    assert "H1" in text
    assert "H2" in text


def _sample_aspects():
    return [
        Aspect(
            body_a="Sun",
            sign_a="Aries",
            body_b="Moon",
            sign_b="Cancer",
            name="Square",
            symbol="□",
            angle=90.0,
            orb=1.5,
            kind="Major",
        ),
        Aspect(
            body_a="Venus",
            sign_a="Taurus",
            body_b="Mars",
            sign_b="Aries",
            name="Semi-sextile",
            symbol="⚺",
            angle=30.0,
            orb=0.8,
            kind="Minor",
        ),
        Aspect(
            body_a="Sun",
            sign_a="Aries",
            body_b="Jupiter",
            sign_b="Aries",
            name="Conjunction",
            symbol="☌",
            angle=0.0,
            orb=2.0,
            kind="Major",
        ),
    ]


def test_render_aspects_by_category():
    text = _capture(
        lambda c: _render_aspects(c, _sample_aspects(), group_by="category")
    )
    assert "Major Aspects" in text
    assert "Minor Aspects" in text
    assert "Sun" in text
    assert "Square" in text


def test_render_aspects_by_planet():
    text = _capture(lambda c: _render_aspects(c, _sample_aspects(), group_by="planet"))
    assert "Sun" in text
    assert "Moon" in text
    assert "Venus" in text
    assert "Mars" in text
    assert "Jupiter" in text


def test_render_aspects_by_sign():
    text = _capture(lambda c: _render_aspects(c, _sample_aspects(), group_by="sign"))
    assert "Aries" in text
    assert "Cancer" in text
    assert "Taurus" in text


def test_render_aspects_by_house():
    body_houses = {"Sun": 1, "Moon": 4, "Venus": 2, "Mars": 1, "Jupiter": 1}
    text = _capture(
        lambda c: _render_aspects(
            c, _sample_aspects(), group_by="house", body_houses=body_houses
        )
    )
    assert "House 1" in text
    assert "House 4" in text
    assert "House 2" in text


def test_render_aspects_by_house_no_house_data_falls_back_to_category():
    text = _capture(lambda c: _render_aspects(c, _sample_aspects(), group_by="house"))
    assert "Major Aspects" in text
    assert "Minor Aspects" in text


def test_render_aspects_with_prefix():
    text = _capture(
        lambda c: _render_aspects(c, _sample_aspects(), "Test: ", group_by="planet")
    )
    assert "Test: Sun" in text


# ---------------------------------------------------------------------------
# TransitAspect natal_sensitivity field
# ---------------------------------------------------------------------------


def _make_chart_input(*, lat=51.5, lon=-0.13, time="12:00"):
    return ChartInput(
        name="test",
        date="2000-01-01",
        time=time,
        tz="UTC",
        lat=lat,
        lon=lon,
    )


def _transit_dt():
    return datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc)


class TestTransitAspectNatalSensitivity:
    def test_transit_aspect_has_natal_sensitivity_field(self):
        asp = TransitAspect(
            body_a="Sun",
            body_b="Saturn",
            name="Conjunction",
            symbol="☌",
            angle=0.0,
            orb=1.0,
            kind="Major",
        )
        assert asp.natal_sensitivity == ""

    def test_transits_output_aspects_have_sensitivity(self):
        from hoshi.chart import Chart
        from hoshi.output import TransitsOutput

        ci = _make_chart_input()
        chart_natal = Chart.from_input(ci)
        output = TransitsOutput.build(
            ci,
            chart_natal,
            _transit_dt(),
            "tropical",
            aspects=True,
            windows=False,
        )
        assert output.aspects is not None
        for asp in output.aspects:
            assert asp.natal_sensitivity in ("primary", "secondary", "tertiary")

    def test_transits_sensitivity_filter_primary(self):
        from hoshi.chart import Chart
        from hoshi.output import TransitsOutput

        ci = _make_chart_input()
        chart_natal = Chart.from_input(ci)
        all_output = TransitsOutput.build(
            ci, chart_natal, _transit_dt(), "tropical", aspects=True, windows=False
        )
        prim_output = TransitsOutput.build(
            ci,
            chart_natal,
            _transit_dt(),
            "tropical",
            aspects=True,
            windows=False,
            sensitivity="primary",
        )
        assert prim_output.aspects is not None
        assert all(a.natal_sensitivity == "primary" for a in prim_output.aspects)
        assert len(prim_output.aspects) <= len(all_output.aspects or [])

    def test_sensitivity_primary_without_location_excludes_asc(self):
        from hoshi.chart import Chart
        from hoshi.output import TransitsOutput

        ci = ChartInput(name="test", date="2000-01-01", time="12:00", tz="UTC")
        chart_natal = Chart.from_input(ci)
        output = TransitsOutput.build(
            ci,
            chart_natal,
            _transit_dt(),
            "tropical",
            aspects=True,
            windows=False,
            sensitivity="primary",
        )
        assert output.aspects is not None
        for asp in output.aspects:
            assert asp.body_a not in ("Ascendant", "Asc", "Midheaven", "MC")

    def test_forecast_aspects_have_sensitivity(self):
        from hoshi.chart import Chart
        from hoshi.output import ForecastOutput

        ci = _make_chart_input()
        chart_natal = Chart.from_input(ci)
        from_dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        output = ForecastOutput.build(ci, chart_natal, from_dt, to_dt, "tropical")
        for asp in output.aspects:
            assert asp.natal_sensitivity in ("primary", "secondary", "tertiary")

    def test_forecast_sensitivity_filter_reduces_results(self):
        from hoshi.chart import Chart
        from hoshi.output import ForecastOutput

        ci = _make_chart_input()
        chart_natal = Chart.from_input(ci)
        from_dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        to_dt = datetime(2025, 9, 30, tzinfo=timezone.utc)
        all_out = ForecastOutput.build(ci, chart_natal, from_dt, to_dt, "tropical")
        prim_out = ForecastOutput.build(
            ci, chart_natal, from_dt, to_dt, "tropical", sensitivity="primary"
        )
        assert all(a.natal_sensitivity == "primary" for a in prim_out.aspects)
        assert len(prim_out.aspects) <= len(all_out.aspects)
