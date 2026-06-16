# Hoshi

A CLI for astrological charting, with a focus on real-sky astrology. Inspired by [Nuastro](https://nuastro.com).

Traditional astrology divides the sky into 12 equal 30° signs. Real-sky astrology uses the actual IAU constellation boundaries — 13 unequal signs along the ecliptic, including Ophiuchus — which makes charting by hand significantly more difficult. Hoshi handles the calculation, using JPL-grade ephemerides ([Skyfield](https://rhodesmill.org/skyfield/) DE421 for planets, JPL Horizons for Chiron and the lunar nodes).

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv tool install --editable .     # puts `hoshi` on your PATH (~/.local/bin/hoshi)
```

`--editable` means source changes take effect immediately. If you change `pyproject.toml` dependencies, re-run with `--reinstall`. To remove: `uv tool uninstall hoshi`.

On first run, Skyfield downloads `de421.bsp` (~17 MB) into the current directory. Chiron and lunar (node/Lilith) lookups hit JPL Horizons and are cached in `~/.cache/hoshi/`.

## Commands

```sh
hoshi chart add      NAME DATE [TIME] [--lat LAT] [--lon LON] [--tz TZ] [--mode MODE] [--houses SYS]
                                      [--details] [--aspects] [--group-by category|sign|house]
                                      [--cusps] [--force]
hoshi chart show     NAME|DATE [TIME] [--lat LAT --lon LON] ...
                                      [--format table|json] [--compare-houses]
hoshi chart cusps    NAME|DATE [TIME] [--lat LAT --lon LON] ... [--mode MODE] [--houses SYS]
hoshi chart transits NAME [DATE [TIME]] [--tz TZ] [--mode MODE] [--houses SYS]
                                        [--details] [--aspects] [--natal]
hoshi chart compare  NAME1 NAME2        [--mode MODE] [--houses SYS] [--aspects] [--details]
hoshi chart list
hoshi chart delete   NAME [--yes]
```

`NAME|DATE` — pass a saved chart name, or a `YYYY-MM-DD` date with `--lat`/`--lon` for a one-off chart.

`--lat` and `--lon` are optional for `chart add` — omit either or both if the birth location is unknown. If time is also omitted, only the date is stored. Placements computed from unknown inputs are shown in yellow with a warning; angles and houses are omitted entirely when time or location is unknown.

## Options

### `--mode`

| Mode | Description |
|------|-------------|
| `realsky` (default) | IAU real-sky boundaries — 13 unequal signs including Ophiuchus |
| `tropical` | Standard 12 equal 30° signs from the vernal equinox |
| `vedic` | Sidereal: tropical longitudes minus the Lahiri ayanamsa |

### `--houses`

| System | Description |
|--------|-------------|
| `porphyry` (default) | Trisects the quadrants |
| `equal` | Equal 30° houses from the Ascendant |
| `placidus` | Time-based Placidus division |
| `arc13` | 13-arc wheel with widths matching the IAU constellation boundaries |

### `--details`

Expands the display to include all six angles (Asc, MC, IC, Dsc, Vertex, Antivertex), true lunar nodes, Black Moon Lilith, seven Hermetic lots, planetary dignities, and element/modality tallies.

### `--aspects`

Prints aspect tables grouped by type (Major / Minor / Micro). Without `--details`, aspects are computed for planets + Ascendant only; with `--details`, all chart bodies are included.

### `--group-by sign|house`

Alternative layout grouping bodies by zodiac sign or house instead of category. `--group-by house` labels each house with its cusp sign and includes empty houses.

### `--format json`

Outputs a mode-specific JSON summary instead of the Rich table. Includes body placements, house assignments, and cusp longitudes. Useful for scripting or piping into other tools. When time or location is unknown, the JSON includes a `"warnings"` array and an `"approximate": true` flag on affected body entries.

## Bodies

### Planets
Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto, Chiron

### Angles
Ascendant, Midheaven (MC), Imum Coeli (IC), Descendant, Vertex, Antivertex

### Calculated points
- **N.Node / S.Node** — True (osculating) lunar nodes from JPL Horizons
- **Lilith** — True Black Moon Lilith: ascending node + argument of perigee + 180°

### Hermetic lots
Fortune, Spirit, Eros, Necessity, Courage, Victory, Nemesis

## Aspects

| Class | Aspects | Orb |
|-------|---------|-----|
| Major | Conjunction (0°), Opposition (180°), Trine (120°), Square (90°), Sextile (60°) | 4° |
| Minor | Inconjunct (150°), Semi-sextile (30°), Semi-square (45°), Sesquiquadrate (135°) | 2° |
| Micro | Quintile (72°), Bi-quintile (144°), Septile (360°/7) | 1° |

## Dignities

The Planets table in `--details` shows a dignity indicator per planet:

| Symbol | Dignity |
|--------|---------|
| ⊕ | Domicile |
| △ | Exaltation |
| ▽ | Detriment |
| ✕ | Fall |

Assignments follow standard conventions adapted for the 13-sign real-sky scheme (Chiron domicile = Ophiuchus).

## Transits

```sh
hoshi chart transits person               # current moment vs natal
hoshi chart transits person 2026-01-01    # specific date (noon UTC)
hoshi chart transits person 2026-01-01 14:30 --tz America/Chicago
hoshi chart transits person --natal       # side-by-side natal vs transit table
hoshi chart transits person --aspects     # inter-aspects (natal × transit)
```

Computes current (or specified date) planetary positions and places them against the saved natal chart. The house column (`H`) always shows which **natal house** each transiting planet falls in, using the natal chart's cusps.

`--natal` adds a side-by-side table showing each body's natal sign/degree alongside its current transit sign/degree. `--details` and `--aspects` work the same as in other commands.

## Synastry

```sh
hoshi chart compare person1 person2 --aspects
hoshi chart compare person1 person2 --aspects --details
```

Computes inter-aspects between two saved charts. Body selection respects `--details` the same way single-chart aspects do.

## Accuracy notes

### Reference frame

All ecliptic longitudes are in the **equinox of date** frame, matching standard astrological convention. Skyfield's `ecliptic_latlon()` defaults to J2000, so `epoch=t` is passed explicitly. The IAU constellation boundaries are J2000-fixed; Hoshi applies the precession offset at lookup time so sign assignments stay consistent with the of-date planet positions.

### Per-body accuracy

- **Planets**: Skyfield + JPL DE421 — sub-arcsecond
- **Chiron**: Horizons OBSERVER ephemeris, cached per minute
- **Nodes / Lilith**: Horizons ELEMENTS API (Moon osculating elements), cached per minute
- **Angles / cusps**: standard formulas with a linear obliquity model — accurate to under 1′ for 20th–21st century dates
- **Lahiri ayanamsa**: linear approximation anchored at J2000 — adequate for chart display

## Project layout

```
hoshi/
  ephemeris.py   Skyfield positions, Horizons fetch, JSON cache helpers
  zodiac.py      IAU real-sky boundaries, tropical and sidereal placements
  houses.py      Placidus, Porphyry, Equal, Arc-13 cusps; angles
  points.py      True lunar nodes, Black Moon Lilith, Hermetic lots
  chart.py       Chart.build() — assembles all bodies
  aspects.py     Aspect detection (single-chart and inter-chart)
  dignities.py   Dignities table, element/modality tallies
  store.py       JSON persistence for named charts (./charts/)
  cli.py         Typer entry point
```
