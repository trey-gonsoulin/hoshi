"""Typer CLI entry point."""

import json
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

import typer
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hoshi import store
from hoshi.aspects import KIND_ORDER, compute_aspects, compute_inter_aspects, fmt_orb
from hoshi.chart import Chart, HouseSystem, Placed
from hoshi.dignities import DIGNITY_SYMBOLS, dignity_for, element_modality_tally
from hoshi.ephemeris import ecliptic_precession, lahiri_ayanamsa, positions
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
info_app = typer.Typer(help="Reference info on astrological concepts.")
app.add_typer(info_app, name="info")


ANGLE_DISPLAY_NAMES: dict[str, str] = {
    "asc": "Ascendant",
    "mc": "Midheaven",
    "ic": "Imum Coeli",
    "dsc": "Descendant",
    "vertex": "Vertex",
    "antivertex": "Antivertex",
}


class ZodiacMode(StrEnum):
    realsky = "realsky"
    tropical = "tropical"
    vedic = "vedic"


class GroupBy(StrEnum):
    category = "category"
    sign = "sign"
    house = "house"


@app.callback()
def _root() -> None:
    """Forces Typer into multi-command mode so `chart` isn't collapsed."""



NODE_NAMES = {"N.Node", "S.Node"}


def _sign_order(mode: str) -> list[str]:
    return [s.name for s in IAU] if mode == "realsky" else TROP_NAMES


def _uncertain_pids(ci: ChartInput, mode: str) -> frozenset[str]:
    """Return the set of planet pids whose sign changes at any point on the birth date.

    Only inner planets (Sun through Mars) can realistically change sign in 24 hours;
    outer planets are excluded from the check to avoid unnecessary Horizons fetches.
    """
    d = datetime.fromisoformat(ci.date)
    tz = ZoneInfo(ci.tz)
    start = d.replace(hour=0, minute=0, second=0, tzinfo=tz)
    end = d.replace(hour=23, minute=59, second=59, tzinfo=tz)
    pos_start = positions(start)
    pos_end = positions(end)
    ayan = lahiri_ayanamsa(start)
    prec_start = ecliptic_precession(start)
    prec_end = ecliptic_precession(end)
    uncertain: set[str] = set()
    for pid in ("sun", "moon", "mercury", "venus", "mars"):
        s = getattr(Placed.for_longitude(pos_start[pid].lon, ayan, prec_start), mode).name
        e = getattr(Placed.for_longitude(pos_end[pid].lon, ayan, prec_end), mode).name
        if s != e:
            uncertain.add(pid)
    return frozenset(uncertain)


def _collect_entries(
    chart: Chart,
    mode: str,
    details: bool,
    *,
    uncertain_pids: frozenset[str] = frozenset(),
    include_angles: bool = True,
    include_lots: bool = True,
) -> list[dict]:
    """Flatten all displayed bodies into one record list for pivoting."""

    def row(kind: str, name: str, placed, lon: float, house: int, rx: str = "", pid: str = "") -> dict:
        return {
            "kind": kind,
            "name": name,
            "placement": getattr(placed, mode),
            "lon": lon,
            "house": house,
            "rx": rx,
            "uncertain": pid in uncertain_pids,
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
                pid=p.pid,
            )
        )
    if include_angles:
        angles = chart.angles if details else [a for a in chart.angles if a.name == "asc"]
        for a in angles:
            entries.append(
                row("Angle", ANGLE_DISPLAY_NAMES[a.name], a.placed, a.placed.lon, a.house)
            )
    if details:
        for pt in chart.points:
            kind = "Node" if pt.name in NODE_NAMES else "Point"
            entries.append(row(kind, pt.name, pt.placed, pt.placed.lon, pt.house))
        if include_lots:
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
    uncertain = e.get("uncertain", False)

    def _s(val: str) -> "str | Text":
        return Text(val, style="yellow") if uncertain else val

    cells: list = []
    if include_kind:
        cells.append(e["kind"])
    cells.append(e["name"])
    if include_sign:
        cells.append(_s(e["placement"].name))
    cells.append(_s(format_deg(e["placement"].deg)))
    cells.append(_s(f"{e['lon']:.2f}°"))
    if include_rx:
        cells.append(e["rx"] or "")
    if include_house:
        cells.append(str(e["house"]))
    table.add_row(*cells)


