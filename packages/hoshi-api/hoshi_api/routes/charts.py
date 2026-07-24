"""Chart endpoints."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from hoshi import ChartInput
from hoshi.chart import Chart, HouseSystem
from hoshi.output import (
    BirthRangeOutput,
    ChartOutput,
    CompareOutput,
    CuspsOutput,
    ForecastOutput,
    TransitsOutput,
)
from hoshi.zodiac import ZodiacMode

router = APIRouter(prefix="/charts", tags=["charts"])


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class ChartData(BaseModel):
    """Positional data for a single chart — used when embedding charts in
    multi-chart requests (transits, compare)."""

    date: str
    time: str | None = None
    lat: float | None = None
    lon: float | None = None
    location: str | None = None
    tz: str = "UTC"


class ChartCompute(BaseModel):
    date: str
    time: str | None = None
    lat: float | None = None
    lon: float | None = None
    location: str | None = None
    tz: str = "UTC"
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False
    cusps: bool = False


class ChartImportRequest(BaseModel):
    source: str
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False
    cusps: bool = False


class CuspsRequest(BaseModel):
    date: str
    time: str
    lat: float
    lon: float
    tz: str = "UTC"
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry


class TransitsRequest(BaseModel):
    natal: ChartData
    date: str | None = None
    time: str | None = None
    tz: str = "UTC"
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False
    show_natal: bool = False
    windows: bool = False
    tier: str = "all"
    sensitivity: str = ""


class ForecastRequest(BaseModel):
    natal: ChartData
    from_date: str | None = None
    to_date: str | None = None
    tz: str = "UTC"
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    tier: str = "slow"
    details: bool = False
    sensitivity: str = ""


class CompareRequest(BaseModel):
    chart_a: ChartData
    chart_b: ChartData
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False


class BirthRangeConstraint(BaseModel):
    planet: str
    sign: str


class BirthRangeRequest(BaseModel):
    constraints: list[BirthRangeConstraint]
    from_date: str = "1900-01-01"
    to_date: str | None = None
    lat: float | None = None
    lon: float | None = None
    mode: ZodiacMode = ZodiacMode.realsky


# ---------------------------------------------------------------------------
# Helpers
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
        raise ValueError("Cannot use location together with lat/lon.")
    if location is not None:
        return _geocode(location)
    if (lat is None) != (lon is None):
        raise ValueError("lat and lon must both be provided or both omitted.")
    return lat, lon


def _chart_input_from(data: ChartData, name: str = "") -> ChartInput:
    lat, lon = _resolve_coords(data.lat, data.lon, data.location)
    return ChartInput(
        name=name, date=data.date, time=data.time, tz=data.tz, lat=lat, lon=lon
    )


def _build_chart_response(
    ci: ChartInput,
    mode: ZodiacMode,
    houses: HouseSystem,
    *,
    details: bool,
    aspects: bool,
    cusps: bool,
) -> ChartOutput:
    chart = Chart.from_input(ci, house_system=houses)
    return ChartOutput.build(
        ci,
        chart,
        mode,
        details=details,
        aspects=aspects,
        show_cusps=cusps,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/compute", response_model=ChartOutput)
def compute_chart(body: ChartCompute) -> ChartOutput:
    lat, lon = _resolve_coords(body.lat, body.lon, body.location)
    ci = ChartInput(
        name="", date=body.date, time=body.time, tz=body.tz, lat=lat, lon=lon
    )
    return _build_chart_response(
        ci,
        body.mode,
        body.houses,
        details=body.details,
        aspects=body.aspects,
        cusps=body.cusps,
    )


@router.post("/import", response_model=ChartOutput)
def import_chart(body: ChartImportRequest) -> ChartOutput:
    from hoshi.adb import adb_to_chart_input

    result = adb_to_chart_input(body.source, None)
    ci = result.chart_input
    return _build_chart_response(
        ci,
        body.mode,
        body.houses,
        details=body.details,
        aspects=body.aspects,
        cusps=body.cusps,
    )


@router.post("/cusps", response_model=CuspsOutput)
def chart_cusps(body: CuspsRequest) -> CuspsOutput:
    ci = ChartInput(
        name="", date=body.date, time=body.time, tz=body.tz, lat=body.lat, lon=body.lon
    )
    chart = Chart.from_input(ci, house_system=body.houses)
    return CuspsOutput.build(chart, body.mode)


@router.post("/transits", response_model=TransitsOutput)
def chart_transits(body: TransitsRequest) -> TransitsOutput:
    ci = _chart_input_from(body.natal)
    now = datetime.now().astimezone()
    if body.date is None:
        transit_dt = now
    else:
        t = body.time if body.time is not None else now.strftime("%H:%M")
        local = datetime.fromisoformat(f"{body.date}T{t}")
        transit_dt = local.replace(tzinfo=ZoneInfo(body.tz))

    chart_natal = Chart.from_input(ci, house_system=body.houses)
    return TransitsOutput.build(
        ci,
        chart_natal,
        transit_dt,
        body.mode,
        details=body.details,
        aspects=body.aspects,
        natal=body.show_natal,
        windows=body.windows,
        tier=body.tier,
        sensitivity=body.sensitivity,
    )


@router.post("/forecast", response_model=ForecastOutput)
def chart_forecast(body: ForecastRequest) -> ForecastOutput:
    ci = _chart_input_from(body.natal)
    now = datetime.now().astimezone(ZoneInfo(body.tz))
    from_dt = (
        datetime.fromisoformat(body.from_date).replace(tzinfo=ZoneInfo(body.tz))
        if body.from_date is not None
        else now.replace(hour=0, minute=0, second=0, microsecond=0)
    )
    to_dt = (
        datetime.fromisoformat(body.to_date).replace(tzinfo=ZoneInfo(body.tz))
        if body.to_date is not None
        else from_dt + timedelta(days=90)
    )
    chart_natal = Chart.from_input(ci, house_system=body.houses)
    return ForecastOutput.build(
        ci,
        chart_natal,
        from_dt,
        to_dt,
        body.mode,
        tier=body.tier,
        details=body.details,
        sensitivity=body.sensitivity,
    )


@router.post("/birthrange", response_model=BirthRangeOutput)
def chart_birthrange(body: BirthRangeRequest) -> BirthRangeOutput:
    from hoshi.birthrange import Constraint, _step_hours, find_birth_date_ranges

    parsed = [Constraint(planet=c.planet, sign=c.sign) for c in body.constraints]
    search_start = datetime.fromisoformat(body.from_date).replace(tzinfo=timezone.utc)
    if body.to_date is not None:
        search_end = datetime.fromisoformat(body.to_date).replace(tzinfo=timezone.utc)
    else:
        search_end = datetime.now(timezone.utc).replace(
            hour=23, minute=59, second=59, microsecond=0
        )
    try:
        step_h = _step_hours([c.planet for c in parsed], body.mode)
        windows = find_birth_date_ranges(
            parsed, search_start, search_end, body.mode, lat=body.lat, lon=body.lon
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return BirthRangeOutput.build(
        parsed, str(body.mode), search_start, search_end, step_h, windows
    )


@router.post("/compare", response_model=CompareOutput)
def chart_compare(body: CompareRequest) -> CompareOutput:
    ci_a = _chart_input_from(body.chart_a)
    ci_b = _chart_input_from(body.chart_b)
    chart_a = Chart.from_input(ci_a, house_system=body.houses)
    chart_b = Chart.from_input(ci_b, house_system=body.houses)
    return CompareOutput.build(
        ci_a,
        ci_b,
        chart_a,
        chart_b,
        body.mode,
        details=body.details,
        aspects=body.aspects,
    )
