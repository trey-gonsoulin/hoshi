"""Build a complete chart: positions placed in all three zodiac modes,
plus angles, Placidus cusps, and house numbers."""

from collections.abc import Callable, Iterator
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from hoshi.ephemeris import (
    PLANET_ORDER,
    PlanetPosition,
    ecliptic_precession,
    lahiri_ayanamsa,
    positions,
)
from hoshi.houses import (
    Angles,
    arc13_cusps,
    equal_cusps,
    house_13_arc,
    house_from_cusps,
    placidus_cusps,
    porphyry_cusps,
)
from hoshi.points import HERMETIC_LOT_NAMES, LunarElements, hermetic_lots
from hoshi.store import ChartInput
from hoshi.zodiac import Placement, ZodiacMode


# A latitude of exactly 0° makes the Vertex calculation (cot(lat)) divide by
# zero, so charts with an unknown location are computed a hair off the equator.
# Location-derived output (angles, houses, lots) should be suppressed anyway —
# `Chart.location_known` is False on charts built this way via `from_input`.
PLACEHOLDER_LAT = 0.001
PLACEHOLDER_LON = 0.0

# Angle ids → short canonical labels used by `BodyRef.label` (and aspects).
_ANGLE_LABELS: dict[str, str] = {
    "asc": "Asc",
    "mc": "MC",
    "ic": "IC",
    "dsc": "Dsc",
    "vertex": "Vertex",
    "antivertex": "Antivertex",
}
_NODE_NAMES = frozenset({"N.Node", "S.Node"})


class Placed(BaseModel, frozen=True):
    """A point (planet or angle) placed in all three zodiac modes."""

    lon: float
    realsky: Placement
    tropical: Placement
    vedic: Placement

    @classmethod
    def for_longitude(
        cls, lon: float, ayanamsa: float, precession: float = 0.0
    ) -> "Placed":
        return cls(
            lon=lon,
            realsky=Placement.realsky(lon, precession),
            tropical=Placement.tropical(lon),
            vedic=Placement.vedic(lon, ayanamsa),
        )

    def placement(self, mode: "ZodiacMode | str") -> Placement:
        """Return the placement for the named zodiac mode (validated)."""
        if mode not in (
            ZodiacMode.realsky,
            ZodiacMode.tropical,
            ZodiacMode.vedic,
        ):
            raise ValueError(f"Unknown zodiac mode: {mode!r}")
        return getattr(self, mode)


class HouseSystem(StrEnum):
    porphyry = "porphyry"
    equal = "equal"
    placidus = "placidus"
    arc13 = "arc13"


class BodyRef(BaseModel, frozen=True):
    """A uniform handle on any placed point in a chart.

    `Chart.bodies()` yields these so consumers can iterate every body —
    planets, angles, nodes, points, and lots — without reaching across the
    chart's four separate lists or re-deriving display labels.
    """

    id: str  # stable key: pid for planets, name/angle-id otherwise
    label: str  # human label, e.g. "Sun", "Asc", "N.Node", "Fortune"
    kind: str  # Planet / Angle / Node / Point / Lot
    placed: Placed
    house: int | None = None
    retrograde: bool | None = None  # only meaningful for planets


class PlanetChart(BaseModel, frozen=True):
    pid: str
    pos: PlanetPosition
    placed: Placed
    house: int | None = None  # None when location is unknown


class AngleChart(BaseModel, frozen=True):
    name: str  # asc / mc / ic / dsc / vertex / antivertex
    placed: Placed
    house: int | None = None


class PointChart(BaseModel, frozen=True):
    """A calculated point (node, lilith, fortune) — no retrograde state."""

    name: str
    placed: Placed
    house: int | None = None


