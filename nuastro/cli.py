"""Typer CLI entry point."""

from datetime import datetime
from zoneinfo import ZoneInfo

import typer

from nuastro import store
from nuastro.chart import HOUSE_SYSTEMS, Chart
from nuastro.store import ChartInput
from nuastro.zodiac import IAU, TROP_NAMES, Placement, format_deg


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

VALID_MODES = {"nuastro", "tropical", "vedic"}
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
    return [s.name for s in IAU] if mode == "nuastro" else TROP_NAMES


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


def _print_by_sign(entries: list[dict], mode: str, house_label: str) -> None:
    order = _sign_order(mode)
    rank = {name: i for i, name in enumerate(order)}
    grouped: dict[str, list[dict]] = {}
    for e in entries:
        grouped.setdefault(e["placement"].name, []).append(e)

    for sign in sorted(grouped, key=lambda s: rank.get(s, 99)):
        rows = sorted(grouped[sign], key=lambda e: e["placement"].deg)
        typer.echo("")
        typer.echo(f"{sign}")
        typer.echo(
            f"  {'Kind':<7} {'Name':<11} {'Degree':<8} {'Lon':>8}  Rx  {house_label:>3}"
        )
        typer.echo("  " + "-" * 46)
        for e in rows:
            typer.echo(
                f"  {e['kind']:<7} {e['name']:<11} "
                f"{format_deg(e['placement'].deg):<8} {e['lon']:7.2f}°  "
                f"{e['rx'] or ' ':<2} {e['house']:>3}"
            )


def _print_by_house(entries: list[dict], asc: float, house_label: str) -> None:
    grouped: dict[int, list[dict]] = {}
    for e in entries:
        grouped.setdefault(e["house"], []).append(e)

    for house in sorted(grouped):
        rows = sorted(grouped[house], key=lambda e: (e["lon"] - asc) % 360.0)
        typer.echo("")
        typer.echo(f"{house_label}{house}")
        typer.echo(
            f"  {'Kind':<7} {'Name':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}  Rx"
        )
        typer.echo("  " + "-" * 55)
        for e in rows:
            typer.echo(
                f"  {e['kind']:<7} {e['name']:<11} {e['placement'].name:<13} "
                f"{format_deg(e['placement'].deg):<8} {e['lon']:7.2f}°  "
                f"{e['rx'] or ' '}"
            )


