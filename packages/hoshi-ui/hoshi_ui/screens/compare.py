from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static
from textual import work

from hoshi import Chart, CompareOutput, format_deg, store

from hoshi_ui.widgets.body_table import populate_aspect_table


class CompareScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, name_a: str, name_b: str) -> None:
        super().__init__()
        self.name_a = name_a
        self.name_b = name_b

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="compare-header")
        yield LoadingIndicator(id="loading")
        with VerticalScroll(id="compare-content"):
            yield DataTable(id="placement-table", cursor_type="row")
            yield DataTable(id="compare-aspect-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
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
            details=self.app.details,
            aspects=self.app.aspects,
            group_by=self.app.group_by,
        )
        self.app.call_from_thread(self._display_output, output)

    def _display_output(self, output: CompareOutput) -> None:
        self.query_one("#loading").display = False
        self.query_one("#compare-content").display = True
        self.query_one("#placement-table", DataTable).focus()

        h = output.header
        header_text = (
            f"[bold]Synastry:[/bold] {h.name_a.title()} ({h.date_a})  ×  "
            f"{h.name_b.title()} ({h.date_b})  mode: {h.mode}"
        )
        warnings = "\n".join(output.warnings)
        if warnings:
            header_text += f"\n{warnings}"
        self.query_one("#compare-header", Static).update(header_text)

        self._populate_placements(output)

        aspect_table = self.query_one("#compare-aspect-table", DataTable)
        if output.aspects:
            show_signs = any(a.sign_a or a.sign_b for a in output.aspects)
            populate_aspect_table(
                aspect_table,
                output.aspects,
                show_signs=show_signs,
                group_by=output.group_by,
            )
            aspect_table.display = True
        else:
            aspect_table.clear(columns=True)
            aspect_table.display = False

    def _populate_placements(self, output: CompareOutput) -> None:
        table = self.query_one("#placement-table", DataTable)
        table.clear(columns=True)

        h = output.header
        table.add_columns(
            "Body",
            f"{h.name_a.title()} Sign",
            "Deg",
            "Rx",
            "│",
            f"{h.name_b.title()} Sign",
            "Deg",
            "Rx",
        )

        index_a = {b.name: b for b in output.bodies_a}
        index_b = {b.name: b for b in output.bodies_b}
        all_names = list(
            dict.fromkeys(b.name for b in output.bodies_a + output.bodies_b)
        )

        for name in all_names:
            ba = index_a.get(name)
            bb = index_b.get(name)
            row: list[str] = [name]
            if ba:
                row.extend([ba.sign, format_deg(ba.degree), "℞" if ba.rx else ""])
            else:
                row.extend(["—", "—", ""])
            row.append("│")
            if bb:
                row.extend([bb.sign, format_deg(bb.degree), "℞" if bb.rx else ""])
            else:
                row.extend(["—", "—", ""])
            table.add_row(*row)
