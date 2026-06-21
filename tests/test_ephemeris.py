from datetime import datetime, timezone

import pytest

from hoshi.ephemeris import (
    PLANET_ORDER,
    _parse_horizons_ecliptic,
    ecliptic_precession,
    json_cache_get,
    json_cache_put,
    lahiri_ayanamsa,
    positions,
)


class TestJsonCache:
    def test_roundtrip(self, tmp_path):
        path = tmp_path / "cache.json"
        json_cache_put(path, "k1", {"val": 42})
        assert json_cache_get(path, "k1") == {"val": 42}

    def test_missing_file(self, tmp_path):
        assert json_cache_get(tmp_path / "nope.json", "k") is None

    def test_missing_key(self, tmp_path):
        path = tmp_path / "cache.json"
        json_cache_put(path, "k1", {"val": 1})
        assert json_cache_get(path, "other") is None

    def test_merge_keys(self, tmp_path):
        path = tmp_path / "cache.json"
        json_cache_put(path, "a", {"x": 1})
        json_cache_put(path, "b", {"y": 2})
        assert json_cache_get(path, "a") == {"x": 1}
        assert json_cache_get(path, "b") == {"y": 2}

    def test_malformed_json(self, tmp_path):
        path = tmp_path / "cache.json"
        path.write_text("not json{{{")
        assert json_cache_get(path, "k") is None


class TestParseHorizonsEcliptic:
    VALID_RESPONSE = """\
some header stuff
$$SOE
 2451545.000000, , ,  25.123,  1.456,
 2451545.000694, , ,  25.125,  1.457,
$$EOE
some footer"""

    def test_valid(self):
        lon, lat, lon_next = _parse_horizons_ecliptic(self.VALID_RESPONSE)
        assert lon == pytest.approx(25.123)
        assert lat == pytest.approx(1.456)
        assert lon_next == pytest.approx(25.125)

    def test_missing_markers(self):
        with pytest.raises(RuntimeError, match="missing"):
            _parse_horizons_ecliptic("no markers here")

    def test_no_data_rows(self):
        with pytest.raises(RuntimeError, match="Expected 2"):
            _parse_horizons_ecliptic("$$SOE\n$$EOE")

    def test_one_row(self):
        body = "$$SOE\n 2451545.0, , , 25.0, 1.0,\n$$EOE"
        with pytest.raises(RuntimeError, match="Expected 2"):
            _parse_horizons_ecliptic(body)


class TestLahiriAyanamsa:
    def test_at_j2000(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._timescale", lambda: FakeTS())
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert lahiri_ayanamsa(when) == pytest.approx(23.85)

    def test_linear_growth(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0 + 365.25 * 100  # 100 years later

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._timescale", lambda: FakeTS())
        when = datetime(2100, 1, 1, 12, 0, tzinfo=timezone.utc)
        expected = 23.85 + 100 * (50.29 / 3600.0)
        assert lahiri_ayanamsa(when) == pytest.approx(expected)

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            lahiri_ayanamsa(datetime(2000, 1, 1))


class TestEclipticPrecession:
    def test_at_j2000(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._timescale", lambda: FakeTS())
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert ecliptic_precession(when) == pytest.approx(0.0)

    def test_linear(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0 + 365.25 * 50

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._timescale", lambda: FakeTS())
        when = datetime(2050, 1, 1, 12, 0, tzinfo=timezone.utc)
        expected = 50 * (50.29 / 3600.0)
        assert ecliptic_precession(when) == pytest.approx(expected)

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            ecliptic_precession(datetime(2000, 1, 1))


class TestPositions:
    def test_returns_all_planets(self, monkeypatch):
        from hoshi.ephemeris import PlanetPosition

        fake_pos = PlanetPosition(lon=100.0, lat=1.0, retrograde=False)

        class FakeAngle:
            def __init__(self, deg):
                self._deg = deg

            @property
            def degrees(self):
                return self._deg

        class FakeAstrometric:
            def __init__(self, lon):
                self._lon = lon

            def ecliptic_latlon(self, epoch=None):
                return FakeAngle(0.0), FakeAngle(self._lon), None

        class FakeBody:
            def __init__(self, lon):
                self._lon = lon

            def observe(self, target):
                return FakeAstrometric(self._lon)

        class FakeEarth:
            def at(self, t):
                return FakeBody(100.0)

        class FakeEph:
            def __getitem__(self, key):
                if key == "earth":
                    return FakeEarth()
                return "target"

        class FakeTime:
            tt = 2451545.0
            tdb = 2451545.0
            ut1 = 2451545.0

            def __add__(self, other):
                return self

            def replace(self, **kw):
                return self

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._load_ephemeris", lambda: FakeEph())
        monkeypatch.setattr("hoshi.ephemeris._timescale", lambda: FakeTS())
        monkeypatch.setattr(
            "hoshi.ephemeris._chiron_position",
            lambda _: fake_pos,
        )

        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = positions(when)
        assert set(result.keys()) == set(PLANET_ORDER)
        for pp in result.values():
            assert isinstance(pp, PlanetPosition)

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            positions(datetime(2000, 1, 1))
