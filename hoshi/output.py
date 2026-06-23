"""Pydantic output models for every CLI command.

Each model serializes to JSON via ``model_dump_json()`` and renders to a Rich
terminal via ``.render(console)``.
"""

from __future__ import annotations

import csv
import io
from abc import abstractmethod
from datetime import datetime

import yaml
from pydantic import BaseModel, Field
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from hoshi.aspects import (
    Aspect,
    KIND_ORDER,
    compute_aspects,
    compute_inter_aspects,
    fmt_orb,
)
from hoshi.chart import (
    PLACEHOLDER_LAT,
    PLACEHOLDER_LON,
    Chart,
    HouseSystem,
    uncertain_signs,
)
from hoshi.dignities import DIGNITY_SYMBOLS, dignity_for, element_modality_tally
from hoshi.houses import house_13_arc, house_from_cusps
from hoshi.store import ChartInput
from hoshi.zodiac import IAU, TROP_NAMES, Placement, format_deg


ANGLE_DISPLAY_NAMES: dict[str, str] = {
    "asc": "Ascendant",
    "mc": "Midheaven",
    "ic": "Imum Coeli",
    "dsc": "Descendant",
    "vertex": "Vertex",
    "antivertex": "Antivertex",
}

NODE_NAMES = {"N.Node", "S.Node"}


class BodySelection(BaseModel, frozen=True):
    """Which body groups to include when assembling display rows."""

    details: bool = False
    angles: bool = True
    lots: bool = True
    houses: bool = True
    uncertain_pids: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Shared table helpers
# ---------------------------------------------------------------------------


def _new_table(title: str = "") -> Table:
    return Table(
        title=title or None,
        title_style="bold cyan",
        title_justify="left",
        box=box.SIMPLE_HEAD,
        header_style="bold",
        pad_edge=False,
    )


def _panel(title: str, content: Table | Text) -> Panel:
    return Panel(
        content,
        title=f"[bold cyan]{title}[/bold cyan]",
        title_align="left",
        border_style="dim",
        padding=(0, 1),
        expand=False,
    )


def _styled(val: str, approximate: bool) -> str | Text:
    return Text(val, style="yellow") if approximate else val


def _rx_str(rx: bool) -> str:
    return "℞" if rx else ""


def _sign_order(mode: str) -> list[str]:
    return [s.name for s in IAU] if mode == "realsky" else TROP_NAMES


def _build_bodies(
    chart: Chart, mode: str, sel: BodySelection = BodySelection()
) -> list[BodyEntry]:
    def house_of(h: int | None) -> int | None:
        return h if sel.houses else None

    bodies: list[BodyEntry] = []
    for p in chart.planets:
        pl = p.placed.placement(mode)
        dig = dignity_for(p.pid.capitalize(), pl.name)
        bodies.append(
            BodyEntry(
                kind="Planet",
                name=p.pid.capitalize(),
                sign=pl.name,
                degree=round(pl.deg, 4),
                lon=round(p.placed.lon, 4),
                house=house_of(p.house),
                rx=p.pos.retrograde,
                approximate=p.pid in sel.uncertain_pids,
                dignity=DIGNITY_SYMBOLS.get(dig, "") if dig else "",
            )
        )
    if sel.angles:
        angles = (
            chart.angles
            if sel.details
            else [a for a in chart.angles if a.name == "asc"]
        )
        for a in angles:
            pl = a.placed.placement(mode)
            bodies.append(
                BodyEntry(
                    kind="Angle",
                    name=ANGLE_DISPLAY_NAMES[a.name],
                    sign=pl.name,
                    degree=round(pl.deg, 4),
                    lon=round(a.placed.lon, 4),
                    house=house_of(a.house),
                )
            )
    if sel.details:
        for pt in chart.points:
            pl = pt.placed.placement(mode)
            kind = "Node" if pt.name in NODE_NAMES else "Point"
            bodies.append(
                BodyEntry(
                    kind=kind,
                    name=pt.name,
                    sign=pl.name,
                    degree=round(pl.deg, 4),
                    lon=round(pt.placed.lon, 4),
                    house=house_of(pt.house),
                )
            )
        if sel.lots:
            for pt in chart.lots:
                pl = pt.placed.placement(mode)
                bodies.append(
                    BodyEntry(
                        kind="Lot",
                        name=pt.name,
                        sign=pl.name,
                        degree=round(pl.deg, 4),
                        lon=round(pt.placed.lon, 4),
                        house=house_of(pt.house),
                    )
                )
    return bodies


