#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
# How to run: uv run --with pytest pytest research/a321-quality/test_native_summary.py -q
"""Requested layer count must never be published as the achieved average."""

from pathlib import Path

import pytest
from native_summary import layer_mean


def test_final_native_summary_wins_over_requested_table() -> None:
    """The first table is an input request; only the final measured row is the average."""
    log = """patch faces layers
aircraft 57556 8 0.001 0.0165

patch faces layers overall thickness
                       [m]       [%]
----- ----- ------ --- ---
aircraft 57556 3.14 0.0536 81.6
Writing mesh to time constant
"""
    assert layer_mean(log) == pytest.approx(3.14)


def test_request_only_or_missing_final_row_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="MISSING_NATIVE"):
        layer_mean("aircraft 57556 8 0.001 0.0165\n")


@pytest.mark.parametrize(
    "name, expected", [("snappy-04", 1.81), ("snappy-06", 3.14), ("snappy-07", 3.16)]
)
def test_saved_native_logs(name: str, expected: float) -> None:
    path = Path(__file__).parent / "artifacts" / name / "log.snappy"
    if not path.exists():
        pytest.skip("Large generated CPU trial is local-only")
    assert layer_mean(path.read_text()) == pytest.approx(expected)
