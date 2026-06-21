"""Pydantic output models for every CLI command.

Each model serializes to JSON via ``model_dump_json()`` and renders to a Rich
terminal via ``.render(console)``.
"""

from __future__ import annotations

import csv
import io
from abc import abstractmethod

import yaml
from pydantic import BaseModel, Field
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hoshi.aspects import Aspect, KIND_ORDER, fmt_orb
from hoshi.zodiac import IAU, TROP_NAMES, format_deg


# ---------------------------------------------------------------------------
# Shared table helpers
# ---------------------------------------------------------------------------


def _new_table(title: str) -> Table:
    return Table(
        title=title,
        title_style="bold cyan",
        title_justify="left",
        box=box.SIMPLE_HEAD,
        header_style="bold",
        pad_edge=False,
    )


def _styled(val: str, approximate: bool) -> str | Text:
    return Text(val, style="yellow") if approximate else val


def _rx_str(rx: bool) -> str:
    return "℞" if rx else ""


def _sign_order(mode: str) -> list[str]:
    return [s.name for s in IAU] if mode == "realsky" else TROP_NAMES


def _render_section(
    console: Console,
    title: str,
    bodies: list[BodyEntry],
    *,
    show_houses: bool,
    show_kind: bool = False,
    show_sign: bool = True,
    show_rx: bool = True,
) -> None:
    table = _new_table(title)
    if show_kind:
        table.add_column("Kind")
    table.add_column("Name", style="bold")
    if show_sign:
        table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    if show_rx:
        table.add_column("Rx", justify="center")
    if show_houses:
        table.add_column("H", justify="right")
    for b in bodies:
        cells: list = []
        if show_kind:
            cells.append(b.kind)
        cells.append(b.name)
        if show_sign:
            cells.append(_styled(b.sign, b.approximate))
        cells.append(_styled(format_deg(b.degree), b.approximate))
        cells.append(_styled(f"{b.lon:.2f}°", b.approximate))
        if show_rx:
            cells.append(_rx_str(b.rx))
        if show_houses:
            cells.append(str(b.house) if b.house else "")
        table.add_row(*cells)
    console.print(table)


def _render_planets_section(
    console: Console, bodies: list[BodyEntry], *, show_houses: bool
) -> None:
    table = _new_table("Planets")
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Rx", justify="center")
    if show_houses:
        table.add_column("H", justify="right")
    table.add_column("Dig", justify="center")
    for b in bodies:
        row: list = [
            b.name,
            _styled(b.sign, b.approximate),
            _styled(format_deg(b.degree), b.approximate),
            _styled(f"{b.lon:.2f}°", b.approximate),
            _rx_str(b.rx),
        ]
        if show_houses:
            row.append(str(b.house) if b.house else "")
        row.append(b.dignity or "")
        table.add_row(*row)
    console.print(table)


def _render_by_sign(
    console: Console,
    bodies: list[BodyEntry],
    mode: str,
    *,
    show_houses: bool,
) -> None:
    order = _sign_order(mode)
    rank = {name: i for i, name in enumerate(order)}
    grouped: dict[str, list[BodyEntry]] = {}
    for b in bodies:
        grouped.setdefault(b.sign, []).append(b)
    for sign in sorted(grouped, key=lambda s: rank.get(s, 99)):
        rows = sorted(grouped[sign], key=lambda b: b.degree)
        table = _new_table(sign)
        table.add_column("Kind")
        table.add_column("Name", style="bold")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        table.add_column("Rx", justify="center")
        if show_houses:
            table.add_column("H", justify="right")
        for b in rows:
            cells: list = [
                b.kind,
                b.name,
                _styled(format_deg(b.degree), b.approximate),
                _styled(f"{b.lon:.2f}°", b.approximate),
                _rx_str(b.rx),
            ]
            if show_houses:
                cells.append(str(b.house) if b.house else "")
            table.add_row(*cells)
        console.print(table)


def _render_by_house(
    console: Console,
    bodies: list[BodyEntry],
    cusp_signs: list[str],
    asc_lon: float,
) -> None:
    grouped: dict[int, list[BodyEntry]] = {}
    for b in bodies:
        if b.house is not None:
            grouped.setdefault(b.house, []).append(b)
    for i, sign in enumerate(cusp_signs, start=1):
        rows = sorted(grouped.get(i, []), key=lambda b: (b.lon - asc_lon) % 360.0)
        table = _new_table(f"H{i} — {sign}")
        table.add_column("Kind")
        table.add_column("Name", style="bold")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        table.add_column("Rx", justify="center")
        for b in rows:
            cells: list = [
                b.kind,
                b.name,
                _styled(b.sign, b.approximate),
                _styled(format_deg(b.degree), b.approximate),
                _styled(f"{b.lon:.2f}°", b.approximate),
                _rx_str(b.rx),
            ]
            table.add_row(*cells)
        console.print(table)


