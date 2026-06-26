from __future__ import annotations

import pytest

from hoshi_ui.main import HoshiApp


@pytest.mark.asyncio
async def test_app_launches(mock_store):
    app = HoshiApp()
    async with app.run_test():
        assert app.title == "hoshi"


@pytest.mark.asyncio
async def test_chart_list_shows_charts(mock_store):
    app = HoshiApp()
    async with app.run_test():
        from textual.widgets import Select

        screen = app.screen
        select = screen.query_one("#chart-select", Select)
        non_blank = [v for _, v in select._options if v is not Select.NULL]
        assert len(non_blank) == 2


@pytest.mark.asyncio
async def test_mode_cycling(mock_store):
    app = HoshiApp()
    async with app.run_test() as pilot:
        assert app.zodiac_mode == "realsky"
        await pilot.press("m")
        assert app.zodiac_mode == "tropical"
        await pilot.press("m")
        assert app.zodiac_mode == "vedic"
        await pilot.press("m")
        assert app.zodiac_mode == "realsky"