def _build_cusp_entries(chart: Chart, mode: str) -> list[CuspEntry]:
    entries: list[CuspEntry] = []
    for i, c in enumerate(chart.cusps, start=1):
        p = Placement.for_mode(c, mode, ayanamsa=chart.ayanamsa)
        entries.append(CuspEntry(house=i, sign=p.name, degree=p.deg, lon=c))
    return entries


def _build_transit_bodies(
    transit: Chart,
    natal: Chart,
    mode: str,
    details: bool,
    *,
    natal_loc_known: bool = True,
) -> list[BodyEntry]:
    natal_asc = next(a.placed.lon for a in natal.angles if a.name == "asc")

    def natal_house(lon: float) -> int | None:
        if not natal_loc_known:
            return None
        if natal.house_system == "arc13":
            return house_13_arc(lon, natal_asc)
        return house_from_cusps(lon, natal.cusps)

    bodies: list[BodyEntry] = []
    for p in transit.planets:
        pl = p.placed.placement(mode)
        bodies.append(
            BodyEntry(
                kind="Planet",
                name=p.pid.capitalize(),
                sign=pl.name,
                degree=round(pl.deg, 4),
                lon=round(p.placed.lon, 4),
                house=natal_house(p.placed.lon),
                rx=p.pos.retrograde,
            )
        )
    if details:
        for pt in transit.points:
            pl = pt.placed.placement(mode)
            kind = "Node" if pt.name in NODE_NAMES else "Point"
            bodies.append(
                BodyEntry(
                    kind=kind,
                    name=pt.name,
                    sign=pl.name,
                    degree=round(pl.deg, 4),
                    lon=round(pt.placed.lon, 4),
                    house=natal_house(pt.placed.lon),
                )
            )
    return bodies


def _body_table(
    title: str,
    bodies: list[BodyEntry],
    *,
    show_kind: bool = False,
    show_sign: bool = True,
    show_rx: bool = True,
    show_houses: bool = False,
    show_dignity: bool = False,
) -> Table:
    """Build a body table with a consistent column set and styled cells.

    Columns (in order): [Kind] Name [Sign] Degree Lon [Rx] [H] [Dig]. Every
    body-row renderer routes through this so column order and the
    approximate/retrograde styling live in one place.
    """
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
    if show_dignity:
        table.add_column("Dig", justify="center")
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
        if show_dignity:
            cells.append(b.dignity or "")
        table.add_row(*cells)
    return table


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
    table = _body_table(
        "",
        bodies,
        show_kind=show_kind,
        show_sign=show_sign,
        show_rx=show_rx,
        show_houses=show_houses,
    )
    console.print()
    console.print(_panel(title, table))


def _render_planets_section(
    console: Console, bodies: list[BodyEntry], *, show_houses: bool
) -> None:
    table = _body_table("", bodies, show_houses=show_houses, show_dignity=True)
    console.print()
    console.print(_panel("Planets", table))


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
        table = _body_table(
            "", rows, show_kind=True, show_sign=False, show_houses=show_houses
        )
        console.print()
        console.print(_panel(sign, table))


def _render_by_house(
    console: Console,
    bodies: list[BodyEntry],
    cusp_entries: list[CuspEntry],
    asc_lon: float,
) -> None:
    grouped: dict[int, list[BodyEntry]] = {}
    for b in bodies:
        if b.house is not None:
            grouped.setdefault(b.house, []).append(b)
    n = len(cusp_entries)

    for idx, cusp in enumerate(cusp_entries):
        rows = sorted(
            grouped.get(cusp.house, []), key=lambda b: (b.lon - asc_lon) % 360.0
        )
        next_lon = cusp_entries[(idx + 1) % n].lon
        title = f"H{cusp.house} │ {cusp.sign} │ {format_deg(cusp.lon)} – {format_deg(next_lon)}"
        if rows:
            content: Table | Text = _body_table("", rows, show_kind=True)
        else:
            content = Text("(empty)")
        console.print()
        console.print(_panel(title, content))


