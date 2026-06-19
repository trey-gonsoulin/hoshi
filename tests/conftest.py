from datetime import datetime, timezone

from hoshi.chart import AngleChart, Chart, Placed, PlanetChart, PointChart
from hoshi.ephemeris import PlanetPosition


def make_planet(pid: str, lon: float, retrograde: bool = False) -> PlanetChart:
    placed = Placed.for_longitude(lon, ayanamsa=23.85, precession=0.0)
    return PlanetChart(
        pid=pid,
        pos=PlanetPosition(lon=lon, lat=0.0, retrograde=retrograde),
        placed=placed,
        house=1,
    )


def make_angle(name: str, lon: float) -> AngleChart:
    placed = Placed.for_longitude(lon, ayanamsa=23.85, precession=0.0)
    return AngleChart(name=name, placed=placed, house=1)


def make_point(name: str, lon: float) -> PointChart:
    placed = Placed.for_longitude(lon, ayanamsa=23.85, precession=0.0)
    return PointChart(name=name, placed=placed, house=1)


def make_chart(
    planets=None,
    angles=None,
    points=None,
    lots=None,
    cusps=None,
) -> Chart:
    return Chart(
        when=datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        lat=0.0,
        lon=0.0,
        ayanamsa=23.85,
        house_system="porphyry",
        angles=angles or [],
        planets=planets or [],
        points=points or [],
        lots=lots or [],
        cusps=cusps or [i * 30.0 for i in range(12)],
    )