def _print_by_sign(entries: list[dict], mode: str, house_label: str | None) -> None:
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
        if house_label is not None:
            table.add_column(house_label, justify="right")
        for e in rows:
            _add_entity_row(
                table, e,
                include_kind=True, include_sign=False,
                include_rx=True, include_house=house_label is not None,
            )
        console.print(table)


def _print_by_house(
    entries: list[dict], asc: float, house_label: str | None, chart: Chart, mode: str
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
    title: str, entries: list[dict], house_label: str | None
) -> None:
    """Render one category section (Planets/Angles/Nodes/Points/Lots)."""
    table = _new_table(title)
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Rx", justify="center")
    if house_label is not None:
        table.add_column(house_label, justify="right")
    for e in entries:
        _add_entity_row(
            table, e,
            include_kind=False, include_sign=True,
            include_rx=True, include_house=house_label is not None,
        )
    console.print(table)


def _print_planets_section(entries: list[dict], house_label: str | None) -> None:
    """Planets section with an extra Dignity column."""
    table = _new_table("Planets")
    table.add_column("Name", style="bold")
    table.add_column("Sign")
    table.add_column("Degree", justify="right")
    table.add_column("Lon", justify="right")
    table.add_column("Rx", justify="center")
    if house_label is not None:
        table.add_column(house_label, justify="right")
    table.add_column("Dig", justify="center")
    for e in entries:
        uncertain = e.get("uncertain", False)

        def _s(val: str, u: bool = uncertain) -> "str | Text":
            return Text(val, style="yellow") if u else val

        p = e["placement"]
        dig = dignity_for(e["name"], p.name)
        row: list = [
            e["name"],
            _s(p.name),
            _s(format_deg(p.deg)),
            _s(f"{e['lon']:.2f}°"),
            e["rx"] or "",
        ]
        if house_label is not None:
            row.append(str(e["house"]))
        row.append(DIGNITY_SYMBOLS.get(dig, "") if dig else "")
        table.add_row(*row)
    console.print(table)