def _aspect_table(
    aspects: list[Aspect],
    *,
    show_signs: bool = False,
    show_kind: bool = False,
) -> Table:
    table = _new_table()
    table.add_column("Body A", style="bold")
    if show_signs:
        table.add_column("Sign")
    table.add_column("", justify="center")
    table.add_column("Body B", style="bold")
    if show_signs:
        table.add_column("Sign")
    table.add_column("Aspect")
    if show_kind:
        table.add_column("Kind")
    table.add_column("Angle", justify="right")
    table.add_column("Orb", justify="right")
    for asp in aspects:
        row: list[str] = [asp.body_a]
        if show_signs:
            row.append(asp.sign_a)
        row.append(asp.symbol)
        row.append(asp.body_b)
        if show_signs:
            row.append(asp.sign_b)
        row.append(asp.name)
        if show_kind:
            row.append(asp.kind)
        row.extend([f"{asp.angle:.0f}°", fmt_orb(asp.orb)])
        table.add_row(*row)
    return table


def _render_aspects(
    console: Console,
    aspects: list[Aspect],
    prefix: str = "",
    *,
    group_by: str = "category",
    body_houses: dict[str, int] | None = None,
    mode: str = "realsky",
) -> None:
    if not aspects:
        return
    show_signs = any(asp.sign_a or asp.sign_b for asp in aspects)

    if group_by == "planet":
        seen: dict[str, list[Aspect]] = {}
        for asp in aspects:
            seen.setdefault(asp.body_a, []).append(asp)
            seen.setdefault(asp.body_b, []).append(asp)
        for body, group in seen.items():
            table = _aspect_table(group, show_signs=show_signs, show_kind=True)
            console.print()
            console.print(_panel(f"{prefix}{body}", table))
    elif group_by == "sign":
        order = _sign_order(mode)
        rank = {name: i for i, name in enumerate(order)}
        by_sign: dict[str, list[Aspect]] = {}
        for asp in aspects:
            if asp.sign_a:
                by_sign.setdefault(asp.sign_a, []).append(asp)
            if asp.sign_b and asp.sign_b != asp.sign_a:
                by_sign.setdefault(asp.sign_b, []).append(asp)
        for sign in sorted(by_sign, key=lambda s: rank.get(s, 99)):
            table = _aspect_table(by_sign[sign], show_signs=show_signs, show_kind=True)
            console.print()
            console.print(_panel(f"{prefix}{sign}", table))
    elif group_by == "house" and body_houses:
        by_house: dict[int, list[Aspect]] = {}
        for asp in aspects:
            h_a = body_houses.get(asp.body_a)
            h_b = body_houses.get(asp.body_b)
            if h_a is not None:
                by_house.setdefault(h_a, []).append(asp)
            if h_b is not None and h_b != h_a:
                by_house.setdefault(h_b, []).append(asp)
        for house in sorted(by_house):
            table = _aspect_table(
                by_house[house], show_signs=show_signs, show_kind=True
            )
            console.print()
            console.print(_panel(f"{prefix}House {house}", table))
    else:
        by_kind: dict[str, list[Aspect]] = {}
        for asp in aspects:
            by_kind.setdefault(asp.kind, []).append(asp)
        for kind in KIND_ORDER:
            group = by_kind.get(kind)
            if not group:
                continue
            table = _aspect_table(group, show_signs=show_signs)
            console.print()
            console.print(_panel(f"{prefix}{kind} Aspects", table))


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


