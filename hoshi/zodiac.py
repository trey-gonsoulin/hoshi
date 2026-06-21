"""Sign placement across the three modes Nuastro supports.

Ported from `nuastro-calc.js`. The IAU table is the distinguishing feature:
13 unequal real-sky constellations (including Ophiuchus) along the ecliptic,
expressed as tropical J2000 ecliptic-longitude ranges.
"""

from enum import StrEnum

from pydantic import BaseModel


class ZodiacMode(StrEnum):
    """The three placement schemes Hoshi supports.

    A `StrEnum`, so members compare equal to their plain-string values —
    callers may pass either `ZodiacMode.realsky` or `"realsky"`.
    """

    realsky = "realsky"
    tropical = "tropical"
    vedic = "vedic"


class IAUSign(BaseModel, frozen=True):
    name: str
    abbr: str
    lo: float
    hi: float


# Tropical J2000 ecliptic longitudes. Aries wraps past 360 (hi=389.00 means 29.00).
_IAU_ROWS: list[tuple[str, str, float, float]] = [
    ("Aries", "Ari", 29.00, 53.41),
    ("Taurus", "Tau", 53.41, 90.46),
    ("Gemini", "Gem", 90.46, 118.23),
    ("Cancer", "Cnc", 118.23, 138.18),
    ("Leo", "Leo", 138.18, 174.07),
    ("Virgo", "Vir", 174.07, 217.84),
    ("Libra", "Lib", 217.84, 241.03),
    ("Scorpio", "Sco", 241.03, 247.74),
    ("Ophiuchus", "Oph", 247.74, 266.55),
    ("Sagittarius", "Sgr", 266.55, 299.71),
    ("Capricorn", "Cap", 299.71, 327.61),
    ("Aquarius", "Aqr", 327.61, 351.65),
    ("Pisces", "Psc", 351.65, 389.00),
]
IAU: list[IAUSign] = [
    IAUSign(name=n, abbr=a, lo=lo, hi=hi) for n, a, lo, hi in _IAU_ROWS
]


class SignInfo(BaseModel, frozen=True):
    """A tropical sign's name, abbreviation, element, and modality."""

    name: str
    abbr: str
    element: str
    modality: str


# The twelve tropical signs, in zodiac order. Single source of truth for
# names, abbreviations, elements, and modalities — derive parallel lists from
# this rather than maintaining hand-aligned arrays.
TROP_SIGNS: list[SignInfo] = [
    SignInfo(name="Aries", abbr="Ari", element="Fire", modality="Cardinal"),
    SignInfo(name="Taurus", abbr="Tau", element="Earth", modality="Fixed"),
    SignInfo(name="Gemini", abbr="Gem", element="Air", modality="Mutable"),
    SignInfo(name="Cancer", abbr="Cnc", element="Water", modality="Cardinal"),
    SignInfo(name="Leo", abbr="Leo", element="Fire", modality="Fixed"),
    SignInfo(name="Virgo", abbr="Vir", element="Earth", modality="Mutable"),
    SignInfo(name="Libra", abbr="Lib", element="Air", modality="Cardinal"),
    SignInfo(name="Scorpio", abbr="Sco", element="Water", modality="Fixed"),
    SignInfo(name="Sagittarius", abbr="Sgr", element="Fire", modality="Mutable"),
    SignInfo(name="Capricorn", abbr="Cap", element="Earth", modality="Cardinal"),
    SignInfo(name="Aquarius", abbr="Aqr", element="Air", modality="Fixed"),
    SignInfo(name="Pisces", abbr="Psc", element="Water", modality="Mutable"),
]

TROP_NAMES = [s.name for s in TROP_SIGNS]
TROP_ABBR = [s.abbr for s in TROP_SIGNS]

# Sign name → (element, modality), covering all 13 real-sky signs.
# Ophiuchus is Water / Fixed by Nuastro convention.
SIGN_ATTRS: dict[str, tuple[str, str]] = {
    s.name: (s.element, s.modality) for s in TROP_SIGNS
}
SIGN_ATTRS["Ophiuchus"] = ("Water", "Fixed")


def n360(v: float) -> float:
    return v % 360.0


def _iau_index(lon: float, precession: float = 0.0) -> int:
    lon = n360(lon)
    for i, c in enumerate(IAU):
        lo = n360(c.lo + precession)
        hi = n360(c.hi + precession)
        if (
            lo > hi
        ):  # wraps past 360 (Pisces, or any sign near 0° after precession shift)
            if lon >= lo or lon < hi:
                return i
        else:
            if lo <= lon < hi:
                return i
    return 12


class Placement(BaseModel, frozen=True):
    name: str
    abbr: str
    deg: float  # degrees into the sign (0–width)

    @classmethod
    def realsky(cls, lon: float, precession: float = 0.0) -> "Placement":
        """Real-sky IAU constellation placement (13 signs, unequal widths).

        The IAU boundary table is J2000-fixed. Pass `precession` (degrees
        since J2000) to shift the boundaries to the of-date frame before
        comparing against `lon`.
        """
        i = _iau_index(lon, precession)
        c = IAU[i]
        lo = n360(c.lo + precession)
        hi = n360(c.hi + precession)
        lng = n360(lon)
        if lo > hi:  # wraps past 360
            deg = lng - lo if lng >= lo else (360 - lo) + lng
        else:
            deg = lng - lo
        return cls(name=c.name, abbr=c.abbr, deg=deg)

    @classmethod
    def tropical(cls, lon: float) -> "Placement":
        """Standard 12 equal 30° signs from the vernal equinox."""
        lng = n360(lon)
        i = int(lng // 30)
        return cls(name=TROP_NAMES[i], abbr=TROP_ABBR[i], deg=lng - i * 30)

    @classmethod
    def vedic(cls, lon: float, ayanamsa: float) -> "Placement":
        """Sidereal placement with ayanamsa offset applied."""
        s = n360(lon - ayanamsa)
        i = int(s // 30)
        return cls(name=TROP_NAMES[i], abbr=TROP_ABBR[i], deg=s - i * 30)

    @classmethod
    def for_mode(
        cls,
        lon: float,
        mode: "ZodiacMode | str",
        *,
        ayanamsa: float = 0.0,
        precession: float = 0.0,
    ) -> "Placement":
        """Place a longitude according to the named zodiac mode.

        Single dispatch point for the three modes so callers don't repeat the
        mode→method mapping (and a bad mode fails here, at the boundary).
        Accepts a `ZodiacMode` or its plain-string value.
        """
        if mode == ZodiacMode.realsky:
            return cls.realsky(lon, precession)
        if mode == ZodiacMode.tropical:
            return cls.tropical(lon)
        if mode == ZodiacMode.vedic:
            return cls.vedic(lon, ayanamsa)
        raise ValueError(f"Unknown zodiac mode: {mode!r}")


def format_deg(d: float) -> str:
    """Format ecliptic-degree value as DD°MM'."""
    d = max(0.0, d)
    return f"{int(d):02d}°{int((d % 1) * 60):02d}'"
