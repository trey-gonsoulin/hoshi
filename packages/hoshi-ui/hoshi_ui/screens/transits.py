from __future__ import annotations

from datetime import datetime, timezone

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Collapsible,
    DataTable,
    Footer,
    Header,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)
from textual import work

from hoshi import Chart, TransitsOutput, store

from hoshi_ui.widgets.body_display import build_list_items
from hoshi_ui.widgets.body_table import populate_aspect_table


class TransitsScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("n", "refresh_now", "Now"),
        Binding("a", "toggle_aspects", "Aspects"),
    ]

    def __init__(self, chart_name: str) -> None:
        super().__init__()
        self.chart_name = chart_name

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="transit-header")
        yield LoadingIndicator(id="loading")
        with VerticalScroll(id="transit-content"):
            yield ListView(id="transit-bodies-list")
            with Collapsible(
                title="Aspects", collapsed=True, id="transit-aspects-panel"
            ):
                yield DataTable(id="transit-aspect-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#transit-content").display = False
        for attr in ("zodiac_mode", "group_by", "house_system"):
            self.watch(self.app, attr, self._recompute, init=False)
        self._compute_transits()

    def _recompute(self) -> None:
        self.query_one("#loading").display = True
        self.query_one("#transit-content").display = False
        self._compute_transits()

    @work(thread=True)
    def _compute_transits(self) -> None:
        ci = store.load(self.chart_name)
        chart_natal = Chart.from_input(ci, house_system=self.app.house_system)
        transit_dt = datetime.now(timezone.utc).astimezone()
        output = TransitsOutput.build(
            ci,
            chart_natal,
            transit_dt,
            self.app.zodiac_mode,
            details=True,
            aspects=True,
            natal=False,
            group_by=self.app.group_by,
        )
        self.app.call_from_thread(self._display_output, output)

    def _display_output(self, output: TransitsOutput) -> None:
        h = output.header
        header_text = (
            f"[bold]Transits:[/bold] {h.name.title()}  "
            f"natal {h.natal_date} → transit {h.transit_when}  "
            f"mode: {h.mode}"
        )
        if h.house_system:
            header_text += f"  houses: {h.house_system}"
        for w in output.warnings:
            header_text += f"\n{w}"
        self.query_one("#transit-header", Static).update(header_text)

        bodies_lv = self.query_one("#transit-bodies-list", ListView)
        bodies_lv.clear()
        bodies_lv.extend(
            build_list_items(
                output.transit_bodies,
                show_house=output.show_houses,
                group_by=output.group_by,
            )
        )

        aspect_table = self.query_one("#transit-aspect-table", DataTable)
        if output.aspects:
            show_signs = any(a.sign_a or a.sign_b for a in output.aspects)
            populate_aspect_table(
                aspect_table,
                output.aspects,
                show_signs=show_signs,
                group_by=output.group_by,
            )

        self.query_one("#loading").display = False
        self.query_one("#transit-content").display = True
        bodies_lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item: ListItem = event.item
        data = getattr(item, "data", None)
        if data:
            from hoshi_ui.screens.info_modal import InfoModal

            self.app.push_screen(InfoModal(data["name"], data["kind"]))

    def action_toggle_aspects(self) -> None:
        panel = self.query_one("#transit-aspects-panel", Collapsible)
        panel.collapsed = not panel.collapsed
        if not panel.collapsed:
            self.query_one("#transit-aspect-table", DataTable).focus()

    def action_refresh_now(self) -> None:
        self.query_one("#loading").display = True
        self.query_one("#transit-content").display = False
        self._compute_transits()