class TallyOutput(OutputModel):
    elements: dict[str, TallyRow]
    modalities: dict[str, TallyRow]

    @classmethod
    def build(cls, chart: Chart, mode: str, *, show_full: bool = True) -> TallyOutput:
        tally = element_modality_tally(
            chart, mode, include_angles=show_full, include_lots=show_full
        )
        return cls(
            elements={
                k: TallyRow(
                    primary=tally["primary"]["elements"].get(k, 0),
                    total=tally["total"]["elements"].get(k, 0),
                )
                for k in ["Fire", "Earth", "Air", "Water"]
            },
            modalities={
                k: TallyRow(
                    primary=tally["primary"]["modalities"].get(k, 0),
                    total=tally["total"]["modalities"].get(k, 0),
                )
                for k in ["Cardinal", "Fixed", "Mutable"]
            },
        )

    def render(self, console: Console) -> None:
        table = _new_table()
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
        console.print()
        console.print(_panel("Tallies", table))


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

    @classmethod
    def build(
        cls,
        ci: ChartInput,
        chart: Chart,
        mode: str,
        *,
        details: bool = False,
        aspects: bool = False,
        group_by: str = "category",
        show_cusps: bool = False,
    ) -> ChartOutput:
        time_known = ci.time_known
        loc_known = ci.location_known
        show_full = time_known and loc_known
        uncertain = uncertain_signs(ci, mode) if not time_known else frozenset()

        when_str = (
            ci.to_datetime().strftime("%Y-%m-%d")
            if not time_known
            else ci.to_datetime().isoformat()
        )

        warnings: list[str] = []
        if not time_known:
            if uncertain:
                names = ", ".join(p.capitalize() for p in uncertain)
                warnings.append(
                    f"⚠ Birth time unknown — {names} may be in a different sign (highlighted)"
                )
            else:
                warnings.append(
                    "⚠ Birth time unknown — all signs stable on this date, degrees approximate"
                )
        if not loc_known:
            warnings.append("⚠ Birth location unknown — angles and houses omitted")

        effective_group_by = group_by
        if group_by == "house" and not show_full:
            warnings.append(
                "⚠ Cannot group by house without known birth time and location; using category grouping."
            )
            effective_group_by = "category"

        bodies = _build_bodies(
            chart,
            mode,
            BodySelection(
                details=details,
                angles=show_full,
                lots=show_full,
                houses=show_full,
                uncertain_pids=uncertain,
            ),
        )
        cusp_entries = _build_cusp_entries(chart, mode) if show_full else []
        tallies = (
            TallyOutput.build(chart, mode, show_full=show_full) if details else None
        )
        aspect_list = compute_aspects(chart, details, mode) if aspects else None

        return cls(
            chart=ChartHeader(
                name=ci.name,
                when=when_str,
                lat=ci.lat,
                lon=ci.lon,
                mode=mode,
                house_system=chart.house_system if show_full else None,
            ),
            warnings=warnings,
            bodies=bodies,
            cusps=[round(c, 4) for c in chart.cusps] if show_full else [],
            tallies=tallies,
            aspects=aspect_list,
            group_by=effective_group_by,
            show_cusp_table=show_cusps and show_full,
            show_houses=show_full,
            cusp_entries=cusp_entries,
            asc_lon=next((a.placed.lon for a in chart.angles if a.name == "asc"), 0.0),
            details=details,
            ayanamsa=chart.ayanamsa,
        )

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
            _render_by_house(console, self.bodies, self.cusp_entries, self.asc_lon)
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
            body_houses = {b.name: b.house for b in self.bodies if b.house is not None}
            _render_aspects(
                console,
                self.aspects,
                group_by=self.group_by,
                body_houses=body_houses,
                mode=self.chart.mode,
            )
        if self.show_cusp_table and self.cusp_entries:
            self._render_cusps(console)

    def _render_cusps(self, console: Console) -> None:
        title = f"{self.chart.house_system.capitalize() if self.chart.house_system else ''} cusps"
        table = _new_table()
        table.add_column("House", justify="right")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        for c in self.cusp_entries:
            table.add_row(f"H{c.house}", c.sign, format_deg(c.degree), f"{c.lon:.2f}°")
        console.print()
        console.print(_panel(title, table))


class ChartListEntry(BaseModel, frozen=True):
    name: str
    date: str
    time: str | None = None
    tz: str = "UTC"
    lat: float | None = None
    lon: float | None = None


class ChartListOutput(OutputModel):
    charts: list[ChartListEntry] = []

    @classmethod
    def build(cls) -> ChartListOutput:
        from hoshi import store

        return cls(
            charts=[
                ChartListEntry(
                    name=ci.name,
                    date=ci.date,
                    time=ci.time,
                    tz=ci.tz,
                    lat=ci.lat,
                    lon=ci.lon,
                )
                for ci in store.list_all()
            ]
        )

    def render(self, console: Console) -> None:
        if not self.charts:
            console.print(
                "No saved charts. Use `hoshi chart add NAME DATE [TIME] --lat ... --lon ...` to create one."
            )
            return
        table = _new_table()
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
        console.print()
        console.print(_panel("Saved charts", table))


