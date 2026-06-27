"""Skyfield-backed ecliptic positions for the classical planets, plus a
Horizons-API fetcher for Chiron (which JPL distributes as an SPK type 21
that jplephem doesn't decode).

Positions are geocentric apparent ecliptic lon/lat in degrees, J2000 frame
to match the IAU constellation boundaries.
"""

import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from functools import cache
from pathlib import Path

from pydantic import BaseModel
from skyfield.api import load


# Skyfield target names from DE421/DE440. Outer-planet IDs are barycenters,
# which is fine for naked-eye-scale ecliptic longitude.
SKYFIELD_TARGETS: dict[str, str] = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}

PLANET_ORDER = list(SKYFIELD_TARGETS.keys()) + ["chiron"]

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
CHIRON_HORIZONS_ID = "2060;"  # trailing ';' = small-body designation


def cache_dir() -> Path:
    env = os.environ.get("HOSHI_CACHE_DIR")
    p = Path(env) if env else Path.home() / ".cache" / "hoshi"
    p.mkdir(parents=True, exist_ok=True)
    return p


class HorizonsError(RuntimeError):
    """Raised when a JPL Horizons request fails or returns unusable data.

    Carries a user-facing message; the CLI turns it into a clean error.
    """


def horizons_fetch(params: dict[str, str]) -> str:
    """GET against the Horizons API with a certifi-backed SSL context.

    Shared by Chiron (OBSERVER ephemeris) and true lunar elements (ELEMENTS).
    Network and HTTP failures are wrapped in `HorizonsError`.
    """
    url = f"{HORIZONS_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=20, context=_ssl_context()) as resp:
            return resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HorizonsError(
            f"Could not reach JPL Horizons ({exc}). Check your network connection "
            f"and try again."
        ) from exc


def json_cache_get(path: Path, key: str) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data.get(key)


def json_cache_put(path: Path, key: str, value: dict) -> None:
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}
    data[key] = value
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


class PlanetPosition(BaseModel, frozen=True):
    lon: float  # ecliptic longitude, degrees [0, 360)
    lat: float  # ecliptic latitude, degrees
    retrograde: bool


@cache
def _load_ephemeris():
    """Load DE421 (covers 1900–2050 — fine for birth charts)."""
    return load("de421.bsp")


@cache
def timescale():
    return load.timescale()


@cache
def _ssl_context() -> ssl.SSLContext:
    """SSL context that trusts certifi's CA bundle.

    stdlib `urllib` ignores certifi by default and uses OpenSSL's compiled-in
    bundle, which misses some roots on macOS.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def positions(
    when: datetime, *, include_chiron: bool = True
) -> dict[str, PlanetPosition]:
    """Return geocentric ecliptic positions for all supported bodies at `when`.

    `when` must be timezone-aware. Use UTC for reproducibility. Set
    `include_chiron=False` to skip the Horizons round-trip when Chiron isn't
    needed (e.g. the birth-time uncertainty check).
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (use UTC)")
    when_utc = when.astimezone(timezone.utc)

    eph = _load_ephemeris()
    ts = timescale()
    t = ts.from_datetime(when_utc)
    # Sample one minute later to detect retrograde via longitude derivative.
    t_next = ts.from_datetime(when_utc.replace(microsecond=0)) + (1.0 / 1440.0)

    earth = eph["earth"]
    out: dict[str, PlanetPosition] = {}
    for pid, target in SKYFIELD_TARGETS.items():
        body = eph[target]
        astrometric = earth.at(t).observe(body)  # type: ignore[reportAttributeAccessIssue]  # skyfield stubs mistype eph[...] as ndarray
        # epoch=t requests ecliptic-of-date longitudes (matching the convention
        # online Nuastro / standard astrology software use). Skyfield's
        # default ecliptic_latlon() actually returns J2000 ecliptic, which
        # differs from of-date by the precession over years since J2000.
        lat, lon, _ = astrometric.ecliptic_latlon(epoch=t)
        astrometric_next = earth.at(t_next).observe(body)  # type: ignore[reportAttributeAccessIssue]  # skyfield stubs mistype eph[...] as ndarray
        _, lon_next, _ = astrometric_next.ecliptic_latlon(epoch=t_next)

        lon_deg = lon.degrees % 360.0
        lon_next_deg = lon_next.degrees % 360.0
        # Shortest signed delta in [-180, 180].
        delta = ((lon_next_deg - lon_deg + 540.0) % 360.0) - 180.0
        retrograde = delta < 0

        out[pid] = PlanetPosition(
            lon=lon_deg,
            lat=lat.degrees,
            retrograde=retrograde,
        )

    if include_chiron:
        out["chiron"] = _chiron_position(when_utc)
    return out