def _print_tallies(chart: Chart, mode: str, *, show_full: bool = True) -> None:
    tally = element_modality_tally(chart, mode, include_angles=show_full, include_lots=show_full)
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
    time_known = ci.time_known
    loc_known = ci.location_known
    show_full = time_known and loc_known

    try:
        when = ci.to_datetime()
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    lat = ci.lat if ci.lat is not None else 0.001
    lon = ci.lon if ci.lon is not None else 0.0
    chart = Chart.build(when, lat, lon, house_system=house_system)

    # Header — omit unknown fields
    when_str = when.strftime("%Y-%m-%d") if not time_known else when.isoformat()
    loc_str = f"([cyan]{lat:.4f}°[/cyan], [cyan]{lon:.4f}°[/cyan])  " if loc_known else ""
    houses_str = f"  houses: [magenta]{chart.house_system}[/magenta]" if show_full else ""
    header = (
        f"[bold]Chart for[/bold] {when_str}  {loc_str}"
        f"mode: [magenta]{mode}[/magenta]{houses_str}"
    )
    if ci.name:
        header = f"[yellow]\\[{ci.name.title()}][/yellow] " + header
    console.print(header)
    if mode == "vedic":
        console.print(f"Ayanamsa (Lahiri, approx): {chart.ayanamsa:.4f}°")

    house_label: str | None = "H" if show_full else None
    uncertain_pids = _uncertain_pids(ci, mode) if not time_known else frozenset()

    if not time_known:
        if uncertain_pids:
            names = ", ".join(p.capitalize() for p in uncertain_pids)
            console.print(
                f"[yellow]⚠ Birth time unknown — {names} may be in a different sign (highlighted)[/yellow]"
            )
        else:
            console.print(
                "[yellow]⚠ Birth time unknown — all signs stable on this date, degrees approximate[/yellow]"
            )
    if not loc_known:
        console.print(
            "[yellow]⚠ Birth location unknown — angles and houses omitted[/yellow]"
        )
    entries = _collect_entries(
        chart, mode, details,
        uncertain_pids=uncertain_pids,
        include_angles=show_full,
        include_lots=show_full,
    )

    # Fallback from group-by house when houses unavailable
    if group_by == "house" and not show_full:
        console.print(
            "[yellow]⚠ Cannot group by house without known birth time and location; "
            "using category grouping.[/yellow]"
        )
        group_by = "category"

    if group_by == "sign":
        _print_by_sign(entries, mode, house_label)
        if aspects:
            _print_aspects(chart, details)
        if show_cusps and show_full:
            _print_cusps(chart, mode)
        return

    if group_by == "house":
        asc = next(a.placed.lon for a in chart.angles if a.name == "asc")
        _print_by_house(entries, asc, house_label, chart, mode)
        if aspects:
            _print_aspects(chart, details)
        if show_cusps and show_full:
            _print_cusps(chart, mode)
        return

    by_kind: dict[str, list[dict]] = {}
    for e in entries:
        by_kind.setdefault(e["kind"], []).append(e)

    if details:
        _print_planets_section(by_kind.get("Planet", []), house_label)
        if show_full:
            _print_section("Angles", by_kind.get("Angle", []), house_label)
        _print_section("Nodes", by_kind.get("Node", []), house_label)
        _print_section("Points", by_kind.get("Point", []), house_label)
        if show_full:
            _print_section("Lots", by_kind.get("Lot", []), house_label)
        _print_tallies(chart, mode, show_full=show_full)
    else:
        _print_section(
            "Placements",
            by_kind.get("Planet", []) + by_kind.get("Angle", []),
            house_label,
        )

    if aspects:
        _print_aspects(chart, details)
    if show_cusps and show_full:
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
    when = ci.to_datetime()
    lat = ci.lat if ci.lat is not None else 0.001
    lon = ci.lon if ci.lon is not None else 0.0
    charts = {
        sys: Chart.build(when, lat, lon, house_system=sys)
        for sys in HouseSystem
    }
    base = charts[HouseSystem.porphyry]
    entries = _collect_entries(base, mode, details)
    house_columns = {sys: _entity_houses(charts[sys], details) for sys in HouseSystem}

    header = (
        f"[bold]Chart for[/bold] {when.isoformat()}  "
        f"([cyan]{ci.lat:.4f}°[/cyan], [cyan]{ci.lon:.4f}°[/cyan])  "
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
    for sys in HouseSystem:
        table.add_column(sys.capitalize(), justify="right")

    for i, e in enumerate(entries):
        houses_row = [house_columns[s][i] for s in HouseSystem]
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
    time_known = ci.time_known
    loc_known = ci.location_known
    show_full = time_known and loc_known
    uncertain_pids = _uncertain_pids(ci, mode) if not time_known else frozenset()
    entries = _collect_entries(
        chart, mode, details,
        uncertain_pids=uncertain_pids,
        include_angles=show_full,
        include_lots=show_full,
    )
    when = ci.to_datetime()
    warnings: list[str] = []
    if not time_known:
        warnings.append("Birth time unknown — planet degrees approximate; Moon sign may differ")
    if not loc_known:
        warnings.append("Birth location unknown — angles and houses omitted")
    return json.dumps(
        {
            "chart": {
                "when": when.isoformat(),
                "lat": ci.lat,
                "lon": ci.lon,
                "mode": mode,
                "house_system": chart.house_system if show_full else None,
            },
            "warnings": warnings,
            "bodies": [
                {
                    "name": e["name"],
                    "sign": e["placement"].name,
                    "degree": round(e["placement"].deg, 4),
                    "lon": round(e["lon"], 4),
                    "house": e["house"] if show_full else None,
                    "rx": e["rx"] == "℞",
                    "approximate": e.get("uncertain", False),
                }
                for e in entries
            ],
            "cusps": [round(c, 4) for c in chart.cusps] if show_full else [],
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
    time: str | None = typer.Argument(
        None, help="Birth time, HH:MM (24h). Omit if unknown."
    ),
    lat: float | None = typer.Option(
        None, "--lat", help="Birth latitude, degrees (N positive). Omit if unknown."
    ),
    lon: float | None = typer.Option(
        None, "--lon", help="Birth longitude, degrees (E positive). Omit if unknown."
    ),
    location: str | None = typer.Option(
        None, "--location", help="Birth location to geocode, e.g. 'Austin, TX'. Cannot be used with --lat/--lon."
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="IANA timezone of the birth time, e.g. America/Chicago."
    ),
    mode: ZodiacMode = typer.Option(
        ZodiacMode.realsky, "--mode", help="Zodiac mode."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing saved chart with the same name."
    ),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry,
        "--houses",
        help="House system.",
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
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group entries by category, sign, or house.",
    ),
) -> None:
    """Save a named birth chart to ./charts/ and print it."""
    if location is not None and (lat is not None or lon is not None):
        raise typer.BadParameter("Cannot use --location together with --lat/--lon.")
    if location is not None:
        from geopy.geocoders import Nominatim
        geo = Nominatim(user_agent="hoshi")
        result = geo.geocode(location)
        if result is None:
            raise typer.BadParameter(f"Could not geocode location: {location!r}")
        lat = result.latitude
        lon = result.longitude
        typer.echo(f"Resolved location: {result.address}")
        typer.echo(f"Coordinates: {lat:.4f}°N, {lon:.4f}°E")
    if (lat is None) != (lon is None):
        raise typer.BadParameter("--lat and --lon must both be provided or both omitted.")
    ci = ChartInput(name=name, date=date, time=time, tz=tz, lat=lat, lon=lon)
    try:
        path = store.save(ci, overwrite=force)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Saved chart to {path}")
    typer.echo("")
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
            "No saved charts. Use `astro chart add NAME DATE [TIME] --lat ... --lon ...` to create one."
        )
        return
    table = _new_table("Saved charts")
    table.add_column("Name", style="bold")
    table.add_column("Date")
    table.add_column("Time")
    table.add_column("Timezone")
    table.add_column("Lat", justify="right")
    table.add_column("Lon", justify="right")
    for ci in charts:
        table.add_row(
            ci.name.title(),
            ci.date,
            ci.time or "—",
            ci.tz if ci.time is not None else "—",
            f"{ci.lat:.4f}" if ci.lat is not None else "—",
            f"{ci.lon:.4f}" if ci.lon is not None else "—",
        )
    console.print(table)


