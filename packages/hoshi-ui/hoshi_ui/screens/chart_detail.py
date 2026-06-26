from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Collapsible,
    DataTable,
    Footer,
    Header,
    LoadingIndicator,
    Static,
)
from textual import work

from hoshi import Chart, ChartOutput, store

from hoshi_ui.widgets.body_table import populate_aspect_table, populate_body_table


class ChartDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("t", "transits", "Transits"),
        Binding("c", "compare", "Compare"),
        Binding("a", "toggle_aspects", "Aspects"),
    ]

    def __init__(self, chart_name: str) -> None:
        super().__init__()
        self.chart_name = chart_name

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="chart-header")
        yield LoadingIndicator(id="loading")
        with VerticalScroll(id="chart-content"):
            with Collapsible(
                title="Placements", collapsed=False, id="placements-panel"
            ):
                yield DataTable(id="body-table", cursor_type="row")
            with Collapsible(title="Aspects", collapsed=True, id="aspects-panel"):
                yield DataTable(id="aspect-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chart-content").display = False
        for attr in ("zodiac_mode", "details", "group_by", "house_system"):
            self.watch(self.app, attr, self._on_option_changed, init=False)
        self._compute_chart()

    def _on_option_changed(self) -> None:
        self._recompute()

    def _recompute(self) -> None:
        self.query_one("#loading").display = True
        self.query_one("#chart-content").display = False
        self._compute_chart()

    @work(thread=True)
    def _compute_chart(self) -> None:
        ci = store.load(self.chart_name)
        chart = Chart.from_input(ci, house_system=self.app.house_system)
        output = ChartOutput.build(
            ci,
            chart,
            self.app.zodiac_mode,
            details=self.app.details,
            aspects=True,
            group_by=self.app.group_by,
        )
        self.app.call_from_thread(self._display_output, output)

    def _display_output(self, output: ChartOutput) -> None:
        self.query_one("#loading").display = False
        self.query_one("#chart-content").display = True
        self.query_one("#body-table", DataTable).focus()

        h = output.chart
        header_parts = [f"[bold]{h.name.title()}[/bold]  {h.when}"]
        if h.lat is not None:
            header_parts.append(f"({h.lat:.4f}°, {h.lon:.4f}°)")
        header_parts.append(f"mode: {h.mode}")
        if h.house_system:
            header_parts.append(f"houses: {h.house_system}")
        header_text = "  ".join(header_parts)
        warnings = "\n".join(output.warnings)
        if warnings:
            header_text += f"\n{warnings}"
        self.query_one("#chart-header", Static).update(header_text)

        body_table = self.query_one("#body-table", DataTable)
        show_houses = output.show_houses
        populate_body_table(
            body_table,
            output.bodies,
            show_houses=show_houses,
            show_dignity=True,
            group_by=output.group_by,
        )

        aspects_panel = self.query_one("#aspects-panel", Collapsible)
        aspect_table = self.query_one("#aspect-table", DataTable)
        if output.aspects:
            show_signs = any(a.sign_a or a.sign_b for a in output.aspects)
            populate_aspect_table(
                aspect_table,
                output.aspects,
                show_signs=show_signs,
                group_by=output.group_by,
            )
            aspects_panel.display = True
        else:
            aspect_table.clear(columns=True)
            aspects_panel.display = False

    def action_toggle_aspects(self) -> None:
        panel = self.query_one("#aspects-panel", Collapsible)
        panel.collapsed = not panel.collapsed
        if not panel.collapsed:
            self.query_one("#aspect-table", DataTable).focus()

    def action_transits(self) -> None:
        from hoshi_ui.screens.transits import TransitsScreen

        self.app.push_screen(TransitsScreen(self.chart_name))

    def action_compare(self) -> None:
        from hoshi_ui.screens.chart_picker import ChartPickerModal
        from hoshi_ui.screens.compare import CompareScreen

        def _on_picked(name: str | None) -> None:
            if name is not None:
                self.app.push_screen(CompareScreen(self.chart_name, name))

        self.app.push_screen(
            ChartPickerModal(prompt="Compare with:", exclude=self.chart_name),
            _on_picked,
        )
