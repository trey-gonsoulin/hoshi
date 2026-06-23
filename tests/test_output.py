from io import StringIO

from rich.console import Console

from hoshi.aspects import Aspect
from hoshi.output import BodyEntry, CuspEntry, _render_aspects, _render_by_house


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
