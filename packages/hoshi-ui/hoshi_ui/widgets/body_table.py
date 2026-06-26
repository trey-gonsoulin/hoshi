from __future__ import annotations

from collections import defaultdict

from textual.widgets import DataTable

from hoshi import Aspect, format_deg
from hoshi.aspects import fmt_orb
from hoshi.output import BodyEntry

_BODY_KIND_ORDER = ["Planet", "Angle", "Node", "Point", "Lot"]
_ASPECT_KIND_ORDER = ["Major", "Minor", "Micro"]


def populate_body_table(
    table: DataTable,
    bodies: list[BodyEntry],
    *,
    show_houses: bool = True,
    show_dignity: bool = False,
    show_kind: bool = False,
    group_by: str = "category",
) -> None:
    table.clear(columns=True)
    if show_kind:
        table.add_column("Kind", key="kind")
    table.add_column("Name", key="name")
    table.add_column("Sign", key="sign")
    table.add_column("Degree", key="degree")
    table.add_column("Lon", key="lon")
    table.add_column("Rx", key="rx")
    if show_houses:
        table.add_column("H", key="house")
    if show_dignity:
        table.add_column("Dig", key="dignity")

    n_extra = (
        (1 if show_kind else 0) + (1 if show_houses else 0) + (1 if show_dignity else 0)
    )
    n_cols = 5 + n_extra  # name sign degree lon rx + extras

    def _add_header(label: str) -> None:
        row = [""] * n_cols
        row[0] = f"[bold dim]── {label} ──[/bold dim]"
        table.add_row(*row)

    def _add_body(b: BodyEntry) -> None:
        row: list[str] = []
        if show_kind:
            row.append(b.kind)
        row.extend(
            [
                b.name,
                b.sign,
                format_deg(b.degree),
                f"{b.lon:.2f}°",
                "℞" if b.rx else "",
            ]
        )
        if show_houses:
            row.append(str(b.house) if b.house else "")
        if show_dignity:
            row.append(b.dignity or "")
        table.add_row(*row)

    if group_by == "sign":
        grouped: dict[str, list[BodyEntry]] = defaultdict(list)
        for b in bodies:
            grouped[b.sign].append(b)
        seen_signs: list[str] = []
        for b in bodies:
            if b.sign not in seen_signs:
                seen_signs.append(b.sign)
        for sign in seen_signs:
            _add_header(sign)
            for b in grouped[sign]:
                _add_body(b)

    elif group_by == "house":
        grouped_h: dict[int | None, list[BodyEntry]] = defaultdict(list)
        for b in bodies:
            grouped_h[b.house].append(b)
        seen_houses: list[int | None] = []
        for b in bodies:
            if b.house not in seen_houses:
                seen_houses.append(b.house)
        for house in seen_houses:
            label = f"House {house}" if house is not None else "No House"
            _add_header(label)
            for b in grouped_h[house]:
                _add_body(b)

    elif group_by == "category":
        grouped_k: dict[str, list[BodyEntry]] = defaultdict(list)
        for b in bodies:
            grouped_k[b.kind].append(b)
        present_kinds = [k for k in _BODY_KIND_ORDER if k in grouped_k]
        for kind in present_kinds:
            _add_header(kind + "s" if not kind.endswith("s") else kind)
            for b in grouped_k[kind]:
                _add_body(b)

    else:
        for b in bodies:
            _add_body(b)


def populate_aspect_table(
    table: DataTable,
    aspects: list[Aspect],
    *,
    show_signs: bool = False,
    group_by: str = "category",
) -> None:
    table.clear(columns=True)
    table.add_column("Body A", key="body_a")
    if show_signs:
        table.add_column("Sign", key="sign_a")
    table.add_column("", key="symbol")
    table.add_column("Body B", key="body_b")
    if show_signs:
        table.add_column("Sign", key="sign_b")
    table.add_column("Aspect", key="aspect")
    table.add_column("Kind", key="kind")
    table.add_column("Orb", key="orb")

    n_cols = 5 + (
        2 if show_signs else 0
    )  # body_a symbol body_b aspect kind orb + signs

    def _add_header(label: str) -> None:
        row = [""] * n_cols
        row[0] = f"[bold dim]── {label} ──[/bold dim]"
        table.add_row(*row)

    def _add_aspect(asp: Aspect) -> None:
        row: list[str] = [asp.body_a]
        if show_signs:
            row.append(asp.sign_a)
        row.extend([asp.symbol, asp.body_b])
        if show_signs:
            row.append(asp.sign_b)
        row.extend([asp.name, asp.kind, fmt_orb(asp.orb)])
        table.add_row(*row)

    if group_by == "planet":
        grouped_p: dict[str, list[Aspect]] = defaultdict(list)
        for asp in aspects:
            grouped_p[asp.body_a].append(asp)
        seen_planets: list[str] = []
        for asp in aspects:
            if asp.body_a not in seen_planets:
                seen_planets.append(asp.body_a)
        for planet in seen_planets:
            _add_header(planet)
            for asp in grouped_p[planet]:
                _add_aspect(asp)

    elif group_by == "category":
        grouped_k: dict[str, list[Aspect]] = defaultdict(list)
        for asp in aspects:
            grouped_k[asp.kind].append(asp)
        present_kinds = [k for k in _ASPECT_KIND_ORDER if k in grouped_k]
        for kind in present_kinds:
            _add_header(kind)
            for asp in grouped_k[kind]:
                _add_aspect(asp)

    else:
        for asp in aspects:
            _add_aspect(asp)