class Chart(BaseModel, frozen=True):
    when: datetime
    lat: float
    lon: float
    ayanamsa: float
    house_system: str
    angles: list[AngleChart]
    planets: list[PlanetChart]
    points: list[PointChart]
    lots: list[PointChart]
    cusps: list[float]  # 12 cusps (or 13 for arc13)
    location_known: bool = True  # False when lat/lon were placeholders
    time_known: bool = True  # False when the birth time was unknown

    @classmethod
    def build(
        cls,
        when: datetime,
        lat: float,
        lon: float,
        house_system: HouseSystem | str = HouseSystem.porphyry,
    ) -> "Chart":
        """Compute a full birth chart for the given moment and location."""
        ayan = lahiri_ayanamsa(when)
        prec = ecliptic_precession(when)
        angles = Angles.compute(when, lat, lon)
        pos = positions(when)
        lunar = LunarElements.at(when)

        if house_system == "porphyry":
            cusps = porphyry_cusps(angles)
        elif house_system == "equal":
            cusps = equal_cusps(angles.asc)
        elif house_system == "placidus":
            cusps = placidus_cusps(when, lat, lon, angles)
        else:  # arc13
            cusps = arc13_cusps(angles.asc)

        if house_system == "arc13":

            def house_of(lon: float) -> int:
                return house_13_arc(lon, angles.asc)
        else:

            def house_of(lon: float) -> int:
                return house_from_cusps(lon, cusps)

        planets = _build_planets(pos, ayan, prec, house_of)
        point_charts = _build_points(lunar, ayan, prec, house_of)
        angle_charts = [
            AngleChart(
                name=name,
                placed=Placed.for_longitude(getattr(angles, name), ayan, prec),
                house=house_of(getattr(angles, name)),
            )
            for name in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
        ]

        lot_lons = hermetic_lots(
            angles.asc,
            pos["sun"].lon,
            pos["moon"].lon,
            pos["mercury"].lon,
            pos["venus"].lon,
            pos["mars"].lon,
            pos["jupiter"].lon,
            pos["saturn"].lon,
        )
        lot_charts = [
            PointChart(
                name=name,
                placed=Placed.for_longitude(lot_lons[name], ayan, prec),
                house=house_of(lot_lons[name]),
            )
            for name in HERMETIC_LOT_NAMES
        ]

        return cls(
            when=when,
            lat=lat,
            lon=lon,
            ayanamsa=ayan,
            house_system=house_system,
            angles=angle_charts,
            planets=planets,
            points=point_charts,
            lots=lot_charts,
            cusps=cusps,
        )

    @classmethod
    def from_input(
        cls,
        ci: ChartInput,
        house_system: HouseSystem | str = HouseSystem.porphyry,
    ) -> "Chart":
        """Build a chart from a (possibly incomplete) `ChartInput`.

        When the location is unknown, placeholder coordinates are substituted
        so computation succeeds; the resulting chart reports
        `location_known=False` (and `time_known` from the input) so callers
        know to suppress angle/house/lot output. This folds the optional
        birth-data handling into the SDK rather than leaving it to callers.
        """
        lat = ci.lat if ci.lat is not None else PLACEHOLDER_LAT
        lon = ci.lon if ci.lon is not None else PLACEHOLDER_LON
        chart = cls.build(ci.to_datetime(), lat, lon, house_system=house_system)
        return chart.model_copy(
            update={
                "location_known": ci.location_known,
                "time_known": ci.time_known,
            }
        )

    @classmethod
    def positions_only(cls, when: datetime) -> "Chart":
        """Compute planet and point positions without angles, cusps, or lots."""
        ayan = lahiri_ayanamsa(when)
        prec = ecliptic_precession(when)
        pos = positions(when)
        lunar = LunarElements.at(when)

        return cls(
            when=when,
            lat=0.0,
            lon=0.0,
            ayanamsa=ayan,
            house_system="",
            angles=[],
            planets=_build_planets(pos, ayan, prec),
            points=_build_points(lunar, ayan, prec),
            lots=[],
            cusps=[],
            location_known=False,
        )

    # -- iteration -----------------------------------------------------------

    def bodies(self) -> Iterator[BodyRef]:
        """Yield every placed body in the chart as a uniform `BodyRef`.

        Order is planets, angles, nodes/points, then lots — the same order the
        chart's individual lists use. Consumers that want a subset filter on
        `BodyRef.kind`.
        """
        for p in self.planets:
            yield BodyRef(
                id=p.pid,
                label=p.pid.capitalize(),
                kind="Planet",
                placed=p.placed,
                house=p.house,
                retrograde=p.pos.retrograde,
            )
        for a in self.angles:
            yield BodyRef(
                id=a.name,
                label=_ANGLE_LABELS.get(a.name, a.name.capitalize()),
                kind="Angle",
                placed=a.placed,
                house=a.house,
            )
        for pt in self.points:
            yield BodyRef(
                id=pt.name,
                label=pt.name,
                kind="Node" if pt.name in _NODE_NAMES else "Point",
                placed=pt.placed,
                house=pt.house,
            )
        for lot in self.lots:
            yield BodyRef(
                id=lot.name,
                label=lot.name,
                kind="Lot",
                placed=lot.placed,
                house=lot.house,
            )

    def body(self, id: str) -> BodyRef:
        """Return the body with the given id (planet pid or point name).

        Raises `KeyError` if no body matches.
        """
        for b in self.bodies():
            if b.id == id:
                return b
        raise KeyError(f"No body with id {id!r} in chart")


