"""Verify that astroData.json stays in sync with hoshi.info."""

import json
from pathlib import Path

ASTRO_DATA = (
    Path(__file__).parent.parent
    / "packages"
    / "hoshi-ui"
    / "src"
    / "lib"
    / "astroData.json"
)
EXPORT_SCRIPT = Path(__file__).parent.parent / "scripts" / "export_astro_data.py"


def _load_current() -> dict:
    return json.loads(ASTRO_DATA.read_text())


def _generate_fresh() -> dict:
    """Run the export script and return what it would write, without touching the file."""
    import importlib.util
    import io
    from contextlib import redirect_stdout
    from unittest.mock import patch

    captured: dict = {}

    original_write_text = Path.write_text

    def mock_write_text(self, data, *args, **kwargs):
        if self == ASTRO_DATA:
            captured["data"] = data
        else:
            original_write_text(self, data, *args, **kwargs)

    with patch.object(Path, "write_text", mock_write_text):
        with redirect_stdout(io.StringIO()):
            spec = importlib.util.spec_from_file_location("export", EXPORT_SCRIPT)
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            spec.loader.exec_module(mod)  # type: ignore[union-attr]

    return json.loads(captured["data"])


class TestAstroDataSync:
    def test_file_exists(self):
        assert ASTRO_DATA.exists(), (
            f"{ASTRO_DATA} not found — run: uv run python scripts/export_astro_data.py"
        )

    def test_contains_all_categories(self):
        data = _load_current()
        for key in (
            "planets",
            "signs",
            "angles",
            "aspects",
            "houses",
            "points",
            "retrograde",
        ):
            assert key in data, f"Missing category: {key}"

    def test_in_sync_with_info_py(self):
        """Fail if info.py was edited without re-running the export script."""
        current = _load_current()
        fresh = _generate_fresh()
        assert current == fresh, (
            "astroData.json is out of sync with hoshi/info.py. "
            "Run: uv run python scripts/export_astro_data.py"
        )

    def test_all_planets_present(self):
        from hoshi.info import PLANETS

        data = _load_current()
        for name in PLANETS:
            assert name in data["planets"], f"Missing planet: {name}"

    def test_all_signs_present(self):
        from hoshi.info import SIGNS

        data = _load_current()
        for name in SIGNS:
            assert name in data["signs"], f"Missing sign: {name}"