def _render_aspects(console: Console, aspects: list[Aspect], prefix: str = "") -> None:
    if not aspects:
        return
    by_kind: dict[str, list[Aspect]] = {}
    for asp in aspects:
        by_kind.setdefault(asp.kind, []).append(asp)
    for kind in KIND_ORDER:
        group = by_kind.get(kind)
        if not group:
            continue
        table = _new_table(f"{prefix}{kind} Aspects")
        table.add_column("Body A", style="bold")
        table.add_column("", justify="center")
        table.add_column("Body B", style="bold")
        table.add_column("Aspect")
        table.add_column("Angle", justify="right")
        table.add_column("Orb", justify="right")
        for asp in group:
            table.add_row(
                asp.body_a,
                asp.symbol,
                asp.body_b,
                asp.name,
                f"{asp.angle:.0f}°",
                fmt_orb(asp.orb),
            )
        console.print(table)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


def _flatten_for_csv(data: dict | list, parent_key: str = "") -> list[dict[str, str]]:
    """Best-effort flattening of nested model data into CSV rows.

    Looks for the first list-of-dicts field to use as rows.  If the model
    is a single-record structure (e.g. InfoDetailOutput), wraps it in one row.
    """
    if isinstance(data, list):
        rows: list[dict[str, str]] = []
        for item in data:
            if isinstance(item, dict):
                rows.append(
                    {
                        k: str(v)
                        for k, v in item.items()
                        if not isinstance(v, (dict, list))
                    }
                )
            else:
                rows.append({"value": str(item)})
        return rows

    # Find the best list field to use as rows
    list_field: list | None = None
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            list_field = v
            break

    if list_field is not None:
        return [
            {k: str(v) for k, v in item.items() if not isinstance(v, (dict, list))}
            for item in list_field
        ]

    # Single-record: flatten scalar fields into one row
    return [{k: str(v) for k, v in data.items() if not isinstance(v, (dict, list))}]


