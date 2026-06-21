# Using Hoshi as a library

Hoshi's chart engine is importable from other Python projects. Everything you
need is re-exported from the top-level `hoshi` package — import from there
rather than reaching into submodules, which are not a stable interface.

```bash
pip install hoshi   # or: uv add hoshi
```

The package ships a `py.typed` marker, so your type-checker sees Hoshi's
annotations.

## Compute a chart in a few lines

```python
from hoshi import Chart, ChartInput, ZodiacMode, compute_aspects

ci = ChartInput(
    name="example",
    date="1990-07-04",
    time="13:00",
    tz="Europe/London",
    lat=51.5074,
    lon=-0.1278,
)
# Note: planetary positions come from the DE421 ephemeris, which covers
# roughly 1900–2050.

chart = Chart.from_input(ci)            # porphyry by default; pass house_system=...

for body in chart.bodies():             # planets, angles, nodes, points, lots
    place = body.placed.placement(ZodiacMode.realsky)
    print(f"{body.label:10} {place.name} {place.deg:5.2f}°  house {body.house}")

for asp in compute_aspects(chart):
    print(asp.body_a, asp.symbol, asp.body_b, f"orb {asp.orb:+.2f}")
```

`Chart.from_input` is the recommended entry point because it handles incomplete
birth data. `Chart.build(when, lat, lon, house_system=...)` is the lower-level
constructor when you already have a timezone-aware `datetime` and real
coordinates.

## Incomplete birth data

`ChartInput` accepts an unknown time and/or location (`time`, `lat`, `lon` are
optional). When location is unknown, `Chart.from_input` substitutes placeholder
coordinates so computation still succeeds and records the gaps on the chart:

```python
ci = ChartInput(name="unknown", date="1990-07-04")   # no time, no location
chart = Chart.from_input(ci)

assert chart.time_known is False
assert chart.location_known is False
```

Use these flags to decide what to trust — angles, houses, and Hermetic lots are
only meaningful when `location_known`, and signs/degrees are uncertain when
`time_known` is False. To find which fast-moving planets actually change sign
across an unknown-time birth date:

```python
from hoshi import uncertain_signs, ZodiacMode

pids = uncertain_signs(ci, ZodiacMode.realsky)   # e.g. frozenset({"moon"})
```

## Iterating bodies

`Chart.bodies()` yields a uniform `BodyRef` for every placed point so you don't
have to walk `chart.planets`, `chart.angles`, `chart.points`, and `chart.lots`
separately:

| field        | meaning                                            |
|--------------|----------------------------------------------------|
| `id`         | stable key — planet pid (`"sun"`) or point name    |
| `label`      | display label (`"Sun"`, `"Asc"`, `"N.Node"`)       |
| `kind`       | `Planet` / `Angle` / `Node` / `Point` / `Lot`      |
| `placed`     | `Placed` — call `.placement(mode)` for sign/degree |
| `house`      | house number, or `None` when location unknown      |
| `retrograde` | `bool` for planets, `None` otherwise               |

`chart.body("sun")` looks one up by id (raises `KeyError` if absent).

## Zodiac modes

`ZodiacMode` is a `StrEnum` with `realsky` (default, 13 IAU signs), `tropical`,
and `vedic`. Functions accept the enum or its string value interchangeably:

```python
chart.body("sun").placed.placement("tropical")        # str
chart.body("sun").placed.placement(ZodiacMode.vedic)  # enum
```

## Other useful exports

- `positions(when, include_chiron=...)` — raw geocentric ecliptic positions.
- `Placement.for_mode(lon, mode, ayanamsa=..., precession=...)` — place a bare
  longitude without building a full chart.
- `compute_inter_aspects(chart_a, chart_b)` — synastry between two charts.
- `element_modality_tally(chart, mode)` and `dignity_for(planet, sign)`.
- `HorizonsError` — raised when a JPL Horizons request (Chiron, lunar nodes,
  Lilith) fails; catch it to handle network errors.

See `hoshi.__all__` for the complete list.
