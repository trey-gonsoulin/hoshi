"""Typer CLI entry point."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hoshi import store
from hoshi.aspects import KIND_ORDER, compute_aspects, compute_inter_aspects, fmt_orb
from hoshi.chart import HOUSE_SYSTEMS, Chart
from hoshi.dignities import DIGNITY_SYMBOLS, dignity_for, element_modality_tally
from hoshi.houses import house_13_arc, house_from_cusps
from hoshi.store import ChartInput
from hoshi.zodiac import IAU, TROP_NAMES, Placement, format_deg


console = Console()


app = typer.Typer(
    add_completion=False,
    help="Real-sky astrology CLI — Python port of Nuastro.",
)
chart_app = typer.Typer(help="Create, view, list, and delete birth charts.")
app.add_typer(chart_app, name="chart")


ANGLE_DISPLAY_NAMES: dict[str, str] = {
    "asc": "Ascendant",
    "mc": "Midheaven",
    "ic": "Imum Coeli",
    "dsc": "Descendant",
    "vertex": "Vertex",
    "antivertex": "Antivertex",
}

VALID_MODES = {"realsky", "tropical", "vedic"}
VALID_GROUPINGS = {"category", "sign", "house"}
VALID_HOUSE_SYSTEMS = set(HOUSE_SYSTEMS)


@app.callback()
def _root() -> None:
    """Forces Typer into multi-command mode so `chart` isn't collapsed."""


def _validate_mode(mode: str) -> None:
    if mode not in VALID_MODES:
        raise typer.BadParameter(
            f"mode must be one of: {', '.join(sorted(VALID_MODES))}"
        )


def _validate_group_by(group_by: str) -> None:
    if group_by not in VALID_GROUPINGS:
        raise typer.BadParameter(
            f"group-by must be one of: {', '.join(sorted(VALID_GROUPINGS))}"
        )


def _validate_house_system(house_system: str) -> None:
    if house_system not in VALID_HOUSE_SYSTEMS:
        raise typer.BadParameter(
            f"houses must be one of: {', '.join(HOUSE_SYSTEMS)}"
        )


def _to_datetime(ci: ChartInput) -> datetime:
    try:
        local = datetime.fromisoformat(f"{ci.date}T{ci.time}")
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    return local.replace(tzinfo=ZoneInfo(ci.tz))


NODE_NAMES = {"N.Node", "S.Node"}


def _sign_order(mode: str) -> list[str]:
    return [s.name for s in IAU] if mode == "realsky" else TROP_NAMES


def _collect_entries(chart: Chart, mode: str, details: bool) -> list[dict]:
    """Flatten all displayed bodies into one record list for pivoting."""

    def row(kind: str, name: str, placed, lon: float, house: int, rx: str = "") -> dict:
        return {
            "kind": kind,
            "name": name,
            "placement": getattr(placed, mode),
            "lon": lon,
            "house": house,
            "rx": rx,
        }

    entries: list[dict] = []
    for p in chart.planets:
        entries.append(
            row(
                "Planet",
                p.pid.capitalize(),
                p.placed,
                p.placed.lon,
                p.house,
                "℞" if p.pos.retrograde else "",
            )
        )
    angles = chart.angles if details else [a for a in chart.angles if a.name == "asc"]
    for a in angles:
        entries.append(
            row("Angle", ANGLE_DISPLAY_NAMES[a.name], a.placed, a.placed.lon, a.house)
        )
    if details:
        for pt in chart.points:
            kind = "Node" if pt.name in NODE_NAMES else "Point"
            entries.append(row(kind, pt.name, pt.placed, pt.placed.lon, pt.house))
        for pt in chart.lots:
            entries.append(row("Lot", pt.name, pt.placed, pt.placed.lon, pt.house))
    return entries


def _new_table(title: str) -> Table:
    return Table(
        title=title,
        title_style="bold cyan",
        title_justify="left",
        box=box.SIMPLE_HEAD,
        header_style="bold",
        pad_edge=False,
    )


def _add_entity_row(
    table: Table,
    e: dict,
    *,
    include_kind: bool,
    include_sign: bool,
    include_rx: bool,
    include_house: bool,
) -> None:
    cells: list[str] = []
    if include_kind:
        cells.append(e["kind"])
    cells.append(e["name"])
    if include_sign:
        cells.append(e["placement"].name)
    cells.append(format_deg(e["placement"].deg))
    cells.append(f"{e['lon']:.2f}°")
    if include_rx:
        cells.append(e["rx"] or "")
    if include_house:
        cells.append(str(e["house"]))
    table.add_row(*cells)


