import json
from io import BytesIO
from unittest.mock import patch

import pytest

from hoshi.adb import (
    ADBError,
    adb_to_chart_input,
    parse_coordinate,
    parse_template,
    parse_time,
    parse_timezone,
    parse_url,
)

# ---------------------------------------------------------------------------
# Sample wikitext fixture (trimmed from real Mercury, Freddie page)
# ---------------------------------------------------------------------------

SAMPLE_WIKITEXT = """\
__NOTOC__
{{ASTRODATABANK_dma
|DatamainID=19726
|Name=Mercury, Freddie
|sflname=Freddie Mercury
|sbdate=1946/09/05
|sbdate_dmy=5 September 1946
|sbtime=
|t_unknown=1
|sbtime_ampm=
|Place=Zanzibar
|BirthCountry=Tanzania
|slati=6s10
|slong=39e11
|TmZnAbbr=MSK
|stmerid=h3e
|sroddenrating=X
|Gender=M
}}
{{ASTRODATABANK_img
|DatamainID=19726
}}
==Biography==
British superstar musician.
"""

SAMPLE_WIKITEXT_WITH_TIME = """\
__NOTOC__
{{ASTRODATABANK_dma
|Name=Lennon, John
|sflname=John Lennon
|sbdate=1940/10/09
|sbtime=6:30
|t_unknown=0
|sbtime_ampm=PM
|Place=Liverpool
|BirthCountry=England
|slati=53n25
|slong=2w55
|stmerid=h0
|sroddenrating=AA
}}
"""


class TestParseUrl:
    def test_full_url(self):
        url = "https://www.astro.com/astro-databank/Mercury,_Freddie"
        assert parse_url(url) == "Mercury,_Freddie"

    def test_plain_title_with_spaces(self):
        assert parse_url("Mercury, Freddie") == "Mercury,_Freddie"

    def test_title_already_underscored(self):
        assert parse_url("Mercury,_Freddie") == "Mercury,_Freddie"

    def test_url_with_encoded_chars(self):
        url = "https://www.astro.com/astro-databank/Mercury%2C_Freddie"
        assert parse_url(url) == "Mercury,_Freddie"

    def test_strips_whitespace(self):
        assert parse_url("  Lennon, John  ") == "Lennon,_John"


class TestParseTemplate:
    def test_extracts_fields(self):
        fields = parse_template(SAMPLE_WIKITEXT)
        assert fields["Name"] == "Mercury, Freddie"
        assert fields["sflname"] == "Freddie Mercury"
        assert fields["sbdate"] == "1946/09/05"
        assert fields["slati"] == "6s10"
        assert fields["slong"] == "39e11"
        assert fields["stmerid"] == "h3e"
        assert fields["sroddenrating"] == "X"
        assert fields["t_unknown"] == "1"

    def test_missing_template_raises(self):
        with pytest.raises(ADBError, match="No ASTRODATABANK_dma"):
            parse_template("==Biography==\nSome text here.")

    def test_with_time(self):
        fields = parse_template(SAMPLE_WIKITEXT_WITH_TIME)
        assert fields["sbtime"] == "6:30"
        assert fields["sbtime_ampm"] == "PM"
        assert fields["t_unknown"] == "0"


class TestParseCoordinate:
    def test_south(self):
        assert parse_coordinate("6s10") == pytest.approx(-6.1667, abs=0.001)

    def test_east(self):
        assert parse_coordinate("39e11") == pytest.approx(39.1833, abs=0.001)

    def test_north(self):
        assert parse_coordinate("51n30") == pytest.approx(51.5)

    def test_west(self):
        assert parse_coordinate("122w25") == pytest.approx(-122.4167, abs=0.001)

    def test_zero(self):
        assert parse_coordinate("0n0") == 0.0

    def test_single_digit_minutes(self):
        assert parse_coordinate("1w5") == pytest.approx(-1.0833, abs=0.001)

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid ADB coordinate"):
            parse_coordinate("bad")


