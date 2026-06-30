"""MCP server exposing hoshi chart tools via Streamable HTTP transport."""

from datetime import datetime
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

from hoshi import ChartInput
from hoshi.chart import Chart, HouseSystem
from hoshi.output import ChartOutput, CompareOutput, CuspsOutput, TransitsOutput
from hoshi.zodiac import ZodiacMode

# stateless_http=True: each Lambda invocation handles one request independently,
# no in-memory session state to preserve across container instances.
# json_response=True: plain JSON responses instead of SSE streams — required
# behind API Gateway which cannot hold long-lived streaming connections.
# streamable_http_path="/": the MCP endpoint lives at the root of this sub-app,
# so mounting at /mcp in FastAPI exposes it at /mcp (not /mcp/mcp).
mcp = FastMCP(
    "hoshi",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    # host is unused when mounted into FastAPI, but the default "127.0.0.1"
    # triggers DNS-rebinding protection that rejects non-localhost Host headers.
    # "0.0.0.0" signals a public deployment, leaving transport_security=None.
    host="0.0.0.0",
)


# ---------------------------------------------------------------------------
# Shared helpers (mirror routes/charts.py — kept local to avoid coupling)
# ---------------------------------------------------------------------------


def _geocode(location: str) -> tuple[float, float]:
    from geopy.geocoders import Nominatim

    geo = Nominatim(user_agent="hoshi")
    result = geo.geocode(location)
    if result is None:
        raise ValueError(f"Could not geocode location: {location!r}")
    return result.latitude, result.longitude  # type: ignore[reportAttributeAccessIssue]


def _resolve_coords(
    lat: float | None,
    lon: float | None,
    location: str | None,
) -> tuple[float | None, float | None]:
    if location is not None and (lat is not None or lon is not None):
        raise ValueError("Cannot specify location together with lat/lon.")
    if location is not None:
        return _geocode(location)
    if (lat is None) != (lon is None):
        raise ValueError("lat and lon must both be provided or both omitted.")
    return lat, lon


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def compute_chart(
    date: str,
    time: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    location: str | None = None,
    tz: str = "UTC",
    mode: str = "realsky",
    houses: str = "porphyry",
    details: bool = True,
    aspects: bool = True,
    cusps: bool = False,
) -> dict:
    """Compute a real-sky natal astrological chart.

    Returns planetary positions, signs, degrees, houses, dignities, and aspects.
    Use mode='realsky' (default) for IAU constellation-based 13-sign placements,
    'tropical' for standard 12-sign, or 'vedic' for sidereal/Lahiri.
    Time and location are optional — noon UTC and suppressed angles are used
    when omitted, with uncertainty warnings included in the response.

    Args:
        date: Birth date in YYYY-MM-DD format.
        time: Birth time in HH:MM or HH:MM:SS (24-hour). Omit if unknown.
        lat: Latitude in decimal degrees. Use with lon; omit if using location.
        lon: Longitude in decimal degrees. Use with lat; omit if using location.
        location: City or place name to geocode instead of lat/lon.
        tz: IANA timezone name (e.g. 'America/New_York'). Defaults to UTC.
        mode: Zodiac mode — 'realsky', 'tropical', or 'vedic'.
        houses: House system — 'porphyry', 'placidus', 'equal', or 'arc13'.
        details: Include minor bodies (Chiron, nodes, lots, etc.).
        aspects: Include aspect table.
        cusps: Include house cusp table.
    """
    lat, lon = _resolve_coords(lat, lon, location)
    ci = ChartInput(name="", date=date, time=time, tz=tz, lat=lat, lon=lon)
    chart = Chart.from_input(ci, house_system=HouseSystem(houses))
    return ChartOutput.build(
        ci,
        chart,
        ZodiacMode(mode),
        details=details,
        aspects=aspects,
        show_cusps=cusps,
    ).model_dump()


@mcp.tool()
def compute_transits(
    natal_date: str,
    natal_time: str | None = None,
    natal_lat: float | None = None,
    natal_lon: float | None = None,
    natal_location: str | None = None,
    natal_tz: str = "UTC",
    transit_date: str | None = None,
    transit_time: str | None = None,
    transit_tz: str = "UTC",
    mode: str = "realsky",
    houses: str = "porphyry",
    details: bool = True,
    aspects: bool = True,
    show_natal: bool = False,
) -> dict:
    """Compute current (or specified) transits against a natal chart.

    Shows transiting planetary positions and their aspects to natal placements.
    Defaults to now if no transit date/time is given.

    Args:
        natal_date: Natal birth date in YYYY-MM-DD.
        natal_time: Natal birth time in HH:MM (24-hour). Omit if unknown.
        natal_lat: Natal latitude in decimal degrees.
        natal_lon: Natal longitude in decimal degrees.
        natal_location: Natal birth city/place name to geocode.
        natal_tz: IANA timezone for natal chart. Defaults to UTC.
        transit_date: Date for transits in YYYY-MM-DD. Defaults to today.
        transit_time: Time for transits in HH:MM. Defaults to now.
        transit_tz: IANA timezone for transit time. Defaults to UTC.
        mode: Zodiac mode — 'realsky', 'tropical', or 'vedic'.
        houses: House system — 'porphyry', 'placidus', 'equal', or 'arc13'.
        details: Include minor bodies.
        aspects: Include transit-to-natal aspects.
        show_natal: Include natal planets alongside transiting planets.
    """
    lat, lon = _resolve_coords(natal_lat, natal_lon, natal_location)
    ci = ChartInput(
        name="", date=natal_date, time=natal_time, tz=natal_tz, lat=lat, lon=lon
    )
    chart_natal = Chart.from_input(ci, house_system=HouseSystem(houses))

    now = datetime.now().astimezone()
    if transit_date is None:
        transit_dt = now
    else:
        t = transit_time if transit_time is not None else now.strftime("%H:%M")
        local = datetime.fromisoformat(f"{transit_date}T{t}")
        transit_dt = local.replace(tzinfo=ZoneInfo(transit_tz))

    return TransitsOutput.build(
        ci,
        chart_natal,
        transit_dt,
        ZodiacMode(mode),
        details=details,
        aspects=aspects,
        natal=show_natal,
    ).model_dump()


