from __future__ import annotations

from unittest.mock import patch

import pytest

from hoshi.dignities import DIGNITY_SYMBOLS
from hoshi.info import HOUSES, RETROGRADE, SIGNS
from hoshi.output import BodyEntry, ChartHeader, ChartOutput
from hoshi_ui.main import HoshiApp
from hoshi_ui.screens.chart_detail import ChartDetailScreen
from hoshi_ui.widgets.body_display import BodyRow, _body_cells


# ---------------------------------------------------------------------------
# Unit tests — cell tooltip content (no app required)
# ---------------------------------------------------------------------------


def _sun_entry(**kwargs) -> BodyEntry:
    defaults = dict(
        kind="Planet",
        name="Sun",
        sign="Gemini",
        degree=28.0,
        lon=88.0,
        house=3,
        dignity=DIGNITY_SYMBOLS["domicile"],
    )
    return BodyEntry(**{**defaults, **kwargs})


def test_planet_cell_tooltip():
    b = _sun_entry()
    cells = _body_cells(b, show_house=True)
    planet_cell = cells[0]
    assert planet_cell.tooltip
    assert "identity" in planet_cell.tooltip or "vitality" in planet_cell.tooltip


def test_sign_cell_tooltip():
    b = _sun_entry()
    cells = _body_cells(b, show_house=True)
    sign_cell = cells[1]
    sign_info = SIGNS["Gemini"]
    assert sign_cell.tooltip == "  ·  ".join(sign_info.keywords)


def test_house_cell_tooltip():
    b = _sun_entry(house=3)
    cells = _body_cells(b, show_house=True)
    # Planet, sign, degree, house = index 3
    house_cell = cells[3]
    house_info = HOUSES[3]
    assert house_cell.tooltip == "  ·  ".join(house_info.keywords)


def test_dignity_cell_tooltip():
    b = _sun_entry(dignity=DIGNITY_SYMBOLS["domicile"])
    cells = _body_cells(b, show_house=True)
    dignity_cell = cells[-1]
    assert "Domicile" in dignity_cell.tooltip
    assert "at home" in dignity_cell.tooltip


def test_degree_cell_has_no_tooltip():
    b = _sun_entry()
    cells = _body_cells(b, show_house=True)
    degree_cell = cells[2]
    assert not degree_cell.tooltip


def test_no_house_omits_house_cell():
    b = _sun_entry(house=None)
    cells = _body_cells(b, show_house=False)
    # planet, sign, degree, rx (always reserved), dignity
    assert len(cells) == 5


def test_rx_cell_tooltip():
    b = _sun_entry(rx=True)
    cells = _body_cells(b, show_house=False)
    # planet, sign, degree, rx, dignity
    rx_cell = cells[3]
    assert rx_cell.tooltip == "  ·  ".join(RETROGRADE.keywords)


def test_non_rx_cell_has_no_tooltip():
    b = _sun_entry(rx=False)
    cells = _body_cells(b, show_house=False)
    rx_cell = cells[3]
    assert not rx_cell.tooltip


def test_dignity_column_consistent_with_and_without_rx():
    b_rx = _sun_entry(rx=True)
    b_no_rx = _sun_entry(rx=False)
    cells_rx = _body_cells(b_rx, show_house=False)
    cells_no_rx = _body_cells(b_no_rx, show_house=False)
    # Dignity is always the last cell at index 4 regardless of rx
    assert len(cells_rx) == len(cells_no_rx)
    assert "Domicile" in cells_rx[-1].tooltip
    assert "Domicile" in cells_no_rx[-1].tooltip


# ---------------------------------------------------------------------------
# Integration test — BodyRow appears in the list after chart loads
# ---------------------------------------------------------------------------


def _minimal_output() -> ChartOutput:
    return ChartOutput(
        chart=ChartHeader(name="Alice", when="1990-06-19", mode="realsky"),
        bodies=[
            BodyEntry(
                kind="Planet",
                name="Sun",
                sign="Gemini",
                degree=28.0,
                lon=88.0,
                house=3,
                dignity=DIGNITY_SYMBOLS["domicile"],
            ),
            BodyEntry(kind="Planet", name="Moon", sign="Libra", degree=15.0, lon=195.0),
        ],
    )


@pytest.mark.asyncio
async def test_body_row_cells_present_after_load(mock_store):
    app = HoshiApp()
    with patch.object(ChartDetailScreen, "_compute_chart"):
        async with app.run_test() as pilot:
            screen = ChartDetailScreen("alice")
            app.push_screen(screen)
            await pilot.pause()
            screen._display_output(_minimal_output())
            await pilot.pause()

            rows = screen.query(BodyRow)
            assert len(rows) >= 2

            # First planet row should have sign tooltip
            first_row = rows.first(BodyRow)
            sign_cells = [
                c
                for c in first_row.children
                if c.tooltip and "communication" in c.tooltip
            ]
            assert sign_cells, "Gemini sign cell should have keyword tooltip"
