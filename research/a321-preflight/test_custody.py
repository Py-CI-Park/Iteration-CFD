#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
# ─── How to run ───
# uv run --with pytest -m pytest test_custody.py -q
"""Fail closed before overwriting any frozen input or existing result."""

from pathlib import Path

import pytest
from custody import output_file, trial_directory


def test_source_path_is_refused():
    # Given / When / Then
    with pytest.raises(RuntimeError, match="OUTPUT_OUTSIDE_ALLOWED_ROOT"):
        output_file(
            Path("D:/Chanil_Park/Project/Programming/Aircraft-Workbench/model.blend")
        )


def test_frozen_path_is_refused():
    # Given
    frozen = Path(__file__).resolve().parent / "artifacts/input/A321_G1B_FROZEN.blend"
    # When / Then
    with pytest.raises(RuntimeError, match="PROTECTED_INPUT"):
        output_file(frozen)


def test_existing_receipt_is_refused():
    # Given
    receipt = Path(__file__).resolve().parent / "evidence/native-inventory.json"
    # When / Then
    with pytest.raises(RuntimeError, match="OUTPUT_ALREADY_EXISTS"):
        output_file(receipt)


def test_existing_trial_is_refused():
    # Given
    trial = Path(__file__).resolve().parent / "artifacts/trial-v040"
    # When / Then
    with pytest.raises(RuntimeError, match="OUTPUT_ALREADY_EXISTS"):
        trial_directory(trial)