@chart_app.command(name="cusps")
def chart_cusps(
    target: str = typer.Argument(
        ...,
        help="Saved chart name, OR a birth date (YYYY-MM-DD) for a one-off chart "
        "(in which case --lat and --lon are required).",
    ),
    time: str = typer.Argument("12:00", help="Birth time for one-off charts, HH:MM (24h)."),
    lat: float = typer.Option(None, "--lat", help="One-off chart latitude (N positive)."),
    lon: float = typer.Option(None, "--lon", help="One-off chart longitude (E positive)."),
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone, e.g. America/Chicago."),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(HouseSystem.porphyry, "--houses", help="House system."),
) -> None:
    """Print house cusps for a saved or one-off chart."""
    one_off = lat is not None or lon is not None
    if one_off:
        if lat is None or lon is None:
            raise typer.BadParameter("One-off charts require both --lat and --lon.")
        ci = ChartInput(name="", date=target, time=time, tz=tz, lat=lat, lon=lon)
    else:
        try:
            ci = store.load(target)
        except FileNotFoundError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if not ci.time_known:
            raise typer.BadParameter(
                f"Chart {ci.name!r} has no birth time — house cusps cannot be computed."
            )
        if not ci.location_known:
            raise typer.BadParameter(
                f"Chart {ci.name!r} has no birth location — house cusps cannot be computed."
            )
    try:
        when = ci.to_datetime()
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    chart_lat = ci.lat if ci.lat is not None else 0.001
    chart_lon = ci.lon if ci.lon is not None else 0.0
    chart = Chart.build(when, chart_lat, chart_lon, house_system=houses)
    _print_cusps(chart, mode)