def _print_by_sign(entries: list[dict], mode: str, house_label: str) -> None:
    order = _sign_order(mode)
    rank = {name: i for i, name in enumerate(order)}
    grouped: dict[str, list[dict]] = {}
    for e in entries:
        grouped.setdefault(e["placement"].name, []).append(e)

    for sign in sorted(grouped, key=lambda s: rank.get(s, 99)):
        rows = sorted(grouped[sign], key=lambda e: e["placement"].deg)
        table = _new_table(sign)
        table.add_column("Kind")
        table.add_column("Name", style="bold")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        table.add_column("Rx", justify="center")
        table.add_column(house_label, justify="right")
        for e in rows:
            _add_entity_row(
                table, e,
                include_kind=True, include_sign=False,
                include_rx=True, include_house=True,
            )
        console.print(table)


def _print_by_house(
    entries: list[dict], asc: float, house_label: str, chart: Chart, mode: str
) -> None:
    grouped: dict[int, list[dict]] = {}
    for e in entries:
        grouped.setdefault(e["house"], []).append(e)

    place_cusp = {
        "realsky": Placement.realsky,
        "tropical": Placement.tropical,
        "vedic": lambda c: Placement.vedic(c, chart.ayanamsa),
    }[mode]

    for house in range(1, len(chart.cusps) + 1):
        rows = sorted(grouped.get(house, []), key=lambda e: (e["lon"] - asc) % 360.0)
        cusp_sign = place_cusp(chart.cusps[house - 1]).name
        table = _new_table(f"{house_label}{house} — {cusp_sign}")
        table.add_column("Kind")
        table.add_column("Name", style="bold")
        table.add_column("Sign")
        table.add_column("Degree", justify="right")
        table.add_column("Lon", justify="right")
        table.add_column("Rx", justify="center")
        for e in rows:
            _add_entity_row(
                table, e,
                include_kind=True, include_sign=True,
                include_rx=True, include_house=False,
            )
        console.print(table)


def _print_section(
    title: str, entries: list[dict], house_label: str
) -> None:
    """Render one category section (Planets/Angles/Nodes/Points/Lots)."""
    table = _new_table(title)
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Rx", justify="center")
    table.add_column(house_label, justify="right")
    for e in entries:
        _add_entity_row(
            table, e,
            include_kind=False, include_sign=True,
            include_rx=True, include_house=True,
        )
    console.print(table)


def _print_planets_section(entries: list[dict], house_label: str) -> None:
    """Planets section with an extra Dignity column."""
    table = _new_table("Planets")
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Rx", justify="center")
    table.add_column(house_label, justify="right")
    table.add_column("Dig", justify="center")
    for e in entries:
        p = e["placement"]
        dig = dignity_for(e["name"], p.name)
        table.add_row(
            e["name"],
            p.name,
            format_deg(p.deg),
            f"{e['lon']:.2f}°",
            e["rx"] or "",
            str(e["house"]),
            DIGNITY_SYMBOLS.get(dig, "") if dig else "",
        )
    console.print(table)


