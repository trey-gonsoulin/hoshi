import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from hoshi.cli import app
from hoshi.store import ChartInput
from tests.conftest import make_angle, make_chart, make_planet, make_point

runner = CliRunner()


def _full_mock_chart():
    from hoshi.points import HERMETIC_LOT_NAMES

    planets = [
        make_planet(pid, i * 30.0)
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
        make_angle("asc", 0.0),
        make_angle("mc", 270.0),
        make_angle("ic", 90.0),
        make_angle("dsc", 180.0),
        make_angle("vertex", 200.0),
        make_angle("antivertex", 20.0),
    ]
    points = [
        make_point("N.Node", 125.0),
        make_point("S.Node", 305.0),
        make_point("Lilith", 350.0),
    ]
    lots = [make_point(name, i * 50.0) for i, name in enumerate(HERMETIC_LOT_NAMES)]
    return make_chart(planets=planets, angles=angles, points=points, lots=lots)


@pytest.fixture
def mock_chart_build():
    chart = _full_mock_chart()
    with patch("hoshi.chart.Chart.build", return_value=chart):
        yield chart


class TestChartFromInput:
    def test_uses_real_coords(self):
        from hoshi.chart import Chart

        ci = ChartInput(name="x", date="2000-01-01", time="12:00", lat=40.0, lon=-70.0)
        with patch("hoshi.chart.Chart.build", return_value=_full_mock_chart()) as build:
            Chart.from_input(ci, house_system="porphyry")
        _, args, _ = build.mock_calls[0]
        assert args[1] == 40.0
        assert args[2] == -70.0

    def test_substitutes_placeholder_when_location_unknown(self):
        from hoshi.chart import PLACEHOLDER_LAT, PLACEHOLDER_LON, Chart

        ci = ChartInput(name="x", date="2000-01-01")
        with patch("hoshi.chart.Chart.build", return_value=_full_mock_chart()) as build:
            Chart.from_input(ci, house_system="porphyry")
        _, args, _ = build.mock_calls[0]
        assert args[1] == PLACEHOLDER_LAT
        assert args[2] == PLACEHOLDER_LON


class TestChartList:
    def test_empty(self):
        with patch("hoshi.cli.store.list_all", return_value=[]):
            result = runner.invoke(app, ["chart", "list"])
            assert result.exit_code == 0

    def test_with_charts(self):
        items = [
            ChartInput(name="alice", date="2000-01-01", time="12:00", lat=0.0, lon=0.0),
            ChartInput(name="bob", date="1990-06-15"),
        ]
        with patch("hoshi.cli.store.list_all", return_value=items):
            result = runner.invoke(app, ["chart", "list"])
            assert result.exit_code == 0
            assert "Alice" in result.output or "alice" in result.output
            assert "Bob" in result.output or "bob" in result.output


class TestChartAdd:
    def test_success(self, mock_chart_build):
        ci = ChartInput(name="test", date="2000-01-01", time="12:00", lat=0.0, lon=0.0)
        with (
            patch("hoshi.cli.store.save") as save_mock,
            patch("hoshi.cli.store.load", return_value=ci),
        ):
            result = runner.invoke(
                app,
                [
                    "chart",
                    "add",
                    "test",
                    "2000-01-01",
                    "12:00",
                    "--lat",
                    "0.0",
                    "--lon",
                    "0.0",
                ],
            )
            assert result.exit_code == 0
            save_mock.assert_called_once()


class TestChartShow:
    def test_saved_chart(self, mock_chart_build):
        ci = ChartInput(name="alice", date="2000-01-01", time="12:00", lat=0.0, lon=0.0)
        with patch("hoshi.cli.store.load", return_value=ci):
            result = runner.invoke(app, ["chart", "show", "alice"])
            assert result.exit_code == 0

    def test_json_format(self, mock_chart_build):
        ci = ChartInput(name="alice", date="2000-01-01", time="12:00", lat=0.0, lon=0.0)
        with patch("hoshi.cli.store.load", return_value=ci):
            result = runner.invoke(app, ["chart", "show", "alice", "--format", "json"])
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert "bodies" in parsed


class TestChartDelete:
    def test_success(self):
        with (
            patch("hoshi.cli.store.exists", return_value=True),
            patch("hoshi.cli.store.delete"),
        ):
            result = runner.invoke(app, ["chart", "delete", "test", "--yes"])
            assert result.exit_code == 0

    def test_not_found(self):
        with patch("hoshi.cli.store.exists", return_value=False):
            result = runner.invoke(app, ["chart", "delete", "test", "--yes"])
            assert result.exit_code != 0
