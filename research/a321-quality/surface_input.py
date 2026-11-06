#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh"]
# ///
# How to run: imported by netgen_surface.py; explicit ASCII STL adapter for the Windows loader.
"""Preserve triangle coordinates while avoiding binary text-mode control bytes."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh


def ascii_copy(source: Path, output: Path) -> None:
    """Write a fresh ASCII copy and verify every triangle coordinate round-trips exactly."""
    if output.exists():
        raise RuntimeError("ASCII_OUTPUT_EXISTS")
    mesh = trimesh.load_mesh(source, process=False)
    output.write_text(
        mesh.export(file_type="stl_ascii"), encoding="ascii", newline="\n"
    )
    copy = trimesh.load_mesh(output, process=False)
    if not np.array_equal(mesh.triangles, copy.triangles):
        raise RuntimeError("ASCII_COORDINATE_CHANGE")
