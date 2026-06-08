"""Sign placement across the three modes Nuastro supports.

Ported from `nuastro-calc.js`. The IAU table is the distinguishing feature:
13 unequal real-sky constellations (including Ophiuchus) along the ecliptic,
expressed as tropical J2000 ecliptic-longitude ranges.
"""

from pydantic import BaseModel


class IAUSign(BaseModel, frozen=True):
    name: str
    abbr: str
    lo: float
    hi: float


# Tropical J2000 ecliptic longitudes. Aries wraps past 360 (hi=389.00 means 29.00).
_IAU_ROWS: list[tuple[str, str, float, float]] = [
    ("Aries",        "Ari",  29.00,  53.41),
    ("Taurus",       "Tau",  53.41,  90.46),
    ("Gemini",       "Gem",  90.46, 118.23),
    ("Cancer",       "Cnc", 118.23, 138.18),
    ("Leo",          "Leo", 138.18, 174.07),
    ("Virgo",        "Vir", 174.07, 217.84),
    ("Libra",        "Lib", 217.84, 241.03),
    ("Scorpio",      "Sco", 241.03, 247.74),
    ("Ophiuchus",    "Oph", 247.74, 266.55),
    ("Sagittarius",  "Sgr", 266.55, 299.71),
    ("Capricorn",    "Cap", 299.71, 327.61),
    ("Aquarius",     "Aqr", 327.61, 351.65),
    ("Pisces",       "Psc", 351.65, 389.00),
]
IAU: list[IAUSign] = [IAUSign(name=n, abbr=a, lo=lo, hi=hi) for n, a, lo, hi in _IAU_ROWS]

TROP_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
              "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
TROP_ABBR  = ["Ari", "Tau", "Gem", "Cnc", "Leo", "Vir",
              "Lib", "Sco", "Sgr", "Cap", "Aqr", "Psc"]


class Placement(BaseModel, frozen=True):
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
    return Placement(name=c.name, abbr=c.abbr, deg=deg)


def tropical_placement(lon: float) -> Placement:
    """Standard 12 equal 30° signs from the vernal equinox."""
    l = n360(lon)
    i = int(l // 30)
    return Placement(name=TROP_NAMES[i], abbr=TROP_ABBR[i], deg=l - i * 30)


def vedic_placement(lon: float, ayanamsa: float) -> Placement:
    """Sidereal placement with ayanamsa offset applied."""
    s = n360(lon - ayanamsa)
    i = int(s // 30)
    return Placement(name=TROP_NAMES[i], abbr=TROP_ABBR[i], deg=s - i * 30)


def format_deg(d: float) -> str:
    """Format ecliptic-degree value as DD°MM'."""
    d = max(0.0, d)
    return f"{int(d):02d}°{int((d % 1) * 60):02d}'"
