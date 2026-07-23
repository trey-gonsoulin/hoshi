#!/usr/bin/env python3
"""Export hoshi.info reference data to astroData.json for the UI bundle.

Run from the repo root:
    uv run python scripts/export_astro_data.py

The output is committed alongside the UI source so builds are hermetic.
Add a CI step or pre-commit hook to verify the file is up-to-date.
"""

import json
from pathlib import Path

from hoshi.info import (
    ANGLES,
    ASPECTS,
    DIGNITIES,
    HOUSES,
    PLANETS,
    POINTS,
    RETROGRADE,
    SIGNS,
)


def _info(item) -> dict:
    return {
        "name": item.name,
        "keywords": list(item.keywords),
        "meaning": item.meaning,
        "aliases": list(getattr(item, "aliases", [])),
    }


def _sign(item) -> dict:
    return {
        **_info(item),
        "element": item.element,
        "modality": item.modality,
        "ruler": item.ruler,
        "lo": item.lo,
        "size": item.size,
    }


output = {
    "planets": {k: _info(v) for k, v in PLANETS.items()},
    "signs": {k: _sign(v) for k, v in SIGNS.items()},
    "angles": {k: _info(v) for k, v in ANGLES.items()},
    "aspects": {k: _info(v) for k, v in ASPECTS.items()},
    "houses": {str(k): _info(v) for k, v in HOUSES.items()},
    "points": {k: _info(v) for k, v in POINTS.items()},
    "dignities": {k: _info(v) for k, v in DIGNITIES.items()},
    "retrograde": _info(RETROGRADE),
}

out_path = (
    Path(__file__).parent.parent
    / "packages"
    / "hoshi-ui"
    / "src"
    / "lib"
    / "astroData.json"
)
out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
print(f"Written {out_path}")