def _print_chart(
    ci: ChartInput,
    mode: str,
    *,
    show_cusps: bool = False,
    details: bool = False,
    group_by: str = "category",
    house_system: str = "porphyry",
) -> None:
    when = _to_datetime(ci)
    chart = Chart.build(when, ci.lat, ci.lng, house_system=house_system)
    house_label = "H"

    header = (
        f"Chart for {when.isoformat()}  ({ci.lat:.4f}°, {ci.lng:.4f}°)  "
        f"mode: {mode}  houses: {chart.house_system}"
    )
    if ci.name:
        header = f"[{ci.name}] " + header
    typer.echo(header)
    if mode == "vedic":
        typer.echo(f"Ayanamsa (Lahiri, approx): {chart.ayanamsa:.4f}°")

    if group_by != "category":
        entries = _collect_entries(chart, mode, details)
        typer.echo("")
        if group_by == "sign":
            typer.echo("By Sign")
            _print_by_sign(entries, mode, house_label)
        else:
            typer.echo("By House")
            asc = next(a.placed.lon for a in chart.angles if a.name == "asc")
            _print_by_house(entries, asc, house_label)
        if show_cusps:
            _print_cusps(chart, mode)
        return

    typer.echo("")
    typer.echo("Planets")
    typer.echo(
        f"  {'Planet':<10} {'Sign':<13} {'Degree':<8} {'Lon':>8}  Rx  {house_label:>3}"
    )
    typer.echo("  " + "-" * 50)
    for p in chart.planets:
        placement = getattr(p.placed, mode)
        rx = "℞" if p.pos.retrograde else " "
        h = p.house
        typer.echo(
            f"  {p.pid.capitalize():<10} {placement.name:<13} {format_deg(placement.deg):<8} "
            f"{p.placed.lon:7.2f}°  {rx}  {h:>3}"
        )

    angles = chart.angles if details else [a for a in chart.angles if a.name == "asc"]
    typer.echo("")
    typer.echo("Angles")
    typer.echo(
        f"  {'Point':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}"
    )
    typer.echo("  " + "-" * 50)
    for a in angles:
        placement = getattr(a.placed, mode)
        h = a.house
        typer.echo(
            f"  {ANGLE_DISPLAY_NAMES[a.name]:<11} {placement.name:<13} {format_deg(placement.deg):<8} "
            f"{a.placed.lon:7.2f}°     {h:>3}"
        )

    if details:
        nodes = [pt for pt in chart.points if pt.name in NODE_NAMES]
        points = [pt for pt in chart.points if pt.name not in NODE_NAMES]

        typer.echo("")
        typer.echo("Nodes")
        typer.echo(
            f"  {'Point':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}"
        )
        typer.echo("  " + "-" * 50)
        for pt in nodes:
            placement = getattr(pt.placed, mode)
            h = pt.house
            typer.echo(
                f"  {pt.name:<10} {placement.name:<13} {format_deg(placement.deg):<8} "
                f"{pt.placed.lon:7.2f}°     {h:>3}"
            )

        typer.echo("")
        typer.echo("Points")
        typer.echo(
            f"  {'Point':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}"
        )
        typer.echo("  " + "-" * 50)
        for pt in points:
            placement = getattr(pt.placed, mode)
            h = pt.house
            typer.echo(
                f"  {pt.name:<10} {placement.name:<13} {format_deg(placement.deg):<8} "
                f"{pt.placed.lon:7.2f}°     {h:>3}"
            )

        typer.echo("")
        typer.echo("Lots")
        typer.echo(
            f"  {'Lot':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}"
        )
        typer.echo("  " + "-" * 50)
        for pt in chart.lots:
            placement = getattr(pt.placed, mode)
            h = pt.house
            typer.echo(
                f"  {pt.name:<11} {placement.name:<13} {format_deg(placement.deg):<8} "
                f"{pt.placed.lon:7.2f}°     {h:>3}"
            )

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
        f"Chart for {when.isoformat()}  ({ci.lat:.4f}°, {ci.lng:.4f}°)  mode: {mode}"
    )
    if ci.name:
        header = f"[{ci.name}] " + header
    typer.echo(header)
    typer.echo("")
    typer.echo("House comparison (yellow = differs from Porphyry)")
    typer.echo("")

    col_headers = "  ".join(f"{s.capitalize():>8}" for s in HOUSE_SYSTEMS)
    typer.echo(
        f"  {'Kind':<7} {'Name':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}   {col_headers}"
    )
    typer.echo("  " + "-" * (52 + len(col_headers)))

    for i, e in enumerate(entries):
        houses_row = [house_columns[s][i] for s in HOUSE_SYSTEMS]
        baseline = houses_row[0]  # porphyry
        cells: list[str] = []
        for h in houses_row:
            text = f"{h:>8}"
            if h != baseline:
                text = typer.style(text, fg=typer.colors.YELLOW, bold=True)
            cells.append(text)
        typer.echo(
            f"  {e['kind']:<7} {e['name']:<11} {e['placement'].name:<13} "
            f"{format_deg(e['placement'].deg):<8} {e['lon']:7.2f}°   "
            + "  ".join(cells)
        )


def _print_cusps(chart: Chart, mode: str) -> None:
    typer.echo("")
    typer.echo(f"{chart.house_system.capitalize()} cusps")
    place_cusp = {
        "nuastro": Placement.nuastro,
        "tropical": Placement.tropical,
        "vedic": lambda c: Placement.vedic(c, chart.ayanamsa),
    }[mode]
    for i, c in enumerate(chart.cusps, start=1):
        p = place_cusp(c)
        typer.echo(f"  H{i:<2} {p.name:<13} {format_deg(p.deg):<8} {c:7.2f}°")


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
        "nuastro", "--mode", help="Zodiac mode: nuastro, tropical, or vedic."
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
    typer.echo(
        f"{'Name':<24} {'Date':<10} {'Time':<6} {'Timezone':<22} {'Lat':>10} {'Lng':>10}"
    )
    typer.echo("-" * 86)
    for ci in charts:
        typer.echo(
            f"{ci.name:<24} {ci.date:<10} {ci.time:<6} {ci.tz:<22} {ci.lat:>10.4f} {ci.lng:>10.4f}"
        )


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
        "nuastro", "--mode", help="Zodiac mode: nuastro, tropical, or vedic."
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
    group_by: str = typer.Option(
        "category",
        "--group-by",
        help="Group entries by: category (default), sign, or house.",
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

    if compare_houses:
        _print_house_comparison(ci, mode, details=details)
        return

    _print_chart(
        ci,
        mode,
        show_cusps=cusps,
        details=details,
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