def _print_tallies(chart: Chart, mode: str) -> None:
    tally = element_modality_tally(chart, mode)
    pri_e = tally["primary"]["elements"]
    tot_e = tally["total"]["elements"]
    pri_m = tally["primary"]["modalities"]
    tot_m = tally["total"]["modalities"]

    table = _new_table("Tallies")
    table.add_column("Element", style="bold")
    table.add_column("Primary", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("  ", no_wrap=True)  # spacer
    table.add_column("Modality", style="bold")
    table.add_column("Primary", justify="right")
    table.add_column("Total", justify="right")

    elem_order = ["Fire", "Earth", "Air", "Water"]
    mod_order = ["Cardinal", "Fixed", "Mutable"]
    for i in range(max(len(elem_order), len(mod_order))):
        e = elem_order[i] if i < len(elem_order) else ""
        m = mod_order[i] if i < len(mod_order) else ""
        table.add_row(
            e, str(pri_e.get(e, 0)) if e else "", str(tot_e.get(e, 0)) if e else "",
            "",
            m, str(pri_m.get(m, 0)) if m else "", str(tot_m.get(m, 0)) if m else "",
        )
    console.print(table)


def _print_chart(
    ci: ChartInput,
    mode: str,
    *,
    show_cusps: bool = False,
    details: bool = False,
    aspects: bool = False,
    group_by: str = "category",
    house_system: str = "porphyry",
) -> None:
    when = _to_datetime(ci)
    chart = Chart.build(when, ci.lat, ci.lng, house_system=house_system)
    house_label = "H"

    header = (
        f"[bold]Chart for[/bold] {when.isoformat()}  "
        f"([cyan]{ci.lat:.4f}°[/cyan], [cyan]{ci.lng:.4f}°[/cyan])  "
        f"mode: [magenta]{mode}[/magenta]  houses: [magenta]{chart.house_system}[/magenta]"
    )
    if ci.name:
        header = f"[yellow]\\[{ci.name.title()}][/yellow] " + header
    console.print(header)
    if mode == "vedic":
        console.print(f"Ayanamsa (Lahiri, approx): {chart.ayanamsa:.4f}°")

    entries = _collect_entries(chart, mode, details)

    if group_by != "category":
        if group_by == "sign":
            _print_by_sign(entries, mode, house_label)
        else:
            asc = next(a.placed.lon for a in chart.angles if a.name == "asc")
            _print_by_house(entries, asc, house_label, chart, mode)
        if aspects:
            _print_aspects(chart, details)
        if show_cusps:
            _print_cusps(chart, mode)
        return

    by_kind: dict[str, list[dict]] = {}
    for e in entries:
        by_kind.setdefault(e["kind"], []).append(e)

    if details:
        _print_planets_section(by_kind.get("Planet", []), house_label)
        _print_section("Angles", by_kind.get("Angle", []), house_label)
        _print_section("Nodes", by_kind.get("Node", []), house_label)
        _print_section("Points", by_kind.get("Point", []), house_label)
        _print_section("Lots", by_kind.get("Lot", []), house_label)
        _print_tallies(chart, mode)
    else:
        _print_section(
            "Placements",
            by_kind.get("Planet", []) + by_kind.get("Angle", []),
            house_label,
        )

    if aspects:
        _print_aspects(chart, details)
    if show_cusps:
        _print_cusps(chart, mode)


def _entity_houses(chart: Chart, details: bool) -> list[int]:
    """Walk a chart in the same order _collect_entries uses, returning houses only."""
    out = [p.house for p in chart.planets]
    angles = chart.angles if details else [a for a in chart.angles if a.name == "asc"]
    out.extend(a.house for a in angles)
    if details:
        out.extend(pt.house for pt in chart.points)
        out.extend(pt.house for pt in chart.lots)
    return out


def _print_house_comparison(ci: ChartInput, mode: str, *, details: bool) -> None:
    when = _to_datetime(ci)
    charts = {
        sys: Chart.build(when, ci.lat, ci.lng, house_system=sys)
        for sys in HOUSE_SYSTEMS
    }
    base = charts["porphyry"]
    entries = _collect_entries(base, mode, details)
    house_columns = {sys: _entity_houses(charts[sys], details) for sys in HOUSE_SYSTEMS}

    header = (
        f"[bold]Chart for[/bold] {when.isoformat()}  "
        f"([cyan]{ci.lat:.4f}°[/cyan], [cyan]{ci.lng:.4f}°[/cyan])  "
        f"mode: [magenta]{mode}[/magenta]"
    )
    if ci.name:
        header = f"[yellow]\\[{ci.name.title()}][/yellow] " + header
    console.print(header)

    table = _new_table(
        "House comparison (yellow = differs from Porphyry)"
    )
    table.add_column("Kind")
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    for sys in HOUSE_SYSTEMS:
        table.add_column(sys.capitalize(), justify="right")

    for i, e in enumerate(entries):
        houses_row = [house_columns[s][i] for s in HOUSE_SYSTEMS]
        baseline = houses_row[0]
        cells: list = [
            e["kind"],
            e["name"],
            e["placement"].name,
            format_deg(e["placement"].deg),
            f"{e['lon']:.2f}°",
        ]
        for h in houses_row:
            cells.append(
                Text(str(h), style="bold yellow") if h != baseline else str(h)
            )
        table.add_row(*cells)
    console.print(table)


def _chart_to_json(chart: Chart, ci: ChartInput, mode: str, details: bool) -> str:
    entries = _collect_entries(chart, mode, details)
    when = _to_datetime(ci)
    return json.dumps(
        {
            "chart": {
                "when": when.isoformat(),
                "lat": ci.lat,
                "lng": ci.lng,
                "mode": mode,
                "house_system": chart.house_system,
            },
            "bodies": [
                {
                    "name": e["name"],
                    "sign": e["placement"].name,
                    "degree": round(e["placement"].deg, 4),
                    "lon": round(e["lon"], 4),
                    "house": e["house"],
                    "rx": e["rx"] == "℞",
                }
                for e in entries
            ],
            "cusps": [round(c, 4) for c in chart.cusps],
        },
        indent=2,
    )


def _aspect_tables(aspects: list, title_prefix: str) -> None:
    """Render a list of Aspect objects grouped by kind."""
    if not aspects:
        return
    by_kind: dict[str, list] = {}
    for asp in aspects:
        by_kind.setdefault(asp.kind, []).append(asp)
    for kind in KIND_ORDER:
        group = by_kind.get(kind)
        if not group:
            continue
        table = _new_table(f"{title_prefix}{kind} Aspects")
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


def _print_aspects(chart: Chart, details: bool = True) -> None:
    _aspect_tables(compute_aspects(chart, details), "")


def _print_inter_aspects(
    chart_a: Chart, chart_b: Chart, label_a: str, label_b: str, details: bool
) -> None:
    aspects = compute_inter_aspects(chart_a, chart_b, details)
    prefix = f"{label_a.title()} → {label_b.title()}: "
    _aspect_tables(aspects, prefix)


def _print_cusps(chart: Chart, mode: str) -> None:
    place_cusp = {
        "realsky": Placement.realsky,
        "tropical": Placement.tropical,
        "vedic": lambda c: Placement.vedic(c, chart.ayanamsa),
    }[mode]
    table = _new_table(f"{chart.house_system.capitalize()} cusps")
    table.add_column("House", justify="right")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    for i, c in enumerate(chart.cusps, start=1):
        p = place_cusp(c)
        table.add_row(f"H{i}", p.name, format_deg(p.deg), f"{c:.2f}°")
    console.print(table)


@chart_app.command(name="add")
def chart_add(
    name: str = typer.Argument(
        ..., help="Name to save this chart under (filename-safe key)."
    ),
    date: str = typer.Argument(..., help="Birth date, YYYY-MM-DD."),
    time: str = typer.Argument("12:00", help="Birth time, HH:MM (24h)."),
    lat: float = typer.Option(
        ..., "--lat", help="Birth latitude, degrees (N positive)."
    ),
    lng: float = typer.Option(
        ..., "--lng", help="Birth longitude, degrees (E positive)."
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="IANA timezone of the birth time, e.g. America/Chicago."
    ),
    mode: str = typer.Option(
        "realsky", "--mode", help="Zodiac mode: realsky, tropical, or vedic."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing saved chart with the same name."
    ),
    houses: str = typer.Option(
        "porphyry",
        "--houses",
        help=f"House system: {', '.join(HOUSE_SYSTEMS)}.",
    ),
    cusps: bool = typer.Option(
        False, "--cusps", help="Also print the house cusps for the chosen system."
    ),
    details: bool = typer.Option(
        False, "--details", help="Also print all angles, nodes, and calculated points."
    ),
    aspects: bool = typer.Option(
        False, "--aspects", help="Print aspect tables (uses all bodies with --details, planets+Asc otherwise)."
    ),
    group_by: str = typer.Option(
        "category",
        "--group-by",
        help="Group entries by: category (default), sign, or house.",
    ),
) -> None:
    """Save a named birth chart to ./charts/ and print it."""
    _validate_mode(mode)
    ci = ChartInput(name=name, date=date, time=time, tz=tz, lat=lat, lng=lng)
    try:
        path = store.save(ci, overwrite=force)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Saved chart to {path}")
    typer.echo("")
    _validate_group_by(group_by)
    _validate_house_system(houses)
    _print_chart(
        ci,
        mode,
        show_cusps=cusps,
        details=details,
        aspects=aspects,
        group_by=group_by,
        house_system=houses,
    )


@chart_app.command(name="list")
def chart_list() -> None:
    """List all saved charts."""
    charts = store.list_all()
    if not charts:
        typer.echo(
            "No saved charts. Use `astro chart add NAME DATE [TIME] --lat ... --lng ...` to create one."
        )
        return
    table = _new_table("Saved charts")
    table.add_column("Name", style="bold")
    table.add_column("Date")
    table.add_column("Time")
    table.add_column("Timezone")
    table.add_column("Lat", justify="right")
    table.add_column("Lng", justify="right")
    for ci in charts:
        table.add_row(
            ci.name.title(), ci.date, ci.time, ci.tz, f"{ci.lat:.4f}", f"{ci.lng:.4f}"
        )
    console.print(table)


@chart_app.command(name="cusps")
def chart_cusps(
    target: str = typer.Argument(
        ...,
        help="Saved chart name, OR a birth date (YYYY-MM-DD) for a one-off chart "
        "(in which case --lat and --lng are required).",
    ),
    time: str = typer.Argument("12:00", help="Birth time for one-off charts, HH:MM (24h)."),
    lat: float = typer.Option(None, "--lat", help="One-off chart latitude (N positive)."),
    lng: float = typer.Option(None, "--lng", help="One-off chart longitude (E positive)."),
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone, e.g. America/Chicago."),
    mode: str = typer.Option("realsky", "--mode", help="Zodiac mode: realsky, tropical, or vedic."),
    houses: str = typer.Option("porphyry", "--houses", help=f"House system: {', '.join(HOUSE_SYSTEMS)}."),
) -> None:
    """Print house cusps for a saved or one-off chart."""
    _validate_mode(mode)
    _validate_house_system(houses)
    one_off = lat is not None or lng is not None
    if one_off:
        if lat is None or lng is None:
            raise typer.BadParameter("One-off charts require both --lat and --lng.")
        ci = ChartInput(name="", date=target, time=time, tz=tz, lat=lat, lng=lng)
    else:
        try:
            ci = store.load(target)
        except FileNotFoundError as exc:
            raise typer.BadParameter(str(exc)) from exc
    when = _to_datetime(ci)
    chart = Chart.build(when, ci.lat, ci.lng, house_system=houses)
    _print_cusps(chart, mode)


@chart_app.command(name="show")
def chart_show(
    target: str = typer.Argument(
        ...,
        help="Saved chart name, OR a birth date (YYYY-MM-DD) for a one-off chart "
        "(in which case --lat and --lng are required).",
    ),
    time: str = typer.Argument(
        "12:00", help="Birth time for one-off charts, HH:MM (24h)."
    ),
    lat: float = typer.Option(
        None, "--lat", help="One-off chart latitude (N positive)."
    ),
    lng: float = typer.Option(
        None, "--lng", help="One-off chart longitude (E positive)."
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="One-off chart IANA timezone, e.g. America/Chicago."
    ),
    mode: str = typer.Option(
        "realsky", "--mode", help="Zodiac mode: realsky, tropical, or vedic."
    ),
    houses: str = typer.Option(
        "porphyry",
        "--houses",
        help=f"House system: {', '.join(HOUSE_SYSTEMS)}.",
    ),
    cusps: bool = typer.Option(
        False, "--cusps", help="Also print the house cusps for the chosen system."
    ),
    details: bool = typer.Option(
        False, "--details", help="Also print all angles, nodes, and calculated points."
    ),
    aspects: bool = typer.Option(
        False, "--aspects", help="Print aspect tables (uses all bodies with --details, planets+Asc otherwise)."
    ),
    group_by: str = typer.Option(
        "category",
        "--group-by",
        help="Group entries by: category (default), sign, or house.",
    ),
    fmt: str = typer.Option(
        "table", "--format", help="Output format: table (default) or json."
    ),
    compare_houses: bool = typer.Option(
        False,
        "--compare-houses",
        help="Show house assignments side-by-side across all house systems "
        "and highlight differences.",
    ),
) -> None:
    """Display a chart by saved name, or compute a one-off chart from birth parameters."""
    _validate_mode(mode)

    one_off = lat is not None or lng is not None
    if one_off:
        if lat is None or lng is None:
            raise typer.BadParameter("One-off charts require both --lat and --lng.")
        ci = ChartInput(name="", date=target, time=time, tz=tz, lat=lat, lng=lng)
    else:
        try:
            ci = store.load(target)
        except FileNotFoundError as exc:
            raise typer.BadParameter(
                f"{exc}\nIf you meant a one-off chart, also pass --lat and --lng "
                f"(and the first argument should be a YYYY-MM-DD date)."
            ) from exc

    _validate_group_by(group_by)
    _validate_house_system(houses)

    if fmt == "json":
        when = _to_datetime(ci)
        chart = Chart.build(when, ci.lat, ci.lng, house_system=houses)
        print(_chart_to_json(chart, ci, mode, details))
        return

    if compare_houses:
        _print_house_comparison(ci, mode, details=details)
        return

    _print_chart(
        ci,
        mode,
        show_cusps=cusps,
        details=details,
        aspects=aspects,
        group_by=group_by,
        house_system=houses,
    )


@chart_app.command(name="delete")
def chart_delete(
    name: str = typer.Argument(..., help="Name of a saved chart."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt."
    ),
) -> None:
    """Delete a saved chart."""
    if not store.exists(name):
        raise typer.BadParameter(f"No saved chart named {name!r}")
    if not yes:
        typer.confirm(f"Delete saved chart {name!r}?", abort=True)
    path = store.delete(name)
    typer.echo(f"Deleted {path}")


def _collect_transit_entries(
    transit: Chart, natal: Chart, mode: str, details: bool
) -> list[dict]:
    """Like _collect_entries but house numbers come from natal chart cusps."""
    natal_asc = next(a.placed.lon for a in natal.angles if a.name == "asc")

    def natal_house(lon: float) -> int:
        if natal.house_system == "arc13":
            return house_13_arc(lon, natal_asc)
        return house_from_cusps(lon, natal.cusps)

    def row(kind: str, name: str, placed, lon: float, rx: str = "") -> dict:
        return {
            "kind": kind,
            "name": name,
            "placement": getattr(placed, mode),
            "lon": lon,
            "house": natal_house(lon),
            "rx": rx,
        }

    entries: list[dict] = []
    for p in transit.planets:
        entries.append(
            row("Planet", p.pid.capitalize(), p.placed, p.placed.lon, "℞" if p.pos.retrograde else "")
        )
    angles = transit.angles if details else [a for a in transit.angles if a.name == "asc"]
    for a in angles:
        entries.append(row("Angle", ANGLE_DISPLAY_NAMES[a.name], a.placed, a.placed.lon))
    if details:
        for pt in transit.points:
            kind = "Node" if pt.name in NODE_NAMES else "Point"
            entries.append(row(kind, pt.name, pt.placed, pt.placed.lon))
        for pt in transit.lots:
            entries.append(row("Lot", pt.name, pt.placed, pt.placed.lon))
    return entries


def _print_transits(
    ci_natal: ChartInput,
    transit_dt: datetime,
    mode: str,
    *,
    details: bool,
    aspects: bool,
    show_natal: bool,
    house_system: str,
) -> None:
    chart_natal = Chart.build(_to_datetime(ci_natal), ci_natal.lat, ci_natal.lng, house_system=house_system)
    chart_transit = Chart.build(transit_dt, ci_natal.lat, ci_natal.lng, house_system=house_system)

    label = f"[yellow]\\[{ci_natal.name.title()}][/yellow]"
    console.print(
        f"[bold]Transits:[/bold] {label} natal {ci_natal.date}  →  "
        f"transit {transit_dt.strftime('%Y-%m-%d %H:%M %Z').strip()}  "
        f"mode: [magenta]{mode}[/magenta]  houses: [magenta]{chart_natal.house_system}[/magenta]"
    )

    transit_entries = _collect_transit_entries(chart_transit, chart_natal, mode, details)

    if show_natal:
        natal_entries = _collect_entries(chart_natal, mode, details)
        table = _new_table("Natal vs Transits  (H = natal house)")
        table.add_column("Name", style="bold")
        table.add_column("Natal Sign")
        table.add_column("Natal Deg", justify="right")
        table.add_column("→", justify="center")
        table.add_column("Transit Sign")
        table.add_column("Transit Deg", justify="right")
        table.add_column("Rx", justify="center")
        table.add_column("H", justify="right")
        for n, t in zip(natal_entries, transit_entries):
            table.add_row(
                n["name"],
                n["placement"].name,
                format_deg(n["placement"].deg),
                "→",
                t["placement"].name,
                format_deg(t["placement"].deg),
                t["rx"] or "",
                str(t["house"]),
            )
        console.print(table)
    else:
        by_kind: dict[str, list[dict]] = {}
        for e in transit_entries:
            by_kind.setdefault(e["kind"], []).append(e)
        if details:
            _print_section("Planets", by_kind.get("Planet", []), "H")
            _print_section("Angles", by_kind.get("Angle", []), "H")
            _print_section("Nodes", by_kind.get("Node", []), "H")
            _print_section("Points", by_kind.get("Point", []), "H")
            _print_section("Lots", by_kind.get("Lot", []), "H")
        else:
            _print_section(
                "Transiting Planets  (H = natal house)",
                by_kind.get("Planet", []) + by_kind.get("Angle", []),
                "H",
            )

    if aspects:
        _print_inter_aspects(chart_natal, chart_transit, ci_natal.name, "transit", details)


@chart_app.command(name="transits")
def chart_transits(
    name: str = typer.Argument(..., help="Saved natal chart name."),
    date: str | None = typer.Argument(None, help="Transit date YYYY-MM-DD (default: today)."),
    time: str | None = typer.Argument(None, help="Transit time HH:MM 24h (default: now)."),
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone for the transit date/time."),
    mode: str = typer.Option("realsky", "--mode", help="Zodiac mode: realsky, tropical, or vedic."),
    houses: str = typer.Option(
        "porphyry", "--houses", help=f"House system: {', '.join(HOUSE_SYSTEMS)}."
    ),
    details: bool = typer.Option(
        False, "--details", help="Include angles, nodes, and points."
    ),
    aspects: bool = typer.Option(
        False, "--aspects", help="Print inter-aspect tables (natal × transit)."
    ),
    natal: bool = typer.Option(
        False, "--natal", help="Show natal placements alongside transits in a side-by-side table."
    ),
) -> None:
    """Compare a saved natal chart against current (or specified date) transiting planets."""
    _validate_mode(mode)
    _validate_house_system(houses)
    try:
        ci = store.load(name)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    now = datetime.now().astimezone()
    if date is None:
        transit_dt = now
    else:
        t = time if time is not None else now.strftime("%H:%M")
        try:
            local = datetime.fromisoformat(f"{date}T{t}")
        except ValueError as exc:
            raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
        transit_dt = local.replace(tzinfo=ZoneInfo(tz))

    _print_transits(ci, transit_dt, mode, details=details, aspects=aspects, show_natal=natal, house_system=houses)


@chart_app.command(name="compare")
def chart_compare(
    name_a: str = typer.Argument(..., help="First saved chart name."),
    name_b: str = typer.Argument(..., help="Second saved chart name."),
    mode: str = typer.Option("realsky", "--mode", help="Zodiac mode: realsky, tropical, or vedic."),
    houses: str = typer.Option("porphyry", "--houses", help=f"House system: {', '.join(HOUSE_SYSTEMS)}."),
    details: bool = typer.Option(False, "--details", help="Include angles, nodes, and points in inter-aspects."),
    aspects: bool = typer.Option(False, "--aspects", help="Print inter-aspect tables."),
) -> None:
    """Show synastry (inter-aspects) between two saved charts."""
    _validate_mode(mode)
    _validate_house_system(houses)
    try:
        ci_a = store.load(name_a)
        ci_b = store.load(name_b)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    chart_a = Chart.build(_to_datetime(ci_a), ci_a.lat, ci_a.lng, house_system=houses)
    chart_b = Chart.build(_to_datetime(ci_b), ci_b.lat, ci_b.lng, house_system=houses)

    console.print(
        f"[bold]Synastry:[/bold] [yellow]{ci_a.name.title()}[/yellow] ({ci_a.date})  ×  "
        f"[yellow]{ci_b.name.title()}[/yellow] ({ci_b.date})  "
        f"mode: [magenta]{mode}[/magenta]"
    )
    if aspects:
        _print_inter_aspects(chart_a, chart_b, ci_a.name, ci_b.name, details)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
