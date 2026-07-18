"""Strawberry output types and Pydantic → Strawberry conversion helpers."""

from typing import Optional

import strawberry

from hoshi import output as _pydantic
from hoshi.chart import HouseSystem as _HouseSystem
from hoshi.zodiac import ZodiacMode as _ZodiacMode

# Wrap existing StrEnums so Strawberry registers them as GraphQL enum types.
# strawberry.enum() decorates the class in place and returns the same object,
# so ZodiacMode/HouseSystem here are identical to the originals in hoshi.
ZodiacMode = strawberry.enum(_ZodiacMode)
HouseSystem = strawberry.enum(_HouseSystem)


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@strawberry.input
class ChartDataInput:
    date: str
    tz: str = "UTC"
    time: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------


@strawberry.type
class BodyEntry:
    kind: str
    name: str
    sign: str
    sign_symbol: str
    degree: float
    lon: float
    house: Optional[int]
    rx: bool
    approximate: bool
    dignity: str
    symbol: str


@strawberry.type
class Aspect:
    body_a: str
    sign_a: str
    body_b: str
    sign_b: str
    name: str
    symbol: str
    angle: float
    orb: float
    kind: str


@strawberry.type
class TallyRow:
    primary: int
    total: int


@strawberry.type
class ElementTally:
    fire: TallyRow
    earth: TallyRow
    air: TallyRow
    water: TallyRow


@strawberry.type
class ModalityTally:
    cardinal: TallyRow
    fixed: TallyRow
    mutable: TallyRow


@strawberry.type
class TallyOutput:
    elements: ElementTally
    modalities: ModalityTally


@strawberry.type
class ChartHeader:
    name: str
    when: str
    lat: Optional[float]
    lon: Optional[float]
    mode: str
    house_system: Optional[str]


@strawberry.type
class ChartResult:
    chart: ChartHeader
    warnings: list[str]
    bodies: list[BodyEntry]
    cusps: list[float]
    tallies: Optional[TallyOutput]
    aspects: Optional[list[Aspect]]


@strawberry.type
class CuspEntry:
    house: int
    sign: str
    degree: float
    lon: float


@strawberry.type
class CuspsResult:
    house_system: str
    cusps: list[CuspEntry]


@strawberry.type
class TransitHeader:
    name: str
    natal_date: str
    transit_when: str
    mode: str
    house_system: Optional[str]


@strawberry.type
class TransitsResult:
    header: TransitHeader
    warnings: list[str]
    transit_bodies: list[BodyEntry]
    natal_bodies: Optional[list[BodyEntry]]
    aspects: Optional[list[Aspect]]


@strawberry.type
class CompareHeader:
    name_a: str
    name_b: str
    date_a: str
    date_b: str
    mode: str


@strawberry.type
class CompareResult:
    header: CompareHeader
    warnings: list[str]
    bodies_a: list[BodyEntry]
    bodies_b: list[BodyEntry]
    aspects: Optional[list[Aspect]]


@strawberry.type
class SkyEventEntry:
    when: str
    event_type: str
    body: str
    body_symbol: str
    detail: str
    sign: Optional[str]
    sign_symbol: Optional[str]
    body_b: Optional[str]
    aspect_name: Optional[str]
    aspect_symbol: Optional[str]


@strawberry.type
class SkyEventsResult:
    events: list[SkyEventEntry]
    mode: str
    from_date: str
    to_date: str


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _body_entry(b: dict) -> BodyEntry:
    return BodyEntry(**b)


def _aspect(a: dict) -> Aspect:
    return Aspect(**a)


def _tally(data: dict) -> TallyOutput:
    elems = data["elements"]
    mods = data["modalities"]
    return TallyOutput(
        elements=ElementTally(
            fire=TallyRow(**elems["Fire"]),
            earth=TallyRow(**elems["Earth"]),
            air=TallyRow(**elems["Air"]),
            water=TallyRow(**elems["Water"]),
        ),
        modalities=ModalityTally(
            cardinal=TallyRow(**mods["Cardinal"]),
            fixed=TallyRow(**mods["Fixed"]),
            mutable=TallyRow(**mods["Mutable"]),
        ),
    )


def from_chart_output(output: _pydantic.ChartOutput) -> ChartResult:
    data = output.model_dump(mode="json")
    return ChartResult(
        chart=ChartHeader(**data["chart"]),
        warnings=data["warnings"],
        bodies=[_body_entry(b) for b in data["bodies"]],
        cusps=data["cusps"],
        tallies=_tally(data["tallies"]) if data["tallies"] else None,
        aspects=(
            [_aspect(a) for a in data["aspects"]]
            if data["aspects"] is not None
            else None
        ),
    )


def from_cusps_output(output: _pydantic.CuspsOutput) -> CuspsResult:
    data = output.model_dump(mode="json")
    return CuspsResult(
        house_system=data["house_system"],
        cusps=[CuspEntry(**c) for c in data["cusps"]],
    )


def from_transits_output(output: _pydantic.TransitsOutput) -> TransitsResult:
    data = output.model_dump(mode="json")
    return TransitsResult(
        header=TransitHeader(**data["header"]),
        warnings=data["warnings"],
        transit_bodies=[_body_entry(b) for b in data["transit_bodies"]],
        natal_bodies=(
            [_body_entry(b) for b in data["natal_bodies"]]
            if data["natal_bodies"] is not None
            else None
        ),
        aspects=(
            [_aspect(a) for a in data["aspects"]]
            if data["aspects"] is not None
            else None
        ),
    )


def from_compare_output(output: _pydantic.CompareOutput) -> CompareResult:
    data = output.model_dump(mode="json")
    return CompareResult(
        header=CompareHeader(**data["header"]),
        warnings=data["warnings"],
        bodies_a=[_body_entry(b) for b in data["bodies_a"]],
        bodies_b=[_body_entry(b) for b in data["bodies_b"]],
        aspects=(
            [_aspect(a) for a in data["aspects"]]
            if data["aspects"] is not None
            else None
        ),
    )


def from_sky_events_output(output: _pydantic.SkyEventsOutput) -> SkyEventsResult:
    data = output.model_dump(mode="json")
    return SkyEventsResult(
        events=[SkyEventEntry(**e) for e in data["events"]],
        mode=data["mode"],
        from_date=data["from_date"],
        to_date=data["to_date"],
    )