class CuspsOutput(OutputModel):
    house_system: str = ""
    cusps: list[CuspEntry] = []

    @classmethod
    def build(cls, chart: Chart, mode: str) -> CuspsOutput:
        return cls(
            house_system=chart.house_system,
            cusps=_build_cusp_entries(chart, mode),
        )

    def render(self, console: Console) -> None:
        title = f"{self.house_system.capitalize()} cusps"
        table = _new_table()
        table.add_column("House", justify="right")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        for c in self.cusps:
            table.add_row(f"H{c.house}", c.sign, format_deg(c.degree), f"{c.lon:.2f}°")
        console.print()
        console.print(_panel(title, table))


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
    group_by: str = Field(default="category", exclude=True)

    @classmethod
    def build(
        cls,
        ci: ChartInput,
        chart_natal: Chart,
        transit_dt: datetime,
        mode: str,
        *,
        details: bool = False,
        aspects: bool = False,
        natal: bool = False,
        group_by: str = "category",
    ) -> TransitsOutput:
        natal_time_known = ci.time_known
        natal_loc_known = ci.location_known

        chart_transit = Chart.positions_only(transit_dt)

        warnings: list[str] = []
        if not natal_time_known:
            warnings.append("⚠ Natal time unknown — natal planet degrees approximate")
        if not natal_loc_known:
            warnings.append(
                "⚠ Natal location unknown — natal house placement of transits omitted"
            )

        transit_bodies = _build_transit_bodies(
            chart_transit,
            chart_natal,
            mode,
            details,
            natal_loc_known=natal_loc_known,
        )
        natal_bodies = None
        if natal:
            natal_uncertain = (
                uncertain_signs(ci, mode) if not natal_time_known else frozenset()
            )
            natal_bodies = _build_bodies(
                chart_natal,
                mode,
                BodySelection(
                    details=details,
                    angles=False,
                    lots=False,
                    houses=False,
                    uncertain_pids=natal_uncertain,
                ),
            )

        aspect_list = (
            compute_inter_aspects(chart_natal, chart_transit, details, mode)
            if aspects
            else None
        )

        return cls(
            header=TransitHeader(
                name=ci.name,
                natal_date=ci.date,
                transit_when=transit_dt.strftime("%Y-%m-%d %H:%M %Z").strip(),
                mode=mode,
                house_system=chart_natal.house_system if natal_loc_known else None,
            ),
            warnings=warnings,
            transit_bodies=transit_bodies,
            natal_bodies=natal_bodies,
            aspects=aspect_list,
            show_houses=natal_loc_known,
            details=details,
            group_by=group_by,
        )

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
            body_houses = {
                b.name: b.house for b in self.transit_bodies if b.house is not None
            }
            _render_aspects(
                console,
                self.aspects,
                prefix,
                group_by=self.group_by,
                body_houses=body_houses,
                mode=self.header.mode,
            )

    def _render_side_by_side(self, console: Console) -> None:
        title = "Natal vs Transits" + (
            "  (H = natal house)" if self.show_houses else ""
        )
        table = _new_table()
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
        console.print()
        console.print(_panel(title, table))


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

    # Rendering-only
    group_by: str = Field(default="category", exclude=True)

    @classmethod
    def build(
        cls,
        ci_a: ChartInput,
        ci_b: ChartInput,
        chart_a: Chart,
        chart_b: Chart,
        mode: str,
        *,
        details: bool = False,
        aspects: bool = False,
        group_by: str = "category",
    ) -> CompareOutput:
        show_full_a = ci_a.time_known and ci_a.location_known
        show_full_b = ci_b.time_known and ci_b.location_known

        warnings: list[str] = []
        for ci in (ci_a, ci_b):
            if not ci.time_known:
                warnings.append(
                    f"⚠ {ci.name.title()} birth time unknown — planet positions approximate"
                )
            if not ci.location_known:
                warnings.append(f"⚠ {ci.name.title()} birth location unknown")

        bodies_a = _build_bodies(
            chart_a,
            mode,
            BodySelection(
                details=details, angles=show_full_a, lots=show_full_a, houses=False
            ),
        )
        bodies_b = _build_bodies(
            chart_b,
            mode,
            BodySelection(
                details=details, angles=show_full_b, lots=show_full_b, houses=False
            ),
        )

        aspect_list = (
            compute_inter_aspects(chart_a, chart_b, details, mode) if aspects else None
        )

        return cls(
            header=CompareHeader(
                name_a=ci_a.name,
                name_b=ci_b.name,
                date_a=ci_a.date,
                date_b=ci_b.date,
                mode=mode,
            ),
            warnings=warnings,
            bodies_a=bodies_a,
            bodies_b=bodies_b,
            aspects=aspect_list,
            group_by=group_by,
        )

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
            _render_aspects(
                console,
                self.aspects,
                prefix,
                group_by=self.group_by,
                mode=h.mode,
            )

    def _render_placements(self, console: Console) -> None:
        index_a = {b.name: b for b in self.bodies_a}
        index_b = {b.name: b for b in self.bodies_b}
        all_names = list(dict.fromkeys(b.name for b in self.bodies_a + self.bodies_b))

        table = _new_table()
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
        console.print()
        console.print(_panel("Placements", table))


