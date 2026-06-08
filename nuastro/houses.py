"""Chart angles (ASC/MC/IC/DSC), Placidus house cusps, and house assignment.

Ported from `calcPlacidus` and `houseNumber` in `nuastro-calc.js`. Angles
themselves are derived here rather than read from an ephemeris.
"""

import math
from datetime import datetime, timezone

from pydantic import BaseModel

from nuastro.ephemeris import _timescale


# Fixed house arcs = IAU constellation widths in zodiac order. Nuastro's
# "real-sky" house wheel: 13 unequal houses anchored at the ASC.
FIXED_ARCS: list[float] = [
    24.41, 37.05, 27.77, 19.95, 35.89, 43.77, 23.19,
    6.71, 18.81, 33.16, 27.90, 24.04, 37.35,
]

_FIXED_STARTS: list[float] = []
_acc = 0.0
for _arc in FIXED_ARCS:
    _FIXED_STARTS.append(_acc)
    _acc += _arc


def _n360(v: float) -> float:
    return v % 360.0


def _julian_day_ut(when_utc: datetime) -> float:
    """JD for the UT moment. Skyfield's ut1 differs from UTC by < 1 s."""
    return _timescale().from_datetime(when_utc).ut1


class Angles(BaseModel, frozen=True):
    asc: float
    mc: float
    ic: float
    dsc: float
    vertex: float
    antivertex: float

    @classmethod
    def compute(cls, when: datetime, lat: float, lng: float) -> "Angles":
        """ASC/MC/IC/DSC and Vertex/Antivertex in ecliptic degrees.

        `lng` is geographic longitude, east positive (e.g. Chicago ≈ -87.65).
        """
        if when.tzinfo is None:
            raise ValueError("`when` must be timezone-aware (use UTC)")
        when_utc = when.astimezone(timezone.utc)

        jd = _julian_day_ut(when_utc)
        T = (jd - 2451545.0) / 36525.0
        gmst = _n360(280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T)
        ramc = _n360(gmst + lng)
        eps = math.radians(23.439291111 - 0.013004167 * T)
        lat_r = math.radians(lat)
        ramc_r = math.radians(ramc)

        mc = _n360(math.degrees(math.atan2(math.sin(ramc_r), math.cos(ramc_r) * math.cos(eps))))

        y_a = -math.cos(ramc_r)
        x_a = math.sin(eps) * math.tan(lat_r) + math.cos(eps) * math.sin(ramc_r)
        asc = _n360(math.degrees(math.atan2(y_a, x_a)))
        # ASC must lead MC by 0–180° on the ecliptic.
        if _n360(asc - mc) > 180.0:
            asc = _n360(asc + 180.0)

        # Vertex: the ecliptic intersection of the prime vertical (great circle
        # through east/west horizon points and the zenith). Same form as the
        # ASC equation but with the co-latitude (90°-lat) substituted for
        # latitude, so tan(lat) becomes cot(lat). Quadrant fix forces it into
        # the western hemisphere (houses 5–8), the conventional Vertex side.
        cot_lat = 1.0 / math.tan(lat_r)
        y_v = -math.cos(ramc_r)
        x_v = math.sin(eps) * cot_lat - math.cos(eps) * math.sin(ramc_r)
        vertex = _n360(math.degrees(math.atan2(y_v, x_v)))
        if not 90.0 <= _n360(vertex - asc) <= 270.0:
            vertex = _n360(vertex + 180.0)
        antivertex = _n360(vertex + 180.0)

        return cls(
            asc=asc,
            mc=mc,
            ic=_n360(mc + 180.0),
            dsc=_n360(asc + 180.0),
            vertex=vertex,
            antivertex=antivertex,
        )


def placidus_cusps(when: datetime, lat: float, lng: float, angles: Angles) -> list[float]:
    """Return the 12 Placidus house cusps in ecliptic degrees.

    Cardinal cusps (1/4/7/10) are pinned to the supplied `angles` so axis
    lines drawn elsewhere don't drift from the cusp positions.
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (use UTC)")
    when_utc = when.astimezone(timezone.utc)

    jd = _julian_day_ut(when_utc)
    T = (jd - 2451545.0) / 36525.0
    gmst = _n360(280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T)
    ramc = _n360(gmst + lng)
    eps = math.radians(23.439291111 - 0.013004167 * T)
    lat_r = math.radians(lat)

    # Seed MC for the iteration (the Placidus algorithm needs a starting MC).
    mc_seed = _n360(math.degrees(math.atan2(
        math.sin(math.radians(ramc)),
        math.cos(math.radians(ramc)) * math.cos(eps),
    )))

    def cusp(fraction: float, from_ic: bool) -> float:
        base = _n360(ramc + 180.0) if from_ic else ramc
        lon = _n360(mc_seed + (180.0 if from_ic else 0.0) + fraction * 90.0)
        for _ in range(100):
            prev = lon
            lon_r = math.radians(lon)
            dec = math.asin(math.sin(eps) * math.sin(lon_r))
            cos_d = -math.tan(lat_r) * math.tan(dec)
            if abs(cos_d) > 1.0:
                break  # circumpolar — Placidus undefined
            dsa = math.degrees(math.acos(cos_d))
            nsa = 180.0 - dsa
            sa = nsa if from_ic else dsa
            ad = math.degrees(math.asin(math.sin(dec) / math.cos(dec) * math.tan(lat_r)))
            target_ox = _n360(base - fraction * sa) if from_ic else _n360(base + fraction * sa)
            target_ra = _n360(target_ox - ad) if from_ic else _n360(target_ox + ad)
            lon = _n360(math.degrees(math.atan2(
                math.sin(math.radians(target_ra)) / math.cos(eps),
                math.cos(math.radians(target_ra)),
            )))
            if abs(_n360(lon - prev + 180.0) - 180.0) < 0.0001:
                break
        return _n360(lon)

    h11 = cusp(1 / 3, False)
    h12 = cusp(2 / 3, False)
    h3  = cusp(1 / 3, True)
    h2  = cusp(2 / 3, True)

    return [
        angles.asc,                  # 1  ASC
        h2,                          # 2
        h3,                          # 3
        angles.ic,                   # 4  IC
        _n360(h11 + 180.0),          # 5
        _n360(h12 + 180.0),          # 6
        angles.dsc,                  # 7  DSC
        _n360(h2 + 180.0),           # 8
        _n360(h3 + 180.0),           # 9
        angles.mc,                   # 10 MC
        h11,                         # 11
        h12,                         # 12
    ]


def house_13_arc(lon: float, asc: float) -> int:
    """Nuastro's 13-arc fixed wheel: house 1 starts at ASC, arcs follow IAU widths."""
    w = _n360(lon - asc)
    for i in range(13):
        nxt = _FIXED_STARTS[i + 1] if i < 12 else 360.0
        if _FIXED_STARTS[i] <= w < nxt:
            return i + 1
    return 13


def house_placidus(lon: float, cusps: list[float]) -> int:
    """Standard 12-house assignment from Placidus cusps."""
    l = _n360(lon)
    for i in range(12):
        a = cusps[i]
        b = cusps[(i + 1) % 12]
        if a <= b:
            if a <= l < b:
                return i + 1
        else:  # cusp range wraps past 360
            if l >= a or l < b:
                return i + 1
    return 12
