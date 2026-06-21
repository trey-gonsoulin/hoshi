import pytest

from hoshi import store
from hoshi.store import ChartInput, _safe_filename


@pytest.fixture
def charts_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "CHARTS_DIR", tmp_path)
    return tmp_path


class TestChartInput:
    def test_to_datetime_with_time(self):
        ci = ChartInput(
            name="test", date="2000-01-01", time="14:30", tz="America/Chicago"
        )
        dt = ci.to_datetime()
        assert dt.hour == 14
        assert dt.minute == 30
        assert dt.tzinfo is not None

    def test_to_datetime_without_time(self):
        ci = ChartInput(name="test", date="2000-01-01")
        dt = ci.to_datetime()
        assert dt.hour == 12
        assert dt.minute == 0
        assert str(dt.tzinfo) == "UTC"

    def test_time_known_true(self):
        ci = ChartInput(name="test", date="2000-01-01", time="12:00")
        assert ci.time_known is True

    def test_time_known_false(self):
        ci = ChartInput(name="test", date="2000-01-01")
        assert ci.time_known is False

    def test_location_known_true(self):
        ci = ChartInput(name="test", date="2000-01-01", lat=41.88, lon=-87.65)
        assert ci.location_known is True

    def test_location_known_false_no_lat(self):
        ci = ChartInput(name="test", date="2000-01-01", lon=-87.65)
        assert ci.location_known is False

    def test_location_known_false_no_lon(self):
        ci = ChartInput(name="test", date="2000-01-01", lat=41.88)
        assert ci.location_known is False


class TestSafeFilename:
    def test_simple(self):
        assert _safe_filename("Alice") == "alice"

    def test_spaces(self):
        assert _safe_filename("Foo Bar") == "foo_bar"

    def test_special_chars(self):
        result = _safe_filename("Hello! World?")
        assert result == "hello_world"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _safe_filename("!!!")


class TestStoreCrud:
    def _sample_input(self, name="test"):
        return ChartInput(name=name, date="2000-01-01", time="12:00", lat=0.0, lon=0.0)

    def test_save_creates_file(self, charts_dir):
        ci = self._sample_input()
        path = store.save(ci)
        assert path.exists()

    def test_round_trip(self, charts_dir):
        ci = self._sample_input("Alice")
        store.save(ci)
        loaded = store.load("Alice")
        assert loaded.date == ci.date
        assert loaded.time == ci.time
        assert loaded.lat == ci.lat
        assert loaded.lon == ci.lon

    def test_save_duplicate_raises(self, charts_dir):
        ci = self._sample_input()
        store.save(ci)
        with pytest.raises(FileExistsError):
            store.save(ci)

    def test_save_overwrite(self, charts_dir):
        ci = self._sample_input()
        store.save(ci)
        store.save(ci, overwrite=True)

    def test_load_missing_raises(self, charts_dir):
        with pytest.raises(FileNotFoundError):
            store.load("nonexistent")

    def test_exists_true(self, charts_dir):
        ci = self._sample_input()
        store.save(ci)
        assert store.exists("test") is True

    def test_exists_false(self, charts_dir):
        assert store.exists("nonexistent") is False

    def test_delete(self, charts_dir):
        ci = self._sample_input()
        store.save(ci)
        store.delete("test")
        assert store.exists("test") is False

    def test_delete_missing_raises(self, charts_dir):
        with pytest.raises(FileNotFoundError):
            store.delete("nonexistent")

    def test_list_all_empty(self, charts_dir):
        assert store.list_all() == []

    def test_list_all_multiple(self, charts_dir):
        for name in ["alice", "bob", "carol"]:
            store.save(self._sample_input(name))
        result = store.list_all()
        assert len(result) == 3

    def test_list_all_skips_malformed(self, charts_dir):
        store.save(self._sample_input("good"))
        (charts_dir / "bad.json").write_text("not json{{{")
        result = store.list_all()
        assert len(result) == 1
