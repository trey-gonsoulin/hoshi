"""Persistent storage for birth charts.

Charts are stored as JSON files in `./charts/` (one file per chart, keyed
by a filename-sanitized version of the chart name). Only the inputs are
persisted — the chart is recomputed on read, which is fast because the
Chiron/lunar Horizons responses are cached separately.
"""

import re
from pathlib import Path

from pydantic import BaseModel


CHARTS_DIR = Path("charts")


class ChartInput(BaseModel, frozen=True):
    name: str
    date: str       # YYYY-MM-DD
    time: str       # HH:MM (24h)
    tz: str         # IANA timezone, e.g. "America/Chicago"
    lat: float
    lng: float


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower()).strip("_")
    if not safe:
        raise ValueError(f"Chart name {name!r} produces an empty filename")
    return safe


def path_for(name: str) -> Path:
    return CHARTS_DIR / f"{_safe_filename(name)}.json"


def exists(name: str) -> bool:
    return path_for(name).exists()


def save(chart_input: ChartInput, *, overwrite: bool = False) -> Path:
    path = path_for(chart_input.name)
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"Chart {chart_input.name!r} already exists at {path}. "
            f"Pass --force to overwrite."
        )
    CHARTS_DIR.mkdir(exist_ok=True)
    path.write_text(chart_input.model_dump_json(indent=2))
    return path


def load(name: str) -> ChartInput:
    path = path_for(name)
    if not path.exists():
        raise FileNotFoundError(f"No saved chart named {name!r} (looked at {path})")
    return ChartInput.model_validate_json(path.read_text())


def list_all() -> list[ChartInput]:
    if not CHARTS_DIR.exists():
        return []
    out: list[ChartInput] = []
    for p in sorted(CHARTS_DIR.glob("*.json")):
        try:
            out.append(ChartInput.model_validate_json(p.read_text()))
        except ValueError:
            continue  # skip malformed files
    return out


def delete(name: str) -> Path:
    path = path_for(name)
    if not path.exists():
        raise FileNotFoundError(f"No saved chart named {name!r} (looked at {path})")
    path.unlink()
    return path
