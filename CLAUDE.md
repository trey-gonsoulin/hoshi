# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal

Hoshi is a Python CLI for astrological charting, with a focus on real-sky astrology. Real-sky charts use IAU constellation boundaries (13 signs of unequal width, including Ophiuchus) rather than the traditional 12-sign tropical wheel — this makes charting significantly harder to do by hand, which is where Hoshi helps. Planetary positions come from [Skyfield](https://rhodesmill.org/skyfield/) (JPL ephemerides) for accuracy.

## Repo contents

- `pyproject.toml` / `.python-version` — packaging and pinned interpreter. Requires Python 3.11+ (CI tests 3.11–3.13). The root `pyproject.toml` also configures a **uv workspace** (`[tool.uv.workspace]`) with members under `packages/`.
- `hoshi/` — core Python package. Exposed as the `hoshi` console script via `[project.scripts]`; build backend is `hatchling`. After dependency changes, run `uv sync` to reinstall.
- `packages/hoshi-api/` — FastAPI REST API package (workspace member). Depends on `hoshi` as a workspace dependency. Run with `uv run --package hoshi-api hoshi-api` (starts uvicorn on port 8000). Tests in `packages/hoshi-api/tests/`.
- `charts/` — user-saved charts (one JSON file per chart). Names are normalized to lowercase on save. Not a cache — treat as user data. Persists only inputs; charts are recomputed on `hoshi chart show`.
- `~/.cache/hoshi/chiron.json` — per-minute cache of Horizons OBSERVER responses for Chiron. Safe to delete.
- `~/.cache/hoshi/lunar.json` — per-minute cache of Horizons ELEMENTS responses for the Moon (true nodes and true Lilith). Safe to delete.

## Package modules (`hoshi/`)

| Module | Purpose |
|--------|---------|
| `ephemeris.py` | Skyfield positions (`positions(when, include_chiron=...)`), Horizons HTTP fetch (`HorizonsError` on failure), shared `timescale()`/`cache_dir()`, JSON cache helpers, `ecliptic_precession()` |
| `zodiac.py` | IAU real-sky boundaries, tropical/sidereal placements (`Placement.for_mode(lon, mode, ...)`), `ZodiacMode` enum, `TROP_SIGNS`/`SIGN_ATTRS` sign tables |
| `houses.py` | Placidus, Porphyry, Equal, Arc-13 house cusps; angle computation (shared `_ramc_obliquity`/`_mc_from_ramc`) |
| `points.py` | True lunar nodes, Black Moon Lilith, Hermetic lots |
| `chart.py` | `Chart.build()` / `Chart.from_input()` — assembles all bodies; `Chart.bodies()`/`Chart.body(id)` uniform `BodyRef` iteration; `uncertain_signs()`; `Placed.for_longitude(...)` and `Placed.placement(mode)`; `location_known`/`time_known` flags; `house` is `None` when location unknown |
| `aspects.py` | Aspect definitions and orbs; `compute_aspects()`, `compute_inter_aspects()` |
| `dignities.py` | Planetary dignities table, element/modality tally |
| `output.py` | Pydantic output models for every command (`ChartOutput`, `TransitsOutput`, etc.) with `.build()` classmethods that assemble models from SDK types. Shared by CLI and API. |
| `store.py` | Save/load/list/delete named charts in `./charts/` |
| `utils.py` | Shared utilities (`fuzzy_match`) used by both CLI and API |
| `adb.py` | Astro-Databank import via MediaWiki API; `adb_to_chart_input()` fetches + parses `ASTRODATABANK_dma` template into `ChartInput`; coordinate/time/timezone converters; `ADBError` on failure |
| `cli.py` | Typer entry point — all `hoshi chart` subcommands |

## Public SDK surface

Hoshi is usable as a library, not just a CLI. The top-level `hoshi` package
(`hoshi/__init__.py`) re-exports the stable domain types and functions with an
explicit `__all__`; **import from `hoshi`, not the submodules**, when consuming
Hoshi from another project. A `py.typed` marker ships so downstream
type-checkers see the annotations. See `docs/sdk.md` for a worked example.

Guidance when changing the package:
- New public constructs go in `__all__` (and ideally `docs/sdk.md`).
- Keep computation in the SDK layer (`chart.py`, `zodiac.py`, …); `cli.py`
  should only handle argument parsing and display. `Chart.from_input()`,
  `Chart.bodies()`, and `uncertain_signs()` exist so the CLI doesn't own domain
  logic — prefer extending these over adding logic to `cli.py`.
- `Chart.from_input(ChartInput)` substitutes placeholder coordinates for an
  unknown location and records `location_known` / `time_known` on the chart so
  consumers can drive their own suppression.
- Zodiac mode is the `ZodiacMode` StrEnum (in `zodiac.py`); functions accept it
  or its plain-string value interchangeably.

## CLI commands

```
hoshi chart add      NAME DATE [TIME] [--lat] [--lon] [--tz] [--mode] [--houses] [--details] [--aspects] [--group-by] [--cusps] [--force]
hoshi chart show     NAME|DATE [TIME] [--lat --lon] ...   [--format table|json] [--compare-houses]
hoshi chart cusps    NAME|DATE [TIME] [--lat --lon] ...   [--mode] [--houses]
hoshi chart transits NAME [DATE [TIME]]                   [--tz] [--mode] [--houses] [--details] [--aspects] [--natal] [--group-by]
hoshi chart compare  NAME1 NAME2                          [--mode] [--houses] [--aspects] [--details] [--group-by]
hoshi chart import   SOURCE [NAME]                        [--force] [--mode] [--houses] [--details] [--aspects] [--group-by] [--cusps] [--format]
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

`--group-by` controls grouping for both bodies and aspects: `category`
(default — bodies by kind, aspects by Major/Minor/Micro), `sign`, `house`,
or `planet` (aspects only).

## Dignities

`hoshi/dignities.py` holds the domicile/exaltation/detriment/fall table for
the 13-sign real-sky scheme (Chiron domicile = Ophiuchus). Assignments follow
standard conventions adapted for 13 signs.
`element_modality_tally()` returns separate primary (planets) and total (all
bodies) counts.

## REST API (`packages/hoshi-api/`)

A FastAPI application exposing the same chart functionality as the CLI via
JSON endpoints. It imports the `hoshi` SDK and uses the `.build()` classmethods
on the output models — the same models that back `--format json` in the CLI.

**Running:** `uv run --package hoshi-api hoshi-api` (starts on `0.0.0.0:8000`
with auto-reload). Interactive docs at `/docs`.

**Route overview:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/charts` | Save a new chart |
| `GET` | `/charts` | List saved charts |
| `POST` | `/charts/compute` | Compute a one-off chart (no save) |
| `POST` | `/charts/import` | Import from Astro-Databank |
| `GET` | `/charts/{name}` | Show a saved chart |
| `DELETE` | `/charts/{name}` | Delete a saved chart |
| `GET` | `/charts/{name}/cusps` | House cusps |
| `GET` | `/charts/{name}/transits` | Transits against natal |
| `GET` | `/charts/{name}/compare/{other}` | Synastry |
| `GET` | `/info/{category}` | List reference info |
| `GET` | `/info/{category}/{name}` | Single item detail |

All route handlers are synchronous (`def`, not `async def`) so uvicorn
dispatches them to a thread pool — blocking Horizons/Skyfield calls work
correctly without async wrappers.

**Testing:** `uv run --package hoshi-api pytest packages/hoshi-api/tests/`

## Conventions

- Use `uv` for dependency and run management (`uv add`, `uv run`).

## Commit message format

This repo uses [Conventional Commits](https://www.conventionalcommits.org/) for
`python-semantic-release` to automate versioning. Every commit message must
follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types** (only these trigger releases):
- `fix:` — bug fix → **patch** bump (0.0.x)
- `feat:` — new feature → **minor** bump (0.x.0)
- Append `!` after the type/scope (e.g. `feat!:`) or add a `BREAKING CHANGE:` footer → **major** bump (x.0.0)

**Types** (no release, but still use them):
- `chore:` — maintenance, dependency updates
- `docs:` — documentation only
- `refactor:` — code restructuring with no behavior change
- `test:` — adding or updating tests
- `ci:` — CI/CD changes
- `style:` — formatting, whitespace

**Scope** is optional and names the area of change, e.g. `feat(cli):`, `fix(ephemeris):`.

Keep the first line under 72 characters. Use the body for additional context
when the "why" isn't obvious from the summary line alone.

**Always ask for confirmation before creating a commit.** Show the proposed
commit message and list of staged files, then wait for approval.

## Code change checklist

Before considering any code change complete, verify all of the following:

1. **Lint and format** — run `uv run ruff check --fix .` and `uv run ruff format .` to fix lint issues and enforce consistent formatting.
2. **Tests are written** — new or changed functionality must have corresponding tests.
3. **All tests pass** — run the full test suite (`uv run pytest`) and confirm zero failures.
4. **Documentation is updated** — update this file (CLAUDE.md), CLI help text, and any other relevant docs to reflect the change.
