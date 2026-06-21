"""The top-level `hoshi` package is the public SDK surface."""

import hoshi


def test_version_exported():
    assert isinstance(hoshi.__version__, str)
    assert hoshi.__version__.count(".") == 2


def test_all_names_are_importable():
    for name in hoshi.__all__:
        assert hasattr(hoshi, name), f"{name} in __all__ but not on package"


def test_core_constructs_present():
    for name in ("Chart", "ChartInput", "ZodiacMode", "BodyRef", "compute_aspects"):
        assert name in hoshi.__all__


def test_py_typed_marker_shipped():
    from pathlib import Path

    marker = Path(hoshi.__file__).parent / "py.typed"
    assert marker.exists()
