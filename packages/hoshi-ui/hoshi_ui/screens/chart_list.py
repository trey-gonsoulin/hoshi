from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Select, Static

from hoshi import store


class ChartListScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
    ]

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
        from hoshi_ui.screens.chart_detail import ChartDetailScreen

        self.app.push_screen(ChartDetailScreen(name))
        self.query_one("#chart-select", Select).value = Select.NULL

    def action_refresh(self) -> None:
        self._load_charts()
