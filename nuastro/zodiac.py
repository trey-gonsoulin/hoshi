"""Sign placement across the three modes Nuastro supports.

Ported from `nuastro-calc.js`. The IAU table is the distinguishing feature:
13 unequal real-sky constellations (including Ophiuchus) along the ecliptic,
expressed as tropical J2000 ecliptic-longitude ranges.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IAUSign:
    name: str
    abbr: str
    lo: float
    hi: float


# Tropical J2000 ecliptic longitudes. Aries wraps past 360 (hi=389.00 means 29.00).
IAU: list[IAUSign] = [
    IAUSign("Aries",        "Ari",  29.00,  53.41),
    IAUSign("Taurus",       "Tau",  53.41,  90.46),
    IAUSign("Gemini",       "Gem",  90.46, 118.23),
    IAUSign("Cancer",       "Cnc", 118.23, 138.18),
    IAUSign("Leo",          "Leo", 138.18, 174.07),
    IAUSign("Virgo",        "Vir", 174.07, 217.84),
    IAUSign("Libra",        "Lib", 217.84, 241.03),
    IAUSign("Scorpio",      "Sco", 241.03, 247.74),
    IAUSign("Ophiuchus",    "Oph", 247.74, 266.55),
    IAUSign("Sagittarius",  "Sgr", 266.55, 299.71),
    IAUSign("Capricorn",    "Cap", 299.71, 327.61),
    IAUSign("Aquarius",     "Aqr", 327.61, 351.65),
    IAUSign("Pisces",        "Psc", 351.65, 389.00),
]

TROP_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
TROP_ABBR  = ["Ari", "Tau", "Gem", "Cnc", "Leo", "Vir",
              "Lib", "Sco", "Sgr", "Cap", "Aqr", "Psc"]


@dataclass(frozen=True)
class Placement:
    name: str
    abbr: str
    deg: float  # degrees into the sign (0–width)


def n360(v: float) -> float:
    return v % 360.0


def _iau_index(lon: float) -> int:
    lon = n360(lon)
    for i, c in enumerate(IAU):
        hi = c.hi - 360 if c.hi > 360 else c.hi
        if c.lo > hi:  # wraps past 360 (Pisces)
            if lon >= c.lo or lon < hi:
                return i
        else:
            if c.lo <= lon < c.hi:
                return i
    return 12


def nuastro_placement(lon: float) -> Placement:
    """Real-sky IAU constellation placement (13 signs, unequal widths)."""
    i = _iau_index(lon)
    c = IAU[i]
    l = n360(lon)
    hi = c.hi - 360 if c.hi > 360 else c.hi
    if c.lo > hi:
        deg = l - c.lo if l >= c.lo else (360 - c.lo) + l
    else:
        deg = l - c.lo
    return Placement(c.name, c.abbr, deg)


def tropical_placement(lon: float) -> Placement:
    """Standard 12 equal 30° signs from the vernal equinox."""
    l = n360(lon)
    i = int(l // 30)
    return Placement(TROP_NAMES[i], TROP_ABBR[i], l - i * 30)


def vedic_placement(lon: float, ayanamsa: float) -> Placement:
    """Sidereal placement with ayanamsa offset applied."""
    s = n360(lon - ayanamsa)
    i = int(s // 30)
    return Placement(TROP_NAMES[i], TROP_ABBR[i], s - i * 30)


def format_deg(d: float) -> str:
    """Format ecliptic-degree value as DD°MM'."""
    d = max(0.0, d)
    return f"{int(d):02d}°{int((d % 1) * 60):02d}'"