class HouseComparisonOutput(OutputModel):
    header: ChartHeader = ChartHeader()
    bodies: list[BodyEntry] = []
    systems: list[str] = []
    house_columns: dict[str, list[int | None]] = {}

    @classmethod
    def build(
        cls, ci: ChartInput, mode: str, *, details: bool
    ) -> HouseComparisonOutput:
        when = ci.to_datetime()
        lat = ci.lat if ci.lat is not None else PLACEHOLDER_LAT
        lon = ci.lon if ci.lon is not None else PLACEHOLDER_LON
        charts = {
            sys: Chart.build(when, lat, lon, house_system=sys) for sys in HouseSystem
        }
        base = charts[HouseSystem.porphyry]
        bodies = _build_bodies(base, mode, BodySelection(details=details))

        systems = [str(s) for s in HouseSystem]
        house_columns: dict[str, list[int | None]] = {}
        for sys in HouseSystem:
            c = charts[sys]
            houses: list[int | None] = [p.house for p in c.planets]
            angle_list = (
                c.angles if details else [a for a in c.angles if a.name == "asc"]
            )
            houses.extend(a.house for a in angle_list)
            if details:
                houses.extend(pt.house for pt in c.points)
                houses.extend(pt.house for pt in c.lots)
            house_columns[str(sys)] = houses

        return cls(
            header=ChartHeader(
                name=ci.name,
                when=when.isoformat(),
                lat=ci.lat,
                lon=ci.lon,
                mode=mode,
            ),
            bodies=bodies,
            systems=systems,
            house_columns=house_columns,
        )

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

        table = _new_table()
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
        console.print()
        console.print(
            _panel("House comparison (yellow = differs from Porphyry)", table)
        )


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

    @classmethod
    def build(
        cls, title: str, items: list, *, extra_cols: list[str] | None = None
    ) -> InfoListOutput:
        return cls(
            title=title,
            items=[
                InfoItem(
                    name=item.name,
                    keywords=item.keywords,
                    element=getattr(item, "element", None),
                    modality=getattr(item, "modality", None),
                    ruler=getattr(item, "ruler", None),
                )
                for item in items
            ],
            extra_columns=extra_cols or [],
        )

    def render(self, console: Console) -> None:
        table = _new_table()
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
        console.print()
        console.print(_panel(self.title, table))


class InfoDetailOutput(OutputModel):
    name: str = ""
    keywords: list[str] = []
    meaning: str = ""
    element: str | None = None
    modality: str | None = None
    ruler: str | None = None

    @classmethod
    def build(cls, item) -> InfoDetailOutput:
        return cls(
            name=item.name,
            keywords=item.keywords,
            meaning=item.meaning,
            element=getattr(item, "element", None),
            modality=getattr(item, "modality", None),
            ruler=getattr(item, "ruler", None),
        )

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