@chart_app.command(name="show")
def chart_show(
    target: str = typer.Argument(
        ...,
        help="Saved chart name, OR a birth date (YYYY-MM-DD) for a one-off chart "
        "(in which case --lat and --lon are required).",
    ),
    time: str = typer.Argument(
        "12:00", help="Birth time for one-off charts, HH:MM (24h)."
    ),
    lat: float = typer.Option(
        None, "--lat", help="One-off chart latitude (N positive)."
    ),
    lon: float = typer.Option(
        None, "--lon", help="One-off chart longitude (E positive)."
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="One-off chart IANA timezone, e.g. America/Chicago."
    ),
    mode: ZodiacMode = typer.Option(
        ZodiacMode.realsky, "--mode", help="Zodiac mode."
    ),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry,
        "--houses",
        help="House system.",
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
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group entries by category, sign, or house.",
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
    one_off = lat is not None or lon is not None
    if one_off:
        if lat is None or lon is None:
            raise typer.BadParameter("One-off charts require both --lat and --lon.")
        ci = ChartInput(name="", date=target, time=time, tz=tz, lat=lat, lon=lon)
    else:
        try:
            ci = store.load(target)
        except FileNotFoundError as exc:
            raise typer.BadParameter(
                f"{exc}\nIf you meant a one-off chart, also pass --lat and --lon "
                f"(and the first argument should be a YYYY-MM-DD date)."
            ) from exc

    if fmt == "json":
        when = ci.to_datetime()
        chart_lat = ci.lat if ci.lat is not None else 0.001
        chart_lon = ci.lon if ci.lon is not None else 0.0
        chart = Chart.build(when, chart_lat, chart_lon, house_system=houses)
        print(_chart_to_json(chart, ci, mode, details))
        return

    if compare_houses:
        if not ci.time_known or not ci.location_known:
            raise typer.BadParameter(
                "--compare-houses requires a chart with known birth time and location."
            )
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
    transit: Chart, natal: Chart, mode: str, details: bool, *, natal_loc_known: bool = True
) -> list[dict]:
    """Like _collect_entries but house numbers come from natal chart cusps."""
    natal_asc = next(a.placed.lon for a in natal.angles if a.name == "asc")

    def natal_house(lon: float) -> int:
        if not natal_loc_known:
            return 0
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
            "uncertain": False,
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
    natal_time_known = ci_natal.time_known
    natal_loc_known = ci_natal.location_known
    natal_lat = ci_natal.lat if ci_natal.lat is not None else 0.001
    natal_lon = ci_natal.lon if ci_natal.lon is not None else 0.0

    chart_natal = Chart.build(ci_natal.to_datetime(), natal_lat, natal_lon, house_system=house_system)
    chart_transit = Chart.build(transit_dt, natal_lat, natal_lon, house_system=house_system)

    label = f"[yellow]\\[{ci_natal.name.title()}][/yellow]"
    houses_str = f"  houses: [magenta]{chart_natal.house_system}[/magenta]" if natal_loc_known else ""
    console.print(
        f"[bold]Transits:[/bold] {label} natal {ci_natal.date}  →  "
        f"transit {transit_dt.strftime('%Y-%m-%d %H:%M %Z').strip()}  "
        f"mode: [magenta]{mode}[/magenta]{houses_str}"
    )

    if not natal_time_known:
        console.print(
            "[yellow]⚠ Natal time unknown — natal planet degrees approximate[/yellow]"
        )
    if not natal_loc_known:
        console.print(
            "[yellow]⚠ Natal location unknown — natal house placement of transits omitted[/yellow]"
        )

    transit_house_label: str | None = "H" if natal_loc_known else None
    transit_entries = _collect_transit_entries(
        chart_transit, chart_natal, mode, details, natal_loc_known=natal_loc_known
    )

    if show_natal:
        natal_show_full = natal_time_known and natal_loc_known
        natal_uncertain_pids = _uncertain_pids(ci_natal, mode) if not natal_time_known else frozenset()
        natal_entries = _collect_entries(
            chart_natal, mode, details,
            uncertain_pids=natal_uncertain_pids,
            include_angles=natal_show_full,
            include_lots=natal_show_full,
        )
        title = "Natal vs Transits" + ("  (H = natal house)" if natal_loc_known else "")
        table = _new_table(title)
        table.add_column("Name", style="bold")
        table.add_column("Natal Sign")
        table.add_column("Natal Deg", justify="right")
        table.add_column("→", justify="center")
        table.add_column("Transit Sign")
        table.add_column("Transit Deg", justify="right")
        table.add_column("Rx", justify="center")
        if natal_loc_known:
            table.add_column("H", justify="right")
        for n, t in zip(natal_entries, transit_entries):
            n_uncertain = n.get("uncertain", False)

            def _ns(val: str, u: bool = n_uncertain) -> "str | Text":
                return Text(val, style="yellow") if u else val

            row: list = [
                n["name"],
                _ns(n["placement"].name),
                _ns(format_deg(n["placement"].deg)),
                "→",
                t["placement"].name,
                format_deg(t["placement"].deg),
                t["rx"] or "",
            ]
            if natal_loc_known:
                row.append(str(t["house"]))
            table.add_row(*row)
        console.print(table)
    else:
        by_kind: dict[str, list[dict]] = {}
        for e in transit_entries:
            by_kind.setdefault(e["kind"], []).append(e)
        title_suffix = "  (H = natal house)" if natal_loc_known else ""
        if details:
            _print_section("Planets", by_kind.get("Planet", []), transit_house_label)
            _print_section("Angles", by_kind.get("Angle", []), transit_house_label)
            _print_section("Nodes", by_kind.get("Node", []), transit_house_label)
            _print_section("Points", by_kind.get("Point", []), transit_house_label)
            _print_section("Lots", by_kind.get("Lot", []), transit_house_label)
        else:
            _print_section(
                f"Transiting Planets{title_suffix}",
                by_kind.get("Planet", []) + by_kind.get("Angle", []),
                transit_house_label,
            )

    if aspects:
        _print_inter_aspects(chart_natal, chart_transit, ci_natal.name, "transit", details)


