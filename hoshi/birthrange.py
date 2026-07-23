"""Birth date range estimation from known planetary sign placements.

Given a set of (planet, sign) constraints and a search window, scans the
ephemeris and returns contiguous date ranges where all constraints are
satisfied simultaneously.

Algorithm
---------
Two-stage scan:

1. Coarse prefilter (when the constraint set spans >1 speed tier):
   Sort constraints slowest-to-fastest. Scan only the slowest constraint at
   its natural (large) step to find candidate sub-windows. Pad each result
   by one coarse step on both sides so no true window is missed at ingress /
   egress edges.

2. Vectorized fine scan inside each candidate sub-window:
   Build a time grid, batch-compute each required planet's longitudes with
   a single Skyfield numpy call (no retrograde sampling), then run numpy
   array ops to find timestamps where every constraint is satisfied. Group
   contiguous matching timestamps into BirthDateRange results.

Retrograde is handled implicitly: a planet re-entering a sign creates a new
contiguous run and therefore a new window.

Limitations
-----------
- Only the 10 Skyfield-backed planets are supported (Chiron, Ceres, Eris,
  and the lunar nodes require Horizons HTTP round-trips).
- The search window is clipped to DE421 coverage (1900-01-01 – 2050-12-31).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

import numpy as np

from hoshi.ephemeris import PLANET_ORDER, batch_ecliptic_lons, timescale
from hoshi.store import BirthWindow
from hoshi.zodiac import IAU, TROP_SIGNS, ZodiacMode

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HORIZONS_BODIES = frozenset({"chiron", "ceres", "eris"})

SCANNABLE_PLANETS: frozenset[str] = frozenset(
    pid for pid in PLANET_ORDER if pid not in _HORIZONS_BODIES
)

# Angle bodies require lat/lon and use a fixed fine step (see _step_hours).
SCANNABLE_ANGLES: frozenset[str] = frozenset({"asc", "mc", "ic", "dsc"})

_MEAN_DAILY_MOTION: dict[str, float] = {
    "sun": 0.9856,
    "moon": 13.176,
    "mercury": 1.383,
    "venus": 1.200,
    "mars": 0.524,
    "jupiter": 0.083,
    "saturn": 0.033,
    "uranus": 0.011,
    "neptune": 0.007,
    "pluto": 0.004,
    # Angles rotate at ~360°/day (1 sidereal day). Used for cascade ordering
    # only — step sizing always uses the fixed _ANGLE_STEP_HOURS instead.
    "asc": 360.0,
    "mc": 360.0,
    "ic": 360.0,
    "dsc": 360.0,
}

# Fixed 1-minute step for angle constraints: ASC traverses realsky Scorpio
# (~6.71°) in ~27 min at mean rate; 1 min gives ~27 samples — enough margin.
_ANGLE_STEP_HOURS: float = 1.0 / 60.0

# Maximum search span when any angle constraint is present (memory guard).
_ANGLE_SPAN_MAX_DAYS: int = 5 * 365

DE421_START = datetime(1900, 1, 1, tzinfo=timezone.utc)
DE421_END = datetime(2050, 12, 31, tzinfo=timezone.utc)

# J2000 IAU lower-boundary array, used by the vectorized sign lookup.
_IAU_LO = np.array([s.lo for s in IAU])  # [29.00, 53.41, ..., 351.65]

# Sampling step and cap used by placement_proportions().
_PROPORTION_STEP = timedelta(minutes=30)
_PROPORTION_MAX_SAMPLES: int = 2000

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class Constraint(NamedTuple):
    """A (planet, sign) pair that must hold simultaneously."""

    planet: str  # planet id, e.g. "sun"
    sign: str  # canonical sign name, e.g. "Aries"


class BirthDateRange(NamedTuple):
    """A contiguous window where all constraints are satisfied."""

    start: datetime
    end: datetime

    @property
    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0


class PlacementFraction(NamedTuple):
    """A (sign, fraction) pair from placement_proportions()."""

    sign: str
    fraction: float  # 0.0–1.0; fractions for one body sum to ~1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def valid_signs(mode: ZodiacMode | str) -> dict[str, str]:
    """Canonical sign name → name mapping for the given mode (for fuzzy-matching)."""
    if mode == ZodiacMode.realsky:
        return {s.name: s.name for s in IAU}
    return {s.name: s.name for s in TROP_SIGNS}


def valid_planets() -> dict[str, str]:
    """Planet/angle id → id mapping for fuzzy-matching."""
    return {pid: pid for pid in SCANNABLE_PLANETS | SCANNABLE_ANGLES}


def _min_sign_width(mode: ZodiacMode | str) -> float:
    if mode == ZodiacMode.realsky:
        widths = []
        for s in IAU:
            w = s.hi - s.lo
            if w < 0:
                w += 360.0
            widths.append(w)
        return min(widths)
    return 30.0


def _step_hours(bodies: list[str], mode: ZodiacMode | str) -> float:
    """Sampling step in hours.

    Returns a fixed 1-minute step when any angle body (asc/mc/ic/dsc) is
    present — mean-rate sizing is unsafe for angles whose real traversal time
    varies 2–3× by latitude.  For planet-only sets, targets ~10 samples across
    the narrowest sign, clamped to [1h, 168h].
    """
    if any(b in SCANNABLE_ANGLES for b in bodies):
        return _ANGLE_STEP_HOURS
    max_daily = max(_MEAN_DAILY_MOTION[p] for p in bodies)
    min_width = _min_sign_width(mode)
    raw = min_width / max_daily / 10.0 * 24.0
    return max(1.0, min(168.0, raw))


# ---------------------------------------------------------------------------
# Vectorized sign-index helpers
# ---------------------------------------------------------------------------


def _sign_index_realsky(lons: np.ndarray, precessions: np.ndarray) -> np.ndarray:
    """Return IAU sign index (0–12) for each (longitude, precession) pair.

    Subtracts precession from the of-date longitude to shift into the J2000
    frame, then binary-searches the fixed IAU boundary table. Pisces wraps
    past 360°; lons below Aries' lower boundary (29°) are classified as Pisces.
    """
    adjusted = (lons - precessions) % 360.0
    indices = np.searchsorted(_IAU_LO, adjusted, side="right") - 1
    # Adjusted longitudes < IAU[0].lo (29°) wrap into Pisces (index 12).
    indices = np.where(adjusted < _IAU_LO[0], len(IAU) - 1, indices)
    return indices


def _sign_index_tropical(lons: np.ndarray) -> np.ndarray:
    return ((lons % 360.0) / 30.0).astype(int)


def _sign_index_vedic(lons: np.ndarray, ayanamsas: np.ndarray) -> np.ndarray:
    return (((lons - ayanamsas) % 360.0) / 30.0).astype(int)


def _sign_index_for_name(sign_name: str, mode: ZodiacMode) -> int:
    if mode == ZodiacMode.realsky:
        return next(i for i, s in enumerate(IAU) if s.name == sign_name)
    return next(i for i, s in enumerate(TROP_SIGNS) if s.name == sign_name)


def _precessions_for_times(t_arr) -> np.ndarray:
    years = (np.asarray(t_arr.tt) - 2451545.0) / 365.25
    return years * (50.29 / 3600.0)


def _ayanamsas_for_times(t_arr) -> np.ndarray:
    years = (np.asarray(t_arr.tt) - 2451545.0) / 365.25
    return 23.85 + years * (50.29 / 3600.0)


# ---------------------------------------------------------------------------
# Core vectorized scan
# ---------------------------------------------------------------------------


def _vectorized_scan(
    constraints: list[Constraint],
    sub_start: datetime,
    sub_end: datetime,
    mode: ZodiacMode,
    step: timedelta,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> list[BirthDateRange]:
    """Vectorized scan of [sub_start, sub_end].

    Builds a time grid, batch-computes body longitudes via Skyfield's array
    API (and the vectorized GMST formula for angle bodies), converts to sign
    indices with numpy ops, then finds runs of True in the combined constraint
    mask. Returns BirthDateRange windows.
    """
    # Build the time grid as a list of UTC datetimes
    times: list[datetime] = []
    t = sub_start
    while t <= sub_end:
        times.append(t)
        t += step
    if not times:
        return []

    ts = timescale()
    t_arr = ts.from_datetimes(times)

    # Precompute mode-specific ancillary arrays once
    prec: np.ndarray | None = (
        _precessions_for_times(t_arr) if mode == ZodiacMode.realsky else None
    )
    ayan: np.ndarray | None = (
        _ayanamsas_for_times(t_arr) if mode == ZodiacMode.vedic else None
    )

    # Batch-compute all angle longitudes at once (one GMST pass for all four).
    has_angles = any(c.planet in SCANNABLE_ANGLES for c in constraints)
    angle_lons_map: dict[str, np.ndarray] = {}  # type: ignore[type-arg]
    if has_angles:
        from hoshi.houses import batch_angle_lons

        assert lat is not None and lon is not None
        angle_lons_map = batch_angle_lons(times, lat, lon)

    # Build the per-body constraint mask; AND them together
    combined = np.ones(len(times), dtype=bool)
    for c in constraints:
        if c.planet in SCANNABLE_ANGLES:
            lons = angle_lons_map[c.planet]
        else:
            lons = batch_ecliptic_lons(c.planet, times)
        if mode == ZodiacMode.realsky:
            assert prec is not None
            idx = _sign_index_realsky(lons, prec)
        elif mode == ZodiacMode.vedic:
            assert ayan is not None
            idx = _sign_index_vedic(lons, ayan)
        else:
            idx = _sign_index_tropical(lons)
        expected = _sign_index_for_name(c.sign, mode)
        combined &= idx == expected

    # Find contiguous True runs using diff on a padded array
    padded = np.empty(len(combined) + 2, dtype=bool)
    padded[0] = False
    padded[1:-1] = combined
    padded[-1] = False
    diff = np.diff(padded.view(np.int8))
    run_starts = np.where(diff == 1)[0]
    run_ends = np.where(diff == -1)[0]  # exclusive

    ranges: list[BirthDateRange] = []
    for s, e in zip(run_starts, run_ends):
        ranges.append(BirthDateRange(start=times[s], end=times[e - 1]))
    return ranges


# ---------------------------------------------------------------------------
# Placement proportions (for ranged/uncertain birth charts)
# ---------------------------------------------------------------------------


def placement_proportions(
    windows: list[BirthWindow],
    mode: ZodiacMode | str,
) -> dict[str, list[PlacementFraction]]:
    """Compute sign distribution for each planet across a set of birth windows.

    Samples each window at 30-minute intervals (up to _PROPORTION_MAX_SAMPLES
    total) and tallies which sign each planet occupies at each sample point.
    Returns a dict mapping planet pid → list of PlacementFraction, sorted by
    fraction descending.  Only SCANNABLE_PLANETS are included (Horizons-backed
    bodies are skipped).

    All windows are weighted equally per unit time: a 2-hour window contributes
    twice as many samples as a 1-hour window.

    Args:
        windows: Ordered list of BirthWindow intervals.
        mode: Zodiac mode for sign placement.

    Returns:
        Dict of pid → [PlacementFraction, ...] sorted by fraction descending.
        Each list sums to ~1.0.  Empty dict when windows is empty.
    """
    if not windows:
        return {}

    mode = ZodiacMode(mode)

    # Build sample datetimes: one sample every 30 min across every window.
    times: list[datetime] = []
    for w in windows:
        t = w.start
        while t <= w.end:
            times.append(t)
            t += _PROPORTION_STEP
        if not times or times[-1] < w.end:
            times.append(w.end)

    # Subsample evenly if over the cap.
    if len(times) > _PROPORTION_MAX_SAMPLES:
        indices = np.round(
            np.linspace(0, len(times) - 1, _PROPORTION_MAX_SAMPLES)
        ).astype(int)
        times = [times[int(i)] for i in indices]

    if not times:
        return {}

    ts = timescale()
    t_arr = ts.from_datetimes(times)

    prec: np.ndarray | None = (
        _precessions_for_times(t_arr) if mode == ZodiacMode.realsky else None
    )
    ayan: np.ndarray | None = (
        _ayanamsas_for_times(t_arr) if mode == ZodiacMode.vedic else None
    )

    sign_names = (
        [s.name for s in IAU]
        if mode == ZodiacMode.realsky
        else [s.name for s in TROP_SIGNS]
    )
    n_signs = len(sign_names)

    result: dict[str, list[PlacementFraction]] = {}
    for pid in SCANNABLE_PLANETS:
        lons = batch_ecliptic_lons(pid, times)
        if mode == ZodiacMode.realsky:
            assert prec is not None
            idx = _sign_index_realsky(lons, prec)
        elif mode == ZodiacMode.vedic:
            assert ayan is not None
            idx = _sign_index_vedic(lons, ayan)
        else:
            idx = _sign_index_tropical(lons)

        counts = np.bincount(idx, minlength=n_signs)
        total = counts.sum()
        fracs = [
            PlacementFraction(sign=sign_names[i], fraction=int(counts[i]) / int(total))
            for i in range(n_signs)
            if counts[i] > 0
        ]
        fracs.sort(key=lambda f: f.fraction, reverse=True)
        result[pid] = fracs

    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def find_birth_date_ranges(
    constraints: list[Constraint],
    search_start: datetime,
    search_end: datetime,
    mode: ZodiacMode | str = ZodiacMode.realsky,
    *,
    lat: float | None = None,
    lon: float | None = None,
) -> list[BirthDateRange]:
    """Scan [search_start, search_end] and return windows where all constraints hold.

    Uses a two-stage approach for mixed-speed constraint sets:
    1. Coarse scan of the slowest non-angle constraint to prune the search space.
    2. Vectorized fine scan (numpy array ops) inside each candidate window.

    Angle bodies (asc, mc, ic, dsc) require ``lat`` and ``lon`` (geographic
    decimal degrees, east-positive) and limit the search span to 5 years to
    bound memory usage.  Use ``--from``/``--to`` to specify a narrow window.

    Args:
        constraints: (body, sign) pairs that must all hold simultaneously.
            Planet ids must be in SCANNABLE_PLANETS; angle ids in SCANNABLE_ANGLES.
        search_start: Start of search window (timezone-aware).
        search_end: End of search window (timezone-aware).
        mode: Zodiac mode for sign placement.
        lat: Geographic latitude in decimal degrees (required for angle bodies).
        lon: Geographic longitude in decimal degrees, east-positive
            (required for angle bodies).

    Returns:
        List of BirthDateRange windows ordered by start date.

    Raises:
        ValueError: On unscannable body, invalid sign for mode, missing lat/lon
            for angle constraints, oversized window with angle constraints, or
            search window outside DE421 coverage (1900–2050).
    """
    if not constraints:
        raise ValueError("At least one constraint is required.")

    mode = ZodiacMode(mode)

    scannable = SCANNABLE_PLANETS | SCANNABLE_ANGLES
    for c in constraints:
        if c.planet not in scannable:
            raise ValueError(
                f"{c.planet!r} is not a scannable body. "
                f"Horizons-backed bodies (Chiron, Ceres, Eris) and lunar nodes "
                f"cannot be scanned efficiently. "
                f"Scannable planets: {sorted(SCANNABLE_PLANETS)}. "
                f"Scannable angles: {sorted(SCANNABLE_ANGLES)}"
            )

    valid = valid_signs(mode)
    for c in constraints:
        if c.sign not in valid:
            extra = (
                " (Ophiuchus is only available in realsky mode)"
                if c.sign == "Ophiuchus"
                else ""
            )
            raise ValueError(
                f"{c.sign!r} is not a valid sign for {mode} mode.{extra} "
                f"Valid signs: {sorted(valid)}"
            )

    has_angles = any(c.planet in SCANNABLE_ANGLES for c in constraints)
    if has_angles:
        if lat is None or lon is None:
            raise ValueError(
                "lat and lon are required when using angle constraints "
                "(asc, mc, ic, dsc). Pass --lat and --lon."
            )
        span_days = (search_end - search_start).total_seconds() / 86400.0
        if span_days > _ANGLE_SPAN_MAX_DAYS:
            raise ValueError(
                f"Search window too large for angle constraints "
                f"(max {_ANGLE_SPAN_MAX_DAYS // 365} years; got "
                f"{span_days / 365:.1f} years). Use --from/--to to narrow the range."
            )

    search_start = max(search_start, DE421_START)
    search_end = min(search_end, DE421_END)
    if search_start >= search_end:
        return []

    # Sort slowest to fastest — slowest non-angle body drives the coarse prefilter.
    sorted_c = sorted(constraints, key=lambda c: _MEAN_DAILY_MOTION[c.planet])

    # Fine step: 1 min when angles present; planet-rate otherwise.
    all_bodies = [c.planet for c in constraints]
    fine_step = timedelta(hours=_step_hours(all_bodies, mode))

    # Coarse prefilter: only worthwhile when the speed ratio is large enough
    # (slowest vs. fastest differs by more than a factor of ~4).
    # When angles are present, the coarse body is always a planet (sorted first).
    slowest_body = sorted_c[0].planet
    fastest_body = sorted_c[-1].planet
    speed_ratio = _MEAN_DAILY_MOTION[fastest_body] / _MEAN_DAILY_MOTION[slowest_body]

    if len(sorted_c) > 1 and speed_ratio > 4.0:
        # Coarse step uses planet-rate step for the slowest body (always a planet
        # since angles sort last).
        coarse_step_h = _step_hours([slowest_body], mode)
        coarse_step = timedelta(hours=coarse_step_h)
        # Scan only the slowest constraint at coarse resolution
        coarse_windows = _vectorized_scan(
            [sorted_c[0]], search_start, search_end, mode, coarse_step, lat=lat, lon=lon
        )
        # Pad each coarse window by one step on each side to avoid missing
        # windows at ingress/egress edges, then run the full fine scan inside.
        results: list[BirthDateRange] = []
        for w in coarse_windows:
            padded_start = max(search_start, w.start - coarse_step)
            padded_end = min(search_end, w.end + coarse_step)
            results.extend(
                _vectorized_scan(
                    constraints,
                    padded_start,
                    padded_end,
                    mode,
                    fine_step,
                    lat=lat,
                    lon=lon,
                )
            )
        return results

    # Single constraint or similar-speed set: run the fine scan directly
    return _vectorized_scan(
        constraints, search_start, search_end, mode, fine_step, lat=lat, lon=lon
    )
