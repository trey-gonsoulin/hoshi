from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from hoshi.chart import AngleChart, Chart, Placed, PlanetChart, PointChart
from hoshi.ephemeris import PlanetPosition
from hoshi.points import HERMETIC_LOT_NAMES
from hoshi.store import ChartInput

from hoshi_api.app import app


SAMPLE_CI = ChartInput(
    name="test",
    date="2000-01-01",
    time="12:00",
    tz="UTC",
    lat=30.0,
    lon=-90.0,
)

SAMPLE_CI_MINIMAL = ChartInput(name="notime", date="2000-01-01")


def _make_placed(lon: float) -> Placed:
    return Placed.for_longitude(lon, ayanamsa=23.85, precession=0.0)


def _make_chart(**overrides) -> Chart:
    planets = [
        PlanetChart(
            pid=pid,
            pos=PlanetPosition(lon=i * 30.0, lat=0.0, retrograde=False),
            placed=_make_placed(i * 30.0),
            house=1,
        )
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
    ]
    angles = [
        AngleChart(name="asc", placed=_make_placed(0.0), house=1),
        AngleChart(name="mc", placed=_make_placed(270.0), house=10),
        AngleChart(name="ic", placed=_make_placed(90.0), house=4),
        AngleChart(name="dsc", placed=_make_placed(180.0), house=7),
        AngleChart(name="vertex", placed=_make_placed(200.0), house=8),
        AngleChart(name="antivertex", placed=_make_placed(20.0), house=1),
    ]
    points = [
        PointChart(name="N.Node", placed=_make_placed(125.0), house=5),
        PointChart(name="S.Node", placed=_make_placed(305.0), house=11),
        PointChart(name="Lilith", placed=_make_placed(350.0), house=12),
    ]
    lots = [
        PointChart(name=name, placed=_make_placed(i * 50.0), house=1)
        for i, name in enumerate(HERMETIC_LOT_NAMES)
    ]
    defaults = dict(
        when=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        lat=30.0,
        lon=-90.0,
        ayanamsa=23.85,
        house_system="porphyry",
        angles=angles,
        planets=planets,
        points=points,
        lots=lots,
        cusps=[i * 30.0 for i in range(12)],
    )
    defaults.update(overrides)
    return Chart(**defaults)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_chart():
    chart = _make_chart()
    with patch("hoshi.chart.Chart.build", return_value=chart):
        yield chart
