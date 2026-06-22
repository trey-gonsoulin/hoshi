from io import StringIO

from rich.console import Console

from hoshi.output import BodyEntry, CuspEntry, _render_by_house


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
