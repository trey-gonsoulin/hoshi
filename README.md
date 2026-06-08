# astro

A Python CLI that replicates [Nuastro](https://nuastro.com)'s real-sky
astrology birth chart calculator. Planetary positions come from
[Skyfield](https://rhodesmill.org/skyfield/) (JPL DE421); Chiron is pulled
on-demand from JPL Horizons.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync                          # install deps into ./.venv
uv tool install --editable .     # put `astro` on your PATH (~/.local/bin/astro)
```

After `uv tool install`, you can drop the `uv run` prefix and just invoke
`astro` directly. Edits to the source take effect immediately because of
`--editable`. If you change `pyproject.toml`, re-run with `--reinstall` to
pick up the new dependencies. To remove: `uv tool uninstall astro`.

On first run, Skyfield will download `de421.bsp` (~17 MB) into the current
directory. Chiron and true lunar (node/lilith) lookups hit JPL Horizons and
are cached in `.chiron_cache.json` and `.lunar_cache.json` respectively
(also in the cwd).

## Usage

All chart operations live under the `chart` command group:

```sh
astro chart add NAME DATE [TIME] --lat LAT --lng LNG [--tz TZ] [--mode MODE] [--force] [--cusps]
astro chart list                                                          # list all saved charts
astro chart show NAME [--mode M] [--cusps]                                # show a saved chart
astro chart show DATE [TIME] --lat LAT --lng LNG [--tz] [--mode] [--cusps] # one-off chart
astro chart delete NAME [--yes]                                           # delete a saved chart
```

### `astro chart add` — save a named chart

| Argument / option | Description | Default |
|---|---|---|
| `NAME` | Name to save this chart under | required |
| `DATE` | Birth date, `YYYY-MM-DD` | required |
| `TIME` | Birth time, `HH:MM` (24-hour) | `12:00` |
| `--lat` | Birth latitude, degrees, north positive | required |
| `--lng` | Birth longitude, degrees, **east positive** (US is negative) | required |
| `--tz` | IANA timezone of the birth time (e.g. `America/Chicago`) | `UTC` |
| `--mode` | Zodiac mode: `nuastro` / `tropical` / `vedic` | `nuastro` |
| `--force` | Overwrite an existing saved chart of the same name | `false` |
| `--cusps` | Also print the 12 Placidus house cusps | `false` |

### `astro chart show` — print a chart

Accepts either a saved chart name **or** birth parameters for a one-off
chart. If you pass `--lat`/`--lng`, the first positional is treated as a
birth date (one-off mode); otherwise it's treated as a saved name.

Charts are saved as JSON files in `./charts/<safe_name>.json`. Only the
input parameters are persisted; the chart is recomputed on read (fast,
since Horizons responses are cached separately).

### Zodiac modes

- **`nuastro`** — Real-sky IAU constellation boundaries. 13 unequal signs
  including Ophiuchus. Houses use Nuastro's 13-arc wheel anchored at the
  Ascendant, with arc widths matching the IAU constellation widths.
- **`tropical`** — Standard Western astrology: 12 equal 30° signs from the
  vernal equinox. Houses use standard Placidus assignment.
- **`vedic`** — Sidereal: tropical longitudes minus an approximate Lahiri
  ayanamsa. Houses use standard Placidus assignment.

### Example

Chicago birth, June 15 1990 at 2:30 PM CDT:

```sh
astro chart show 1990-06-15 14:30 \
  --tz America/Chicago --lat 41.8781 --lng -87.6298
```

Output includes three sections by default — Angles, Planets, and Points
(Placidus cusps are hidden unless you pass `--cusps`):

```
Chart for 1990-06-15T14:30:00-05:00  (41.8781°, -87.6298°)  mode: nuastro

Angles
  ASC        Virgo         20°34'    194.65°
  MC         Gemini        16°46'    107.24°
  IC         Sagittarius   20°41'    287.24°
  DSC        Pisces        22°59'     14.65°
  VERTEX     Capricorn     23°00'    323.02°
  ANTIVERTEX Cancer        23°00'    143.02°

Planets
  Planet     Sign          Degree        Lon  Rx  H13
  sun        Taurus        31°09'     84.56°       10
  moon       Aquarius      22°04'    349.68°        6
  ...

Points
  N.Node     Aquarius      09°40'    309.68°       4
  S.Node     Leo           09°40'    129.68°      10
  Lilith     Scorpio       24°55'    234.92°       1
  Fortune    Cancer        09°45'     99.77°       9
```

### Calculated points

- **N.Node / S.Node** — True (osculating) lunar nodes, fetched from JPL
  Horizons (Moon orbital elements, ecliptic J2000). The South Node is
  always exactly opposite the North Node.
- **Lilith** — True (osculating) Black Moon Lilith: ascending node + argument
  of perigee + 180°, giving the apogee direction. Also from Horizons.
- **Fortune** — Part of Fortune (Lot of Fortune). Uses the day formula
  `ASC + Moon − Sun` when the Sun is above the horizon, otherwise the
  night formula `ASC + Sun − Moon`. Above-horizon is detected by Sun's
  house position (houses 7–12).

### Angles

- **ASC / MC / IC / DSC** — Standard chart angles.
- **VERTEX / ANTIVERTEX** — The ecliptic intersection of the prime
  vertical (the great circle through the zenith and east/west horizon
  points). Vertex is always placed in the western hemisphere of the chart
  (houses 5–8); Antivertex is its opposite.

The house column is labeled `H13` in `nuastro` mode (13-arc wheel) and `H`
in `tropical` / `vedic` modes (Placidus). Planets and the Placidus cusp
list are shown in whichever zodiac mode you selected; in `nuastro` mode,
degrees-in-sign can exceed 30° because the real-sky constellations are
unequal (real-sky Leo is 35.89° wide, for example).

## Accuracy notes

### Reference frame

All ecliptic longitudes are reported in the **equinox of date** ("of-date")
frame — measured from the vernal equinox at the moment of the chart. This
matches the convention used by Western tropical astrology and by the
online Nuastro tool.

Skyfield's `ecliptic_latlon()` default actually returns **J2000** ecliptic
(the equinox frozen at noon UT, 2000-01-01), so we pass `epoch=t`
explicitly to get of-date. The two frames differ by the precession of the
equinoxes (~50.3″/year), or roughly 1° per 72 years away from J2000.

The Nuastro real-sky IAU constellation boundaries are themselves *fixed at
J2000* (see the `IAU` table in `nuastro/zodiac.py`). Placing of-date
planet positions against J2000-frozen boundaries is technically a small
inconsistency, but the drift is only a few arcminutes for any chart in
the 20th–21st century — invisible in practice and consistent with how the
upstream Nuastro tool behaves.

### Per-body notes

- Planet positions: Skyfield + JPL DE421 — sub-arcsecond.
- Chiron: Horizons OBSERVER ephemeris at the chart minute. Skyfield can't
  read Horizons' small-body SPK files (data type 21 is unsupported by
  `jplephem`), so the CLI queries Horizons directly and caches results.
- True lunar nodes & Lilith: Horizons ELEMENTS API at the chart minute,
  using the Moon's osculating geocentric ecliptic J2000 orbital elements
  (ascending node OM and argument of perigee W).
- Angles + Placidus cusps: standard formulas using a simple linear model
  for the obliquity of the ecliptic. Accurate to under an arcminute for
  20th–21st century dates.
- Lahiri ayanamsa: linear approximation anchored at J2000. Off by a few
  arcminutes from the official value — fine for chart display, not for
  ephemeris-grade work.

### Disagreement with online Nuastro

For most charts, this CLI matches the online Nuastro tool to within ~1
arcminute. **Two known exceptions** at the time of writing: the online
tool's **Pluto** and **Chiron** values can disagree by several degrees
(observed: ~9° for Pluto, ~22° for Chiron on a 1996 chart). The local
values match JPL Horizons — the authoritative ephemeris NASA itself uses
— so when these conflict, trust the CLI output. The likely cause is that
the online tool falls back to stale or low-accuracy approximations for
bodies outside its built-in VSOP-style polynomial set for the eight main
planets.

## Project layout

- `nuastro/zodiac.py` — IAU table and sign placement for the three modes.
- `nuastro/ephemeris.py` — Skyfield planet positions; Horizons fetcher for
  Chiron.
- `nuastro/houses.py` — Angles, Placidus cusps, and house assignment.
- `nuastro/points.py` — Lunar nodes, Black Moon Lilith, Part of Fortune.
- `nuastro/store.py` — JSON-on-disk persistence for named charts.
- `nuastro/chart.py` — Composes the above into a single `Chart`.
- `nuastro/cli.py` — Typer CLI. Exposed as the `astro` console script
  (see `[project.scripts]` in `pyproject.toml`).
- `nuastro-*.js` — Original Nuastro WordPress widget, kept as reference.
