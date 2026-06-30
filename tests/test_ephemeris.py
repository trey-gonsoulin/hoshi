from datetime import datetime, timezone

import pytest

from hoshi.ephemeris import (
    PLANET_ORDER,
    PlanetPosition,
    _parse_horizons_ecliptic,
    _parse_horizons_range,
    ecliptic_precession,
    json_cache_get,
    json_cache_put,
    lahiri_ayanamsa,
    positions,
    prefetch_chiron_range,
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

        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert lahiri_ayanamsa(when) == pytest.approx(23.85)

    def test_linear_growth(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0 + 365.25 * 100  # 100 years later

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())
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

        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())
        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert ecliptic_precession(when) == pytest.approx(0.0)

    def test_linear(self, monkeypatch):
        class FakeTime:
            tt = 2451545.0 + 365.25 * 50

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())
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
        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())
        monkeypatch.setattr(
            "hoshi.ephemeris._chiron_position",
            lambda _: fake_pos,
        )

        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = positions(when)
        assert set(result.keys()) == set(PLANET_ORDER)
        for pp in result.values():
            assert isinstance(pp, PlanetPosition)

    def test_exclude_chiron_skips_horizons(self, monkeypatch):
        from hoshi.ephemeris import PlanetPosition

        self._patch_skyfield(monkeypatch)

        def _boom(_):
            raise AssertionError("_chiron_position should not be called")

        monkeypatch.setattr("hoshi.ephemeris._chiron_position", _boom)

        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = positions(when, include_chiron=False)
        assert "chiron" not in result
        assert set(result.keys()) == {p for p in PLANET_ORDER if p != "chiron"}
        assert all(isinstance(pp, PlanetPosition) for pp in result.values())

    def _patch_skyfield(self, monkeypatch):
        """Stub Skyfield ephemeris/timescale so positions() needs no network."""

        class FakeAngle:
            def __init__(self, deg):
                self._deg = deg

            @property
            def degrees(self):
                return self._deg

        class FakeAstrometric:
            def ecliptic_latlon(self, epoch=None):
                return FakeAngle(0.0), FakeAngle(100.0), None

        class FakeBody:
            def observe(self, target):
                return FakeAstrometric()

        class FakeEarth:
            def at(self, t):
                return FakeBody()

        class FakeEph:
            def __getitem__(self, key):
                return FakeEarth() if key == "earth" else "target"

        class FakeTime:
            tt = tdb = ut1 = 2451545.0

            def __add__(self, other):
                return self

            def replace(self, **kw):
                return self

        class FakeTS:
            def from_datetime(self, dt):
                return FakeTime()

        monkeypatch.setattr("hoshi.ephemeris._load_ephemeris", lambda: FakeEph())
        monkeypatch.setattr("hoshi.ephemeris.timescale", lambda: FakeTS())

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            positions(datetime(2000, 1, 1))


class TestParseHorizonsRange:
    VALID_RESPONSE = """\
some header
$$SOE
 2000-Jan-01 00:00,  ,  ,  25.100,  1.200,
 2000-Jan-02 00:00,  ,  ,  25.120,  1.201,
 2000-Jan-03 00:00,  ,  ,  25.140,  1.202,
$$EOE
some footer"""

    RETROGRADE_RESPONSE = """\
$$SOE
 2000-Jan-01 00:00,  ,  ,  25.100,  1.200,
 2000-Jan-02 00:00,  ,  ,  25.080,  1.199,
$$EOE"""

    def test_date_keys(self):
        rows = _parse_horizons_range(self.VALID_RESPONSE)
        assert [r[0] for r in rows] == ["2000-01-01", "2000-01-02", "2000-01-03"]

    def test_lon_lat(self):
        rows = _parse_horizons_range(self.VALID_RESPONSE)
        assert rows[0][1] == pytest.approx(25.100)
        assert rows[0][2] == pytest.approx(1.200)

    def test_prograde(self):
        rows = _parse_horizons_range(self.VALID_RESPONSE)
        assert rows[0][3] is False
        assert rows[1][3] is False

    def test_retrograde(self):
        rows = _parse_horizons_range(self.RETROGRADE_RESPONSE)
        assert rows[0][3] is True

    def test_last_row_inherits_direction(self):
        rows = _parse_horizons_range(self.VALID_RESPONSE)
        # Last row has no successor, so delta=0 → prograde
        assert rows[-1][3] is False

    def test_missing_markers(self):
        with pytest.raises(RuntimeError, match="missing"):
            _parse_horizons_range("no markers here")

    def test_no_data_rows(self):
        with pytest.raises(RuntimeError, match="no data rows"):
            _parse_horizons_range("$$SOE\n$$EOE")


