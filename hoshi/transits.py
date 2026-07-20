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

from datetime import datetime

import numpy as np

from hoshi.aspects import AspectDef
from hoshi.ephemeris import SKYFIELD_TARGETS
from hoshi.events import _body_lons, _datetime_to_jd, _jd_to_utc

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


def _bisect_orb_boundary(
    body_pid: str,
    natal_lon: float,
    target: float,
    max_orb: float,
    t_lo: float,
    t_hi: float,
    *,
    lo_outside: bool,
    n: int = 10,
) -> float:
    """Bisect to find the JD where |dev| = max_orb.

    lo_outside=True when t_lo is the outside-orb sample; False when inside.
    """
    for _ in range(n):
        t_mid = (t_lo + t_hi) / 2.0
        mid_outside = abs(_dev_at(body_pid, natal_lon, target, t_mid)) > max_orb
        if mid_outside == lo_outside:
            t_lo = t_mid
        else:
            t_hi = t_mid
    return (t_lo + t_hi) / 2.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transit_aspect_window(
    body_pid: str,
    natal_lon: float,
    aspect_def: AspectDef,
    transit_dt: datetime,
) -> tuple[datetime | None, list[datetime], datetime | None]:
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
    tuple of (ingress, exact_dates, egress)
        All are UTC datetimes.  ingress/egress are ``None`` when the scan
        horizon was reached before a boundary crossing was found.
        exact_dates is a list to accommodate retrograde multi-pass windows.

    Returns ``(None, [], None)`` for bodies without Skyfield support.
    """
    if body_pid not in SKYFIELD_TARGETS:
        return None, [], None

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
        return None, [], None

    dev = ((raw - active_target + 180.0) % 360.0) - 180.0
    abs_dev = np.abs(dev)
    in_orb = abs_dev <= max_orb

    entries: list[float] = []
    exits: list[float] = []
    exact_jds: list[float] = []

    for i in range(1, _N_SAMPLES):
        was_in = bool(in_orb[i - 1])
        now_in = bool(in_orb[i])

        if not was_in and now_in:
            entries.append(
                _bisect_orb_boundary(
                    body_pid,
                    natal_lon,
                    active_target,
                    max_orb,
                    t_jd[i - 1],
                    t_jd[i],
                    lo_outside=True,
                )
            )
        elif was_in and not now_in:
            exits.append(
                _bisect_orb_boundary(
                    body_pid,
                    natal_lon,
                    active_target,
                    max_orb,
                    t_jd[i - 1],
                    t_jd[i],
                    lo_outside=False,
                )
            )

        # Exact crossing: dev changes sign while at least one endpoint is in orb.
        if was_in or now_in:
            d0, d1 = float(dev[i - 1]), float(dev[i])
            if d0 * d1 < 0 and abs(d0) < max_orb + 1.0 and abs(d1) < max_orb + 1.0:
                exact_jds.append(
                    _bisect_exact(
                        body_pid, natal_lon, active_target, t_jd[i - 1], t_jd[i]
                    )
                )

    # ingress = first entry (None if already in-orb at window start — open-ended)
    ingress_jd = entries[0] if (entries and not bool(in_orb[0])) else None
    # egress = last exit (None if still in-orb at window end — open-ended)
    egress_jd = exits[-1] if (exits and not bool(in_orb[-1])) else None

    return (
        _jd_to_utc(ingress_jd) if ingress_jd is not None else None,
        [_jd_to_utc(jd) for jd in sorted(exact_jds)],
        _jd_to_utc(egress_jd) if egress_jd is not None else None,
    )
