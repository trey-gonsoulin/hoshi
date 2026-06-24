from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from hoshi import store


class ChartListScreen(Screen):
    BINDINGS = [
        Binding("t", "transits", "Transits"),
        Binding("c", "compare", "Compare"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "cancel_compare", "Cancel", show=False),
    ]

    _comparing: bool = False
    _compare_a: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="compare-hint")
        yield DataTable(id="chart-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self._load_charts()

    def _load_charts(self) -> None:
        table = self.query_one("#chart-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Date", "Time", "Timezone", "Lat", "Lon")
        charts = store.list_all()
        for ci in charts:
            table.add_row(
                ci.name.title(),
                ci.date,
                ci.time or "—",
                ci.tz if ci.time is not None else "—",
                f"{ci.lat:.4f}" if ci.lat is not None else "—",
                f"{ci.lon:.4f}" if ci.lon is not None else "—",
                key=ci.name,
            )
        hint = self.query_one("#compare-hint", Static)
        if not charts:
            hint.update("No saved charts. Use `hoshi chart add` to create one.")
        else:
            hint.update("")

    def _selected_name(self) -> str | None:
        table = self.query_one("#chart-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return None
        return str(table.coordinate_to_cell_key((table.cursor_row, 0)).row_key.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        name = str(event.row_key.value)
        if self._comparing:
            if not self._compare_a:
                self._compare_a = name
                hint = self.query_one("#compare-hint", Static)
                hint.update(f"Compare: [{self._compare_a.title()}] → select chart B...")
            else:
                from hoshi_ui.screens.compare import CompareScreen

                self.app.push_screen(CompareScreen(self._compare_a, name))
                self._cancel_compare()
        else:
            from hoshi_ui.screens.chart_detail import ChartDetailScreen

            self.app.push_screen(ChartDetailScreen(name))

    def action_transits(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        from hoshi_ui.screens.transits import TransitsScreen

        self.app.push_screen(TransitsScreen(name))

    def action_compare(self) -> None:
        if self._comparing:
            return
        self._comparing = True
        self._compare_a = ""
        hint = self.query_one("#compare-hint", Static)
        hint.update("Compare: select chart A...")

    def action_cancel_compare(self) -> None:
        if self._comparing:
            self._cancel_compare()

    def _cancel_compare(self) -> None:
        self._comparing = False
        self._compare_a = ""
        hint = self.query_one("#compare-hint", Static)
        hint.update("")

    def action_refresh(self) -> None:
        self._load_charts()