@chart_app.command(name="transits")
def chart_transits(
    name: str = typer.Argument(..., help="Saved natal chart name."),
    date: str | None = typer.Argument(None, help="Transit date YYYY-MM-DD (default: today)."),
    time: str | None = typer.Argument(None, help="Transit time HH:MM 24h (default: now)."),
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone for the transit date/time."),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(HouseSystem.porphyry, "--houses", help="House system."),
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
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(HouseSystem.porphyry, "--houses", help="House system."),
    details: bool = typer.Option(False, "--details", help="Include angles, nodes, and points in inter-aspects."),
    aspects: bool = typer.Option(False, "--aspects", help="Print inter-aspect tables."),
) -> None:
    """Show synastry (inter-aspects) between two saved charts."""
    try:
        ci_a = store.load(name_a)
        ci_b = store.load(name_b)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    chart_a = Chart.build(
        ci_a.to_datetime(),
        ci_a.lat if ci_a.lat is not None else 0.001,
        ci_a.lon if ci_a.lon is not None else 0.0,
        house_system=houses,
    )
    chart_b = Chart.build(
        ci_b.to_datetime(),
        ci_b.lat if ci_b.lat is not None else 0.001,
        ci_b.lon if ci_b.lon is not None else 0.0,
        house_system=houses,
    )

    console.print(
        f"[bold]Synastry:[/bold] [yellow]{ci_a.name.title()}[/yellow] ({ci_a.date})  ×  "
        f"[yellow]{ci_b.name.title()}[/yellow] ({ci_b.date})  "
        f"mode: [magenta]{mode}[/magenta]"
    )
    for ci in (ci_a, ci_b):
        if not ci.time_known:
            console.print(
                f"[yellow]⚠ {ci.name.title()} birth time unknown — planet positions approximate[/yellow]"
            )
        if not ci.location_known:
            console.print(
                f"[yellow]⚠ {ci.name.title()} birth location unknown[/yellow]"
            )
    if aspects:
        _print_inter_aspects(chart_a, chart_b, ci_a.name, ci_b.name, details)


def _print_info_list(title: str, items: list, *, extra_cols: list[tuple[str, str]] | None = None) -> None:
    table = _new_table(title)
    table.add_column("Name", style="bold")
    if extra_cols:
        for col_name, _ in extra_cols:
            table.add_column(col_name)
    table.add_column("Keywords")
    for item in items:
        row: list[str] = [item.name]
        if extra_cols:
            for _, attr in extra_cols:
                row.append(getattr(item, attr, ""))
        row.append(", ".join(item.keywords))
        table.add_row(*row)
    console.print(table)


