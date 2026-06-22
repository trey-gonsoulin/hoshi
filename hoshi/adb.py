"""Import birth data from Astro-Databank (ADB) wiki pages.

Fetches wikitext via the ADB MediaWiki API, parses the structured
``ASTRODATABANK_dma`` template, and converts it to a ``ChartInput``.
"""

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel

from hoshi.ephemeris import _ssl_context
from hoshi.store import ChartInput

ADB_API_URL = "https://www.astro.com/wiki/astro-databank/api.php"

_FRACTIONAL_OFFSET_ZONES: dict[float, str] = {
    3.5: "Asia/Tehran",
    4.5: "Asia/Kabul",
    5.5: "Asia/Kolkata",
    5.75: "Asia/Kathmandu",
    6.5: "Asia/Yangon",
    9.5: "Australia/Darwin",
    10.5: "Australia/Lord_Howe",
    -3.5: "America/St_Johns",
    -9.5: "Pacific/Marquesas",
}


class ADBError(RuntimeError):
    """Raised when an ADB fetch or parse operation fails."""


class ADBResult(BaseModel, frozen=True):
    chart_input: ChartInput
    rodden_rating: str | None = None
    source_url: str | None = None


def parse_url(url_or_title: str) -> str:
    """Extract and normalize an ADB page title from a URL or plain string."""
    stripped = url_or_title.strip()
    if stripped.startswith("http"):
        parsed = urllib.parse.urlparse(stripped)
        path = urllib.parse.unquote(parsed.path)
        prefix = "/astro-databank/"
        idx = path.find(prefix)
        if idx != -1:
            title = path[idx + len(prefix) :]
        else:
            title = path.rsplit("/", 1)[-1]
    else:
        title = stripped
    return title.replace(" ", "_")


def fetch_wikitext(title: str) -> str:
    """Fetch raw wikitext for an ADB page via the MediaWiki API."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
    }
    url = f"{ADB_API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "hoshi-astro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ADBError(
            f"Could not reach Astro-Databank ({exc}). Check your network "
            f"connection and try again."
        ) from exc

    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1":
            raise ADBError(f"ADB page not found: {title!r}")
        revisions = page.get("revisions")
        if not revisions:
            raise ADBError(f"ADB page {title!r} has no content.")
        return revisions[0]["*"]
    raise ADBError(f"Unexpected API response for {title!r}")


def parse_template(wikitext: str) -> dict[str, str]:
    """Extract key=value pairs from the ``ASTRODATABANK_dma`` template."""
    marker = "{{ASTRODATABANK_dma"
    start = wikitext.find(marker)
    if start == -1:
        raise ADBError("No ASTRODATABANK_dma template found in page.")

    depth = 0
    i = start
    end = -1
    while i < len(wikitext):
        if wikitext[i : i + 2] == "{{":
            depth += 1
            i += 2
        elif wikitext[i : i + 2] == "}}":
            depth -= 1
            if depth == 0:
                end = i
                break
            i += 2
        else:
            i += 1

    if end == -1:
        raise ADBError("Malformed ASTRODATABANK_dma template (unclosed braces).")

    body = wikitext[start + len(marker) : end]
    fields: dict[str, str] = {}
    for segment in body.split("|"):
        if "=" not in segment:
            continue
        key, _, value = segment.partition("=")
        fields[key.strip()] = value.strip()
    return fields


_COORD_RE = re.compile(r"^(\d+)([nsew])(\d+)$", re.IGNORECASE)


def parse_coordinate(coord: str) -> float:
    """Convert ADB coordinate like ``"6s10"`` to decimal degrees."""
    m = _COORD_RE.match(coord.strip())
    if not m:
        raise ValueError(f"Invalid ADB coordinate format: {coord!r}")
    deg = int(m.group(1))
    direction = m.group(2).lower()
    minutes = int(m.group(3))
    value = deg + minutes / 60.0
    if direction in ("s", "w"):
        value = -value
    return value


def parse_time(sbtime: str, sbtime_ampm: str, t_unknown: str) -> str | None:
    """Convert ADB time fields to ``HH:MM`` or ``None`` if unknown."""
    if t_unknown == "1" or not sbtime.strip():
        return None

    time_str = sbtime.strip().split(":")[0:2]
    if len(time_str) < 2:
        raise ADBError(f"Cannot parse ADB time: {sbtime!r}")
    hour = int(time_str[0])
    minute = int(time_str[1])

    ampm = sbtime_ampm.strip().upper()
    if ampm == "PM" and hour < 12:
        hour += 12
    elif ampm == "AM" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute:02d}"


_MERIDIAN_RE = re.compile(r"^h(\d+)([ew])(\d*)$", re.IGNORECASE)


def parse_timezone(stmerid: str) -> str:
    """Convert ADB meridian like ``"h3e"`` to an IANA timezone string."""
    raw = stmerid.strip()
    if not raw or raw == "h0":
        return "UTC"

    m = _MERIDIAN_RE.match(raw)
    if not m:
        raise ADBError(f"Cannot parse ADB timezone meridian: {stmerid!r}")

    hours = int(m.group(1))
    direction = m.group(2).lower()
    minutes = int(m.group(3)) if m.group(3) else 0

    offset = hours + minutes / 60.0
    if direction == "w":
        offset = -offset

    if minutes != 0:
        iana = _FRACTIONAL_OFFSET_ZONES.get(offset)
        if iana:
            return iana
        raise ADBError(
            f"Fractional UTC offset {offset:+.2f}h from {stmerid!r} has no known "
            f"IANA mapping. Use --tz to specify the timezone manually."
        )

    # Etc/GMT sign convention is inverted: Etc/GMT-3 = UTC+3
    gmt_sign = -int(offset)
    if gmt_sign == 0:
        return "UTC"
    return f"Etc/GMT{gmt_sign:+d}"


def adb_to_chart_input(url_or_title: str, name: str | None = None) -> ADBResult:
    """Fetch an ADB page and convert it to a ``ChartInput``."""
    title = parse_url(url_or_title)
    wikitext = fetch_wikitext(title)
    fields = parse_template(wikitext)

    sbdate = fields.get("sbdate", "").strip()
    if not sbdate:
        raise ADBError("ADB page has no birth date (sbdate field missing).")
    date = sbdate.replace("/", "-")

    time = parse_time(
        fields.get("sbtime", ""),
        fields.get("sbtime_ampm", ""),
        fields.get("t_unknown", "0"),
    )

    slati = fields.get("slati", "").strip()
    slong = fields.get("slong", "").strip()
    if slati and slong:
        lat = parse_coordinate(slati)
        lon = parse_coordinate(slong)
    else:
        lat = None
        lon = None

    stmerid = fields.get("stmerid", "").strip()
    if time is not None and stmerid:
        tz = parse_timezone(stmerid)
    else:
        tz = "UTC"

    chart_name = name or fields.get("sflname", "") or title.replace("_", " ")
    chart_name = chart_name.strip()

    source_url = f"https://www.astro.com/astro-databank/{urllib.parse.quote(title)}"

    return ADBResult(
        chart_input=ChartInput(
            name=chart_name,
            date=date,
            time=time,
            tz=tz,
            lat=lat,
            lon=lon,
        ),
        rodden_rating=fields.get("sroddenrating") or None,
        source_url=source_url,
    )
