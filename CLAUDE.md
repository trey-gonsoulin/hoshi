# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal

Build a Python CLI that replicates parts of [Nuastro](https://nuastro.com)'s real-sky astrology birth chart calculator. Planetary positions come from the [Skyfield](https://rhodesmill.org/skyfield/) package (JPL ephemerides) rather than the browser-side ephemeris Nuastro uses.

## Repo contents

- `main.py` / `pyproject.toml` / `.python-version` — `uv init` skeleton. Python 3.13+. No dependencies declared yet; Skyfield needs to be added (`uv add skyfield`).
- `nuastro-*.js`, `smush-lazy-load.min.js` — **reference material only**, copied from Nuastro's WordPress widget. Read these to understand the algorithms and conventions to port; do not edit them.
- `nuastro/` — Python package with the port (`zodiac`, `ephemeris`, `houses`, `points`, `chart`, `store`, `cli`). Exposed as the `astro` console script via `[project.scripts]`; build backend is `hatchling`. After dependency changes, `uv sync` reinstalls the project in editable mode.
- `charts/` — user-saved charts (one JSON file per chart, written by `astro chart --name ...`). Not a cache — treat as user data. Persists only inputs; charts are recomputed on `astro show`.
- `.chiron_cache.json` — per-minute cache of Horizons OBSERVER responses for Chiron, written next to wherever the CLI is run. Safe to delete.
- `.lunar_cache.json` — per-minute cache of Horizons ELEMENTS responses for the Moon (used for true nodes and true Lilith). Safe to delete.

## Reference JS, in dependency order

1. `nuastro-calc.js` (`window.NuastroCalc`) — the math worth porting first: IAU constellation boundaries, tropical signs, sidereal conversion, aspects.
2. `nuastro-chart.js` / `nuastro-chart-north-indian.js` — SVG rendering. Not directly useful for a CLI unless we emit SVG/PNG output.
3. `nuastro-widget.js` — top-level WordPress glue. Source of truth for the planet registry, `ASPECT_ORB = 4`, and the `DIGNITIES` / `ELEMENTS` tables. These tables are tuned to the real-sky 13-sign scheme (e.g. Chiron domicile = Ophiuchus) — preserve them as-is when porting; they are not standard tropical assignments.

`nuastro-ephemeris.js` is referenced by the JS but not in the repo; Skyfield replaces it on the Python side.

## Three zodiac modes to support

Nuastro exposes three, and the port should too:

- `'nuastro'` — IAU real-sky boundaries (13 signs incl. Ophiuchus, unequal widths) — see `IAU[]` in `nuastro-calc.js`. This is the distinguishing feature.
- `'tropical'` — standard 12 equal 30° signs from the vernal equinox.
- `'vedic'` — sidereal, with an ayanamsa offset applied (check `nuastro-calc.js` for which one).

## Reference frame: of-date, not J2000

All ecliptic longitudes are in the **equinox of date** frame (measured from
the vernal equinox at the chart moment), matching tropical astrology and the
upstream Nuastro tool. This requires explicit `epoch=t` in Skyfield calls —
**`ecliptic_latlon()` default returns J2000**, contrary to what the Skyfield
docs suggest. The two differ by precession (~50.3″/year), so a chart 4 years
off J2000 lands ~3-4′ apart between the two frames. The IAU constellation
table in `nuastro/zodiac.py` is J2000-fixed; mixing it with of-date positions
is a minor inconsistency we accept to match upstream behavior.

## Pluto / Chiron disagreement with online Nuastro

Online Nuastro can be off from JPL Horizons by several degrees (~9° Pluto,
~22° Chiron observed on a 1996 chart) — apparently the online tool uses
stale or low-accuracy fallback ephemeris for bodies outside its main VSOP
polynomial set. Our local values come from Skyfield/DE421 (Pluto) and
Horizons OBSERVER (Chiron), which are authoritative. Don't "fix" the CLI
to match online for these two bodies.

## Horizons-backed bodies

Skyfield/jplephem can't read JPL Horizons' small-body SPKs (SPK data type 21
is unsupported). Two things use Horizons HTTP APIs directly:

- **Chiron** (`_chiron_position` in `nuastro/ephemeris.py`) — Horizons
  **OBSERVER** ephemeris at chart time + 1 minute for ecliptic lon/lat and
  retrograde state.
- **True lunar nodes & Black Moon Lilith** (`lunar_elements` in
  `nuastro/points.py`) — Horizons **ELEMENTS** API at chart time, parses
  OM (ascending node) and W (argument of perigee) for the Moon. True Lilith
  = OM + W + 180°.

Shared HTTP/SSL/cache helpers (`horizons_fetch`, `json_cache_get/put`) live
in `nuastro/ephemeris.py`. The SSL context uses `certifi` because macOS
stdlib `urllib` ships with an incomplete root bundle.

## Conventions

- Use `uv` for dependency and run management (`uv add`, `uv run`).
- No tests or linter configured yet.