class TestParseTime:
    def test_24h_format(self):
        assert parse_time("14:30", "", "0") == "14:30"

    def test_12h_pm(self):
        assert parse_time("6:30", "PM", "0") == "18:30"

    def test_12h_am(self):
        assert parse_time("8:15", "AM", "0") == "08:15"

    def test_noon_pm(self):
        assert parse_time("12:00", "PM", "0") == "12:00"

    def test_midnight_am(self):
        assert parse_time("12:00", "AM", "0") == "00:00"

    def test_unknown(self):
        assert parse_time("", "", "1") is None

    def test_unknown_flag_overrides_time(self):
        assert parse_time("14:30", "", "1") is None

    def test_empty_time_no_flag(self):
        assert parse_time("", "", "0") is None

    def test_with_seconds_stripped(self):
        assert parse_time("14:30:00", "", "0") == "14:30"


class TestParseTimezone:
    def test_east(self):
        assert parse_timezone("h3e") == "Etc/GMT-3"

    def test_west(self):
        assert parse_timezone("h5w") == "Etc/GMT+5"

    def test_utc_h0(self):
        assert parse_timezone("h0") == "UTC"

    def test_empty(self):
        assert parse_timezone("") == "UTC"

    def test_fractional_india(self):
        assert parse_timezone("h5e30") == "Asia/Kolkata"

    def test_fractional_newfoundland(self):
        assert parse_timezone("h3w30") == "America/St_Johns"

    def test_unknown_fractional_raises(self):
        with pytest.raises(ADBError, match="no known IANA mapping"):
            parse_timezone("h7e30")

    def test_invalid_format_raises(self):
        with pytest.raises(ADBError, match="Cannot parse ADB timezone"):
            parse_timezone("xyz")


class TestAdbToChartInput:
    def _mock_api_response(self, wikitext: str):
        body = json.dumps(
            {"query": {"pages": {"12345": {"revisions": [{"*": wikitext}]}}}}
        ).encode()
        return BytesIO(body)

    def test_time_unknown(self):
        with patch("hoshi.adb.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: self._mock_api_response(
                SAMPLE_WIKITEXT
            )
            mock_open.return_value.__exit__ = lambda s, *a: None
            result = adb_to_chart_input("Mercury, Freddie")

        ci = result.chart_input
        assert ci.name == "Freddie Mercury"
        assert ci.date == "1946-09-05"
        assert ci.time is None
        assert ci.lat == pytest.approx(-6.1667, abs=0.001)
        assert ci.lon == pytest.approx(39.1833, abs=0.001)
        assert result.rodden_rating == "X"

    def test_with_time(self):
        with patch("hoshi.adb.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: self._mock_api_response(
                SAMPLE_WIKITEXT_WITH_TIME
            )
            mock_open.return_value.__exit__ = lambda s, *a: None
            result = adb_to_chart_input("Lennon, John")

        ci = result.chart_input
        assert ci.name == "John Lennon"
        assert ci.date == "1940-10-09"
        assert ci.time == "18:30"
        assert ci.tz == "UTC"
        assert ci.lat == pytest.approx(53.4167, abs=0.001)
        assert ci.lon == pytest.approx(-2.9167, abs=0.001)
        assert result.rodden_rating == "AA"

    def test_name_override(self):
        with patch("hoshi.adb.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: self._mock_api_response(
                SAMPLE_WIKITEXT
            )
            mock_open.return_value.__exit__ = lambda s, *a: None
            result = adb_to_chart_input("Mercury, Freddie", name="freddie")

        assert result.chart_input.name == "freddie"

    def test_page_not_found(self):
        body = json.dumps(
            {"query": {"pages": {"-1": {"title": "Nonexistent"}}}}
        ).encode()
        with patch("hoshi.adb.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__ = lambda s: BytesIO(body)
            mock_open.return_value.__exit__ = lambda s, *a: None
            with pytest.raises(ADBError, match="page not found"):
                adb_to_chart_input("Nonexistent_Person")
