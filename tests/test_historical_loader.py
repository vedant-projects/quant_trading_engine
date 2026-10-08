"""CSV round-trip and continuity validation tests."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from app.data.demo import make_demo_bars
from app.data.historical_loader import (
    load_csv,
    validate_bar_sequence,
    write_bars_csv,
)
from app.utils.exceptions import DataValidationError


def test_csv_round_trip(tmp_path: Path) -> None:
    """Writing and loading preserves completed bar values."""
    original = make_demo_bars(10)
    path = write_bars_csv(original, tmp_path / "bars.csv")

    restored = load_csv(
        path,
        symbol="TEST",
        timeframe="1h",
    )

    assert restored == original


def test_gap_is_rejected() -> None:
    """A missing fixed-width bar cannot be silently ignored."""
    bars = make_demo_bars(5)
    bars[3] = replace(
        bars[3],
        timestamp=bars[3].timestamp + timedelta(hours=1),
    )

    with pytest.raises(DataValidationError):
        validate_bar_sequence(bars)


def test_duplicate_is_rejected() -> None:
    """Duplicate timestamps cannot enter the replay."""
    bars = make_demo_bars(5)
    bars[2] = replace(
        bars[2],
        timestamp=bars[1].timestamp,
    )

    with pytest.raises(DataValidationError):
        validate_bar_sequence(bars)