@mcp.tool()
def compare_charts(
    date_a: str,
    date_b: str,
    time_a: str | None = None,
    time_b: str | None = None,
    lat_a: float | None = None,
    lon_a: float | None = None,
    location_a: str | None = None,
    tz_a: str = "UTC",
    lat_b: float | None = None,
    lon_b: float | None = None,
    location_b: str | None = None,
    tz_b: str = "UTC",
    mode: str = "realsky",
    houses: str = "porphyry",
    details: bool = True,
    aspects: bool = True,
) -> dict:
    """Compare two natal charts (synastry).

    Computes inter-aspects between two people's planetary placements.

    Args:
        date_a: First person's birth date in YYYY-MM-DD.
        date_b: Second person's birth date in YYYY-MM-DD.
        time_a: First person's birth time in HH:MM. Omit if unknown.
        time_b: Second person's birth time in HH:MM. Omit if unknown.
        lat_a: First person's natal latitude in decimal degrees.
        lon_a: First person's natal longitude in decimal degrees.
        location_a: First person's birth city/place name to geocode.
        tz_a: First person's IANA timezone.
        lat_b: Second person's natal latitude in decimal degrees.
        lon_b: Second person's natal longitude in decimal degrees.
        location_b: Second person's birth city/place name to geocode.
        tz_b: Second person's IANA timezone.
        mode: Zodiac mode — 'realsky', 'tropical', or 'vedic'.
        houses: House system — 'porphyry', 'placidus', 'equal', or 'arc13'.
        details: Include minor bodies.
        aspects: Include synastry aspects.
    """
    lat_a, lon_a = _resolve_coords(lat_a, lon_a, location_a)
    lat_b, lon_b = _resolve_coords(lat_b, lon_b, location_b)
    ci_a = ChartInput(name="", date=date_a, time=time_a, tz=tz_a, lat=lat_a, lon=lon_a)
    ci_b = ChartInput(name="", date=date_b, time=time_b, tz=tz_b, lat=lat_b, lon=lon_b)
    chart_a = Chart.from_input(ci_a, house_system=HouseSystem(houses))
    chart_b = Chart.from_input(ci_b, house_system=HouseSystem(houses))
    return CompareOutput.build(
        ci_a,
        ci_b,
        chart_a,
        chart_b,
        ZodiacMode(mode),
        details=details,
        aspects=aspects,
    ).model_dump()


@mcp.tool()
def compute_cusps(
    date: str,
    time: str,
    lat: float,
    lon: float,
    tz: str = "UTC",
    mode: str = "realsky",
    houses: str = "porphyry",
) -> dict:
    """Compute house cusps for a chart.

    Requires an exact birth time and location — angles are undefined without both.

    Args:
        date: Birth date in YYYY-MM-DD.
        time: Birth time in HH:MM (24-hour). Required.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        tz: IANA timezone name.
        mode: Zodiac mode — 'realsky', 'tropical', or 'vedic'.
        houses: House system — 'porphyry', 'placidus', 'equal', or 'arc13'.
    """
    ci = ChartInput(name="", date=date, time=time, tz=tz, lat=lat, lon=lon)
    chart = Chart.from_input(ci, house_system=HouseSystem(houses))
    return CuspsOutput.build(chart, ZodiacMode(mode)).model_dump()


@mcp.tool()
def import_chart(
    source: str,
    mode: str = "realsky",
    houses: str = "porphyry",
    details: bool = True,
    aspects: bool = True,
) -> dict:
    """Import and compute a chart for a person from Astro-Databank.

    Fetches birth data from the ADB MediaWiki API by person name and computes
    the chart. Use this when the user provides a celebrity or historical name
    rather than raw birth data.

    Args:
        source: Person's name as it appears in Astro-Databank (e.g. 'Albert Einstein').
        mode: Zodiac mode — 'realsky', 'tropical', or 'vedic'.
        houses: House system — 'porphyry', 'placidus', 'equal', or 'arc13'.
        details: Include minor bodies.
        aspects: Include aspect table.
    """
    from hoshi.adb import adb_to_chart_input

    result = adb_to_chart_input(source, None)
    ci = result.chart_input
    chart = Chart.from_input(ci, house_system=HouseSystem(houses))
    return ChartOutput.build(
        ci,
        chart,
        ZodiacMode(mode),
        details=details,
        aspects=aspects,
        show_cusps=False,
    ).model_dump()