def _chiron_position(when_utc: datetime) -> PlanetPosition:
    """Fetch geocentric ecliptic lon/lat for Chiron from JPL Horizons.

    Skyfield can't read Horizons' small-body SPKs (data type 21), so we use
    the OBSERVER ephemeris API and parse two epochs to derive retrograde.
    Results are cached per minute in `~/.cache/hoshi/chiron.json`.
    """
    ts = timescale()
    t = ts.from_datetime(when_utc)
    jd = t.tdb
    jd_next = jd + 1.0 / 1440.0  # +1 minute

    cache_key = when_utc.replace(second=0, microsecond=0).isoformat()
    chiron_cache_path = cache_dir() / "chiron.json"
    cached = json_cache_get(chiron_cache_path, cache_key)
    if cached is not None:
        return PlanetPosition.model_validate(cached)

    body = horizons_fetch(
        {
            "format": "text",
            "COMMAND": CHIRON_HORIZONS_ID,
            "OBJ_DATA": "NO",
            "MAKE_EPHEM": "YES",
            "EPHEM_TYPE": "OBSERVER",
            "CENTER": "500@399",  # geocentric
            "TLIST": f"{jd},{jd_next}",
            "TLIST_TYPE": "JD",
            "QUANTITIES": "31",  # observer ecliptic lon/lat (J2000)
            "ANG_FORMAT": "DEG",
            "CSV_FORMAT": "YES",
        }
    )

    lon, lat, lon_next = _parse_horizons_ecliptic(body)
    delta = ((lon_next - lon + 540.0) % 360.0) - 180.0
    pos = PlanetPosition(lon=lon % 360.0, lat=lat, retrograde=delta < 0)
    json_cache_put(chiron_cache_path, cache_key, pos.model_dump())
    return pos


def _parse_horizons_ecliptic(body: str) -> tuple[float, float, float]:
    """Pull (lon_t0, lat_t0, lon_t1) from a Horizons OBSERVER CSV response."""
    lines = body.splitlines()
    try:
        start = lines.index("$$SOE")
        end = lines.index("$$EOE")
    except ValueError as exc:
        raise HorizonsError(
            f"Horizons response missing $$SOE/$$EOE:\n{body[:500]}"
        ) from exc
    rows = [ln for ln in lines[start + 1 : end] if ln.strip()]
    if len(rows) < 2:
        raise HorizonsError(f"Expected 2 Horizons rows, got {len(rows)}: {rows}")
    # CSV columns: date, solar-presence, lunar-presence, lon, lat, (trailing)
    cols0 = [c.strip() for c in rows[0].split(",")]
    cols1 = [c.strip() for c in rows[1].split(",")]
    return float(cols0[3]), float(cols0[4]), float(cols1[3])


def lahiri_ayanamsa(when: datetime) -> float:
    """Approximate Lahiri ayanamsa (degrees) for sidereal/Vedic mode.

    Simple linear model anchored at J2000. Accurate to a few arcminutes —
    fine for chart display, not for ephemeris-grade work.
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware (use UTC)")
    when_utc = when.astimezone(timezone.utc)
    ts = timescale()
    t = ts.from_datetime(when_utc)
    years_since_j2000 = (t.tt - 2451545.0) / 365.25
    return 23.85 + years_since_j2000 * (50.29 / 3600.0)


def ecliptic_precession(when: datetime) -> float:
    """Degrees of ecliptic precession since J2000.0 at the given moment.

    Subtracting this from an of-date ecliptic longitude converts it to J2000.
    """
    if when.tzinfo is None:
        raise ValueError("`when` must be timezone-aware")
    when_utc = when.astimezone(timezone.utc)
    t = timescale().from_datetime(when_utc)
    years_since_j2000 = (t.tt - 2451545.0) / 365.25
    return years_since_j2000 * (50.29 / 3600.0)
