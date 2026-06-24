from __future__ import annotations

from textual.widgets import DataTable

from hoshi import Aspect, format_deg
from hoshi.aspects import fmt_orb


def populate_body_table(
    table: DataTable,
    bodies: list,
    *,
    show_houses: bool = True,
    show_dignity: bool = False,
    show_kind: bool = False,
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

    for b in bodies:
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


def populate_aspect_table(
    table: DataTable,
    aspects: list[Aspect],
    *,
    show_signs: bool = False,
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

    for asp in aspects:
        row: list[str] = [asp.body_a]
        if show_signs:
            row.append(asp.sign_a)
        row.extend([asp.symbol, asp.body_b])
        if show_signs:
            row.append(asp.sign_b)
        row.extend([asp.name, asp.kind, fmt_orb(asp.orb)])
        table.add_row(*row)
