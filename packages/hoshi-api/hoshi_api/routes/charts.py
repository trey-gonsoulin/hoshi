"""Chart endpoints."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

from hoshi import store
from hoshi.chart import Chart, HouseSystem
from hoshi.output import (
    ChartListOutput,
    ChartOutput,
    CompareOutput,
    CuspsOutput,
    DeleteOutput,
    HouseComparisonOutput,
    TransitsOutput,
)
from hoshi.store import ChartInput
from hoshi.zodiac import ZodiacMode

router = APIRouter(prefix="/charts", tags=["charts"])


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class ChartCreate(BaseModel):
    name: str
    date: str
    time: str | None = None
    lat: float | None = None
    lon: float | None = None
    location: str | None = None
    tz: str = "UTC"
    force: bool = False
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False
    cusps: bool = False


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
    name: str | None = None
    force: bool = False
    mode: ZodiacMode = ZodiacMode.realsky
    houses: HouseSystem = HouseSystem.porphyry
    details: bool = False
    aspects: bool = False
    cusps: bool = False


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
# Routes — static paths first, then parameterized
# ---------------------------------------------------------------------------


@router.get("", response_model=ChartListOutput)
def list_charts() -> ChartListOutput:
    return ChartListOutput.build()


@router.post("", response_model=ChartOutput, status_code=201)
def create_chart(body: ChartCreate) -> ChartOutput:
    lat, lon = _resolve_coords(body.lat, body.lon, body.location)
    ci = ChartInput(
        name=body.name,
        date=body.date,
        time=body.time,
        tz=body.tz,
        lat=lat,
        lon=lon,
    )
    store.save(ci, overwrite=body.force)
    return _build_chart_response(
        ci,
        body.mode,
        body.houses,
        details=body.details,
        aspects=body.aspects,
        cusps=body.cusps,
    )


@router.post("/compute", response_model=ChartOutput)
def compute_chart(body: ChartCompute) -> ChartOutput:
    lat, lon = _resolve_coords(body.lat, body.lon, body.location)
    ci = ChartInput(
        name="",
        date=body.date,
        time=body.time,
        tz=body.tz,
        lat=lat,
        lon=lon,
    )
    return _build_chart_response(
        ci,
        body.mode,
        body.houses,
        details=body.details,
        aspects=body.aspects,
        cusps=body.cusps,
    )


@router.post("/import", response_model=ChartOutput, status_code=201)
def import_chart(body: ChartImportRequest) -> ChartOutput:
    from hoshi.adb import adb_to_chart_input

    result = adb_to_chart_input(body.source, body.name)
    ci = result.chart_input
    store.save(ci, overwrite=body.force)
    return _build_chart_response(
        ci,
        body.mode,
        body.houses,
        details=body.details,
        aspects=body.aspects,
        cusps=body.cusps,
    )


@router.get("/{name}", response_model=ChartOutput)
def show_chart(
    name: str,
    mode: ZodiacMode = ZodiacMode.realsky,
    houses: HouseSystem = HouseSystem.porphyry,
    details: bool = False,
    aspects: bool = False,
    cusps: bool = False,
    compare_houses: bool = False,
) -> ChartOutput | HouseComparisonOutput:
    ci = store.load(name)
    if compare_houses:
        if not ci.time_known or not ci.location_known:
            raise ValueError(
                "compare_houses requires a chart with known birth time and location."
            )
        return HouseComparisonOutput.build(ci, mode, details=details)
    return _build_chart_response(
        ci, mode, houses, details=details, aspects=aspects, cusps=cusps
    )


@router.delete("/{name}", response_model=DeleteOutput)
def delete_chart(name: str) -> DeleteOutput:
    path = store.delete(name)
    return DeleteOutput(path=str(path))


@router.get("/{name}/cusps", response_model=CuspsOutput)
def chart_cusps(
    name: str,
    mode: ZodiacMode = ZodiacMode.realsky,
    houses: HouseSystem = HouseSystem.porphyry,
) -> CuspsOutput:
    ci = store.load(name)
    if not ci.time_known:
        raise ValueError(
            f"Chart {ci.name!r} has no birth time — house cusps cannot be computed."
        )
    if not ci.location_known:
        raise ValueError(
            f"Chart {ci.name!r} has no birth location — house cusps cannot be computed."
        )
    chart = Chart.from_input(ci, house_system=houses)
    return CuspsOutput.build(chart, mode)


@router.get("/{name}/transits", response_model=TransitsOutput)
def chart_transits(
    name: str,
    date: str | None = None,
    time: str | None = None,
    tz: str = "UTC",
    mode: ZodiacMode = ZodiacMode.realsky,
    houses: HouseSystem = HouseSystem.porphyry,
    details: bool = False,
    aspects: bool = False,
    natal: bool = False,
) -> TransitsOutput:
    ci = store.load(name)
    now = datetime.now().astimezone()
    if date is None:
        transit_dt = now
    else:
        t = time if time is not None else now.strftime("%H:%M")
        local = datetime.fromisoformat(f"{date}T{t}")
        transit_dt = local.replace(tzinfo=ZoneInfo(tz))

    chart_natal = Chart.from_input(ci, house_system=houses)
    return TransitsOutput.build(
        ci,
        chart_natal,
        transit_dt,
        mode,
        details=details,
        aspects=aspects,
        natal=natal,
    )


@router.get("/{name}/compare/{other}", response_model=CompareOutput)
def chart_compare(
    name: str,
    other: str,
    mode: ZodiacMode = ZodiacMode.realsky,
    houses: HouseSystem = HouseSystem.porphyry,
    details: bool = False,
    aspects: bool = False,
) -> CompareOutput:
    ci_a = store.load(name)
    ci_b = store.load(other)
    chart_a = Chart.from_input(ci_a, house_system=houses)
    chart_b = Chart.from_input(ci_b, house_system=houses)
    return CompareOutput.build(
        ci_a,
        ci_b,
        chart_a,
        chart_b,
        mode,
        details=details,
        aspects=aspects,
    )
