"""Sky endpoints — current placements and event timeline."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from hoshi.chart import Chart
from hoshi.events import sky_events
from hoshi.output import ChartOutput, SkyEventsOutput
from hoshi.store import ChartInput
from hoshi.zodiac import ZodiacMode

router = APIRouter(prefix="/sky", tags=["sky"])


@router.get("/now", response_model=ChartOutput)
def sky_now(
    mode: ZodiacMode = Query(ZodiacMode.realsky),
    tz: str = Query("UTC"),
) -> ChartOutput:
    """Current transiting sky — all bodies, no natal chart required."""
    try:
        now = datetime.now(ZoneInfo(tz))
    except Exception:
        now = datetime.now(timezone.utc)

    ci = ChartInput(
        name="", date=now.date().isoformat(), time=now.strftime("%H:%M"), tz=tz
    )
    chart = Chart.positions_only(now.astimezone(timezone.utc))
    return ChartOutput.build(ci, chart, mode, details=True, aspects=True)


@router.get("/events", response_model=SkyEventsOutput)
def sky_events_route(
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    mode: ZodiacMode = Query(ZodiacMode.realsky),
    tz: str = Query("UTC"),
    stations: bool = Query(True),
    ingresses: bool = Query(True),
    phases: bool = Query(True),
    voc: bool = Query(True),
    aspects: bool = Query(True),
) -> SkyEventsOutput:
    """Sky events in a date range (stations, ingresses, moon phases, VoC, exact aspects).

    Defaults to today in the given timezone when *from* and *to* are omitted.
    """
    try:
        local_tz = ZoneInfo(tz)
    except Exception:
        local_tz = timezone.utc

    now = datetime.now(local_tz)
    today = now.date()

    if from_date:
        start = datetime.fromisoformat(from_date).replace(tzinfo=local_tz)
    else:
        start = datetime.combine(today, datetime.min.time()).replace(tzinfo=local_tz)

    if to_date:
        end = datetime.fromisoformat(to_date).replace(tzinfo=local_tz)
        # Extend to end-of-day
        end = end.replace(hour=23, minute=59, second=59)
    else:
        end = datetime.combine(today, datetime.max.time()).replace(tzinfo=local_tz)

    events = sky_events(
        start,
        end,
        mode,
        include_stations=stations,
        include_ingresses=ingresses,
        include_moon_phases=phases,
        include_voc=voc,
        include_aspects=aspects,
    )

    return SkyEventsOutput.build(
        events,
        mode=str(mode),
        from_date=start.date().isoformat(),
        to_date=end.date().isoformat(),
    )
