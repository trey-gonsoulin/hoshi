"""Build a complete chart: positions placed in all three zodiac modes,
plus angles, Placidus cusps, and house numbers."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from hoshi.ephemeris import PLANET_ORDER, PlanetPosition, ecliptic_precession, lahiri_ayanamsa, positions
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
from hoshi.zodiac import Placement


class Placed(BaseModel, frozen=True):
    """A point (planet or angle) placed in all three zodiac modes."""

    lon: float
    realsky: Placement
    tropical: Placement
    vedic: Placement

    @classmethod
    def for_longitude(cls, lon: float, ayanamsa: float, precession: float = 0.0) -> "Placed":
        return cls(
            lon=lon,
            realsky=Placement.realsky(lon, precession),
            tropical=Placement.tropical(lon),
            vedic=Placement.vedic(lon, ayanamsa),
        )


class HouseSystem(StrEnum):
    porphyry = "porphyry"
    equal = "equal"
    placidus = "placidus"
    arc13 = "arc13"


class PlanetChart(BaseModel, frozen=True):
    pid: str
    pos: PlanetPosition
    placed: Placed
    house: int


class AngleChart(BaseModel, frozen=True):
    name: str  # asc / mc / ic / dsc / vertex / antivertex
    placed: Placed
    house: int


class PointChart(BaseModel, frozen=True):
    """A calculated point (node, lilith, fortune) — no retrograde state."""

    name: str
    placed: Placed
    house: int


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

        planets = [
            PlanetChart(
                pid=pid,
                pos=pos[pid],
                placed=Placed.for_longitude(pos[pid].lon, ayan, prec),
                house=house_of(pos[pid].lon),
            )
            for pid in PLANET_ORDER
        ]
        angle_charts = [
            AngleChart(
                name=name,
                placed=Placed.for_longitude(getattr(angles, name), ayan, prec),
                house=house_of(getattr(angles, name)),
            )
            for name in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
        ]

        point_lons: dict[str, float] = {
            "N.Node": lunar.north_node,
            "S.Node": lunar.south_node,
            "Lilith": lunar.lilith,
        }

        def to_point(name: str, lon: float) -> PointChart:
            return PointChart(
                name=name,
                placed=Placed.for_longitude(lon, ayan, prec),
                house=house_of(lon),
            )

        point_charts = [to_point(name, lon) for name, lon in point_lons.items()]

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
        lot_charts = [to_point(name, lot_lons[name]) for name in HERMETIC_LOT_NAMES]

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
    def positions_only(cls, when: datetime) -> "Chart":
        """Compute planet and point positions without angles, cusps, or lots."""
        ayan = lahiri_ayanamsa(when)
        prec = ecliptic_precession(when)
        pos = positions(when)
        lunar = LunarElements.at(when)

        planets = [
            PlanetChart(
                pid=pid,
                pos=pos[pid],
                placed=Placed.for_longitude(pos[pid].lon, ayan, prec),
                house=0,
            )
            for pid in PLANET_ORDER
        ]

        point_lons: dict[str, float] = {
            "N.Node": lunar.north_node,
            "S.Node": lunar.south_node,
            "Lilith": lunar.lilith,
        }
        point_charts = [
            PointChart(
                name=name,
                placed=Placed.for_longitude(lon, ayan, prec),
                house=0,
            )
            for name, lon in point_lons.items()
        ]

        return cls(
            when=when,
            lat=0.0,
            lon=0.0,
            ayanamsa=ayan,
            house_system="",
            angles=[],
            planets=planets,
            points=point_charts,
            lots=[],
            cusps=[],
        )
