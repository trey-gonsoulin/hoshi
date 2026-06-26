from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Select, Static

from hoshi import store


class ChartPickerModal(ModalScreen[str | None]):
    """Modal to pick a chart by name. Dismisses with the chart name or None."""

    DEFAULT_CSS = """
    ChartPickerModal {
        align: center middle;
    }
    ChartPickerModal #picker-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $accent;
    }
    ChartPickerModal #picker-label {
        height: auto;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_none", "Cancel", show=True),
    ]

    def __init__(
        self, prompt: str = "Select a chart", exclude: str | None = None
    ) -> None:
        super().__init__()
        self._prompt = prompt
        self._exclude = exclude

    def compose(self) -> ComposeResult:
        charts = [ci for ci in store.list_all() if ci.name != self._exclude]
        options = [(self._chart_label(ci), ci.name) for ci in charts]
        with Vertical(id="picker-container"):
            yield Static(self._prompt, id="picker-label")
            yield Select[str](options, prompt="— choose —", id="picker-select")
            yield Footer()

    @staticmethod
    def _chart_label(ci: store.ChartInput) -> str:
        parts = [ci.name.title(), ci.date]
        if ci.time:
            parts.append(ci.time)
        return "  —  ".join(parts)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is not Select.NULL:
            self.dismiss(str(event.value))

    def action_dismiss_none(self) -> None:
        self.dismiss(None)
