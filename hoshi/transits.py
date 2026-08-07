"""Transit aspect window computation: ingress, exact, and egress dates.

For each active transit-to-natal aspect, computes three moments:

- **ingress**: when the transiting planet first entered orb
- **exact**: when the aspect is at 0° separation (list, to handle retrograde
  passes that produce 2–3 exact moments for the same aspect window)
- **egress**: when the transiting planet last leaves orb

All datetimes are UTC.  Either ingress or egress (or both) may be None when
the scan window was exhausted before a boundary was found — the window is
open-ended at that edge.

Bodies without Skyfield ephemeris support (Chiron, Ceres, Eris, nodes)
always return (None, [], None).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

import numpy as np

from hoshi.aspects import AspectDef
from hoshi.ephemeris import SKYFIELD_TARGETS
from hoshi.events import (
    _body_lons,
    _datetime_to_jd,
    _jd_to_utc,
    _sign_indices,
    _sign_name,
)


@dataclass
class TransitPass:
    """Ingress, exact, and egress for one retrograde pass of a transit aspect.

    For a triple-hit transit, pass boundaries are the station points (where
    the planet reverses direction relative to the natal point) rather than
    true orb exits.  The first pass inherits the overall ingress; the last
    pass inherits the overall egress.  Middle passes share a station date as
    their egress/ingress with adjacent passes.
    """

    ingress: datetime | None
    exact: datetime
    egress: datetime | None


@dataclass
class TransitWindow:
    """Full window returned by :func:`transit_aspect_window`.

    Replaces the former 3-tuple so per-pass data can be carried alongside
    the aggregate ingress/exact/egress fields.
    """

    ingress: datetime | None
    exact: list[datetime]
    egress: datetime | None
    passes: list[TransitPass]


class TransitTier(StrEnum):
    """Speed tier classification for transiting bodies."""

    slow = "slow"
    medium = "medium"
    fast = "fast"
    luminary = "luminary"


_BODY_TIER: dict[str, TransitTier] = {
    "moon": TransitTier.luminary,
    "sun": TransitTier.fast,
    "mercury": TransitTier.fast,
    "venus": TransitTier.fast,
    "mars": TransitTier.medium,
    "jupiter": TransitTier.slow,
    "saturn": TransitTier.slow,
    "uranus": TransitTier.slow,
    "neptune": TransitTier.slow,
    "pluto": TransitTier.slow,
    "chiron": TransitTier.slow,
    "ceres": TransitTier.slow,
    "eris": TransitTier.slow,
}


def transit_tier(pid: str) -> str:
    """Return the speed tier for a transiting body pid (defaults to slow)."""
    return _BODY_TIER.get(pid.lower(), TransitTier.slow)


# Approximate mean daily motions (degrees/day) for scan-window scaling.
# Using averages; retrograde periods cut actual progress significantly.
_MEAN_MOTION: dict[str, float] = {
    "sun": 0.9856,
    "moon": 13.176,
    "mercury": 1.383,
    "venus": 1.202,
    "mars": 0.524,
    "jupiter": 0.0831,
    "saturn": 0.0335,
    "uranus": 0.0117,
    "neptune": 0.00599,
    "pluto": 0.00397,
}

# Hard cap on the scan window in days (~15 years).  When the window is hit,
# ingress/egress are returned as None to indicate "open-ended."
_MAX_HORIZON_DAYS: float = 15 * 365.25

# Approximate target number of grid samples per scan.  Stays constant across
# body speeds because window_days and step_days both scale with mean motion.
_N_SAMPLES: int = 120


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _dev_at(body_pid: str, natal_lon: float, target: float, jd: float) -> float:
    """Signed deviation from the target aspect angle at a single Julian Day.

    Uses the directed-arc approach: raw = (lon_transit - natal_lon) % 360,
    then dev = ((raw - target + 180) % 360) - 180, placing the result in
    (-180, 180].  Zero means the aspect is exact; sign indicates which side.
    """
    lon = float(_body_lons(body_pid, np.array([jd]))[0])
    raw = (lon - natal_lon) % 360.0
    return ((raw - target + 180.0) % 360.0) - 180.0


def _bisect_exact(
    body_pid: str,
    natal_lon: float,
    target: float,
    t_lo: float,
    t_hi: float,
    n: int = 10,
) -> float:
    """Bisect to find the JD where dev changes sign (aspect is exact)."""
    d_lo = _dev_at(body_pid, natal_lon, target, t_lo)
    for _ in range(n):
        t_mid = (t_lo + t_hi) / 2.0
        d_mid = _dev_at(body_pid, natal_lon, target, t_mid)
        if d_lo * d_mid <= 0:
            t_hi = t_mid
        else:
            t_lo = t_mid
            d_lo = d_mid
    return (t_lo + t_hi) / 2.0


def _sign_at(body_pid: str, jd: float, mode: str) -> str:
    """Return the zodiac sign name of a transiting body at a given Julian Day."""
    lon = _body_lons(body_pid, np.array([jd]))
    return _sign_name(int(_sign_indices(lon, np.array([jd]), mode)[0]), mode)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transit_aspect_window(
    body_pid: str,
    natal_lon: float,
    aspect_def: AspectDef,
    transit_dt: datetime,
) -> TransitWindow:
    """Compute ingress / exact / egress for an active transit-to-natal aspect.

    Parameters
    ----------
    body_pid:
        Lowercase planet id (e.g. ``"saturn"``), matching the keys of
        :data:`~hoshi.ephemeris.SKYFIELD_TARGETS`.
    natal_lon:
        Ecliptic longitude of the natal body (degrees, equinox of date).
    aspect_def:
        The matching :class:`~hoshi.aspects.AspectDef` (supplies angle and orb).
    transit_dt:
        The snapshot datetime (timezone-aware).  The scan window is centred
        here so the body should be within orb at this moment.

    Returns
    -------
    :class:`TransitWindow`
        ``ingress``/``egress`` are ``None`` when the scan horizon was reached.
        ``exact`` is a list to accommodate retrograde multi-pass windows.
        ``passes`` breaks multi-exact windows into per-pass ingress/exact/egress,
        using station points (local dev extrema) as pass boundaries.

    Returns an empty :class:`TransitWindow` for bodies without Skyfield support.
    """
    if body_pid not in SKYFIELD_TARGETS:
        return TransitWindow(ingress=None, exact=[], egress=None, passes=[])

    mean_motion = _MEAN_MOTION[body_pid]
    max_orb = aspect_def.orb
    asp_angle = aspect_def.angle

    # Scale window and step so the grid covers ~4 full orb-traversals in each
    # direction — enough to capture retrograde back-and-forth — with a constant
    # sample budget regardless of planet speed.
    traverse_days = max_orb / mean_motion
    window_days = min(traverse_days * 4.0, _MAX_HORIZON_DAYS)

    ref_jd = _datetime_to_jd(transit_dt)
    t_jd = np.linspace(ref_jd - window_days, ref_jd + window_days, _N_SAMPLES)

    lons = _body_lons(body_pid, t_jd)
    raw = (lons - natal_lon) % 360.0

    # Determine the active target angle (asp_angle or its supplement 360-asp_angle).
    # Only one of the two directed arcs can be within orb at a given moment.
    ref_idx = _N_SAMPLES // 2
    raw_now = float(raw[ref_idx])
    targets = [asp_angle]
    if asp_angle not in (0.0, 180.0):
        targets.append(360.0 - asp_angle)

    active_target: float | None = None
    for tgt in targets:
        if abs(((raw_now - tgt + 180.0) % 360.0) - 180.0) <= max_orb:
            active_target = tgt
            break

    if active_target is None:
        return TransitWindow(ingress=None, exact=[], egress=None, passes=[])

    dev = ((raw - active_target + 180.0) % 360.0) - 180.0
    abs_dev = np.abs(dev)
    in_orb = abs_dev <= max_orb

    entries: list[float] = []
    exits: list[float] = []
    # (jd, grid_index_before_crossing) pairs — index used for station finding
    exact_pairs: list[tuple[float, int]] = []

    for i in range(1, _N_SAMPLES):
        was_in = bool(in_orb[i - 1])
        now_in = bool(in_orb[i])

        if not was_in and now_in:
            # Linear interpolation: find t where |dev| = max_orb
            y0 = float(abs_dev[i - 1]) - max_orb
            y1 = float(abs_dev[i]) - max_orb
            entries.append(
                t_jd[i - 1] + (t_jd[i] - t_jd[i - 1]) * abs(y0) / (abs(y0) + abs(y1))
            )
        elif was_in and not now_in:
            y0 = float(abs_dev[i - 1]) - max_orb
            y1 = float(abs_dev[i]) - max_orb
            exits.append(
                t_jd[i - 1] + (t_jd[i] - t_jd[i - 1]) * abs(y0) / (abs(y0) + abs(y1))
            )

        # Exact crossing: dev changes sign while at least one endpoint is in orb.
        if was_in or now_in:
            d0, d1 = float(dev[i - 1]), float(dev[i])
            if d0 * d1 < 0 and abs(d0) < max_orb + 1.0 and abs(d1) < max_orb + 1.0:
                # Bisect to find the precise crossing time — exact transit dates
                # are user-facing timestamps that warrant full precision.
                exact_jd = _bisect_exact(
                    body_pid, natal_lon, active_target, t_jd[i - 1], t_jd[i]
                )
                exact_pairs.append((exact_jd, i - 1))

    # ingress = first entry (None if already in-orb at window start — open-ended)
    ingress_jd = entries[0] if (entries and not bool(in_orb[0])) else None
    # egress = last exit (None if still in-orb at window end — open-ended)
    egress_jd = exits[-1] if (exits and not bool(in_orb[-1])) else None

    exact_pairs.sort()
    exact_jds_sorted = [p[0] for p in exact_pairs]
    exact_idxs_sorted = [p[1] for p in exact_pairs]
    ingress_dt = _jd_to_utc(ingress_jd) if ingress_jd is not None else None
    egress_dt = _jd_to_utc(egress_jd) if egress_jd is not None else None
    exact_dts = [_jd_to_utc(jd) for jd in exact_jds_sorted]

    # Build per-pass breakdown.  For a triple-hit, the planet typically stays
    # within orb the whole time — station points between consecutive exacts
    # serve as pass boundaries rather than true orb exits/entries.
    passes: list[TransitPass] = []
    if len(exact_jds_sorted) == 1:
        passes = [TransitPass(ingress=ingress_dt, exact=exact_dts[0], egress=egress_dt)]
    elif len(exact_jds_sorted) > 1:
        # Station points: peak of |dev| between consecutive exact crossings.
        # Use grid argmax instead of iterative ternary-search Skyfield calls —
        # the 120-point grid is accurate enough for pass-boundary splitting.
        station_dts = []
        for k in range(len(exact_jds_sorted) - 1):
            lo = exact_idxs_sorted[k] + 1
            hi = exact_idxs_sorted[k + 1] + 1
            if lo >= hi:
                # Crossings are adjacent grid points — use midpoint JD
                station_jd = (exact_jds_sorted[k] + exact_jds_sorted[k + 1]) / 2.0
            else:
                station_idx = lo + int(np.argmax(abs_dev[lo : hi + 1]))
                station_jd = float(t_jd[station_idx])
            station_dts.append(_jd_to_utc(station_jd))
        pass_ingresses = [ingress_dt] + station_dts
        pass_egresses = station_dts + [egress_dt]
        passes = [
            TransitPass(
                ingress=pass_ingresses[i], exact=exact_dts[i], egress=pass_egresses[i]
            )
            for i in range(len(exact_jds_sorted))
        ]

    return TransitWindow(
        ingress=ingress_dt, exact=exact_dts, egress=egress_dt, passes=passes
    )


# ---------------------------------------------------------------------------
# Date-range forecast
# ---------------------------------------------------------------------------


@dataclass
class ForecastWindow:
    """One transit-to-natal aspect window found by :func:`forecast_transits`.

    Represents a period during which a transiting body forms an aspect to a
    natal point and becomes exact at least once within the requested range.
    """

    transit_pid: str
    transit_name: str
    transit_sign: str
    natal_name: str
    natal_lon: float
    natal_sign: str
    aspect_name: str
    aspect_symbol: str
    aspect_angle: float
    aspect_kind: str
    ingress: datetime | None
    egress: datetime | None
    exact: list[datetime] = field(default_factory=list)
    tier: str = ""
    pass_count: int = 0
    passes: list[TransitPass] = field(default_factory=list)


def forecast_transits(
    natal_bodies: list[tuple[str, float, str]],
    from_dt: datetime,
    to_dt: datetime,
    mode: str = "realsky",
    *,
    tiers: frozenset[str] | None = None,
    aspect_defs: list[AspectDef] | None = None,
) -> list[ForecastWindow]:
    """Find all transit-to-natal aspect windows with at least one exact date in [from_dt, to_dt].

    Parameters
    ----------
    natal_bodies:
        List of (display_name, ecliptic_lon, sign) tuples — e.g. the output of
        ``hoshi.aspects._bodies(chart, details, mode)``.
    from_dt, to_dt:
        Date range (timezone-aware).  Only windows whose exact date(s) fall
        within this inclusive range are returned.
    mode:
        Zodiac mode string (``"realsky"``, ``"tropical"``, ``"vedic"``).
    tiers:
        Which speed tiers to include.  ``None`` defaults to slow planets only
        (Jupiter, Saturn, Uranus, Neptune, Pluto).
    aspect_defs:
        Which aspects to scan.  ``None`` defaults to all
        :data:`~hoshi.aspects.ASPECT_DEFS`.

    Returns
    -------
    list of :class:`ForecastWindow`
        Sorted by first in-range exact date.  ``exact`` contains *all* exact
        dates for the window (retrograde passes may fall outside the range).
    """
    from hoshi.aspects import ASPECT_DEFS as _ALL_ASPECTS

    if tiers is None:
        tiers = frozenset({TransitTier.slow})
    if aspect_defs is None:
        aspect_defs = _ALL_ASPECTS

    scan_pids = [
        pid
        for pid in SKYFIELD_TARGETS
        if str(_BODY_TIER.get(pid, TransitTier.slow)) in tiers
    ]

    from_jd = _datetime_to_jd(from_dt)
    to_jd = _datetime_to_jd(to_dt)

    _DT_MIN = datetime.min.replace(tzinfo=timezone.utc)
    _DT_MAX = datetime.max.replace(tzinfo=timezone.utc)

    results: list[ForecastWindow] = []

    for transit_pid in scan_pids:
        mean_motion = _MEAN_MOTION.get(transit_pid, 0.01)
        min_orb = min(a.orb for a in aspect_defs)
        # Step: at least 20 samples per orb-traversal so no crossing is missed.
        step = max(min_orb / mean_motion / 20.0, 0.05)
        n_samples = max(int((to_jd - from_jd) / step) + 2, 5)
        t_jd = np.linspace(from_jd, to_jd, n_samples)
        lons = _body_lons(transit_pid, t_jd)  # one ephemeris call per planet
        tier_val = str(_BODY_TIER.get(transit_pid, TransitTier.slow))

        for natal_name, natal_lon, natal_sign in natal_bodies:
            raw_arc = (lons - natal_lon) % 360.0

            for adef in aspect_defs:
                asp_angle = adef.angle
                max_orb = adef.orb
                targets = [asp_angle]
                if asp_angle not in (0.0, 180.0):
                    targets.append(360.0 - asp_angle)

                # Collect sign-change JDs (potential exact dates) within the range.
                in_range_jds: list[float] = []
                for tgt in targets:
                    dev = ((raw_arc - tgt + 180.0) % 360.0) - 180.0
                    abs_dev = np.abs(dev)
                    for i in range(1, len(t_jd)):
                        d0 = float(dev[i - 1])
                        d1 = float(dev[i])
                        if (
                            d0 * d1 < 0
                            and float(abs_dev[i - 1]) <= max_orb + 1.0
                            and float(abs_dev[i]) <= max_orb + 1.0
                        ):
                            exact_jd = _bisect_exact(
                                transit_pid, natal_lon, tgt, t_jd[i - 1], t_jd[i]
                            )
                            in_range_jds.append(exact_jd)

                in_range_jds.sort()

                # Interval-skip dedup: once a window is emitted its (ingress,
                # egress) interval absorbs any later crossing from the same window
                # (e.g. retrograde triple passes).
                emitted: list[tuple[datetime, datetime]] = []

                for exact_jd in in_range_jds:
                    exact_dt = _jd_to_utc(exact_jd)
                    if any(lo <= exact_dt <= hi for lo, hi in emitted):
                        continue

                    win = transit_aspect_window(transit_pid, natal_lon, adef, exact_dt)
                    emitted.append((win.ingress or _DT_MIN, win.egress or _DT_MAX))

                    t_sign = _sign_at(transit_pid, exact_jd, mode)
                    results.append(
                        ForecastWindow(
                            transit_pid=transit_pid,
                            transit_name=transit_pid.capitalize(),
                            transit_sign=t_sign,
                            natal_name=natal_name,
                            natal_lon=natal_lon,
                            natal_sign=natal_sign,
                            aspect_name=adef.name,
                            aspect_symbol=adef.symbol,
                            aspect_angle=adef.angle,
                            aspect_kind=adef.kind,
                            ingress=win.ingress,
                            egress=win.egress,
                            exact=win.exact,
                            tier=tier_val,
                            pass_count=len(win.exact),
                            passes=win.passes,
                        )
                    )

    def _sort_key(w: ForecastWindow) -> datetime:
        in_range = [e for e in w.exact if from_dt <= e <= to_dt]
        return in_range[0] if in_range else (w.ingress or from_dt)

    results.sort(key=_sort_key)
    return results
