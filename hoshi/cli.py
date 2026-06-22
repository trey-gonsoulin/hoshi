"""Typer CLI entry point."""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

import typer
from rich.console import Console

from pydantic import BaseModel

from hoshi import store
from hoshi.aspects import compute_aspects, compute_inter_aspects
from hoshi.chart import (
    PLACEHOLDER_LAT,
    PLACEHOLDER_LON,
    Chart,
    HouseSystem,
    uncertain_signs,
)
from hoshi.dignities import DIGNITY_SYMBOLS, dignity_for, element_modality_tally
from hoshi.ephemeris import HorizonsError
from hoshi.houses import house_13_arc, house_from_cusps
from hoshi.output import (
    BodyEntry,
    ChartHeader,
    ChartListEntry,
    ChartListOutput,
    ChartOutput,
    CompareHeader,
    CompareOutput,
    CuspEntry,
    CuspsOutput,
    DeleteOutput,
    HouseComparisonOutput,
    InfoDetailOutput,
    InfoItem,
    InfoListOutput,
    OutputModel,
    TallyOutput,
    TallyRow,
    TransitHeader,
    TransitsOutput,
)
from hoshi.store import ChartInput
from hoshi.zodiac import Placement, ZodiacMode


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


class GroupBy(StrEnum):
    category = "category"
    sign = "sign"
    house = "house"


class OutputFormat(StrEnum):
    table = "table"
    json = "json"
    yaml = "yaml"
    csv = "csv"


@app.callback()
def _root() -> None:
    """Forces Typer into multi-command mode so `chart` isn't collapsed."""


NODE_NAMES = {"N.Node", "S.Node"}