def uncertain_signs(ci: ChartInput, mode: "ZodiacMode | str") -> frozenset[str]:
    """Planet pids whose sign changes across the input's birth date.

    When the birth time is unknown, a planet may sit in different signs at
    midnight and end-of-day; those placements can't be trusted. Only the
    fast-moving bodies (Sun through Mars) are checked, and Chiron's Horizons
    round-trip is skipped. Returns an empty set when every sign is stable.
    """
    d = datetime.fromisoformat(ci.date)
    tz = ZoneInfo(ci.tz)
    start = d.replace(hour=0, minute=0, second=0, tzinfo=tz)
    end = d.replace(hour=23, minute=59, second=59, tzinfo=tz)
    pos_start = positions(start, include_chiron=False)
    pos_end = positions(end, include_chiron=False)
    ayan = lahiri_ayanamsa(start)
    prec_start = ecliptic_precession(start)
    prec_end = ecliptic_precession(end)
    uncertain: set[str] = set()
    for pid in ("sun", "moon", "mercury", "venus", "mars"):
        s = Placed.for_longitude(pos_start[pid].lon, ayan, prec_start).placement(mode)
        e = Placed.for_longitude(pos_end[pid].lon, ayan, prec_end).placement(mode)
        if s.name != e.name:
            uncertain.add(pid)
    return frozenset(uncertain)


def _no_house(lon: float) -> None:
    """House assignment for charts with no location — house is unknown."""
    return None


def _build_planets(
    pos: dict[str, PlanetPosition],
    ayan: float,
    prec: float,
    house_of: Callable[[float], int | None] = _no_house,
) -> list[PlanetChart]:
    return [
        PlanetChart(
            pid=pid,
            pos=pos[pid],
            placed=Placed.for_longitude(pos[pid].lon, ayan, prec),
            house=house_of(pos[pid].lon),
        )
        for pid in PLANET_ORDER
    ]


def _build_points(
    lunar: LunarElements,
    ayan: float,
    prec: float,
    house_of: Callable[[float], int | None] = _no_house,
) -> list[PointChart]:
    point_lons: dict[str, float] = {
        "N.Node": lunar.north_node,
        "S.Node": lunar.south_node,
        "Lilith": lunar.lilith,
    }
    return [
        PointChart(
            name=name,
            placed=Placed.for_longitude(lon, ayan, prec),
            house=house_of(lon),
        )
        for name, lon in point_lons.items()
    ]
