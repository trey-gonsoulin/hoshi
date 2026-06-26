from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Select, Static

from hoshi.info import ANGLES, HOUSES, PLANETS, POINTS, SIGNS


def _all_options() -> list[tuple[str, tuple[str, str]]]:
    """Return (label, (name, kind)) pairs for every lookupable entry."""
    options: list[tuple[str, tuple[str, str]]] = []
    for name in PLANETS:
        options.append((f"☿ {name}  [dim](planet)[/dim]", (name, "Planet")))
    for name in SIGNS:
        options.append((f"♈ {name}  [dim](sign)[/dim]", (name, "Sign")))
    for info in HOUSES.values():
        options.append((f"H  {info.name}  [dim](house)[/dim]", (info.name, "House")))
    for info in ANGLES.values():
        options.append((f"∠ {info.name}  [dim](angle)[/dim]", (info.name, "Angle")))
    for info in POINTS.values():
        options.append((f"· {info.name}  [dim](point)[/dim]", (info.name, "Point")))
    return options


class InfoPickerModal(ModalScreen[None]):
    """Global reference lookup — search any planet, sign, house, angle, or point."""

    DEFAULT_CSS = """
    InfoPickerModal {
        align: center middle;
    }
    InfoPickerModal #picker-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $accent;
    }
    InfoPickerModal #picker-label {
        height: auto;
        padding: 0 0 1 0;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
    ]

    def compose(self) -> ComposeResult:
        options = _all_options()
        with Vertical(id="picker-container"):
            yield Static("Look up reference info:", id="picker-label")
            yield Select[tuple[str, str]](
                options,
                prompt="— search or select —",
                id="info-select",
                type_to_search=True,
            )
            yield Footer()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            return
        name, kind = event.value
        from hoshi_ui.screens.info_modal import InfoModal

        self.app.push_screen(InfoModal(name, kind))
