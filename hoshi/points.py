"""Calculated astrological points: true lunar nodes, true Black Moon Lilith,
Part of Fortune.

True nodes and apogee come from JPL Horizons osculating orbital elements
(EPHEM_TYPE=ELEMENTS, target=301 Moon, center=500@399 geocentric, J2000
ecliptic). Per-minute cache in `.lunar_cache.json` in the cwd.

Part of Fortune is computed locally from ASC + Sun + Moon longitudes.
"""

from datetime import datetime, timezone

from pydantic import BaseModel

from hoshi.ephemeris import (
    _cache_dir,
    _timescale,
    horizons_fetch,
    json_cache_get,
    json_cache_put,
)


LUNAR_CACHE_PATH = _cache_dir() / "lunar.json"


class LunarElements(BaseModel, frozen=True):
    """Subset of Moon osculating elements we use, in ecliptic J2000.

    Derived points (true nodes and Black Moon Lilith) are exposed as
    computed properties — they're fully determined by OM and W.
    """

    om: float  # OM — longitude of ascending node (= True N. Node)
    w: float  # W  — argument of perigee, measured from ascending node

    @property
    def north_node(self) -> float:
        """True (osculating) lunar ascending node."""
        return self.om % 360.0

    @property
    def south_node(self) -> float:
        return (self.north_node + 180.0) % 360.0

    @property
    def lilith(self) -> float:
        """True Black Moon Lilith — geocentric longitude of the Moon's apogee.

        Apogee direction = node + argument of perigee + 180° (opposite of perigee).
        """
        return (self.om + self.w + 180.0) % 360.0

    @classmethod
    def at(cls, when: datetime) -> "LunarElements":
        """Fetch the Moon's osculating ecliptic orbital elements from Horizons.

        Results are cached per minute.
        """
        if when.tzinfo is None:
            raise ValueError("`when` must be timezone-aware (use UTC)")
        when_utc = when.astimezone(timezone.utc)

        cache_key = when_utc.replace(second=0, microsecond=0).isoformat()
        cached = json_cache_get(LUNAR_CACHE_PATH, cache_key)
        if cached is not None:
            return cls.model_validate(cached)

        jd = _timescale().from_datetime(when_utc).tdb
        body = horizons_fetch(
            {
                "format": "text",
                "COMMAND": "301",  # Moon
                "OBJ_DATA": "NO",
                "MAKE_EPHEM": "YES",
                "EPHEM_TYPE": "ELEMENTS",
                "CENTER": "500@399",  # geocentric
                "TLIST": f"{jd}",
                "TLIST_TYPE": "JD",
                "REF_PLANE": "ECLIPTIC",
                "OUT_UNITS": "KM-S",
                "CSV_FORMAT": "YES",
            }
        )
        om, w = _parse_horizons_elements(body)
        el = cls(om=om, w=w)
        json_cache_put(LUNAR_CACHE_PATH, cache_key, el.model_dump())
        return el


def _parse_horizons_elements(body: str) -> tuple[float, float]:
    """Pull OM, W from a Horizons ELEMENTS CSV response.

    Column order: JDTDB, CalDate, EC, QR, IN, OM, W, Tp, N, MA, TA, A, AD, PR.
    """
    lines = body.splitlines()
    try:
        start = lines.index("$$SOE")
        end = lines.index("$$EOE")
    except ValueError as exc:
        raise RuntimeError(
            f"Horizons response missing $$SOE/$$EOE:\n{body[:500]}"
        ) from exc
    rows = [ln for ln in lines[start + 1 : end] if ln.strip()]
    if not rows:
        raise RuntimeError("Horizons ELEMENTS response had no data rows")
    cols = [c.strip() for c in rows[0].split(",")]
    return float(cols[5]), float(cols[6])  # OM, W


HERMETIC_LOT_NAMES: list[str] = [
    "Fortune",
    "Spirit",
    "Eros",
    "Necessity",
    "Courage",
    "Victory",
    "Nemesis",
]


def hermetic_lots(
    asc: float,
    sun: float,
    moon: float,
    mercury: float,
    venus: float,
    mars: float,
    jupiter: float,
    saturn: float,
) -> dict[str, float]:
    """The seven Hermetic Lots, day/night-aware.

    Fortune and Spirit are the primary pair (Moon/Sun arc from ASC, reversed
    at night); the other five are built off them with the personal planet
    they correspond to (Venus→Eros, Mercury→Necessity, Mars→Courage,
    Jupiter→Victory, Saturn→Nemesis), also reversed at night.

    Day/night detected by Sun's position in the house wheel: above horizon
    iff `(sun - asc) mod 360` lands in [180, 360) (houses 7-12).
    """
    day = (sun - asc) % 360.0 >= 180.0

    def lot(a: float, b: float) -> float:
        return (asc + a - b) % 360.0 if day else (asc + b - a) % 360.0

    fortune = lot(moon, sun)
    spirit = lot(sun, moon)
    return {
        "Fortune": fortune,
        "Spirit": spirit,
        "Eros": lot(venus, spirit),
        "Necessity": lot(fortune, mercury),
        "Courage": lot(mars, fortune),
        "Victory": lot(jupiter, spirit),
        "Nemesis": lot(fortune, saturn),
    }
