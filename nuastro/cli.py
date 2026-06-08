"""Typer CLI entry point."""

from datetime import datetime
from zoneinfo import ZoneInfo

import typer

from nuastro import store
from nuastro.chart import Chart
from nuastro.store import ChartInput
from nuastro.zodiac import Placement, format_deg


app = typer.Typer(
    add_completion=False,
    help="Real-sky astrology CLI — Python port of Nuastro.",
)
chart_app = typer.Typer(help="Create, view, list, and delete birth charts.")
app.add_typer(chart_app, name="chart")


ANGLE_DISPLAY_NAMES: dict[str, str] = {
    "asc":        "Ascendant",
    "mc":         "Midheaven",
    "ic":         "Imum Coeli",
    "dsc":        "Descendant",
    "vertex":     "Vertex",
    "antivertex": "Antivertex",
}

VALID_MODES = {"nuastro", "tropical", "vedic"}


@app.callback()
def _root() -> None:
    """Forces Typer into multi-command mode so `chart` isn't collapsed."""


def _validate_mode(mode: str) -> None:
    if mode not in VALID_MODES:
        raise typer.BadParameter(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")


def _to_datetime(ci: ChartInput) -> datetime:
    try:
        local = datetime.fromisoformat(f"{ci.date}T{ci.time}")
    except ValueError as exc:
        raise typer.BadParameter(f"Could not parse date/time: {exc}") from exc
    return local.replace(tzinfo=ZoneInfo(ci.tz))


def _print_chart(ci: ChartInput, mode: str, *, show_cusps: bool = False) -> None:
    when = _to_datetime(ci)
    chart = Chart.build(when, ci.lat, ci.lng)
    house_attr = "house_13" if mode == "nuastro" else "house_placidus"
    house_label = "H13" if mode == "nuastro" else "H"

    header = f"Chart for {when.isoformat()}  ({ci.lat:.4f}°, {ci.lng:.4f}°)  mode: {mode}"
    if ci.name:
        header = f"[{ci.name}] " + header
    typer.echo(header)
    if mode == "vedic":
        typer.echo(f"Ayanamsa (Lahiri, approx): {chart.ayanamsa:.4f}°")

    typer.echo("")
    typer.echo("Angles")
    typer.echo(f"  {'Point':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}")
    typer.echo("  " + "-" * 50)
    for a in chart.angles:
        placement = getattr(a.placed, mode)
        h = getattr(a, house_attr)
        typer.echo(
            f"  {ANGLE_DISPLAY_NAMES[a.name]:<11} {placement.name:<13} {format_deg(placement.deg):<8} "
            f"{a.placed.lon:7.2f}°     {h:>3}"
        )

    typer.echo("")
    typer.echo("Planets")
    typer.echo(f"  {'Planet':<10} {'Sign':<13} {'Degree':<8} {'Lon':>8}  Rx  {house_label:>3}")
    typer.echo("  " + "-" * 50)
    for p in chart.planets:
        placement = getattr(p.placed, mode)
        rx = "℞" if p.pos.retrograde else " "
        h = getattr(p, house_attr)
        typer.echo(
            f"  {p.pid:<10} {placement.name:<13} {format_deg(placement.deg):<8} "
            f"{p.placed.lon:7.2f}°  {rx}  {h:>3}"
        )

    typer.echo("")
    typer.echo("Points")
    typer.echo(f"  {'Point':<11} {'Sign':<13} {'Degree':<8} {'Lon':>8}      {house_label:>3}")
    typer.echo("  " + "-" * 50)
    for pt in chart.points:
        placement = getattr(pt.placed, mode)
        h = getattr(pt, house_attr)
        typer.echo(
            f"  {pt.name:<10} {placement.name:<13} {format_deg(placement.deg):<8} "
            f"{pt.placed.lon:7.2f}°     {h:>3}"
        )

    if show_cusps:
        typer.echo("")
        typer.echo("Placidus cusps")
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
    name: str = typer.Argument(..., help="Name to save this chart under (filename-safe key)."),
    date: str = typer.Argument(..., help="Birth date, YYYY-MM-DD."),
    time: str = typer.Argument("12:00", help="Birth time, HH:MM (24h)."),
    lat: float = typer.Option(..., "--lat", help="Birth latitude, degrees (N positive)."),
    lng: float = typer.Option(..., "--lng", help="Birth longitude, degrees (E positive)."),
    tz: str = typer.Option("UTC", "--tz", help="IANA timezone of the birth time, e.g. America/Chicago."),
    mode: str = typer.Option("nuastro", "--mode", help="Zodiac mode: nuastro, tropical, or vedic."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing saved chart with the same name."),
    cusps: bool = typer.Option(False, "--cusps", help="Also print the 12 Placidus house cusps."),
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
    _print_chart(ci, mode, show_cusps=cusps)


@chart_app.command(name="list")
def chart_list() -> None:
    """List all saved charts."""
    charts = store.list_all()
    if not charts:
        typer.echo("No saved charts. Use `astro chart add NAME DATE [TIME] --lat ... --lng ...` to create one.")
        return
    typer.echo(f"{'Name':<24} {'Date':<10} {'Time':<6} {'Timezone':<22} {'Lat':>10} {'Lng':>10}")
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
    time: str = typer.Argument("12:00", help="Birth time for one-off charts, HH:MM (24h)."),
    lat: float = typer.Option(None, "--lat", help="One-off chart latitude (N positive)."),
    lng: float = typer.Option(None, "--lng", help="One-off chart longitude (E positive)."),
    tz: str = typer.Option("UTC", "--tz", help="One-off chart IANA timezone, e.g. America/Chicago."),
    mode: str = typer.Option("nuastro", "--mode", help="Zodiac mode: nuastro, tropical, or vedic."),
    cusps: bool = typer.Option(False, "--cusps", help="Also print the 12 Placidus house cusps."),
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

    _print_chart(ci, mode, show_cusps=cusps)


@chart_app.command(name="delete")
def chart_delete(
    name: str = typer.Argument(..., help="Name of a saved chart."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
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
