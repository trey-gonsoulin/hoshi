"""GraphQL schema — Query type with resolvers.

Resolvers are synchronous (matching the REST routes), so sibling fields in a
batched query execute sequentially rather than in parallel.  The primary win
is eliminating N cold starts and N HTTP round trips for the UI — each batched
query is one Lambda invocation and one network request.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import strawberry
from strawberry.fastapi import GraphQLRouter

from hoshi.chart import Chart, HouseSystem
from hoshi.output import (
    ChartOutput,
    CompareOutput,
    CompositeOutput,
    CuspsOutput,
    CyclesOutput,
    SkyEventsOutput,
    TransitsOutput,
)
from hoshi.store import ChartInput
from hoshi.zodiac import ZodiacMode

from hoshi_api.routes.charts import _resolve_coords

from hoshi_api.graphql.types import (
    BirthRangeResult,
    BirthWindowInput,
    ChartDataInput,
    ChartResult,
    CompareResult,
    CompositeResult,
    ConstraintInput,
    CuspsResult,
    CyclesResult,
    ForecastResult,
    SkyEventsResult,
    TransitsResult,
    from_birth_range_output,
    from_chart_output,
    from_compare_output,
    from_composite_output,
    from_cusps_output,
    from_cycles_output,
    from_forecast_output,
    from_sky_events_output,
    from_transits_output,
)


@strawberry.type
class Query:
    @strawberry.field
    def chart(
        self,
        date: str,
        tz: str = "UTC",
        time: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        location: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
        birth_windows: Optional[list[BirthWindowInput]] = None,
    ) -> ChartResult:
        from hoshi.store import BirthWindow as _BirthWindow

        resolved_lat, resolved_lon = _resolve_coords(lat, lon, location)
        bws = None
        if birth_windows:
            bws = [
                _BirthWindow(
                    start=datetime.fromisoformat(w.start).replace(tzinfo=timezone.utc)
                    if datetime.fromisoformat(w.start).tzinfo is None
                    else datetime.fromisoformat(w.start),
                    end=datetime.fromisoformat(w.end).replace(tzinfo=timezone.utc)
                    if datetime.fromisoformat(w.end).tzinfo is None
                    else datetime.fromisoformat(w.end),
                )
                for w in birth_windows
            ]
        ci = ChartInput(
            name="",
            date=date,
            time=time,
            tz=tz,
            lat=resolved_lat,
            lon=resolved_lon,
            birth_windows=bws,
        )
        chart = Chart.from_input(ci, house_system=houses)
        output = ChartOutput.build(ci, chart, mode, details=details, aspects=aspects)
        return from_chart_output(output)

    @strawberry.field
    def birth_range(
        self,
        constraints: list[ConstraintInput],
        from_date: str,
        to_date: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> BirthRangeResult:
        from hoshi.birthrange import Constraint as _Constraint
        from hoshi.birthrange import _step_hours, find_birth_date_ranges
        from hoshi.output import BirthRangeOutput

        parsed = [_Constraint(planet=c.planet, sign=c.sign) for c in constraints]
        search_start = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
        if to_date:
            search_end = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc)
        else:
            search_end = datetime.now(timezone.utc).replace(
                hour=23, minute=59, second=59, microsecond=0
            )
        windows = find_birth_date_ranges(
            parsed, search_start, search_end, mode, lat=lat, lon=lon
        )
        step_h = _step_hours([c.planet for c in parsed], mode)
        output = BirthRangeOutput.build(
            parsed, str(mode), search_start, search_end, step_h, windows
        )
        return from_birth_range_output(output)

    @strawberry.field
    def import_chart(
        self,
        source: str,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
    ) -> ChartResult:
        from hoshi.adb import adb_to_chart_input

        result = adb_to_chart_input(source, None)
        ci = result.chart_input
        chart = Chart.from_input(ci, house_system=houses)
        output = ChartOutput.build(ci, chart, mode, details=details, aspects=aspects)
        return from_chart_output(output)

    @strawberry.field
    def cusps(
        self,
        date: str,
        time: str,
        lat: float,
        lon: float,
        tz: str = "UTC",
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
    ) -> CuspsResult:
        ci = ChartInput(name="", date=date, time=time, tz=tz, lat=lat, lon=lon)
        chart = Chart.from_input(ci, house_system=houses)
        output = CuspsOutput.build(chart, mode)
        return from_cusps_output(output)

    @strawberry.field
    def transits(
        self,
        natal: ChartDataInput,
        tz: str = "UTC",
        date: Optional[str] = None,
        time: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
        show_natal: bool = False,
    ) -> TransitsResult:
        resolved_lat, resolved_lon = _resolve_coords(
            natal.lat, natal.lon, natal.location
        )
        ci = ChartInput(
            name="",
            date=natal.date,
            time=natal.time,
            tz=natal.tz,
            lat=resolved_lat,
            lon=resolved_lon,
        )
        now = datetime.now().astimezone()
        if date is None:
            transit_dt = now
        else:
            t = time if time is not None else now.strftime("%H:%M")
            local = datetime.fromisoformat(f"{date}T{t}")
            transit_dt = local.replace(tzinfo=ZoneInfo(tz))

        chart_natal = Chart.from_input(ci, house_system=houses)
        output = TransitsOutput.build(
            ci,
            chart_natal,
            transit_dt,
            mode,
            details=details,
            aspects=aspects,
            natal=show_natal,
        )
        return from_transits_output(output)

    @strawberry.field
    def compare(
        self,
        chart_a: ChartDataInput,
        chart_b: ChartDataInput,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
    ) -> CompareResult:
        lat_a, lon_a = _resolve_coords(chart_a.lat, chart_a.lon, chart_a.location)
        lat_b, lon_b = _resolve_coords(chart_b.lat, chart_b.lon, chart_b.location)
        ci_a = ChartInput(
            name="",
            date=chart_a.date,
            time=chart_a.time,
            tz=chart_a.tz,
            lat=lat_a,
            lon=lon_a,
        )
        ci_b = ChartInput(
            name="",
            date=chart_b.date,
            time=chart_b.time,
            tz=chart_b.tz,
            lat=lat_b,
            lon=lon_b,
        )
        a = Chart.from_input(ci_a, house_system=houses)
        b = Chart.from_input(ci_b, house_system=houses)
        output = CompareOutput.build(
            ci_a, ci_b, a, b, mode, details=details, aspects=aspects
        )
        return from_compare_output(output)

    @strawberry.field
    def composite(
        self,
        chart_a: ChartDataInput,
        chart_b: ChartDataInput,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
    ) -> CompositeResult:
        lat_a, lon_a = _resolve_coords(chart_a.lat, chart_a.lon, chart_a.location)
        lat_b, lon_b = _resolve_coords(chart_b.lat, chart_b.lon, chart_b.location)
        ci_a = ChartInput(
            name="",
            date=chart_a.date,
            time=chart_a.time,
            tz=chart_a.tz,
            lat=lat_a,
            lon=lon_a,
        )
        ci_b = ChartInput(
            name="",
            date=chart_b.date,
            time=chart_b.time,
            tz=chart_b.tz,
            lat=lat_b,
            lon=lon_b,
        )
        a = Chart.from_input(ci_a, house_system=houses)
        b = Chart.from_input(ci_b, house_system=houses)
        chart_comp = Chart.composite(a, b, house_system=houses)
        output = CompositeOutput.build(
            ci_a, ci_b, chart_comp, mode, details=details, aspects=aspects
        )
        return from_composite_output(output)

    @strawberry.field
    def composite_transits(
        self,
        chart_a: ChartDataInput,
        chart_b: ChartDataInput,
        tz: str = "UTC",
        date: Optional[str] = None,
        time: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        details: bool = False,
        aspects: bool = False,
        show_natal: bool = False,
        tier: str = "all",
        sensitivity: str = "",
    ) -> TransitsResult:
        lat_a, lon_a = _resolve_coords(chart_a.lat, chart_a.lon, chart_a.location)
        lat_b, lon_b = _resolve_coords(chart_b.lat, chart_b.lon, chart_b.location)
        ci_a = ChartInput(
            name="",
            date=chart_a.date,
            time=chart_a.time,
            tz=chart_a.tz,
            lat=lat_a,
            lon=lon_a,
        )
        ci_b = ChartInput(
            name="",
            date=chart_b.date,
            time=chart_b.time,
            tz=chart_b.tz,
            lat=lat_b,
            lon=lon_b,
        )
        a = Chart.from_input(ci_a, house_system=houses)
        b = Chart.from_input(ci_b, house_system=houses)
        chart_comp = Chart.composite(a, b, house_system=houses)
        ci_comp = ChartInput(
            name=f"{ci_a.date} × {ci_b.date}",
            date=ci_a.date,
            time=ci_a.time if chart_comp.time_known else None,
            lat=chart_comp.lat if chart_comp.location_known else None,
            lon=chart_comp.lon if chart_comp.location_known else None,
        )
        now = datetime.now().astimezone()
        if date is None:
            transit_dt = now
        else:
            t = time if time is not None else now.strftime("%H:%M")
            local = datetime.fromisoformat(f"{date}T{t}")
            transit_dt = local.replace(tzinfo=ZoneInfo(tz))
        output = TransitsOutput.build(
            ci_comp,
            chart_comp,
            transit_dt,
            mode,
            details=details,
            aspects=aspects,
            natal=show_natal,
            tier=tier,
            sensitivity=sensitivity,
        )
        return from_transits_output(output)

    @strawberry.field
    def composite_forecast(
        self,
        chart_a: ChartDataInput,
        chart_b: ChartDataInput,
        tz: str = "UTC",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
        tier: str = "slow",
        details: bool = False,
        sensitivity: str = "",
    ) -> ForecastResult:
        from datetime import timedelta

        from hoshi.output import ForecastOutput

        lat_a, lon_a = _resolve_coords(chart_a.lat, chart_a.lon, chart_a.location)
        lat_b, lon_b = _resolve_coords(chart_b.lat, chart_b.lon, chart_b.location)
        ci_a = ChartInput(
            name="",
            date=chart_a.date,
            time=chart_a.time,
            tz=chart_a.tz,
            lat=lat_a,
            lon=lon_a,
        )
        ci_b = ChartInput(
            name="",
            date=chart_b.date,
            time=chart_b.time,
            tz=chart_b.tz,
            lat=lat_b,
            lon=lon_b,
        )
        a = Chart.from_input(ci_a, house_system=houses)
        b = Chart.from_input(ci_b, house_system=houses)
        chart_comp = Chart.composite(a, b, house_system=houses)
        ci_comp = ChartInput(
            name=f"{ci_a.date} × {ci_b.date}",
            date=ci_a.date,
            time=ci_a.time if chart_comp.time_known else None,
            lat=chart_comp.lat if chart_comp.location_known else None,
            lon=chart_comp.lon if chart_comp.location_known else None,
        )
        now = datetime.now().astimezone(ZoneInfo(tz))
        from_dt = (
            datetime.fromisoformat(from_date).replace(tzinfo=ZoneInfo(tz))
            if from_date is not None
            else now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        to_dt = (
            datetime.fromisoformat(to_date).replace(tzinfo=ZoneInfo(tz))
            if to_date is not None
            else from_dt + timedelta(days=90)
        )
        output = ForecastOutput.build(
            ci_comp,
            chart_comp,
            from_dt,
            to_dt,
            mode,
            tier=tier,
            details=details,
            sensitivity=sensitivity,
        )
        return from_forecast_output(output)

    @strawberry.field
    def cycles(
        self,
        natal: ChartDataInput,
        tz: str = "UTC",
        from_date: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        houses: HouseSystem = HouseSystem.porphyry,
    ) -> CyclesResult:
        resolved_lat, resolved_lon = _resolve_coords(
            natal.lat, natal.lon, natal.location
        )
        ci = ChartInput(
            name="",
            date=natal.date,
            time=natal.time,
            tz=natal.tz,
            lat=resolved_lat,
            lon=resolved_lon,
        )
        if from_date is not None:
            from_dt = datetime.fromisoformat(from_date).replace(tzinfo=ZoneInfo(tz))
        else:
            from_dt = datetime.now(timezone.utc)
        chart_natal = Chart.from_input(ci, house_system=houses)
        output = CyclesOutput.build(ci, chart_natal, from_dt, str(mode))
        return from_cycles_output(output)

    @strawberry.field
    def sky_now(
        self,
        mode: ZodiacMode = ZodiacMode.realsky,
        tz: str = "UTC",
    ) -> ChartResult:
        try:
            now = datetime.now(ZoneInfo(tz))
        except Exception:
            now = datetime.now(timezone.utc)
        ci = ChartInput(
            name="", date=now.date().isoformat(), time=now.strftime("%H:%M"), tz=tz
        )
        chart = Chart.positions_only(now.astimezone(timezone.utc))
        output = ChartOutput.build(ci, chart, mode, details=True, aspects=True)
        return from_chart_output(output)

    @strawberry.field
    def sky_events(
        self,
        tz: str = "UTC",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        mode: ZodiacMode = ZodiacMode.realsky,
        stations: bool = True,
        ingresses: bool = True,
        phases: bool = True,
        voc: bool = True,
        aspects: bool = True,
    ) -> SkyEventsResult:
        from hoshi.events import sky_events as _sky_events

        try:
            local_tz = ZoneInfo(tz)
        except Exception:
            local_tz = timezone.utc

        now = datetime.now(local_tz)
        today = now.date()

        if from_date:
            start = datetime.fromisoformat(from_date).replace(tzinfo=local_tz)
        else:
            start = datetime.combine(today, datetime.min.time()).replace(
                tzinfo=local_tz
            )

        if to_date:
            end = datetime.fromisoformat(to_date).replace(tzinfo=local_tz)
            end = end.replace(hour=23, minute=59, second=59)
        else:
            end = datetime.combine(today, datetime.max.time()).replace(tzinfo=local_tz)

        events = _sky_events(
            start,
            end,
            mode,
            include_stations=stations,
            include_ingresses=ingresses,
            include_moon_phases=phases,
            include_voc=voc,
            include_aspects=aspects,
        )
        output = SkyEventsOutput.build(
            events,
            mode=str(mode),
            from_date=start.date().isoformat(),
            to_date=end.date().isoformat(),
        )
        return from_sky_events_output(output)


schema = strawberry.Schema(query=Query)
router = GraphQLRouter(schema, graphql_ide="graphiql")