class TestPrefetchChironRange:
    MOCK_RESPONSE = """\
$$SOE
 2000-Jan-01 00:00,  ,  ,  17.500,  0.500,
 2000-Jan-02 00:00,  ,  ,  17.520,  0.501,
$$EOE"""

    def test_writes_seed_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "hoshi.ephemeris.horizons_fetch", lambda _: self.MOCK_RESPONSE
        )
        out = prefetch_chiron_range("2000-01-01", "2000-01-02", tmp_path / "seed.json")
        assert out.exists()
        data = json_cache_get(out, "2000-01-01")
        assert data is not None
        pos = PlanetPosition.model_validate(data)
        assert pos.lon == pytest.approx(17.500)
        assert pos.lat == pytest.approx(0.500)
        assert pos.retrograde is False

    def test_default_path_uses_cache_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "hoshi.ephemeris.horizons_fetch", lambda _: self.MOCK_RESPONSE
        )
        monkeypatch.setattr("hoshi.ephemeris.cache_dir", lambda: tmp_path)
        out = prefetch_chiron_range("2000-01-01", "2000-01-02")
        assert out == tmp_path / "chiron_seed.json"
        assert out.exists()

    def test_compact_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "hoshi.ephemeris.horizons_fetch", lambda _: self.MOCK_RESPONSE
        )
        out = prefetch_chiron_range("2000-01-01", "2000-01-02", tmp_path / "seed.json")
        raw = out.read_text()
        # Compact JSON: no whitespace after separators
        assert "  " not in raw


class TestChironSeedFallback:
    """_chiron_position() uses the seed cache before hitting Horizons."""

    SEED_DATA = {"2000-01-01": {"lon": 17.5, "lat": 0.5, "retrograde": False}}

    def test_seed_hit_skips_horizons(self, tmp_path, monkeypatch):
        seed = tmp_path / "chiron_seed.json"
        seed.write_text(__import__("json").dumps(self.SEED_DATA))

        monkeypatch.setattr("hoshi.ephemeris._chiron_seed_path", lambda: seed)
        monkeypatch.setattr("hoshi.ephemeris.cache_dir", lambda: tmp_path)

        def _boom(_):
            raise AssertionError("Horizons should not be called when seed hits")

        monkeypatch.setattr("hoshi.ephemeris.horizons_fetch", _boom)

        from hoshi.ephemeris import _chiron_position

        when = datetime(2000, 1, 1, 15, 30, tzinfo=timezone.utc)
        pos = _chiron_position(when)
        assert pos.lon == pytest.approx(17.5)
        assert pos.retrograde is False

    def test_minute_cache_takes_priority(self, tmp_path, monkeypatch):
        seed = tmp_path / "chiron_seed.json"
        seed.write_text(__import__("json").dumps(self.SEED_DATA))

        minute_cache = tmp_path / "chiron.json"
        minute_data = {
            "2000-01-01T15:30:00+00:00": {
                "lon": 99.9,
                "lat": 0.1,
                "retrograde": True,
            }
        }
        minute_cache.write_text(__import__("json").dumps(minute_data))

        monkeypatch.setattr("hoshi.ephemeris._chiron_seed_path", lambda: seed)
        monkeypatch.setattr("hoshi.ephemeris.cache_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "hoshi.ephemeris.horizons_fetch",
            lambda _: (_ for _ in ()).throw(AssertionError("should not call")),
        )

        from hoshi.ephemeris import _chiron_position

        when = datetime(2000, 1, 1, 15, 30, tzinfo=timezone.utc)
        pos = _chiron_position(when)
        assert pos.lon == pytest.approx(99.9)

    def test_no_seed_falls_through_to_horizons(self, tmp_path, monkeypatch):
        monkeypatch.setattr("hoshi.ephemeris._chiron_seed_path", lambda: None)
        monkeypatch.setattr("hoshi.ephemeris.cache_dir", lambda: tmp_path)

        horizons_calls = []

        def _fake_horizons(params):
            horizons_calls.append(params)
            return """\
$$SOE
 2451545.500000, , ,  17.000,  0.300,
 2451545.500694, , ,  17.001,  0.300,
$$EOE"""

        monkeypatch.setattr("hoshi.ephemeris.horizons_fetch", _fake_horizons)

        from hoshi.ephemeris import _chiron_position

        when = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
        _chiron_position(when)
        assert len(horizons_calls) == 1


class TestChironSeedPath:
    def test_returns_none_without_lambda_env(self, monkeypatch):
        monkeypatch.delenv("LAMBDA_TASK_ROOT", raising=False)
        from hoshi.ephemeris import _chiron_seed_path

        assert _chiron_seed_path() is None

    def test_returns_none_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LAMBDA_TASK_ROOT", str(tmp_path))
        from hoshi.ephemeris import _chiron_seed_path

        assert _chiron_seed_path() is None

    def test_returns_path_when_file_exists(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LAMBDA_TASK_ROOT", str(tmp_path))
        seed = tmp_path / "chiron_seed.json"
        seed.write_text("{}")
        from hoshi.ephemeris import _chiron_seed_path

        assert _chiron_seed_path() == seed


class TestHorizonsFetch:
    def test_network_failure_wrapped(self, monkeypatch):
        import urllib.error

        from hoshi.ephemeris import HorizonsError, horizons_fetch

        def _raise(*args, **kwargs):
            raise urllib.error.URLError("no route to host")

        monkeypatch.setattr("urllib.request.urlopen", _raise)
        with pytest.raises(HorizonsError, match="Could not reach JPL Horizons"):
            horizons_fetch({"format": "text"})
