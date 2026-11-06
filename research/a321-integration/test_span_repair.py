#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_span_repair.py
"""Known R2 flap junction must not create a narrow trailing-edge notch."""

import json
from pathlib import Path

import numpy as np


def test_repaired_wing_has_no_narrow_chord_notch():
    # Given / When
    path = Path(__file__).resolve().parent / "evidence/reconstruction-r3.json"
    if not path.exists():
        path = (
            Path(__file__).resolve().parent.parent
            / "a321-shell/evidence/reconstruction-r2.json"
        )
    rec = json.loads(path.read_text())
    p = next(p for p in rec["parts"] if p["name"] == "wing")
    y = np.array(p["stations_m"])
    rings = np.array(p["rings_2d_m"])
    trailing = rings[:, :, 0].max(axis=1)
    slope = np.diff(trailing) / np.diff(y)
    # Then: observed R2 slope reversal is about -6.4; negative slope is spurious for this chosen clean wing.
    assert float(slope.min()) >= -0.1
