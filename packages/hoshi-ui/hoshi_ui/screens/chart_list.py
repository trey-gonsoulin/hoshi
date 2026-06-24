from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Select, Static

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
        yield Select[str]([], prompt="Select a chart", id="chart-select")
        yield Footer()

    def on_mount(self) -> None:
        self._load_charts()

    def _load_charts(self) -> None:
        charts = store.list_all()
        select = self.query_one("#chart-select", Select)
        hint = self.query_one("#compare-hint", Static)
        if not charts:
            select.set_options([])
            hint.update("No saved charts. Use `hoshi chart add` to create one.")
        else:
            options = [(self._chart_label(ci), ci.name) for ci in charts]
            select.set_options(options)
            hint.update("")

    @staticmethod
    def _chart_label(ci: store.ChartInput) -> str:
        parts = [ci.name.title(), ci.date]
        if ci.time:
            parts.append(ci.time)
        return "  —  ".join(parts)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return
        name = str(event.value)
        if self._comparing:
            if not self._compare_a:
                self._compare_a = name
                hint = self.query_one("#compare-hint", Static)
                hint.update(f"Compare: [{self._compare_a.title()}] → select chart B...")
                self.query_one("#chart-select", Select).value = Select.NULL
            else:
                from hoshi_ui.screens.compare import CompareScreen

                self.app.push_screen(CompareScreen(self._compare_a, name))
                self._cancel_compare()
        else:
            from hoshi_ui.screens.chart_detail import ChartDetailScreen

            self.app.push_screen(ChartDetailScreen(name))
            self.query_one("#chart-select", Select).value = Select.NULL

    def action_transits(self) -> None:
        select = self.query_one("#chart-select", Select)
        if select.value is Select.NULL:
            return
        name = str(select.value)
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
        self.query_one("#chart-select", Select).value = Select.NULL

    def action_refresh(self) -> None:
        self._load_charts()
