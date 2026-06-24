from __future__ import annotations

from unittest.mock import patch

import pytest

from hoshi.store import ChartInput


SAMPLE_CHARTS = [
    ChartInput(
        name="alice",
        date="1990-06-19",
        time="15:30",
        tz="America/Chicago",
        lat=30.22,
        lon=-93.22,
    ),
    ChartInput(
        name="bob",
        date="1985-03-12",
        time="08:00",
        tz="Europe/London",
        lat=51.50,
        lon=-0.12,
    ),
]


@pytest.fixture()
def mock_store():
    with (
        patch("hoshi.store.list_all", return_value=SAMPLE_CHARTS),
        patch(
            "hoshi.store.load",
            side_effect=lambda name: next(c for c in SAMPLE_CHARTS if c.name == name),
        ),
    ):
        yield
