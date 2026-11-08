#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pytest"]
# ///
# How to run: uv run --with numpy --with pytest -m pytest test_native_surface_binding.py
"""Reject same-sized NPZ substitution against a frozen binary STL."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import numpy as np
import pytest
from native_surface_binding import BindingError, bind_arrays


def fixture_stl(path: Path) -> str:
    """Serialize one triangle using the public binary STL record layout."""
    path.write_bytes(
        b"binding fixture".ljust(80, b" ")
        + struct.pack("<I12fH", 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_triangle_correspondence(tmp_path: Path) -> None:
    # Given a frozen STL and its exact indexed triangle.
    path = tmp_path / "part.stl"
    sha = fixture_stl(path)
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    faces = np.array([[0, 1, 2]], dtype=np.int64)
    # When / Then exact coordinates and ordering are accepted.
    bind_arrays(vertices, faces, path, sha)


def test_same_shape_coordinate_substitution_rejected(tmp_path: Path) -> None:
    # Given unchanged array counts but altered coordinates.
    path = tmp_path / "part.stl"
    sha = fixture_stl(path)
    vertices = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    # When / Then the independently frozen STL rejects the substituted NPZ.
    with pytest.raises(BindingError, match="NPZ_STL_TRIANGLES_DIFFER"):
        bind_arrays(vertices, np.array([[0, 1, 2]], dtype=np.int64), path, sha)


def test_same_coordinates_reversed_winding_rejected(tmp_path: Path) -> None:
    # Given identical vertices with reversed triangle direction.
    path = tmp_path / "part.stl"
    sha = fixture_stl(path)
    vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    # When / Then winding changes cannot obtain a matching receipt.
    with pytest.raises(BindingError, match="NPZ_STL_TRIANGLES_DIFFER"):
        bind_arrays(vertices, np.array([[0, 2, 1]], dtype=np.int64), path, sha)


def test_stl_hash_change_rejected(tmp_path: Path) -> None:
    # Given a different frozen identity.
    path = tmp_path / "part.stl"
    fixture_stl(path)
    # When / Then bytes are rejected before publishing correspondence.
    with pytest.raises(BindingError, match="STL_SHA_CHANGED"):
        bind_arrays(
            np.zeros((3, 3)), np.array([[0, 1, 2]], dtype=np.int64), path, "0" * 64
        )