def _output(result: OutputModel, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        print(result.model_dump_json(indent=2))
    elif fmt == OutputFormat.yaml:
        print(result.dump_yaml(), end="")
    elif fmt == OutputFormat.csv:
        print(result.dump_csv(), end="")
    else:
        result.render(console)


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def chart_from_input(ci: ChartInput, houses: HouseSystem | str) -> Chart:
    """Build a Chart from stored input (placeholder coords for unknown location).

    Thin alias for `Chart.from_input`; location-derived output is suppressed
    later based on `chart.location_known`."""
    return Chart.from_input(ci, house_system=houses)


def _resolve_chart_input(
    target: str, time: str, lat: float | None, lon: float | None, tz: str
) -> ChartInput:
    """Resolve a command target to a ChartInput: a one-off chart when --lat/--lon
    are given, otherwise a saved chart loaded by name."""
    one_off = lat is not None or lon is not None
    if one_off:
        if lat is None or lon is None:
            raise typer.BadParameter("One-off charts require both --lat and --lon.")
        return ChartInput(name="", date=target, time=time, tz=tz, lat=lat, lon=lon)
    try:
        return store.load(target)
    except FileNotFoundError as exc:
        raise typer.BadParameter(
            f"{exc}\nIf you meant a one-off chart, also pass --lat and --lon "
            f"(and the first argument should be a YYYY-MM-DD date)."
        ) from exc


class BodySelection(BaseModel, frozen=True):
    """Which body groups to include when assembling display rows.

    Replaces a row of boolean parameters on `_build_bodies`; callers construct
    one explicitly. `details` pulls in nodes/points (and, with `lots`, lots);
    `angles`/`lots`/`houses` gate those columns/sections independently.
    """

    details: bool = False
    angles: bool = True
    lots: bool = True
    houses: bool = True
    uncertain_pids: frozenset[str] = frozenset()


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


def _build_tallies(chart: Chart, mode: str, *, show_full: bool = True) -> TallyOutput:
    tally = element_modality_tally(
        chart, mode, include_angles=show_full, include_lots=show_full
    )
    return TallyOutput(
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


def _build_chart_output(
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
    tallies = _build_tallies(chart, mode, show_full=show_full) if details else None
    aspect_list = compute_aspects(chart, details) if aspects else None

    return ChartOutput(
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


def _build_house_comparison(
    ci: ChartInput, mode: str, *, details: bool
) -> HouseComparisonOutput:
    when = ci.to_datetime()
    lat = ci.lat if ci.lat is not None else PLACEHOLDER_LAT
    lon = ci.lon if ci.lon is not None else PLACEHOLDER_LON
    charts = {sys: Chart.build(when, lat, lon, house_system=sys) for sys in HouseSystem}
    base = charts[HouseSystem.porphyry]
    bodies = _build_bodies(base, mode, BodySelection(details=details))

    systems = [str(s) for s in HouseSystem]
    house_columns: dict[str, list[int | None]] = {}
    for sys in HouseSystem:
        c = charts[sys]
        houses: list[int | None] = [p.house for p in c.planets]
        angles = c.angles if details else [a for a in c.angles if a.name == "asc"]
        houses.extend(a.house for a in angles)
        if details:
            houses.extend(pt.house for pt in c.points)
            houses.extend(pt.house for pt in c.lots)
        house_columns[str(sys)] = houses

    return HouseComparisonOutput(
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


def _fuzzy_match(query: str, candidates: Mapping[str, object]) -> object | None:
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


# ---------------------------------------------------------------------------
# Chart commands
# ---------------------------------------------------------------------------


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
        None,
        "--location",
        help="Birth location to geocode, e.g. 'Austin, TX'. Cannot be used with --lat/--lon.",
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="IANA timezone of the birth time, e.g. America/Chicago."
    ),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
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
        False,
        "--aspects",
        help="Print aspect tables (uses all bodies with --details, planets+Asc otherwise).",
    ),
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group entries by category, sign, or house.",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
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
        # geopy types geocode() as possibly-a-coroutine (async adapters); the
        # sync Nominatim path returns a Location, so these attrs are present.
        lat = result.latitude  # type: ignore[reportAttributeAccessIssue]
        lon = result.longitude  # type: ignore[reportAttributeAccessIssue]
        typer.echo(f"Resolved location: {result.address}")  # type: ignore[reportAttributeAccessIssue]
        typer.echo(f"Coordinates: {lat:.4f}°N, {lon:.4f}°E")
    if (lat is None) != (lon is None):
        raise typer.BadParameter(
            "--lat and --lon must both be provided or both omitted."
        )
    ci = ChartInput(name=name, date=date, time=time, tz=tz, lat=lat, lon=lon)
    try:
        path = store.save(ci, overwrite=force)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Saved chart to {path}", err=(fmt == OutputFormat.json))
    if fmt == OutputFormat.table:
        typer.echo("")

    chart = chart_from_input(ci, houses)
    output = _build_chart_output(
        ci,
        chart,
        mode,
        details=details,
        aspects=aspects,
        group_by=group_by,
        show_cusps=cusps,
    )
    _output(output, fmt)


@chart_app.command(name="import")
def chart_import(
    source: str = typer.Argument(
        ...,
        help="ADB URL or page title (e.g. 'Mercury, Freddie').",
    ),
    name: str | None = typer.Argument(
        None, help="Name to save the chart under (default: from ADB page)."
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing saved chart with the same name."
    ),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry, "--houses", help="House system."
    ),
    cusps: bool = typer.Option(
        False, "--cusps", help="Also print the house cusps for the chosen system."
    ),
    details: bool = typer.Option(
        False, "--details", help="Also print all angles, nodes, and calculated points."
    ),
    aspects: bool = typer.Option(
        False,
        "--aspects",
        help="Print aspect tables (uses all bodies with --details, planets+Asc otherwise).",
    ),
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group entries by category, sign, or house.",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Import a birth chart from Astro-Databank."""
    from hoshi.adb import ADBError, adb_to_chart_input

    try:
        result = adb_to_chart_input(source, name)
    except ADBError as exc:
        raise typer.BadParameter(str(exc)) from exc

    ci = result.chart_input
    rating = result.rodden_rating
    if fmt == OutputFormat.table:
        typer.echo(f"Importing: {ci.name}")
        if rating:
            typer.echo(f"Rodden rating: {rating}")
        if result.source_url:
            typer.echo(f"Source: {result.source_url}")

    try:
        path = store.save(ci, overwrite=force)
    except FileExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(f"Saved chart to {path}", err=(fmt == OutputFormat.json))
    if fmt == OutputFormat.table:
        typer.echo("")

    chart = chart_from_input(ci, houses)
    output = _build_chart_output(
        ci,
        chart,
        mode,
        details=details,
        aspects=aspects,
        group_by=group_by,
        show_cusps=cusps,
    )
    _output(output, fmt)


@chart_app.command(name="list")
def chart_list(
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """List all saved charts."""
    charts = store.list_all()
    output = ChartListOutput(
        charts=[
            ChartListEntry(
                name=ci.name,
                date=ci.date,
                time=ci.time,
                tz=ci.tz,
                lat=ci.lat,
                lon=ci.lon,
            )
            for ci in charts
        ]
    )
    _output(output, fmt)


@chart_app.command(name="cusps")
def chart_cusps(
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
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone, e.g. America/Chicago."),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry, "--houses", help="House system."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Print house cusps for a saved or one-off chart."""
    ci = _resolve_chart_input(target, time, lat, lon, tz)
    if not ci.time_known:
        raise typer.BadParameter(
            f"Chart {ci.name!r} has no birth time — house cusps cannot be computed."
        )
    if not ci.location_known:
        raise typer.BadParameter(
            f"Chart {ci.name!r} has no birth location — house cusps cannot be computed."
        )
    try:
        chart = chart_from_input(ci, houses)
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    cusp_entries = _build_cusp_entries(chart, mode)
    output = CuspsOutput(house_system=chart.house_system, cusps=cusp_entries)
    _output(output, fmt)


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
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
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
        False,
        "--aspects",
        help="Print aspect tables (uses all bodies with --details, planets+Asc otherwise).",
    ),
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group entries by category, sign, or house.",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
    compare_houses: bool = typer.Option(
        False,
        "--compare-houses",
        help="Show house assignments side-by-side across all house systems "
        "and highlight differences.",
    ),
) -> None:
    """Display a chart by saved name, or compute a one-off chart from birth parameters."""
    ci = _resolve_chart_input(target, time, lat, lon, tz)

    if compare_houses:
        if not ci.time_known or not ci.location_known:
            raise typer.BadParameter(
                "--compare-houses requires a chart with known birth time and location."
            )
        output = _build_house_comparison(ci, mode, details=details)
        _output(output, fmt)
        return

    chart = chart_from_input(ci, houses)
    output = _build_chart_output(
        ci,
        chart,
        mode,
        details=details,
        aspects=aspects,
        group_by=group_by,
        show_cusps=cusps,
    )
    _output(output, fmt)


@chart_app.command(name="delete")
def chart_delete(
    name: str = typer.Argument(..., help="Name of a saved chart."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip the confirmation prompt."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Delete a saved chart."""
    if not store.exists(name):
        raise typer.BadParameter(f"No saved chart named {name!r}")
    if not yes:
        typer.confirm(f"Delete saved chart {name!r}?", abort=True)
    path = store.delete(name)
    _output(DeleteOutput(path=str(path)), fmt)


@chart_app.command(name="transits")
def chart_transits(
    name: str = typer.Argument(..., help="Saved natal chart name."),
    date: str | None = typer.Argument(
        None, help="Transit date YYYY-MM-DD (default: today)."
    ),
    time: str | None = typer.Argument(
        None, help="Transit time HH:MM 24h (default: now)."
    ),
    tz: str = typer.Option(
        "UTC", "--tz", help="IANA timezone for the transit date/time."
    ),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry, "--houses", help="House system."
    ),
    details: bool = typer.Option(
        False, "--details", help="Include angles, nodes, and points."
    ),
    aspects: bool = typer.Option(
        False, "--aspects", help="Print inter-aspect tables (natal × transit)."
    ),
    natal: bool = typer.Option(
        False,
        "--natal",
        help="Show natal placements alongside transits in a side-by-side table.",
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
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

    natal_time_known = ci.time_known
    natal_loc_known = ci.location_known

    chart_natal = chart_from_input(ci, houses)
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
        compute_inter_aspects(chart_natal, chart_transit, details) if aspects else None
    )

    output = TransitsOutput(
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
    )
    _output(output, fmt)


@chart_app.command(name="compare")
def chart_compare(
    name_a: str = typer.Argument(..., help="First saved chart name."),
    name_b: str = typer.Argument(..., help="Second saved chart name."),
    mode: ZodiacMode = typer.Option(ZodiacMode.realsky, "--mode", help="Zodiac mode."),
    houses: HouseSystem = typer.Option(
        HouseSystem.porphyry, "--houses", help="House system."
    ),
    details: bool = typer.Option(
        False, "--details", help="Include angles, nodes, and points in inter-aspects."
    ),
    aspects: bool = typer.Option(False, "--aspects", help="Print inter-aspect tables."),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Show synastry (inter-aspects) between two saved charts."""
    try:
        ci_a = store.load(name_a)
        ci_b = store.load(name_b)
    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    chart_a = chart_from_input(ci_a, houses)
    chart_b = chart_from_input(ci_b, houses)

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

    aspect_list = compute_inter_aspects(chart_a, chart_b, details) if aspects else None

    output = CompareOutput(
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
    )
    _output(output, fmt)


# ---------------------------------------------------------------------------
# Info commands
# ---------------------------------------------------------------------------


def _build_info_detail(item) -> InfoDetailOutput:
    return InfoDetailOutput(
        name=item.name,
        keywords=item.keywords,
        meaning=item.meaning,
        element=getattr(item, "element", None),
        modality=getattr(item, "modality", None),
        ruler=getattr(item, "ruler", None),
    )


def _build_info_list(
    title: str, items: list, *, extra_cols: list[str] | None = None
) -> InfoListOutput:
    return InfoListOutput(
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


def _render_info(
    name: str | None,
    fmt: OutputFormat,
    catalog: Mapping[str, object],
    *,
    title: str,
    noun: str,
    extra_cols: list[str] | None = None,
) -> None:
    """Render one item (fuzzy-matched) or the whole catalog for an `info` command."""
    if name is not None:
        item = _fuzzy_match(name, catalog)
        if item is None:
            raise typer.BadParameter(f"Unknown {noun}: {name!r}")
        _output(_build_info_detail(item), fmt)
    else:
        _output(
            _build_info_list(title, list(catalog.values()), extra_cols=extra_cols), fmt
        )


@info_app.command(name="planets")
def info_planets(
    name: str | None = typer.Argument(
        None, help="Planet name (e.g. sun, venus, chiron)."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on the planets."""
    from hoshi.info import PLANETS

    _render_info(name, fmt, PLANETS, title="Planets", noun="planet")


@info_app.command(name="signs")
def info_signs(
    name: str | None = typer.Argument(None, help="Sign name (e.g. aries, ophiuchus)."),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on the zodiac signs (13 real-sky signs including Ophiuchus)."""
    from hoshi.info import SIGNS

    _render_info(
        name,
        fmt,
        SIGNS,
        title="Signs",
        noun="sign",
        extra_cols=["Element", "Modality", "Ruler"],
    )


@info_app.command(name="angles")
def info_angles(
    name: str | None = typer.Argument(
        None, help="Angle name (e.g. ascendant, midheaven)."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on chart angles."""
    from hoshi.info import ANGLES

    _render_info(name, fmt, ANGLES, title="Angles", noun="angle")


@info_app.command(name="aspects")
def info_aspects(
    name: str | None = typer.Argument(
        None, help="Aspect name (e.g. conjunction, trine)."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on aspects."""
    from hoshi.info import ASPECTS

    _render_info(name, fmt, ASPECTS, title="Aspects", noun="aspect")


@info_app.command(name="houses")
def info_houses(
    number: int | None = typer.Argument(None, help="House number (1–12)."),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on the twelve houses."""
    from hoshi.info import HOUSES

    if number is not None:
        item = HOUSES.get(number)
        if item is None:
            raise typer.BadParameter(f"Unknown house number: {number}")
        _output(_build_info_detail(item), fmt)
    else:
        _output(_build_info_list("Houses", list(HOUSES.values())), fmt)


@info_app.command(name="points")
def info_points(
    name: str | None = typer.Argument(
        None, help="Point name (e.g. lilith, fortune, n.node)."
    ),
    fmt: OutputFormat = typer.Option(
        OutputFormat.table, "--format", help="Output format: table, json, yaml, or csv."
    ),
) -> None:
    """Reference info on calculated points (nodes, Lilith, Hermetic lots)."""
    from hoshi.info import POINTS

    if name is not None:
        item = _fuzzy_match(name, POINTS)
        if item is None:
            raise typer.BadParameter(f"Unknown point: {name!r}")
        _output(_build_info_detail(item), fmt)
    else:
        _output(_build_info_list("Points", list(POINTS.values())), fmt)


def main() -> None:
    from hoshi.adb import ADBError

    try:
        app()
    except (HorizonsError, ADBError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
