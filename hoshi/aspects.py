"""Astrological aspect detection between chart bodies."""

from pydantic import BaseModel

from hoshi.chart import Chart


class AspectDef(BaseModel, frozen=True):
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
    AspectDef(name="Conjunction", symbol="☌", angle=0.0, orb=MAJOR_ORB, kind="Major"),
    AspectDef(name="Opposition", symbol="☍", angle=180.0, orb=MAJOR_ORB, kind="Major"),
    AspectDef(name="Trine", symbol="△", angle=120.0, orb=MAJOR_ORB, kind="Major"),
    AspectDef(name="Square", symbol="□", angle=90.0, orb=MAJOR_ORB, kind="Major"),
    AspectDef(name="Sextile", symbol="⚹", angle=60.0, orb=MAJOR_ORB, kind="Major"),
    # Minor
    AspectDef(name="Inconjunct", symbol="⚻", angle=150.0, orb=MINOR_ORB, kind="Minor"),
    AspectDef(name="Semi-sextile", symbol="⚺", angle=30.0, orb=MINOR_ORB, kind="Minor"),
    AspectDef(name="Semi-square", symbol="∠", angle=45.0, orb=MINOR_ORB, kind="Minor"),
    AspectDef(
        name="Sesquiquadrate", symbol="⚼", angle=135.0, orb=MINOR_ORB, kind="Minor"
    ),
    # Micro
    AspectDef(name="Quintile", symbol="Q", angle=72.0, orb=MICRO_ORB, kind="Micro"),
    AspectDef(
        name="Bi-quintile", symbol="bQ", angle=144.0, orb=MICRO_ORB, kind="Micro"
    ),
    AspectDef(name="Septile", symbol="S", angle=360.0 / 7, orb=MICRO_ORB, kind="Micro"),
]

KIND_ORDER = ["Major", "Minor", "Micro"]


class Aspect(BaseModel, frozen=True):
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


# Pairs that are definitionally opposite — always 180° apart, never informative.
_AXIS_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"Asc", "Dsc"}),
        frozenset({"MC", "IC"}),
        frozenset({"Vertex", "Antivertex"}),
        frozenset({"N.Node", "S.Node"}),
    }
)

_ANGLE_LABELS: dict[str, str] = {
    "asc": "Asc",
    "mc": "MC",
    "ic": "IC",
    "dsc": "Dsc",
    "vertex": "Vertex",
    "antivertex": "Antivertex",
}


def _bodies(chart: Chart, details: bool = True) -> list[tuple[str, float]]:
    """Collect chart bodies as (display_name, ecliptic_lon) pairs.

    Without details: planets + Asc only.
    With details: all bodies (angles, nodes, points, lots).
    """
    out: list[tuple[str, float]] = []
    for p in chart.planets:
        out.append((p.pid.capitalize(), p.placed.lon))
    for a in chart.angles:
        label = _ANGLE_LABELS.get(a.name, a.name.capitalize())
        if details or a.name == "asc":
            out.append((label, a.placed.lon))
    if details:
        for pt in chart.points:
            out.append((pt.name, pt.placed.lon))
        for lot in chart.lots:
            out.append((lot.name, lot.placed.lon))
    return out


def compute_aspects(chart: Chart, details: bool = True) -> list[Aspect]:
    """Return all significant aspects between chart bodies, sorted by tightness."""
    bodies = _bodies(chart, details)
    aspects: list[Aspect] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            name_a, lon_a = bodies[i]
            name_b, lon_b = bodies[j]
            if frozenset({name_a, name_b}) in _AXIS_PAIRS:
                continue
            # Shortest arc between the two bodies.
            diff = (lon_a - lon_b) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            for adef in ASPECT_DEFS:
                orb = diff - adef.angle
                if abs(orb) <= adef.orb:
                    aspects.append(
                        Aspect(
                            body_a=name_a,
                            body_b=name_b,
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


def compute_inter_aspects(
    chart_a: Chart, chart_b: Chart, details: bool = True
) -> list[Aspect]:
    """Return all significant aspects between bodies of two different charts."""
    bodies_a = _bodies(chart_a, details)
    bodies_b = _bodies(chart_b, details)
    aspects: list[Aspect] = []

    for name_a, lon_a in bodies_a:
        for name_b, lon_b in bodies_b:
            diff = (lon_a - lon_b) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff

            for adef in ASPECT_DEFS:
                orb = diff - adef.angle
                if abs(orb) <= adef.orb:
                    aspects.append(
                        Aspect(
                            body_a=name_a,
                            body_b=name_b,
                            name=adef.name,
                            symbol=adef.symbol,
                            angle=adef.angle,
                            orb=orb,
                            kind=adef.kind,
                        )
                    )
                    break

    aspects.sort(key=lambda asp: abs(asp.orb))
    return aspects


def fmt_orb(orb: float) -> str:
    return _fmt_orb(orb)
