"""Planetary return (cycle completion) dates.

For each body in a natal chart, finds the next date(s) after a reference
datetime when that body returns to its natal ecliptic longitude — completing
one full cycle through the zodiac.  This is the astrological "planetary
return" concept (solar return, Saturn return, etc.).

Only bodies with Skyfield ephemeris support are scannable.  Horizons-backed
bodies (Chiron, Ceres, Eris) and lunar nodes return an explicit ``available=False``
note rather than silently yielding no dates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from skyfield.errors import EphemerisRangeError

from hoshi.chart import Chart
from hoshi.ephemeris import SKYFIELD_TARGETS
from hoshi.events import _body_lons, _datetime_to_jd, _jd_to_utc
from hoshi.transits import _MEAN_MOTION, _bisect_exact


# Bodies that require Horizons HTTP calls — forward scanning is not supported.
_HORIZONS_BODY_IDS = frozenset({"chiron", "ceres", "eris"})

# Approximate orbital periods in days (360° / mean daily motion).
ORBITAL_PERIODS: dict[str, float] = {
    pid: 360.0 / motion for pid, motion in _MEAN_MOTION.items()
}
# Chiron / Ceres / Eris — periods used for display only (not scannable).
ORBITAL_PERIODS.update(
    {
        "chiron": 50.7 * 365.25,
        "ceres": 4.6 * 365.25,
        "eris": 559.0 * 365.25,
    }
)


@dataclass
class CycleReturn:
    """Next planetary return for one body in a natal chart.

    ``exact`` contains all exact crossing dates for the return event —
    usually one, but up to three when the planet is retrograde near the natal
    longitude (triple-pass window).
    """

    body_pid: str  # lowercase stable key: "sun", "moon", "chiron", …
    body_name: str  # display name: "Sun", "Moon", "Chiron", …
    natal_lon: float  # natal ecliptic longitude, degrees (of-date)
    natal_sign: str  # zodiac sign name in the requested mode
    period_days: float  # approximate orbital period in days (nan when unknown)
    exact: list[datetime] = field(default_factory=list)
    available: bool = True  # False for bodies that cannot be forward-scanned
    note: str | None = None  # explanation when available=False


def next_cycles(
    chart: Chart,
    from_dt: datetime,
    mode: str = "realsky",
) -> list[CycleReturn]:
    """Compute next planetary returns for every planet in *chart* after *from_dt*.

    Parameters
    ----------
    chart:
        A natal :class:`~hoshi.chart.Chart` (``chart.planets`` is iterated).
    from_dt:
        Reference datetime (timezone-aware).  Returns are the first cycle
        completions strictly after this moment.
    mode:
        Zodiac mode string used for sign-name display (``"realsky"``,
        ``"tropical"``, ``"vedic"``).

    Returns
    -------
    list of :class:`CycleReturn`, one per planet, in chart planet order.
    """
    from_jd = _datetime_to_jd(from_dt)
    results: list[CycleReturn] = []

    for planet in chart.planets:
        pid = planet.pid
        placement = planet.placed.placement(mode)
        natal_sign = placement.name
        natal_lon = planet.placed.lon

        period = ORBITAL_PERIODS.get(pid)

        if pid in _HORIZONS_BODY_IDS:
            results.append(
                CycleReturn(
                    body_pid=pid,
                    body_name=pid.capitalize(),
                    natal_lon=natal_lon,
                    natal_sign=natal_sign,
                    period_days=period if period is not None else float("nan"),
                    available=False,
                    note=f"{pid.capitalize()} return requires Horizons data (forward scan not available).",
                )
            )
            continue

        if pid not in SKYFIELD_TARGETS or period is None:
            results.append(
                CycleReturn(
                    body_pid=pid,
                    body_name=pid.capitalize(),
                    natal_lon=natal_lon,
                    natal_sign=natal_sign,
                    period_days=float("nan"),
                    available=False,
                    note=f"No forward ephemeris support for {pid.capitalize()}.",
                )
            )
            continue

        exact_dates, approx_note = _find_next_return(pid, natal_lon, from_jd, period)
        results.append(
            CycleReturn(
                body_pid=pid,
                body_name=pid.capitalize(),
                natal_lon=natal_lon,
                natal_sign=natal_sign,
                period_days=period,
                exact=exact_dates,
                available=True,
                note=approx_note,
            )
        )

    return results


def _find_next_return(
    body_pid: str,
    natal_lon: float,
    from_jd: float,
    period: float,
) -> tuple[list[datetime], str | None]:
    """Find the next return date(s) of *body_pid* to *natal_lon* after *from_jd*.

    Returns a (dates, note) pair.  *dates* contains all exact crossing times
    for the first retrograde cluster (typically 1, up to 3 for retrograde
    triple-pass).  *note* is set when results are approximate due to ephemeris
    range limits.

    Scans 1.5 orbital periods forward using 300 grid samples, then bisects
    each zero-crossing to sub-day precision.  If the scan window exceeds the
    DE421 ephemeris boundary, falls back to an approximate date computed from
    mean daily motion.
    """
    # One-day offset avoids re-triggering a return that happens at exactly from_jd.
    start_jd = from_jd + 1.0
    end_jd = from_jd + period * 1.5

    n_samples = 300

    try:
        t_jd = np.linspace(start_jd, end_jd, n_samples)
        lons = _body_lons(body_pid, t_jd)
    except EphemerisRangeError:
        return _approximate_return(body_pid, natal_lon, from_jd, period)

    # Signed deviation from natal_lon in (-180, 180].
    raw = (lons - natal_lon) % 360.0
    dev = ((raw + 180.0) % 360.0) - 180.0

    exact_jds: list[float] = []
    for i in range(1, n_samples):
        d0, d1 = float(dev[i - 1]), float(dev[i])
        if d0 * d1 < 0:
            try:
                jd = _bisect_exact(body_pid, natal_lon, 0.0, t_jd[i - 1], t_jd[i])
                exact_jds.append(jd)
            except EphemerisRangeError:
                break

    if exact_jds:
        # Group crossings within the same retrograde cluster.  The threshold is
        # 30% of the period (capped at 200 days) to comfortably span the longest
        # retrograde windows (Neptune/Pluto ~160 days).
        gap_threshold = min(period * 0.30, 200.0)
        grouped: list[list[float]] = [[exact_jds[0]]]
        for jd in exact_jds[1:]:
            if jd - grouped[-1][-1] < gap_threshold:
                grouped[-1].append(jd)
            else:
                grouped.append([jd])

        first_cluster = grouped[0]
        return [_jd_to_utc(jd) for jd in first_cluster], None

    # No crossing found — could be beyond ephemeris or the period is very long.
    return _approximate_return(body_pid, natal_lon, from_jd, period)


def _approximate_return(
    body_pid: str,
    natal_lon: float,
    from_jd: float,
    period: float,
) -> tuple[list[datetime], str]:
    """Estimate the next return using mean daily motion (no ephemeris scan)."""
    mean_motion = _MEAN_MOTION.get(body_pid, 360.0 / period)
    try:
        current_lon = float(_body_lons(body_pid, np.array([from_jd]))[0])
    except EphemerisRangeError:
        return [], "Ephemeris data not available for this date."
    remaining_deg = (natal_lon - current_lon) % 360.0
    approx_jd = from_jd + remaining_deg / mean_motion
    approx_dt = _jd_to_utc(approx_jd)
    return (
        [approx_dt],
        f"Approximate — beyond ephemeris range (est. {approx_dt.year})",
    )


def format_period(days: float) -> str:
    """Human-readable period string (e.g. ``"365d"`` or ``"29.5y"``)."""
    if days != days:  # nan
        return "—"
    if days >= 365.25:
        years = days / 365.25
        return f"{years:.1f}y"
    return f"{days:.0f}d"