def _print_info_detail(item) -> None:
    console.print(f"[bold cyan]{item.name}[/bold cyan]")
    if hasattr(item, "element"):
        console.print(f"  Element: [magenta]{item.element}[/magenta]  Modality: [magenta]{item.modality}[/magenta]  Ruler: [magenta]{item.ruler}[/magenta]")
    console.print(f"  Keywords: {', '.join(item.keywords)}")
    console.print()
    console.print(item.meaning)


def _fuzzy_match(query: str, candidates: dict[str, object]) -> object | None:
    q = query.lower().replace(" ", "")
    for key, item in candidates.items():
        if key.lower().replace(" ", "") == q:
            return item
    for item in candidates.values():
        for alias in getattr(item, "aliases", []):
            if alias.lower().replace(" ", "") == q:
                return item
    for key, item in candidates.items():
        if key.lower().startswith(query.lower()):
            return item
    for item in candidates.values():
        for alias in getattr(item, "aliases", []):
            if alias.lower().startswith(query.lower()):
                return item
    return None


@info_app.command(name="planets")
def info_planets(
    name: str | None = typer.Argument(None, help="Planet name (e.g. sun, venus, chiron)."),
) -> None:
    """Reference info on the planets."""
    from hoshi.info import PLANETS

    if name is not None:
        item = _fuzzy_match(name, PLANETS)
        if item is None:
            raise typer.BadParameter(f"Unknown planet: {name!r}")
        _print_info_detail(item)
    else:
        _print_info_list("Planets", list(PLANETS.values()))


@info_app.command(name="signs")
def info_signs(
    name: str | None = typer.Argument(None, help="Sign name (e.g. aries, ophiuchus)."),
) -> None:
    """Reference info on the zodiac signs (13 real-sky signs including Ophiuchus)."""
    from hoshi.info import SIGNS

    if name is not None:
        item = _fuzzy_match(name, SIGNS)
        if item is None:
            raise typer.BadParameter(f"Unknown sign: {name!r}")
        _print_info_detail(item)
    else:
        _print_info_list(
            "Signs",
            list(SIGNS.values()),
            extra_cols=[("Element", "element"), ("Modality", "modality"), ("Ruler", "ruler")],
        )


@info_app.command(name="angles")
def info_angles(
    name: str | None = typer.Argument(None, help="Angle name (e.g. ascendant, midheaven)."),
) -> None:
    """Reference info on chart angles."""
    from hoshi.info import ANGLES

    if name is not None:
        item = _fuzzy_match(name, ANGLES)
        if item is None:
            raise typer.BadParameter(f"Unknown angle: {name!r}")
        _print_info_detail(item)
    else:
        _print_info_list("Angles", list(ANGLES.values()))


@info_app.command(name="aspects")
def info_aspects(
    name: str | None = typer.Argument(None, help="Aspect name (e.g. conjunction, trine)."),
) -> None:
    """Reference info on aspects."""
    from hoshi.info import ASPECTS

    if name is not None:
        item = _fuzzy_match(name, ASPECTS)
        if item is None:
            raise typer.BadParameter(f"Unknown aspect: {name!r}")
        _print_info_detail(item)
    else:
        _print_info_list("Aspects", list(ASPECTS.values()))


@info_app.command(name="houses")
def info_houses(
    number: int | None = typer.Argument(None, help="House number (1–12)."),
) -> None:
    """Reference info on the twelve houses."""
    from hoshi.info import HOUSES

    if number is not None:
        item = HOUSES.get(number)
        if item is None:
            raise typer.BadParameter(f"Unknown house number: {number}")
        _print_info_detail(item)
    else:
        _print_info_list("Houses", list(HOUSES.values()))


@info_app.command(name="points")
def info_points(
    name: str | None = typer.Argument(None, help="Point name (e.g. lilith, fortune, n.node)."),
) -> None:
    """Reference info on calculated points (nodes, Lilith, Hermetic lots)."""
    from hoshi.info import POINTS

    if name is not None:
        item = _fuzzy_match(name, POINTS)
        if item is None:
            raise typer.BadParameter(f"Unknown point: {name!r}")
        _print_info_detail(item)
    else:
        _print_info_list("Points", list(POINTS.values()))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
