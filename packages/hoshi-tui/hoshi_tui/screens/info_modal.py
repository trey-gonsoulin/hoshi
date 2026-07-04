from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Static

from hoshi.info import ANGLES, HOUSES, PLANETS, POINTS, SIGNS, Info, SignInfo


def _lookup(name: str, kind: str | None = None) -> Info | SignInfo | None:
    """Find an Info entry by body name, kind hint, sign name, or house number."""
    # Try planet
    if kind == "Planet" or kind is None:
        if name in PLANETS:
            return PLANETS[name]
    # Try sign
    if name in SIGNS:
        return SIGNS[name]
    # Try angle (by display name or alias)
    for info in ANGLES.values():
        if info.name == name or name.lower() in [a.lower() for a in info.aliases]:
            return info
    # Try points (by name or alias)
    for info in POINTS.values():
        if info.name == name or name.lower() in [a.lower() for a in info.aliases]:
            return info
    # Try house number embedded in name like "1st House"
    for h, info in HOUSES.items():
        if info.name == name or str(h) == name:
            return info
    # Fallback: case-insensitive planet search
    for pname, info in PLANETS.items():
        if pname.lower() == name.lower():
            return info
    return None


def lookup_by_kind(name: str, kind: str) -> Info | SignInfo | None:
    if kind == "Planet":
        return PLANETS.get(name)
    if kind == "Angle":
        for info in ANGLES.values():
            if info.name == name or name.lower() in [a.lower() for a in info.aliases]:
                return info
    if kind in ("Node", "Point", "Lot"):
        for info in POINTS.values():
            if info.name == name or name.lower() in [a.lower() for a in info.aliases]:
                return info
    return _lookup(name)


class InfoModal(ModalScreen[None]):
    """Show reference info for a planet, sign, house, or point."""

    DEFAULT_CSS = """
    InfoModal {
        align: center middle;
    }
    InfoModal #info-container {
        width: 70;
        height: auto;
        max-height: 80vh;
        padding: 1 2;
        background: $surface;
        border: round $accent;
    }
    InfoModal #info-name {
        height: auto;
        text-style: bold;
        color: $accent;
    }
    InfoModal #info-meta {
        height: auto;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    InfoModal #info-keywords {
        height: auto;
        padding: 0 0 1 0;
    }
    InfoModal #info-meaning {
        height: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
    ]

    def __init__(self, name: str, kind: str | None = None) -> None:
        super().__init__()
        self._info = lookup_by_kind(name, kind or "") if kind else _lookup(name)
        self._name = name

    def compose(self) -> ComposeResult:
        info = self._info
        if info is None:
            with Vertical(id="info-container"):
                yield Static(self._name, id="info-name")
                yield Static(
                    "[dim]No reference info available.[/dim]", id="info-meaning"
                )
                yield Footer()
            return

        keywords = "  ·  ".join(info.keywords)
        meta_parts: list[str] = []
        if isinstance(info, SignInfo):
            meta_parts += [info.element, info.modality, f"ruled by {info.ruler}"]
        elif hasattr(info, "element") and info.element:
            meta_parts.append(info.element)

        with Vertical(id="info-container"):
            yield Static(info.name, id="info-name")
            if meta_parts:
                yield Static("  ·  ".join(meta_parts), id="info-meta")
            yield Static(f"[dim]{keywords}[/dim]", id="info-keywords")
            yield Static(info.meaning, id="info-meaning")
            yield Footer()
