from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
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

from hoshi import Chart, CompareOutput, store

from hoshi_ui.widgets.body_display import build_list_items
from hoshi_ui.widgets.body_table import populate_aspect_table


class CompareScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "toggle_aspects", "Aspects"),
    ]

    DEFAULT_CSS = """
    CompareScreen #panels {
        height: auto;
    }
    CompareScreen #panel-a, CompareScreen #panel-b {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }
    CompareScreen .panel-label {
        height: auto;
        padding: 0 1;
        color: $accent;
        text-style: bold;
    }
    """

    def __init__(self, name_a: str, name_b: str) -> None:
        super().__init__()
        self.name_a = name_a
        self.name_b = name_b

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="compare-header")
        yield LoadingIndicator(id="loading")
        with VerticalScroll(id="compare-content"):
            with Horizontal(id="panels"):
                with Vertical(id="panel-a"):
                    yield Static("", classes="panel-label", id="label-a")
                    yield ListView(id="list-a")
                with Vertical(id="panel-b"):
                    yield Static("", classes="panel-label", id="label-b")
                    yield ListView(id="list-b")
            with Collapsible(
                title="Aspects", collapsed=True, id="compare-aspects-panel"
            ):
                yield DataTable(id="compare-aspect-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#compare-content").display = False
        for attr in ("zodiac_mode", "group_by", "house_system"):
            self.watch(self.app, attr, self._recompute, init=False)
        self._compute_compare()

    def _recompute(self) -> None:
        self.query_one("#loading").display = True
        self.query_one("#compare-content").display = False
        self._compute_compare()

    @work(thread=True)
    def _compute_compare(self) -> None:
        ci_a = store.load(self.name_a)
        ci_b = store.load(self.name_b)
        chart_a = Chart.from_input(ci_a, house_system=self.app.house_system)
        chart_b = Chart.from_input(ci_b, house_system=self.app.house_system)
        output = CompareOutput.build(
            ci_a,
            ci_b,
            chart_a,
            chart_b,
            self.app.zodiac_mode,
            details=True,
            aspects=True,
            group_by=self.app.group_by,
        )
        self.app.call_from_thread(self._display_output, output)

    def _display_output(self, output: CompareOutput) -> None:
        h = output.header
        header_text = (
            f"[bold]Synastry:[/bold] {h.name_a.title()} ({h.date_a})  ×  "
            f"{h.name_b.title()} ({h.date_b})  mode: {h.mode}"
        )
        for w in output.warnings:
            header_text += f"\n{w}"
        self.query_one("#compare-header", Static).update(header_text)

        self.query_one("#label-a", Static).update(h.name_a.title())
        self.query_one("#label-b", Static).update(h.name_b.title())

        show_houses_a = any(b.house is not None for b in output.bodies_a)
        show_houses_b = any(b.house is not None for b in output.bodies_b)
        group_by = output.group_by

        lv_a = self.query_one("#list-a", ListView)
        lv_a.clear()
        lv_a.extend(
            build_list_items(
                output.bodies_a, show_house=show_houses_a, group_by=group_by
            )
        )

        lv_b = self.query_one("#list-b", ListView)
        lv_b.clear()
        lv_b.extend(
            build_list_items(
                output.bodies_b, show_house=show_houses_b, group_by=group_by
            )
        )

        aspect_table = self.query_one("#compare-aspect-table", DataTable)
        if output.aspects:
            show_signs = any(a.sign_a or a.sign_b for a in output.aspects)
            populate_aspect_table(
                aspect_table,
                output.aspects,
                show_signs=show_signs,
                group_by=group_by,
            )

        self.query_one("#loading").display = False
        self.query_one("#compare-content").display = True
        lv_a.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item: ListItem = event.item
        data = getattr(item, "data", None)
        if data:
            from hoshi_ui.screens.info_modal import InfoModal

            self.app.push_screen(InfoModal(data["name"], data["kind"]))

    def action_toggle_aspects(self) -> None:
        panel = self.query_one("#compare-aspects-panel", Collapsible)
        panel.collapsed = not panel.collapsed
        if not panel.collapsed:
            self.query_one("#compare-aspect-table", DataTable).focus()
