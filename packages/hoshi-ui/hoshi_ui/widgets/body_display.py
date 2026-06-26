from __future__ import annotations

from textual.widgets import ListItem, Static

from hoshi import SIGN_ATTRS, SIGN_GLYPHS, format_deg
from hoshi.info import ANGLES, PLANETS, POINTS
from hoshi.output import BodyEntry, TallyOutput

ELEMENT_COLORS: dict[str, str] = {
    "Fire": "red",
    "Earth": "green",
    "Air": "yellow",
    "Water": "blue",
}

_NAME_WIDTH = 14
_SIGN_WIDTH = 16
_HOUSE_WIDTH = 3  # "H" + up to 2 digits
_BAR_WIDTH = 12  # fixed dot-bar length


def _body_line(b: BodyEntry, *, show_house: bool = True) -> str:
    element, _ = SIGN_ATTRS.get(b.sign, ("", ""))
    color = ELEMENT_COLORS.get(element, "default")
    sign_glyph = SIGN_GLYPHS.get(b.sign, "")

    # Only single-char symbols work as glyphs (multi-char entries like "Asc"/"MC"
    # are not glyphs — render them as a blank slot so alignment is consistent).
    glyph = b.symbol if (b.symbol and len(b.symbol) == 1) else ""
    glyph_slot = f"{glyph} " if glyph else "  "

    sign_display = f"{sign_glyph} {b.sign}"

    line = (
        f"{glyph_slot}{b.name:<{_NAME_WIDTH}}"
        f"  [{color}]{sign_display:<{_SIGN_WIDTH}}[/{color}]"
        f"  {format_deg(b.degree)}"
    )
    if show_house and b.house:
        house_str = f"H{b.house}"
        line += f"  [dim]{house_str:<{_HOUSE_WIDTH}}[/dim]"
    if b.rx:
        line += "  [dim]℞[/dim]"
    if b.dignity:
        line += f"  [dim]{b.dignity}[/dim]"
    return line


def render_bodies(
    bodies: list[BodyEntry],
    *,
    show_house: bool = True,
    group_by: str = "category",
) -> str:
    if not bodies:
        return "[dim]—[/dim]"

    lines: list[str] = []

    if group_by == "sign":
        seen: list[str] = []
        grouped: dict[str, list[BodyEntry]] = {}
        for b in bodies:
            grouped.setdefault(b.sign, []).append(b)
            if b.sign not in seen:
                seen.append(b.sign)
        for sign in seen:
            lines.append(f"[bold dim]── {sign} ──[/bold dim]")
            for b in grouped[sign]:
                lines.append(_body_line(b, show_house=show_house))

    elif group_by == "house":
        seen_h: list[int | None] = []
        grouped_h: dict[int | None, list[BodyEntry]] = {}
        for b in bodies:
            grouped_h.setdefault(b.house, []).append(b)
            if b.house not in seen_h:
                seen_h.append(b.house)
        for house in seen_h:
            label = f"House {house}" if house is not None else "No House"
            lines.append(f"[bold dim]── {label} ──[/bold dim]")
            for b in grouped_h[house]:
                lines.append(_body_line(b, show_house=show_house))

    else:
        for b in bodies:
            lines.append(_body_line(b, show_house=show_house))

    return "\n".join(lines)


def _body_tooltip(b: BodyEntry) -> str:
    """Return a short keyword tooltip string for a body."""
    info = None
    if b.kind == "Planet":
        info = PLANETS.get(b.name)
    elif b.kind == "Angle":
        for entry in ANGLES.values():
            if entry.name == b.name or b.name.lower() in [
                a.lower() for a in entry.aliases
            ]:
                info = entry
                break
    elif b.kind in ("Node", "Point", "Lot"):
        for entry in POINTS.values():
            if entry.name == b.name or b.name.lower() in [
                a.lower() for a in entry.aliases
            ]:
                info = entry
                break
    if info:
        return "  ·  ".join(info.keywords)
    return ""


def build_list_items(
    bodies: list[BodyEntry],
    *,
    show_house: bool = True,
    group_by: str = "category",
) -> list[ListItem]:
    """Return ListItems for body rows with keyword tooltips."""
    items: list[ListItem] = []

    def _item(b: BodyEntry) -> ListItem:
        label = _body_line(b, show_house=show_house)
        item = ListItem(Static(label))
        tooltip = _body_tooltip(b)
        if tooltip:
            item.tooltip = tooltip
        # Store lookup key for InfoModal
        item.data = {"name": b.name, "kind": b.kind}  # type: ignore[attr-defined]
        return item

    if group_by == "sign":
        seen: list[str] = []
        grouped: dict[str, list[BodyEntry]] = {}
        for b in bodies:
            grouped.setdefault(b.sign, []).append(b)
            if b.sign not in seen:
                seen.append(b.sign)
        for sign in seen:
            items.append(ListItem(Static(f"[bold dim]── {sign} ──[/bold dim]")))
            for b in grouped[sign]:
                items.append(_item(b))

    elif group_by == "house":
        seen_h: list[int | None] = []
        grouped_h: dict[int | None, list[BodyEntry]] = {}
        for b in bodies:
            grouped_h.setdefault(b.house, []).append(b)
            if b.house not in seen_h:
                seen_h.append(b.house)
        for house in seen_h:
            label = f"House {house}" if house is not None else "No House"
            items.append(ListItem(Static(f"[bold dim]── {label} ──[/bold dim]")))
            for b in grouped_h[house]:
                items.append(_item(b))

    else:
        for b in bodies:
            items.append(_item(b))

    return items


def render_tally(tally: TallyOutput) -> str:
    def _row(label: str, primary: int, total: int, color: str = "default") -> str:
        filled = "●" * primary
        empty = "○" * (total - primary)
        bar = f"{filled + empty:<{_BAR_WIDTH}}"
        p = f"{primary:>2}"
        t = f"{total:>2}"
        label_str = (
            f"[{color}]{label:<10}[/{color}]" if color != "default" else f"{label:<10}"
        )
        return f"  {label_str}  {bar}  [dim]{p} primary · {t} total[/dim]"

    lines: list[str] = ["[bold]Elements[/bold]"]
    for elem, row in tally.elements.items():
        lines.append(
            _row(elem, row.primary, row.total, ELEMENT_COLORS.get(elem, "default"))
        )

    lines += ["", "[bold]Modalities[/bold]"]
    for mod, row in tally.modalities.items():
        lines.append(_row(mod, row.primary, row.total))

    return "\n".join(lines)
