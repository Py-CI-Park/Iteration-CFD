#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# How to run: imported by package_conditioning.py; test_native_summary.py exercises real native log shape.
"""Extract achieved native layer statistics, distinct from the requested layers table."""

from __future__ import annotations

import re


def layer_mean(text: str) -> float:
    """Return the native mean across all wall faces from its reported summary row."""
    _prefix, marker, final_table = text.rpartition("overall thickness")
    if not marker:
        raise RuntimeError("MISSING_NATIVE_LAYER_SUMMARY")
    match = re.search(
        r"^aircraft\s+\d+\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$",
        final_table,
        flags=re.MULTILINE,
    )
    if match is None:
        raise RuntimeError("MISSING_NATIVE_LAYER_SUMMARY")
    mean = float(match[1])
    if not 0 <= mean <= 8:
        raise RuntimeError("INVALID_NATIVE_LAYER_MEAN")
    return mean
