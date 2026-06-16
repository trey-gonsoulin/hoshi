# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal

Hoshi is a Python CLI for astrological charting, with a focus on real-sky astrology. Real-sky charts use IAU constellation boundaries (13 signs of unequal width, including Ophiuchus) rather than the traditional 12-sign tropical wheel — this makes charting significantly harder to do by hand, which is where Hoshi helps. Planetary positions come from [Skyfield](https://rhodesmill.org/skyfield/) (JPL ephemerides) for accuracy.

## Repo contents

- `main.py` / `pyproject.toml` / `.python-version` — `uv init` skeleton. Python 3.13+.
- `hoshi/` — Python package. Exposed as the `hoshi` console script via `[project.scripts]`; build backend is `hatchling`. After dependency changes, run `uv sync` to reinstall.
- `charts/` — user-saved charts (one JSON file per chart). Names are normalized to lowercase on save. Not a cache — treat as user data. Persists only inputs; charts are recomputed on `hoshi chart show`.
- `~/.cache/hoshi/chiron.json` — per-minute cache of Horizons OBSERVER responses for Chiron. Safe to delete.
- `~/.cache/hoshi/lunar.json` — per-minute cache of Horizons ELEMENTS responses for the Moon (true nodes and true Lilith). Safe to delete.

## Package modules (`hoshi/`)

| Module | Purpose |
|--------|---------|
| `ephemeris.py` | Skyfield positions, Horizons HTTP fetch, JSON cache helpers, `ecliptic_precession()` |
| `zodiac.py` | IAU real-sky boundaries, tropical and sidereal placements, `Placement.realsky(lon, precession)` |
| `houses.py` | Placidus, Porphyry, Equal, Arc-13 house cusps; angle computation |
| `points.py` | True lunar nodes, Black Moon Lilith, Hermetic lots |
| `chart.py` | `Chart.build()` — assembles all bodies; `Placed.for_longitude(lon, ayanamsa, precession)` |
| `aspects.py` | Aspect definitions and orbs; `compute_aspects()`, `compute_inter_aspects()` |
| `dignities.py` | Planetary dignities table, element/modality tally |
| `store.py` | Save/load/list/delete named charts in `./charts/` |
| `cli.py` | Typer entry point — all `hoshi chart` subcommands |

## CLI commands

```
hoshi chart add      NAME DATE [TIME] [--lat] [--lon] [--tz] [--mode] [--houses] [--details] [--aspects] [--group-by] [--cusps] [--force]
hoshi chart show     NAME|DATE [TIME] [--lat --lon] ...   [--format table|json] [--compare-houses]
hoshi chart cusps    NAME|DATE [TIME] [--lat --lon] ...   [--mode] [--houses]
hoshi chart transits NAME [DATE [TIME]]                   [--tz] [--mode] [--houses] [--details] [--aspects] [--natal]
hoshi chart compare  NAME1 NAME2                          [--mode] [--houses] [--aspects] [--details]
hoshi chart list
hoshi chart delete   NAME [--yes]
```

## Optional birth data and uncertainty

`ChartInput` stores `time`, `lat`, and `lon` as `str | None` and `float | None` respectively — all three are optional. Store whatever is known; omit the rest.

When displaying a chart with missing data:
- **Time unknown** — noon UTC is used for computation; all planet sign/degree/lon cells render in **yellow** as a warning; `⚠` note is printed above the table. Moon sign is particularly uncertain (moves ~13°/day).
- **Location unknown** — angles (ASC/MC/etc.), house numbers, and Hermetic lots are **suppressed entirely**; `⚠` note is printed.
- **Both unknown** — both sets of rules apply.

`ChartInput` properties `time_known` and `location_known` drive all suppression logic in `cli.py`. `--compare-houses` and `chart cusps` require both to be known and error if not.

## Three zodiac modes

- `'realsky'` — IAU real-sky boundaries (13 signs incl. Ophiuchus, unequal widths). Default. See `IAU[]` in `hoshi/zodiac.py`.
- `'tropical'` — standard 12 equal 30° signs from the vernal equinox.
- `'vedic'` — sidereal, Lahiri ayanamsa offset applied.

## Reference frame: of-date, not J2000

All ecliptic longitudes are in the **equinox of date** frame (measured from
the vernal equinox at the chart moment), matching standard astrological
convention. This requires explicit `epoch=t` in Skyfield calls —
**`ecliptic_latlon()` default returns J2000**, contrary to what the Skyfield
docs suggest. The two differ by precession (~50.3″/year).

The IAU constellation table is J2000-fixed. `Placement.realsky()` accepts a
`precession` argument (degrees since J2000 from `ecliptic_precession(when)`)
to shift the boundaries into the of-date frame before the sign lookup.
`Placed.for_longitude()` threads this through automatically when built via
`Chart.build()`.

## Horizons-backed bodies

Skyfield/jplephem can't read JPL Horizons' small-body SPKs (SPK data type 21
is unsupported). Two bodies use Horizons HTTP APIs directly:

- **Chiron** (`_chiron_position` in `hoshi/ephemeris.py`) — Horizons
  **OBSERVER** ephemeris at chart time + 1 minute for ecliptic lon/lat and
  retrograde state.
- **True lunar nodes & Black Moon Lilith** (`lunar_elements` in
  `hoshi/points.py`) — Horizons **ELEMENTS** API at chart time, parses
  OM (ascending node) and W (argument of perigee) for the Moon. True Lilith
  = OM + W + 180°.

Shared HTTP/SSL/cache helpers (`horizons_fetch`, `json_cache_get/put`) live
in `hoshi/ephemeris.py`. The SSL context uses `certifi` because macOS
stdlib `urllib` ships with an incomplete root bundle.

## Aspects

Five major aspects (4° orb), four minor (2° orb), three micro (1° orb). See
`hoshi/aspects.py`. Single-chart aspects via `compute_aspects(chart, details)`;
synastry inter-aspects via `compute_inter_aspects(chart_a, chart_b, details)`.
Without `--details`, only planets + Asc are included. Axis pairs (Asc/Dsc,
MC/IC, etc.) are filtered from single-chart aspects.

## Dignities

`hoshi/dignities.py` holds the domicile/exaltation/detriment/fall table for
the 13-sign real-sky scheme (Chiron domicile = Ophiuchus). Assignments follow
standard conventions adapted for 13 signs.
`element_modality_tally()` returns separate primary (planets) and total (all
bodies) counts.

## Conventions

- Use `uv` for dependency and run management (`uv add`, `uv run`).
- No tests or linter configured yet.
