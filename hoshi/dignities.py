"""Planetary dignities and sign element/modality tallies.

Dignities use standard astrological assignments adapted for the real-sky
13-sign scheme (Ophiuchus included, Chiron as its domicile ruler).
The exact Nuastro table may differ; these are a reasonable baseline.
"""

from collections.abc import Iterable

from hoshi.chart import BodyRef, Chart
from hoshi.zodiac import SIGN_ATTRS, ZodiacMode


# ---------------------------------------------------------------------------
# Dignities
# ---------------------------------------------------------------------------

# Maps sign name → {dignity_name: [planet_ids, ...]}
# Using lowercase planet ids matching PLANET_ORDER in ephemeris.py.
_SIGN_DIGNITIES: dict[str, dict[str, list[str]]] = {
    "Aries": {
        "domicile": ["mars"],
        "exaltation": ["sun"],
        "detriment": ["venus"],
        "fall": ["saturn"],
    },
    "Taurus": {
        "domicile": ["venus"],
        "exaltation": ["moon"],
        "detriment": ["mars", "pluto"],
        "fall": ["uranus"],
    },
    "Gemini": {
        "domicile": ["mercury"],
        "exaltation": [],
        "detriment": ["jupiter"],
        "fall": [],
    },
    "Cancer": {
        "domicile": ["moon"],
        "exaltation": ["jupiter"],
        "detriment": ["saturn"],
        "fall": ["mars"],
    },
    "Leo": {"domicile": ["sun"], "exaltation": [], "detriment": ["uranus"], "fall": []},
    "Virgo": {
        "domicile": ["mercury"],
        "exaltation": ["mercury"],
        "detriment": ["jupiter"],
        "fall": ["venus"],
    },
    "Libra": {
        "domicile": ["venus"],
        "exaltation": ["saturn"],
        "detriment": ["mars"],
        "fall": ["sun"],
    },
    "Scorpio": {
        "domicile": ["pluto", "mars"],
        "exaltation": [],
        "detriment": ["venus"],
        "fall": ["moon"],
    },
    "Ophiuchus": {
        "domicile": ["chiron"],
        "exaltation": [],
        "detriment": [],
        "fall": [],
    },
    "Sagittarius": {
        "domicile": ["jupiter"],
        "exaltation": [],
        "detriment": ["mercury"],
        "fall": [],
    },
    "Capricorn": {
        "domicile": ["saturn"],
        "exaltation": ["mars"],
        "detriment": ["moon"],
        "fall": ["jupiter"],
    },
    "Aquarius": {
        "domicile": ["uranus", "saturn"],
        "exaltation": [],
        "detriment": ["sun"],
        "fall": [],
    },
    "Pisces": {
        "domicile": ["neptune", "jupiter"],
        "exaltation": ["venus"],
        "detriment": ["mercury"],
        "fall": ["mercury"],
    },
}

_DIGNITY_PRIORITY = ["domicile", "exaltation", "detriment", "fall"]


def dignity_for(planet: str, sign: str) -> str | None:
    """Return the highest-priority dignity of `planet` in `sign`, or None."""
    entry = _SIGN_DIGNITIES.get(sign, {})
    pid = planet.lower()
    for d in _DIGNITY_PRIORITY:
        if pid in entry.get(d, []):
            return d
    return None


DIGNITY_SYMBOLS: dict[str, str] = {
    "domicile": "⊕",
    "exaltation": "△",
    "detriment": "▽",
    "fall": "✕",
}


# ---------------------------------------------------------------------------
# Elements and modalities
# ---------------------------------------------------------------------------


def _tally_bodies(
    bodies: Iterable[BodyRef], mode: "ZodiacMode | str"
) -> dict[str, dict[str, int]]:
    elements: dict[str, int] = {}
    modalities: dict[str, int] = {}
    for body in bodies:
        placement = body.placed.placement(mode)
        attrs = SIGN_ATTRS.get(placement.name)
        if attrs is None:
            continue
        elem, mod = attrs
        elements[elem] = elements.get(elem, 0) + 1
        modalities[mod] = modalities.get(mod, 0) + 1
    return {"elements": elements, "modalities": modalities}


def element_modality_tally(
    chart: Chart,
    mode: "ZodiacMode | str",
    *,
    include_angles: bool = True,
    include_lots: bool = True,
) -> dict[str, dict[str, dict[str, int]]]:
    """Count element and modality occurrences, returning primary (planets) and total (all bodies).

    Returns {"primary": {"elements": {...}, "modalities": {...}},
             "total":   {"elements": {...}, "modalities": {...}}}
    """
    all_bodies = [b for b in chart.bodies() if b.kind == "Planet"]
    total = [
        b
        for b in chart.bodies()
        if b.kind == "Planet"
        or (b.kind == "Angle" and include_angles)
        or b.kind in ("Node", "Point")
        or (b.kind == "Lot" and include_lots)
    ]
    return {
        "primary": _tally_bodies(all_bodies, mode),
        "total": _tally_bodies(total, mode),
    }
