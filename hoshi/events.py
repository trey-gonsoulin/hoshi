"""Sky event detection over a date range.

Supported events
----------------
- ``retrograde_station`` / ``direct_station`` — body changes direction
- ``ingress`` — body enters a new sign
- ``moon_new`` / ``moon_first_quarter`` / ``moon_full`` / ``moon_last_quarter``
- ``voc_start`` / ``voc_end`` — void-of-course Moon window boundaries
- ``exact_aspect`` — transit-to-transit major Ptolemaic aspect within
  ``EXACT_ASPECT_ORB`` degrees of exactness

Body coverage
-------------
Skyfield bodies (Sun through Pluto + Moon) are computed with vectorized
ephemeris queries and bisection for sub-hour precision.

Chiron, Ceres, and Eris are included in station/ingress scanning only when the
seed-cache files are available (deployed Lambda/Docker environments).  In local
development they are silently omitted from range scans; they still appear in
the "now" snapshot via the normal chart path.

Void-of-course convention
--------------------------
VoC = the window from the Moon's last exact major Ptolemaic aspect to a
classical planet (Sun–Saturn, 1° orb) until the Moon ingresses the next sign.
Sign boundaries follow the active zodiac mode (realsky by default).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from hoshi.ephemeris import (
    PlanetPosition,
    SKYFIELD_TARGETS,
    _ceres_seed_path,
    _chiron_seed_path,
    _eris_seed_path,
    _load_ephemeris,
    timescale,
)
from hoshi.zodiac import IAU, TROP_NAMES, _iau_index

# ── Display tables ────────────────────────────────────────────────────────────

BODY_DISPLAY: dict[str, str] = {
    "sun": "Sun",
    "moon": "Moon",
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
    "pluto": "Pluto",
    "chiron": "Chiron",
    "ceres": "Ceres",
    "eris": "Eris",
}

BODY_SYMBOL: dict[str, str] = {
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "⛢",
    "neptune": "♆",
    "pluto": "♇",
    "chiron": "⚷",
    "ceres": "⚳",
    "eris": "Eri",
}

# U+FE0E text variation selector — forces text rendering in browsers
_T = "︎"
SIGN_SYMBOL: dict[str, str] = {
    "Aries": f"♈{_T}",
    "Taurus": f"♉{_T}",
    "Gemini": f"♊{_T}",
    "Cancer": f"♋{_T}",
    "Leo": f"♌{_T}",
    "Virgo": f"♍{_T}",
    "Libra": f"♎{_T}",
    "Scorpio": f"♏{_T}",
    "Ophiuchus": f"⛎{_T}",
    "Sagittarius": f"♐{_T}",
    "Capricorn": f"♑{_T}",
    "Aquarius": f"♒{_T}",
    "Pisces": f"♓{_T}",
}

# ── Catalogs ──────────────────────────────────────────────────────────────────

# Bodies that can retrograde astrologically (not Sun or Moon)
_STATION_BODIES: list[str] = [k for k in SKYFIELD_TARGETS if k not in ("sun", "moon")]

# Classical planets used for void-of-course aspect checking
_VOC_PLANETS: list[str] = ["sun", "mercury", "venus", "mars", "jupiter", "saturn"]

# Planet pairs scanned for transit-to-transit exact aspects.
# Excludes Mercury/Venus (too fast; produce many short-lived events).
_ASPECT_PAIRS: list[tuple[str, str]] = [
    ("sun", "saturn"),
    ("sun", "uranus"),
    ("sun", "neptune"),
    ("sun", "pluto"),
    ("mars", "jupiter"),
    ("mars", "saturn"),
    ("mars", "uranus"),
    ("mars", "neptune"),
    ("mars", "pluto"),
    ("jupiter", "saturn"),
    ("jupiter", "uranus"),
    ("jupiter", "neptune"),
    ("jupiter", "pluto"),
    ("saturn", "uranus"),
    ("saturn", "neptune"),
    ("saturn", "pluto"),
    ("uranus", "neptune"),
    ("uranus", "pluto"),
    ("neptune", "pluto"),
]

# (angle°, name, symbol) for major Ptolemaic aspects
_MAJOR_ASPECTS: list[tuple[float, str, str]] = [
    (0.0, "Conjunction", "☌"),
    (60.0, "Sextile", "⚹"),
    (90.0, "Square", "□"),
    (120.0, "Trine", "△"),
    (180.0, "Opposition", "☍"),
]

# Orb within which a transit-to-transit aspect is considered "exact"
EXACT_ASPECT_ORB: float = 0.5

# Orb for VoC aspect detection (Moon within this of a classical-planet aspect)
_VOC_ORB: float = 1.0

# Moon-phase bucket names and event-type strings
_PHASE_NAMES: list[str] = [
    "New Moon",
    "First Quarter",
    "Full Moon",
    "Last Quarter",
]
_PHASE_EVENT_TYPES: list[str] = [
    "moon_new",
    "moon_first_quarter",
    "moon_full",
    "moon_last_quarter",
]

# Small bodies backed by seed cache
_SEED_BODIES: dict[str, Path | None] = {}


def _get_seed_path(body_key: str) -> Path | None:
    if body_key not in _SEED_BODIES:
        fn = {
            "chiron": _chiron_seed_path,
            "ceres": _ceres_seed_path,
            "eris": _eris_seed_path,
        }
        _SEED_BODIES[body_key] = fn[body_key]() if body_key in fn else None
    return _SEED_BODIES[body_key]


# ── SkyEvent dataclass ────────────────────────────────────────────────────────


@dataclass(frozen=True, order=True)
class SkyEvent:
    """A single detected sky event sorted by UTC time."""

    when: datetime  # UTC; primary sort key
    event_type: str  # see module docstring for valid values
    body: str  # display name, e.g. "Mercury"
    body_symbol: str = field(compare=False, default="")
    detail: str = field(compare=False, default="")
    sign: str | None = field(compare=False, default=None)
    sign_symbol: str | None = field(compare=False, default=None)
    body_b: str | None = field(compare=False, default=None)  # second body for aspects
    aspect_name: str | None = field(compare=False, default=None)
    aspect_symbol: str | None = field(compare=False, default=None)


# ── Precession / sign helpers ─────────────────────────────────────────────────


def _precession_from_jd(jd: np.ndarray) -> np.ndarray:
    """Ecliptic precession in degrees since J2000 for an array of TT JD values."""
    years = (np.atleast_1d(jd) - 2451545.0) / 365.25
    return years * (50.29 / 3600.0)


def _ayanamsa_from_jd(jd: np.ndarray) -> np.ndarray:
    """Lahiri ayanamsa approximation for an array of TT JD values."""
    return 23.85 + _precession_from_jd(jd)


def _sign_idx_realsky(lons: np.ndarray, precessions: np.ndarray) -> np.ndarray:
    return np.array(
        [_iau_index(float(lon), float(prec)) for lon, prec in zip(lons, precessions)],
        dtype=np.int8,
    )


def _sign_idx_tropical(lons: np.ndarray) -> np.ndarray:
    return (lons % 360.0 / 30.0).astype(np.int8)


def _sign_idx_vedic(lons: np.ndarray, ayanamsas: np.ndarray) -> np.ndarray:
    return ((lons - ayanamsas) % 360.0 / 30.0).astype(np.int8)


def _sign_indices(lons: np.ndarray, t_jd: np.ndarray, mode: str) -> np.ndarray:
    if mode == "tropical":
        return _sign_idx_tropical(lons)
    if mode == "vedic":
        return _sign_idx_vedic(lons, _ayanamsa_from_jd(t_jd))
    return _sign_idx_realsky(lons, _precession_from_jd(t_jd))


def _sign_name(idx: int, mode: str) -> str:
    if mode == "realsky":
        return IAU[int(idx) % 13].name
    return TROP_NAMES[int(idx) % 12]


def _sign_sym(name: str) -> str:
    return SIGN_SYMBOL.get(name, "")


# ── JD ↔ datetime helpers ─────────────────────────────────────────────────────

_UNIX_EPOCH_JD = 2440587.5
_SECS_PER_DAY = 86400.0


def _jd_to_utc(jd: float) -> datetime:
    unix_ts = (jd - _UNIX_EPOCH_JD) * _SECS_PER_DAY
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc)


def _jd_to_date(jd: float) -> date:
    return _jd_to_utc(jd).date()


def _datetime_to_jd(dt: datetime) -> float:
    dt_utc = dt.astimezone(timezone.utc)
    unix_ts = dt_utc.timestamp()
    return unix_ts / _SECS_PER_DAY + _UNIX_EPOCH_JD


# ── Skyfield body longitude array ─────────────────────────────────────────────


def _body_lons(body_key: str, t_jd: np.ndarray) -> np.ndarray:
    """Return ecliptic of-date longitudes [0, 360) for a Skyfield body at a time array."""
    eph = _load_ephemeris()
    ts = timescale()
    earth = eph["earth"]
    sf_body = eph[SKYFIELD_TARGETS[body_key]]
    t = ts.tt_jd(t_jd)
    astrometric = earth.at(t).observe(sf_body)  # type: ignore[reportAttributeAccessIssue]
    _, lon, _ = astrometric.ecliptic_latlon(epoch=t)
    return np.atleast_1d(lon.degrees) % 360.0


def _moon_sun_elongation(t_jd: np.ndarray) -> np.ndarray:
    """Moon ecliptic longitude minus Sun ecliptic longitude, in [0, 360)."""
    return (_body_lons("moon", t_jd) - _body_lons("sun", t_jd)) % 360.0


# ── Station detection (Skyfield bodies) ───────────────────────────────────────


def _body_directions(body_key: str, t_jd: np.ndarray) -> np.ndarray:
    """Return +1 (direct) or -1 (retrograde) for each time in t_jd."""
    dt = 1.0 / 24.0  # 1-hour forward difference for velocity
    lon1 = _body_lons(body_key, t_jd)
    lon2 = _body_lons(body_key, t_jd + dt)
    delta = ((lon2 - lon1 + 540.0) % 360.0) - 180.0
    return np.sign(delta).astype(np.int8)


def _bisect_station(body_key: str, t_lo: float, t_hi: float, n: int = 7) -> float:
    for _ in range(n):
        t_mid = (t_lo + t_hi) / 2.0
        dirs = _body_directions(body_key, np.array([t_lo, t_mid]))
        if dirs[0] != dirs[1]:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2.0


def _find_stations_skyfield(
    body_key: str, start_jd: float, end_jd: float
) -> list[tuple[float, bool]]:
    """Return (jd, going_retrograde) pairs; bisects to ~45-min precision."""
    n = max(2, int(end_jd - start_jd) + 2)
    jd_arr = np.linspace(start_jd, end_jd, n)
    dirs = _body_directions(body_key, jd_arr)

    results: list[tuple[float, bool]] = []
    for i in range(1, len(dirs)):
        d0, d1 = int(dirs[i - 1]), int(dirs[i])
        if d0 != 0 and d1 != 0 and d0 != d1:
            t_exact = _bisect_station(body_key, jd_arr[i - 1], jd_arr[i])
            results.append((t_exact, d1 == -1))
    return results


# ── Station detection (seed-cache bodies: Chiron, Ceres, Eris) ───────────────


def _seed_lons(
    body_key: str, start_jd: float, end_jd: float
) -> list[tuple[float, float, bool]]:
    """Return [(jd, lon, retrograde), ...] from seed cache — daily resolution."""
    seed_path = _get_seed_path(body_key)
    if seed_path is None or not seed_path.exists():
        return []

    try:
        data: dict[str, dict] = json.loads(seed_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    rows: list[tuple[float, float, bool]] = []
    n_days = int(end_jd - start_jd) + 2
    for i in range(n_days):
        jd = start_jd + i
        date_str = _jd_to_date(jd).isoformat()
        entry = data.get(date_str)
        if entry:
            try:
                pos = PlanetPosition.model_validate(entry)
                rows.append((jd, pos.lon, pos.retrograde))
            except Exception:
                pass
    return rows


def _find_stations_seed(
    body_key: str, start_jd: float, end_jd: float
) -> list[tuple[float, bool]]:
    """Return (jd, going_retrograde) pairs from seed cache (daily precision)."""
    rows = _seed_lons(body_key, start_jd, end_jd)
    results: list[tuple[float, bool]] = []
    for i in range(1, len(rows)):
        prev_rx = rows[i - 1][2]
        curr_rx = rows[i][2]
        if prev_rx != curr_rx:
            # Report the midpoint day
            t_mid = (rows[i - 1][0] + rows[i][0]) / 2.0
            results.append((t_mid, curr_rx))
    return results


# ── Ingress detection ─────────────────────────────────────────────────────────

# Sampling interval (days) per body — fine enough to catch every sign change
_SAMPLE_STEP: dict[str, float] = {
    "moon": 2.0 / 24.0,  # 2-hour steps; Moon changes sign every ~2.3 days
    "sun": 1.0,
    "mercury": 0.5,
    "venus": 0.5,
    "mars": 1.0,
    "jupiter": 3.0,
    "saturn": 7.0,
    "uranus": 14.0,
    "neptune": 14.0,
    "pluto": 14.0,
}


def _bisect_ingress(
    body_key: str, mode: str, t_lo: float, t_hi: float, n: int = 8
) -> float:
    sign_lo = _sign_indices(
        _body_lons(body_key, np.array([t_lo])), np.array([t_lo]), mode
    )[0]
    for _ in range(n):
        t_mid = (t_lo + t_hi) / 2.0
        sign_mid = _sign_indices(
            _body_lons(body_key, np.array([t_mid])), np.array([t_mid]), mode
        )[0]
        if sign_mid != sign_lo:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2.0


def _find_ingresses_skyfield(
    body_key: str, start_jd: float, end_jd: float, mode: str
) -> list[tuple[float, int]]:
    """Return (jd, new_sign_idx) pairs; bisects to ~1-hour precision."""
    step = _SAMPLE_STEP.get(body_key, 1.0)
    n = max(2, int((end_jd - start_jd) / step) + 2)
    jd_arr = np.linspace(start_jd, end_jd, n)
    lons = _body_lons(body_key, jd_arr)
    signs = _sign_indices(lons, jd_arr, mode)

    results: list[tuple[float, int]] = []
    for i in range(1, len(signs)):
        if signs[i] != signs[i - 1]:
            t_exact = _bisect_ingress(body_key, mode, jd_arr[i - 1], jd_arr[i])
            results.append((t_exact, int(signs[i])))
    return results


def _find_ingresses_seed(
    body_key: str, start_jd: float, end_jd: float, mode: str
) -> list[tuple[float, int]]:
    """Return (jd, new_sign_idx) pairs from seed cache (daily precision)."""
    rows = _seed_lons(body_key, start_jd, end_jd)
    results: list[tuple[float, int]] = []
    for i in range(1, len(rows)):
        jd_prev, lon_prev, _ = rows[i - 1]
        jd_curr, lon_curr, _ = rows[i]
        jd_arr_prev = np.array([jd_prev])
        jd_arr_curr = np.array([jd_curr])
        sign_prev = _sign_indices(np.array([lon_prev]), jd_arr_prev, mode)[0]
        sign_curr = _sign_indices(np.array([lon_curr]), jd_arr_curr, mode)[0]
        if sign_curr != sign_prev:
            t_mid = (jd_prev + jd_curr) / 2.0
            results.append((t_mid, int(sign_curr)))
    return results


# ── Moon phases ───────────────────────────────────────────────────────────────


def _phase_bucket(elongation: np.ndarray) -> np.ndarray:
    return (elongation / 90.0).astype(np.int8) % 4


def _bisect_phase(t_lo: float, t_hi: float, target: int, n: int = 8) -> float:
    for _ in range(n):
        t_mid = (t_lo + t_hi) / 2.0
        bucket_mid = int(_phase_bucket(_moon_sun_elongation(np.array([t_mid])))[0])
        if bucket_mid == target:
            t_hi = t_mid
        else:
            t_lo = t_mid
    return (t_lo + t_hi) / 2.0


def _find_moon_phases(start_jd: float, end_jd: float) -> list[tuple[float, int]]:
    """Return (jd, phase_bucket) pairs; bisects to ~1-hour precision."""
    step = 4.0 / 24.0  # 4-hour steps; phases repeat every ~7 days
    n = max(2, int((end_jd - start_jd) / step) + 2)
    jd_arr = np.linspace(start_jd, end_jd, n)
    buckets = _phase_bucket(_moon_sun_elongation(jd_arr))

    results: list[tuple[float, int]] = []
    for i in range(1, len(buckets)):
        if buckets[i] != buckets[i - 1]:
            target = int(buckets[i])
            t_exact = _bisect_phase(jd_arr[i - 1], jd_arr[i], target)
            results.append((t_exact, target))
    return results


# ── Void-of-course Moon ───────────────────────────────────────────────────────


def _shortest_arc(a: float, b: float) -> float:
    diff = (a - b) % 360.0
    return float(min(diff, 360.0 - diff))


def _best_aspect_orb(moon_lon: float, planet_lons: dict[str, float]) -> float:
    """Tightest major Ptolemaic aspect orb between Moon and any classical planet."""
    best = math.inf
    for p_lon in planet_lons.values():
        arc = _shortest_arc(moon_lon, p_lon)
        for ang, _, _ in _MAJOR_ASPECTS:
            orb = abs(arc - ang)
            if orb < best:
                best = orb
    return best


def _find_voc_windows(
    start_jd: float, end_jd: float, mode: str
) -> list[tuple[float, float, str]]:
    """Return (voc_start_jd, voc_end_jd, entering_sign_name) tuples."""
    # Buffer to catch VoC windows that started before the requested range
    buf = 5.0
    moon_ingresses = _find_ingresses_skyfield(
        "moon", start_jd - buf, end_jd + 1.0, mode
    )
    if not moon_ingresses:
        return []

    results: list[tuple[float, float, str]] = []

    for i, (ingress_jd, new_sign_idx) in enumerate(moon_ingresses):
        # Search the duration of the preceding Moon sign for the last aspect
        search_start = moon_ingresses[i - 1][0] if i > 0 else ingress_jd - 5.0

        # Skip windows entirely outside the requested range
        if ingress_jd < start_jd and search_start < start_jd:
            continue

        # Sample hourly to find the last Moon-classical aspect before this ingress
        step = 1.0 / 24.0
        n = max(2, int((ingress_jd - search_start) / step) + 1)
        jd_arr = np.linspace(search_start, ingress_jd, n)

        moon_lons = _body_lons("moon", jd_arr)
        planet_lons_arr = {p: _body_lons(p, jd_arr) for p in _VOC_PLANETS}

        last_aspect_jd = search_start  # default: entire duration is VoC
        # Exclude the ingress sample itself (index -1 == ingress_jd) so that an
        # aspect orb satisfied right at the sign boundary isn't counted as the
        # "last aspect before" the ingress — that would produce a zero-duration window.
        for j in range(len(jd_arr) - 2, -1, -1):
            p_lons = {k: float(v[j]) for k, v in planet_lons_arr.items()}
            if _best_aspect_orb(float(moon_lons[j]), p_lons) <= _VOC_ORB:
                last_aspect_jd = float(jd_arr[j])
                break

        voc_start = last_aspect_jd
        voc_end = ingress_jd
        entering = _sign_name(new_sign_idx, mode)

        # Skip zero-duration windows: Moon was aspecting a classical planet
        # right at the ingress moment (no true VoC period).
        if voc_start >= voc_end:
            continue

        # Only include if window overlaps with the requested range
        if voc_end >= start_jd and voc_start <= end_jd:
            results.append((voc_start, voc_end, entering))

    return results


# ── Exact transiting aspects ──────────────────────────────────────────────────


def _find_exact_aspects(
    start_jd: float, end_jd: float
) -> list[tuple[float, str, str, str, str]]:
    """Return (jd, body_a, body_b, aspect_name, aspect_symbol) for exact hits."""
    step = 1.0  # daily sampling; aspects last weeks–months
    n = max(2, int((end_jd - start_jd) / step) + 2)
    jd_arr = np.linspace(start_jd, end_jd, n)

    results: list[tuple[float, str, str, str, str]] = []

    for body_a, body_b in _ASPECT_PAIRS:
        lons_a = _body_lons(body_a, jd_arr)
        lons_b = _body_lons(body_b, jd_arr)
        raw = (lons_a - lons_b) % 360.0  # [0, 360)

        for asp_angle, asp_name, asp_symbol in _MAJOR_ASPECTS:
            # For each aspect, check both the direct and reverse arc
            targets = [asp_angle]
            if asp_angle not in (0.0, 180.0):
                targets.append(360.0 - asp_angle)

            seen: set[int] = set()  # deduplicate hits from both targets

            for target in targets:
                dev = ((raw - target + 180.0) % 360.0) - 180.0  # [-180, 180]

                for i in range(1, len(dev)):
                    d0, d1 = float(dev[i - 1]), float(dev[i])
                    # Zero crossing within a 10° window (guard against wrap artefacts)
                    if d0 * d1 <= 0 and abs(d0) < 10.0 and abs(d1) < 10.0:
                        denom = d1 - d0
                        t_exact = (
                            jd_arr[i - 1] + (jd_arr[i] - jd_arr[i - 1]) * (-d0 / denom)
                            if abs(denom) > 1e-9
                            else (jd_arr[i - 1] + jd_arr[i]) / 2.0
                        )
                        if start_jd <= t_exact <= end_jd and i not in seen:
                            seen.add(i)
                            results.append(
                                (t_exact, body_a, body_b, asp_name, asp_symbol)
                            )

    return results


# ── Public API ────────────────────────────────────────────────────────────────


def sky_events(
    start: datetime,
    end: datetime,
    mode: str = "realsky",
    *,
    include_stations: bool = True,
    include_ingresses: bool = True,
    include_moon_phases: bool = True,
    include_voc: bool = True,
    include_aspects: bool = True,
) -> list[SkyEvent]:
    """Return all sky events between *start* and *end* (timezone-aware datetimes).

    Events are sorted by UTC time.  Small bodies (Chiron, Ceres, Eris) are
    included in station/ingress results only when seed-cache data is available.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")

    start_jd = _datetime_to_jd(start)
    end_jd = _datetime_to_jd(end)

    events: list[SkyEvent] = []

    # ── Stations ──────────────────────────────────────────────────────────────
    if include_stations:
        for bk in _STATION_BODIES:
            hits = _find_stations_skyfield(bk, start_jd, end_jd)
            for jd, going_rx in hits:
                et = "retrograde_station" if going_rx else "direct_station"
                verb = "stations retrograde" if going_rx else "stations direct"
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(jd),
                        event_type=et,
                        body=BODY_DISPLAY[bk],
                        body_symbol=BODY_SYMBOL.get(bk, ""),
                        detail=f"{BODY_DISPLAY[bk]} {verb}",
                    )
                )

        # Seed-cache small bodies
        for bk in ("chiron", "ceres", "eris"):
            hits = _find_stations_seed(bk, start_jd, end_jd)
            for jd, going_rx in hits:
                et = "retrograde_station" if going_rx else "direct_station"
                verb = "stations retrograde" if going_rx else "stations direct"
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(jd),
                        event_type=et,
                        body=BODY_DISPLAY[bk],
                        body_symbol=BODY_SYMBOL.get(bk, ""),
                        detail=f"{BODY_DISPLAY[bk]} {verb}",
                    )
                )

    # ── Ingresses ─────────────────────────────────────────────────────────────
    if include_ingresses:
        ingress_bodies = list(SKYFIELD_TARGETS.keys())  # includes Moon
        for bk in ingress_bodies:
            hits = _find_ingresses_skyfield(bk, start_jd, end_jd, mode)
            for jd, sign_idx in hits:
                sign = _sign_name(sign_idx, mode)
                sym = _sign_sym(sign)
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(jd),
                        event_type="ingress",
                        body=BODY_DISPLAY.get(bk, bk.capitalize()),
                        body_symbol=BODY_SYMBOL.get(bk, ""),
                        detail=f"{BODY_DISPLAY.get(bk, bk)} enters {sign}",
                        sign=sign,
                        sign_symbol=sym,
                    )
                )

        # Seed-cache small bodies
        for bk in ("chiron", "ceres", "eris"):
            hits = _find_ingresses_seed(bk, start_jd, end_jd, mode)
            for jd, sign_idx in hits:
                sign = _sign_name(sign_idx, mode)
                sym = _sign_sym(sign)
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(jd),
                        event_type="ingress",
                        body=BODY_DISPLAY[bk],
                        body_symbol=BODY_SYMBOL.get(bk, ""),
                        detail=f"{BODY_DISPLAY[bk]} enters {sign}",
                        sign=sign,
                        sign_symbol=sym,
                    )
                )

    # ── Moon phases ───────────────────────────────────────────────────────────
    if include_moon_phases:
        for jd, bucket in _find_moon_phases(start_jd, end_jd):
            name = _PHASE_NAMES[bucket]
            et = _PHASE_EVENT_TYPES[bucket]
            events.append(
                SkyEvent(
                    when=_jd_to_utc(jd),
                    event_type=et,
                    body="Moon",
                    body_symbol="☽",
                    detail=name,
                )
            )

    # ── Void-of-course ────────────────────────────────────────────────────────
    if include_voc:
        for voc_start, voc_end, entering in _find_voc_windows(start_jd, end_jd, mode):
            if voc_start >= start_jd:
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(voc_start),
                        event_type="voc_start",
                        body="Moon",
                        body_symbol="☽",
                        detail="Moon void-of-course begins",
                        sign=entering,
                        sign_symbol=_sign_sym(entering),
                    )
                )
            if voc_end <= end_jd:
                events.append(
                    SkyEvent(
                        when=_jd_to_utc(voc_end),
                        event_type="voc_end",
                        body="Moon",
                        body_symbol="☽",
                        detail=f"Moon enters {entering} (VoC ends)",
                        sign=entering,
                        sign_symbol=_sign_sym(entering),
                    )
                )

    # ── Exact transiting aspects ──────────────────────────────────────────────
    if include_aspects:
        for jd, ba, bb, asp_name, asp_sym in _find_exact_aspects(start_jd, end_jd):
            ba_disp = BODY_DISPLAY.get(ba, ba.capitalize())
            bb_disp = BODY_DISPLAY.get(bb, bb.capitalize())
            events.append(
                SkyEvent(
                    when=_jd_to_utc(jd),
                    event_type="exact_aspect",
                    body=ba_disp,
                    body_symbol=BODY_SYMBOL.get(ba, ""),
                    detail=f"{ba_disp} {asp_sym} {bb_disp} (exact)",
                    body_b=bb_disp,
                    aspect_name=asp_name,
                    aspect_symbol=asp_sym,
                )
            )

    events.sort()
    return events
