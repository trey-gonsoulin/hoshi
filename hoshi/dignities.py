"""Planetary dignities and sign element/modality tallies.

Dignities use standard astrological assignments adapted for the real-sky
13-sign scheme (Ophiuchus included, Chiron as its domicile ruler).
The exact Nuastro table may differ; these are a reasonable baseline.
"""

from hoshi.chart import Chart


# ---------------------------------------------------------------------------
# Dignities
# ---------------------------------------------------------------------------

# Maps sign name → {dignity_name: [planet_ids, ...]}
# Using lowercase planet ids matching PLANET_ORDER in ephemeris.py.
_SIGN_DIGNITIES: dict[str, dict[str, list[str]]] = {
    "Aries":        {"domicile": ["mars"],        "exaltation": ["sun"],     "detriment": ["venus"],           "fall": ["saturn"]},
    "Taurus":       {"domicile": ["venus"],        "exaltation": ["moon"],    "detriment": ["mars", "pluto"],   "fall": ["uranus"]},
    "Gemini":       {"domicile": ["mercury"],      "exaltation": [],          "detriment": ["jupiter"],         "fall": []},
    "Cancer":       {"domicile": ["moon"],         "exaltation": ["jupiter"], "detriment": ["saturn"],          "fall": ["mars"]},
    "Leo":          {"domicile": ["sun"],          "exaltation": [],          "detriment": ["uranus"],          "fall": []},
    "Virgo":        {"domicile": ["mercury"],      "exaltation": ["mercury"], "detriment": ["jupiter"],         "fall": ["venus"]},
    "Libra":        {"domicile": ["venus"],        "exaltation": ["saturn"],  "detriment": ["mars"],            "fall": ["sun"]},
    "Scorpio":      {"domicile": ["pluto", "mars"],"exaltation": [],          "detriment": ["venus"],           "fall": ["moon"]},
    "Ophiuchus":    {"domicile": ["chiron"],       "exaltation": [],          "detriment": [],                  "fall": []},
    "Sagittarius":  {"domicile": ["jupiter"],      "exaltation": [],          "detriment": ["mercury"],         "fall": []},
    "Capricorn":    {"domicile": ["saturn"],       "exaltation": ["mars"],    "detriment": ["moon"],            "fall": ["jupiter"]},
    "Aquarius":     {"domicile": ["uranus", "saturn"], "exaltation": [],      "detriment": ["sun"],             "fall": []},
    "Pisces":       {"domicile": ["neptune", "jupiter"], "exaltation": ["venus"], "detriment": ["mercury"],     "fall": ["mercury"]},
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
    "domicile":   "⊕",
    "exaltation": "△",
    "detriment":  "▽",
    "fall":       "✕",
}


# ---------------------------------------------------------------------------
# Elements and modalities
# ---------------------------------------------------------------------------

# Tropical signs in order — index matches TROP_NAMES.
_SIGN_ELEMENT: list[str] = [
    "Fire", "Earth", "Air",  "Water",  # Aries Taurus Gemini Cancer
    "Fire", "Earth", "Air",  "Water",  # Leo Virgo Libra Scorpio
    "Fire", "Earth", "Air",  "Water",  # Sagittarius Capricorn Aquarius Pisces
]

_SIGN_MODALITY: list[str] = [
    "Cardinal", "Fixed", "Mutable", "Cardinal",  # Aries Taurus Gemini Cancer
    "Fixed",    "Mutable","Cardinal","Fixed",     # Leo Virgo Libra Scorpio
    "Mutable",  "Cardinal","Fixed",  "Mutable",  # Sagittarius Capricorn Aquarius Pisces
]

# Tropical sign name → (element, modality)
from hoshi.zodiac import TROP_NAMES  # noqa: E402 — avoids circular at module level

_TROP_SIGN_ATTRS: dict[str, tuple[str, str]] = {
    name: (_SIGN_ELEMENT[i], _SIGN_MODALITY[i]) for i, name in enumerate(TROP_NAMES)
}

# Ophiuchus: Water / Fixed (Nuastro convention)
_REALSKY_EXTRA: dict[str, tuple[str, str]] = {
    "Ophiuchus": ("Water", "Fixed"),
}


def _sign_attrs(sign: str) -> tuple[str, str] | None:
    """Return (element, modality) for a sign name, or None if unknown."""
    return _TROP_SIGN_ATTRS.get(sign) or _REALSKY_EXTRA.get(sign)


def _tally_bodies(bodies: list, mode: str) -> dict[str, dict[str, int]]:
    elements: dict[str, int] = {}
    modalities: dict[str, int] = {}
    for body in bodies:
        placement = getattr(body.placed, mode)
        attrs = _sign_attrs(placement.name)
        if attrs is None:
            continue
        elem, mod = attrs
        elements[elem] = elements.get(elem, 0) + 1
        modalities[mod] = modalities.get(mod, 0) + 1
    return {"elements": elements, "modalities": modalities}


def element_modality_tally(chart: Chart, mode: str) -> dict[str, dict[str, dict[str, int]]]:
    """Count element and modality occurrences, returning primary (planets) and total (all bodies).

    Returns {"primary": {"elements": {...}, "modalities": {...}},
             "total":   {"elements": {...}, "modalities": {...}}}
    """
    all_bodies = list(chart.planets) + list(chart.angles) + list(chart.points) + list(chart.lots)
    return {
        "primary": _tally_bodies(chart.planets, mode),
        "total":   _tally_bodies(all_bodies, mode),
    }
