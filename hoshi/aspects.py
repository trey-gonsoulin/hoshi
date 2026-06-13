"""Astrological aspect detection between chart bodies."""

from dataclasses import dataclass

from hoshi.chart import Chart


@dataclass(frozen=True)
class AspectDef:
    name: str
    symbol: str
    angle: float
    orb: float
    kind: str  # "Major", "Minor", or "Micro"


MAJOR_ORB = 4.0
MINOR_ORB = 2.0
MICRO_ORB = 1.0

ASPECT_DEFS: list[AspectDef] = [
    # Major
    AspectDef("Conjunction",    "☌",  0.0,         MAJOR_ORB, "Major"),
    AspectDef("Opposition",     "☍",  180.0,       MAJOR_ORB, "Major"),
    AspectDef("Trine",          "△",  120.0,       MAJOR_ORB, "Major"),
    AspectDef("Square",         "□",  90.0,        MAJOR_ORB, "Major"),
    AspectDef("Sextile",        "⚹",  60.0,        MAJOR_ORB, "Major"),
    # Minor
    AspectDef("Inconjunct",     "⚻",  150.0,       MINOR_ORB, "Minor"),
    AspectDef("Semi-sextile",   "⚺",  30.0,        MINOR_ORB, "Minor"),
    AspectDef("Semi-square",    "∠",  45.0,        MINOR_ORB, "Minor"),
    AspectDef("Sesquiquadrate", "⚼",  135.0,       MINOR_ORB, "Minor"),
    # Micro
    AspectDef("Quintile",       "Q",  72.0,        MICRO_ORB, "Micro"),
    AspectDef("Bi-quintile",    "bQ", 144.0,       MICRO_ORB, "Micro"),
    AspectDef("Septile",        "S",  360.0 / 7,   MICRO_ORB, "Micro"),
]

KIND_ORDER = ["Major", "Minor", "Micro"]


@dataclass(frozen=True)
class Aspect:
    body_a: str
    body_b: str
    name: str
    symbol: str
    angle: float
    orb: float  # signed: positive = wider than exact, negative = tighter
    kind: str


def _fmt_orb(orb: float) -> str:
    sign = "+" if orb >= 0 else "-"
    total_minutes = round(abs(orb) * 60)
    d, m = divmod(total_minutes, 60)
    return f"{sign}{d}°{m:02d}'"


def compute_aspects(chart: Chart) -> list[Aspect]:
    """Return all significant aspects between planets, sorted by tightness."""
    planets = chart.planets
    aspects: list[Aspect] = []

    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            a = planets[i]
            b = planets[j]
            # Use absolute ecliptic longitudes — shortest arc between the two bodies.
            diff = (a.placed.lon - b.placed.lon) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            for adef in ASPECT_DEFS:
                orb = diff - adef.angle
                if abs(orb) <= adef.orb:
                    aspects.append(
                        Aspect(
                            body_a=a.pid.capitalize(),
                            body_b=b.pid.capitalize(),
                            name=adef.name,
                            symbol=adef.symbol,
                            angle=adef.angle,
                            orb=orb,
                            kind=adef.kind,
                        )
                    )
                    break  # one aspect per pair

    aspects.sort(key=lambda asp: abs(asp.orb))
    return aspects


def fmt_orb(orb: float) -> str:
    return _fmt_orb(orb)
