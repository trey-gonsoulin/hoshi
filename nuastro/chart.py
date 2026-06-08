"""Build a complete chart: positions placed in all three zodiac modes,
plus angles, Placidus cusps, and house numbers."""

from datetime import datetime

from pydantic import BaseModel

from .ephemeris import PLANET_ORDER, PlanetPosition, lahiri_ayanamsa, positions
from .houses import Angles, house_13_arc, house_placidus, placidus_cusps
from .points import LunarElements, part_of_fortune
from .zodiac import Placement


class Placed(BaseModel, frozen=True):
    """A point (planet or angle) placed in all three zodiac modes."""
    lon: float
    nuastro: Placement
    tropical: Placement
    vedic: Placement

    @classmethod
    def for_longitude(cls, lon: float, ayanamsa: float) -> "Placed":
        return cls(
            lon=lon,
            nuastro=Placement.nuastro(lon),
            tropical=Placement.tropical(lon),
            vedic=Placement.vedic(lon, ayanamsa),
        )


class PlanetChart(BaseModel, frozen=True):
    pid: str
    pos: PlanetPosition
    placed: Placed
    house_13: int       # Nuastro 13-arc wheel
    house_placidus: int # Standard 12-house Placidus


class AngleChart(BaseModel, frozen=True):
    name: str           # asc / mc / ic / dsc / vertex / antivertex
    placed: Placed
    house_13: int
    house_placidus: int


class PointChart(BaseModel, frozen=True):
    """A calculated point (node, lilith, fortune) — no retrograde state."""
    name: str
    placed: Placed
    house_13: int
    house_placidus: int


class Chart(BaseModel, frozen=True):
    when: datetime
    lat: float
    lng: float
    ayanamsa: float
    angles: list[AngleChart]
    planets: list[PlanetChart]
    points: list[PointChart]
    cusps: list[float]  # 12 Placidus cusps in ecliptic degrees

    @classmethod
    def build(cls, when: datetime, lat: float, lng: float) -> "Chart":
        """Compute a full birth chart for the given moment and location."""
        ayan = lahiri_ayanamsa(when)
        angles = Angles.compute(when, lat, lng)
        cusps = placidus_cusps(when, lat, lng, angles)
        pos = positions(when)
        lunar = LunarElements.at(when)

        planets = [
            PlanetChart(
                pid=pid,
                pos=pos[pid],
                placed=Placed.for_longitude(pos[pid].lon, ayan),
                house_13=house_13_arc(pos[pid].lon, angles.asc),
                house_placidus=house_placidus(pos[pid].lon, cusps),
            )
            for pid in PLANET_ORDER
        ]
        angle_charts = [
            AngleChart(
                name=name,
                placed=Placed.for_longitude(getattr(angles, name), ayan),
                house_13=house_13_arc(getattr(angles, name), angles.asc),
                house_placidus=house_placidus(getattr(angles, name), cusps),
            )
            for name in ("asc", "mc", "ic", "dsc", "vertex", "antivertex")
        ]

        point_lons: dict[str, float] = {
            "N.Node":  lunar.north_node,
            "S.Node":  lunar.south_node,
            "Lilith":  lunar.lilith,
            "Fortune": part_of_fortune(angles.asc, pos["sun"].lon, pos["moon"].lon),
        }
        point_charts = [
            PointChart(
                name=name,
                placed=Placed.for_longitude(lon, ayan),
                house_13=house_13_arc(lon, angles.asc),
                house_placidus=house_placidus(lon, cusps),
            )
            for name, lon in point_lons.items()
        ]

        return cls(
            when=when,
            lat=lat,
            lng=lng,
            ayanamsa=ayan,
            angles=angle_charts,
            planets=planets,
            points=point_charts,
            cusps=cusps,
        )
