from __future__ import annotations

from unittest.mock import patch

import pytest

from hoshi.output import BodyEntry, ChartHeader, ChartOutput
from hoshi_ui.main import HoshiApp
from hoshi_ui.screens.chart_detail import ChartDetailScreen


def _minimal_output() -> ChartOutput:
    return ChartOutput(
        chart=ChartHeader(name="Alice", when="1990-06-19", mode="realsky"),
        bodies=[
            BodyEntry(kind="Planet", name="Sun", sign="Gemini", degree=28.0, lon=88.0),
            BodyEntry(kind="Planet", name="Moon", sign="Libra", degree=15.0, lon=195.0),
            BodyEntry(kind="Angle", name="Asc", sign="Virgo", degree=10.0, lon=160.0),
            BodyEntry(
                kind="Node", name="North Node", sign="Aquarius", degree=20.0, lon=320.0
            ),
        ],
    )


async def _push_chart_screen(app: HoshiApp, pilot) -> ChartDetailScreen:
    """Push ChartDetailScreen with injected output, bypassing the worker."""
    screen = ChartDetailScreen("alice")
    app.push_screen(screen)
    await pilot.pause()
    screen._display_output(_minimal_output())
    await pilot.pause()
    return screen


@pytest.mark.asyncio
async def test_planet_list_right_focuses_tab_bar(mock_store):
    from textual.widgets import Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)

            assert screen.focused is screen.query_one("#planets-list")
            await pilot.press("right")
            await pilot.pause()
            assert screen.focused is tabs_bar


@pytest.mark.asyncio
async def test_planet_list_left_focuses_tab_bar(mock_store):
    from textual.widgets import Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)

            assert screen.focused is screen.query_one("#planets-list")
            await pilot.press("left")
            await pilot.pause()
            assert screen.focused is tabs_bar


@pytest.mark.asyncio
async def test_tab_bar_down_enters_list(mock_store):
    from textual.widgets import ListView, Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)

            # Move focus to the tab bar
            tabs_bar.focus()
            await pilot.pause()
            assert screen.focused is tabs_bar

            # Angles tab is active by default
            await pilot.press("down")
            await pilot.pause()
            assert screen.focused is screen.query_one("#angles-list", ListView)


@pytest.mark.asyncio
async def test_tab_bar_up_returns_to_planet_list(mock_store):
    from textual.widgets import ListView, Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)
            planet_list = screen.query_one("#planets-list", ListView)

            tabs_bar.focus()
            await pilot.pause()
            await pilot.press("up")
            await pilot.pause()
            assert screen.focused is planet_list


@pytest.mark.asyncio
async def test_extras_list_right_focuses_tab_bar(mock_store):
    from textual.widgets import ListView, Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)
            angles_list = screen.query_one("#angles-list", ListView)

            angles_list.focus()
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            assert screen.focused is tabs_bar


@pytest.mark.asyncio
async def test_extras_list_left_focuses_tab_bar(mock_store):
    from textual.widgets import ListView, Tabs

    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = await _push_chart_screen(app, pilot)
            tabs_bar = screen.query_one("#extras-tabs").query_one(Tabs)
            points_list = screen.query_one("#points-list", ListView)

            points_list.focus()
            await pilot.pause()
            await pilot.press("left")
            await pilot.pause()
            assert screen.focused is tabs_bar
