#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh", "pytest"]
# ///
# How to run: uv run --with numpy --with trimesh --with pytest -m pytest test_surface_input.py.
"""Lock the byte-triggered loader workaround without changing reference coordinates."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import trimesh
from surface_input import ascii_copy


def test_control_byte_coordinates_survive_ascii_conversion(tmp_path: Path) -> None:
    """Given floats containing Windows text-mode control bytes, preserve triangles and source bytes."""
    special = np.array([0x3F80001A], dtype=np.uint32).view(np.float32)[0]
    mesh = trimesh.Trimesh(
        [[0, 0, 0], [special, 0, 0], [0, 1, 0], [0, 0, 1]],
        [[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]],
        process=False,
    )
    source = tmp_path / "binary.stl"
    mesh.export(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / "ascii.stl"
    ascii_copy(source, output)
    assert output.read_bytes().startswith(b"solid")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert np.array_equal(
        trimesh.load_mesh(source, process=False).triangles,
        trimesh.load_mesh(output, process=False).triangles,
    )