class OutputModel(BaseModel):
    """Base for all command output models.

    Subclasses must implement ``render``; serialization methods for JSON,
    YAML, and CSV are provided by the base class.
    """

    @abstractmethod
    def render(self, console: Console) -> None: ...

    def model_dump_json(self, **kwargs) -> str:
        return super().model_dump_json(**kwargs)

    def dump_yaml(self) -> str:
        return yaml.dump(
            self.model_dump(mode="json"),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    def dump_csv(self) -> str:
        data = self.model_dump(mode="json")
        rows = _flatten_for_csv(data)
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Building-block models
# ---------------------------------------------------------------------------


class BodyEntry(BaseModel, frozen=True):
    kind: str
    name: str
    sign: str
    degree: float
    lon: float
    house: int | None = None
    rx: bool = False
    approximate: bool = False
    dignity: str = ""


class CuspEntry(BaseModel, frozen=True):
    house: int
    sign: str
    degree: float
    lon: float


class TallyRow(BaseModel, frozen=True):
    primary: int
    total: int


class TallyOutput(OutputModel, frozen=True):
    elements: dict[str, TallyRow]
    modalities: dict[str, TallyRow]

    def render(self, console: Console) -> None:
        table = _new_table("Tallies")
        table.add_column("Element", style="bold")
        table.add_column("Primary", justify="right")
        table.add_column("Total", justify="right")
        table.add_column("  ", no_wrap=True)
        table.add_column("Modality", style="bold")
        table.add_column("Primary", justify="right")
        table.add_column("Total", justify="right")
        elem_order = ["Fire", "Earth", "Air", "Water"]
        mod_order = ["Cardinal", "Fixed", "Mutable"]
        for i in range(max(len(elem_order), len(mod_order))):
            e = elem_order[i] if i < len(elem_order) else ""
            m = mod_order[i] if i < len(mod_order) else ""
            er = self.elements.get(e)
            mr = self.modalities.get(m)
            table.add_row(
                e,
                str(er.primary) if er else "",
                str(er.total) if er else "",
                "",
                m,
                str(mr.primary) if mr else "",
                str(mr.total) if mr else "",
            )
        console.print(table)


class ChartHeader(BaseModel, frozen=True):
    name: str = ""
    when: str = ""
    lat: float | None = None
    lon: float | None = None
    mode: str = "realsky"
    house_system: str | None = None


# ---------------------------------------------------------------------------
# Command output models
# ---------------------------------------------------------------------------


class ChartOutput(OutputModel):
    chart: ChartHeader = ChartHeader()
    warnings: list[str] = []
    bodies: list[BodyEntry] = []
    cusps: list[float] = []
    tallies: TallyOutput | None = None
    aspects: list[Aspect] | None = None

    # Rendering-only fields
    group_by: str = Field(default="category", exclude=True)
    show_cusp_table: bool = Field(default=False, exclude=True)
    show_houses: bool = Field(default=True, exclude=True)
    cusp_entries: list[CuspEntry] = Field(default_factory=list, exclude=True)
    asc_lon: float = Field(default=0.0, exclude=True)
    details: bool = Field(default=False, exclude=True)
    ayanamsa: float = Field(default=0.0, exclude=True)

    @property
    def cusp_signs(self) -> list[str]:
        return [c.sign for c in self.cusp_entries]

    def render(self, console: Console) -> None:
        h = self.chart
        loc_str = (
            f"([cyan]{h.lat:.4f}°[/cyan], [cyan]{h.lon:.4f}°[/cyan])  "
            if h.lat is not None
            else ""
        )
        houses_str = (
            f"  houses: [magenta]{h.house_system}[/magenta]" if h.house_system else ""
        )
        header = f"[bold]Chart for[/bold] {h.when}  {loc_str}mode: [magenta]{h.mode}[/magenta]{houses_str}"
        if h.name:
            header = f"[yellow]\\[{h.name.title()}][/yellow] " + header
        console.print(header)
        if h.mode == "vedic" and self.ayanamsa:
            console.print(f"Ayanamsa (Lahiri, approx): {self.ayanamsa:.4f}°")
        for w in self.warnings:
            console.print(f"[yellow]{w}[/yellow]")

        if self.group_by == "sign":
            _render_by_sign(console, self.bodies, h.mode, show_houses=self.show_houses)
        elif self.group_by == "house":
            _render_by_house(console, self.bodies, self.cusp_signs, self.asc_lon)
        else:
            by_kind: dict[str, list[BodyEntry]] = {}
            for b in self.bodies:
                by_kind.setdefault(b.kind, []).append(b)
            if self.details:
                _render_planets_section(
                    console, by_kind.get("Planet", []), show_houses=self.show_houses
                )
                if self.show_houses:
                    _render_section(
                        console,
                        "Angles",
                        by_kind.get("Angle", []),
                        show_houses=self.show_houses,
                    )
                _render_section(
                    console,
                    "Nodes",
                    by_kind.get("Node", []),
                    show_houses=self.show_houses,
                )
                _render_section(
                    console,
                    "Points",
                    by_kind.get("Point", []),
                    show_houses=self.show_houses,
                )
                if self.show_houses:
                    _render_section(
                        console,
                        "Lots",
                        by_kind.get("Lot", []),
                        show_houses=self.show_houses,
                    )
                if self.tallies:
                    self.tallies.render(console)
            else:
                _render_section(
                    console,
                    "Placements",
                    by_kind.get("Planet", []) + by_kind.get("Angle", []),
                    show_houses=self.show_houses,
                )

        if self.aspects is not None:
            _render_aspects(console, self.aspects)
        if self.show_cusp_table and self.cusp_entries:
            self._render_cusps(console)

    def _render_cusps(self, console: Console) -> None:
        table = _new_table(
            f"{self.chart.house_system.capitalize() if self.chart.house_system else ''} cusps"
        )
        table.add_column("House", justify="right")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        for c in self.cusp_entries:
            table.add_row(f"H{c.house}", c.sign, format_deg(c.degree), f"{c.lon:.2f}°")
        console.print(table)


class ChartListEntry(BaseModel, frozen=True):
    name: str
    date: str
    time: str | None = None
    tz: str = "UTC"
    lat: float | None = None
    lon: float | None = None


class ChartListOutput(OutputModel):
    charts: list[ChartListEntry] = []

    def render(self, console: Console) -> None:
        if not self.charts:
            console.print(
                "No saved charts. Use `hoshi chart add NAME DATE [TIME] --lat ... --lon ...` to create one."
            )
            return
        table = _new_table("Saved charts")
        table.add_column("Name", style="bold")
        table.add_column("Date")
        table.add_column("Time")
        table.add_column("Timezone")
        table.add_column("Lat", justify="right")
        table.add_column("Lon", justify="right")
        for c in self.charts:
            table.add_row(
                c.name.title(),
                c.date,
                c.time or "—",
                c.tz if c.time is not None else "—",
                f"{c.lat:.4f}" if c.lat is not None else "—",
                f"{c.lon:.4f}" if c.lon is not None else "—",
            )
        console.print(table)


class CuspsOutput(OutputModel):
    house_system: str = ""
    cusps: list[CuspEntry] = []

    def render(self, console: Console) -> None:
        table = _new_table(f"{self.house_system.capitalize()} cusps")
        table.add_column("House", justify="right")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        for c in self.cusps:
            table.add_row(f"H{c.house}", c.sign, format_deg(c.degree), f"{c.lon:.2f}°")
        console.print(table)


class TransitHeader(BaseModel, frozen=True):
    name: str = ""
    natal_date: str = ""
    transit_when: str = ""
    mode: str = "realsky"
    house_system: str | None = None


class TransitsOutput(OutputModel):
    header: TransitHeader = TransitHeader()
    warnings: list[str] = []
    transit_bodies: list[BodyEntry] = []
    natal_bodies: list[BodyEntry] | None = None
    aspects: list[Aspect] | None = None

    # Rendering-only
    show_houses: bool = Field(default=True, exclude=True)
    details: bool = Field(default=False, exclude=True)

    def render(self, console: Console) -> None:
        h = self.header
        houses_str = (
            f"  houses: [magenta]{h.house_system}[/magenta]" if h.house_system else ""
        )
        console.print(
            f"[bold]Transits:[/bold] [yellow]\\[{h.name.title()}][/yellow] natal {h.natal_date}  →  "
            f"transit {h.transit_when}  "
            f"mode: [magenta]{h.mode}[/magenta]{houses_str}"
        )
        for w in self.warnings:
            console.print(f"[yellow]{w}[/yellow]")

        if self.natal_bodies is not None:
            self._render_side_by_side(console)
        else:
            by_kind: dict[str, list[BodyEntry]] = {}
            for b in self.transit_bodies:
                by_kind.setdefault(b.kind, []).append(b)

            if self.details:
                _render_section(
                    console,
                    "Planets",
                    by_kind.get("Planet", []),
                    show_houses=self.show_houses,
                )
                _render_section(
                    console,
                    "Nodes",
                    by_kind.get("Node", []),
                    show_houses=self.show_houses,
                )
                _render_section(
                    console,
                    "Points",
                    by_kind.get("Point", []),
                    show_houses=self.show_houses,
                )
            else:
                title_suffix = "  (H = natal house)" if self.show_houses else ""
                _render_section(
                    console,
                    f"Transiting Planets{title_suffix}",
                    by_kind.get("Planet", []),
                    show_houses=self.show_houses,
                )

        if self.aspects is not None:
            prefix = f"{self.header.name.title()} → Transit: "
            _render_aspects(console, self.aspects, prefix)

    def _render_side_by_side(self, console: Console) -> None:
        title = "Natal vs Transits" + (
            "  (H = natal house)" if self.show_houses else ""
        )
        table = _new_table(title)
        table.add_column("Name", style="bold")
        table.add_column("Natal Sign")
        table.add_column("Natal Deg", justify="right")
        table.add_column("→", justify="center")
        table.add_column("Transit Sign")
        table.add_column("Transit Deg", justify="right")
        table.add_column("Rx", justify="center")
        if self.show_houses:
            table.add_column("H", justify="right")
        for n, t in zip(self.natal_bodies or [], self.transit_bodies):
            row: list = [
                n.name,
                _styled(n.sign, n.approximate),
                _styled(format_deg(n.degree), n.approximate),
                "→",
                t.sign,
                format_deg(t.degree),
                _rx_str(t.rx),
            ]
            if self.show_houses:
                row.append(str(t.house) if t.house else "")
            table.add_row(*row)
        console.print(table)


class CompareHeader(BaseModel, frozen=True):
    name_a: str = ""
    name_b: str = ""
    date_a: str = ""
    date_b: str = ""
    mode: str = "realsky"


class CompareOutput(OutputModel):
    header: CompareHeader = CompareHeader()
    warnings: list[str] = []
    bodies_a: list[BodyEntry] = []
    bodies_b: list[BodyEntry] = []
    aspects: list[Aspect] | None = None

    def render(self, console: Console) -> None:
        h = self.header
        console.print(
            f"[bold]Synastry:[/bold] [yellow]{h.name_a.title()}[/yellow] ({h.date_a})  ×  "
            f"[yellow]{h.name_b.title()}[/yellow] ({h.date_b})  "
            f"mode: [magenta]{h.mode}[/magenta]"
        )
        for w in self.warnings:
            console.print(f"[yellow]{w}[/yellow]")
        self._render_placements(console)
        if self.aspects is not None:
            prefix = f"{h.name_a.title()} → {h.name_b.title()}: "
            _render_aspects(console, self.aspects, prefix)

    def _render_placements(self, console: Console) -> None:
        index_a = {b.name: b for b in self.bodies_a}
        index_b = {b.name: b for b in self.bodies_b}
        all_names = list(dict.fromkeys(b.name for b in self.bodies_a + self.bodies_b))

        table = _new_table("Placements")
        table.add_column("Body", style="bold")
        table.add_column(f"{self.header.name_a.title()} Sign")
        table.add_column("Deg", justify="right")
        table.add_column("Rx", justify="center")
        table.add_column("│", style="dim", width=1)
        table.add_column(f"{self.header.name_b.title()} Sign")
        table.add_column("Deg", justify="right")
        table.add_column("Rx", justify="center")

        for name in all_names:
            ba = index_a.get(name)
            bb = index_b.get(name)
            row: list[str] = [name]
            if ba:
                row.extend([ba.sign, format_deg(ba.degree), _rx_str(ba.rx)])
            else:
                row.extend(["—", "—", ""])
            row.append("│")
            if bb:
                row.extend([bb.sign, format_deg(bb.degree), _rx_str(bb.rx)])
            else:
                row.extend(["—", "—", ""])
            table.add_row(*row)
        console.print(table)


class HouseComparisonOutput(OutputModel):
    header: ChartHeader = ChartHeader()
    bodies: list[BodyEntry] = []
    systems: list[str] = []
    house_columns: dict[str, list[int]] = {}

    def render(self, console: Console) -> None:
        h = self.header
        header = (
            f"[bold]Chart for[/bold] {h.when}  "
            f"([cyan]{h.lat:.4f}°[/cyan], [cyan]{h.lon:.4f}°[/cyan])  "
            f"mode: [magenta]{h.mode}[/magenta]"
        )
        if h.name:
            header = f"[yellow]\\[{h.name.title()}][/yellow] " + header
        console.print(header)

        table = _new_table("House comparison (yellow = differs from Porphyry)")
        table.add_column("Kind")
        table.add_column("Name", style="bold")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        for sys in self.systems:
            table.add_column(sys.capitalize(), justify="right")

        for i, b in enumerate(self.bodies):
            houses_row = [self.house_columns[s][i] for s in self.systems]
            baseline = houses_row[0] if houses_row else 0
            cells: list = [
                b.kind,
                b.name,
                b.sign,
                format_deg(b.degree),
                f"{b.lon:.2f}°",
            ]
            for h_val in houses_row:
                cells.append(
                    Text(str(h_val), style="bold yellow")
                    if h_val != baseline
                    else str(h_val)
                )
            table.add_row(*cells)
        console.print(table)


class InfoItem(BaseModel, frozen=True):
    name: str
    keywords: list[str] = []
    element: str | None = None
    modality: str | None = None
    ruler: str | None = None


class InfoListOutput(OutputModel):
    title: str = ""
    items: list[InfoItem] = []
    extra_columns: list[str] = Field(default_factory=list, exclude=True)

    def render(self, console: Console) -> None:
        table = _new_table(self.title)
        table.add_column("Name", style="bold")
        for col in self.extra_columns:
            table.add_column(col)
        table.add_column("Keywords")
        for item in self.items:
            row: list[str] = [item.name]
            for col in self.extra_columns:
                val = getattr(item, col.lower(), None)
                row.append(val or "")
            row.append(", ".join(item.keywords))
            table.add_row(*row)
        console.print(table)


class InfoDetailOutput(OutputModel):
    name: str = ""
    keywords: list[str] = []
    meaning: str = ""
    element: str | None = None
    modality: str | None = None
    ruler: str | None = None

    def render(self, console: Console) -> None:
        console.print(f"[bold cyan]{self.name}[/bold cyan]")
        if self.element:
            console.print(
                f"  Element: [magenta]{self.element}[/magenta]  "
                f"Modality: [magenta]{self.modality}[/magenta]  "
                f"Ruler: [magenta]{self.ruler}[/magenta]"
            )
        console.print(f"  Keywords: {', '.join(self.keywords)}")
        console.print()
        console.print(self.meaning)


class DeleteOutput(OutputModel):
    path: str = ""

    def render(self, console: Console) -> None:
        console.print(f"Deleted {self.path}")
