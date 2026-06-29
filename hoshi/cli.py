"""Typer CLI entry point."""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

import typer
from rich.console import Console

from hoshi import store
from hoshi.chart import Chart, HouseSystem
from hoshi.ephemeris import HorizonsError
from hoshi.output import (
    ChartListOutput,
    ChartOutput,
    CompareOutput,
    CuspsOutput,
    DeleteOutput,
    HouseComparisonOutput,
    InfoDetailOutput,
    InfoListOutput,
    OutputModel,
    TransitsOutput,
)
from hoshi.store import ChartInput
from hoshi.utils import fuzzy_match
from hoshi.zodiac import ZodiacMode


console = Console()


app = typer.Typer(
    help="Real-sky astrology CLI — Python port of Nuastro.",
)
chart_app = typer.Typer(help="Create, view, list, and delete birth charts.")
app.add_typer(chart_app, name="chart")
info_app = typer.Typer(help="Reference info on astrological concepts.")
app.add_typer(info_app, name="info")


class GroupBy(StrEnum):
    category = "category"
    sign = "sign"
    house = "house"
    planet = "planet"


class OutputFormat(StrEnum):
    table = "table"
    json = "json"
    yaml = "yaml"
    csv = "csv"


@app.callback()
def _root() -> None:
    """Forces Typer into multi-command mode so `chart` isn't collapsed."""


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
# Helpers
# ---------------------------------------------------------------------------


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
        item = fuzzy_match(name, catalog)
        if item is None:
            raise typer.BadParameter(f"Unknown {noun}: {name!r}")
        _output(InfoDetailOutput.build(item), fmt)
    else:
        _output(
            InfoListOutput.build(title, list(catalog.values()), extra_cols=extra_cols),
            fmt,
        )


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
        help="Group output by category (default), sign, house, or planet.",
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

    chart = Chart.from_input(ci, house_system=houses)
    output = ChartOutput.build(
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
        help="Group output by category (default), sign, house, or planet.",
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

    chart = Chart.from_input(ci, house_system=houses)
    output = ChartOutput.build(
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
    _output(ChartListOutput.build(), fmt)


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
        chart = Chart.from_input(ci, house_system=houses)
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    _output(CuspsOutput.build(chart, mode), fmt)


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
        help="Group output by category (default), sign, house, or planet.",
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
        output = HouseComparisonOutput.build(ci, mode, details=details)
        _output(output, fmt)
        return

    chart = Chart.from_input(ci, house_system=houses)
    output = ChartOutput.build(
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
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group output by category (default), sign, house, or planet.",
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

    chart_natal = Chart.from_input(ci, house_system=houses)
    output = TransitsOutput.build(
        ci,
        chart_natal,
        transit_dt,
        mode,
        details=details,
        aspects=aspects,
        natal=natal,
        group_by=group_by,
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
    group_by: GroupBy = typer.Option(
        GroupBy.category,
        "--group-by",
        help="Group output by category (default), sign, house, or planet.",
    ),
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

    chart_a = Chart.from_input(ci_a, house_system=houses)
    chart_b = Chart.from_input(ci_b, house_system=houses)

    output = CompareOutput.build(
        ci_a,
        ci_b,
        chart_a,
        chart_b,
        mode,
        details=details,
        aspects=aspects,
        group_by=group_by,
    )
    _output(output, fmt)


# ---------------------------------------------------------------------------
# Info commands
# ---------------------------------------------------------------------------


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
        extra_cols=["Element", "Modality", "Ruler", "Cusp", "Size"],
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
        _output(InfoDetailOutput.build(item), fmt)
    else:
        _output(InfoListOutput.build("Houses", list(HOUSES.values())), fmt)


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
        item = fuzzy_match(name, POINTS)
        if item is None:
            raise typer.BadParameter(f"Unknown point: {name!r}")
        _output(InfoDetailOutput.build(item), fmt)
    else:
        _output(InfoListOutput.build("Points", list(POINTS.values())), fmt)


def main() -> None:
    from hoshi.adb import ADBError

    try:
        app()
    except (HorizonsError, ADBError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
