#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: imported by the separate Blender adapter; pytest test_native_surface_binding.py.
"""Bind native input arrays to independently frozen STL triangle coordinates."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class BindingError(RuntimeError):
    """Reject a geometry correspondence or byte-identity mismatch."""

    reason: str

    def __str__(self) -> str:
        return self.reason


def bind_arrays(
    vertices: NDArray[np.float64],
    faces: NDArray[np.int64],
    stl: Path,
    expected_sha: str,
) -> None:
    """Require every indexed triangle to equal the receipt-bound binary STL."""
    data = stl.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise BindingError("STL_SHA_CHANGED")
    if len(data) < 84:
        raise BindingError("TRUNCATED_BINARY_STL")
    count = int.from_bytes(data[80:84], "little")
    if count < 1 or len(data) != 84 + 50 * count:
        raise BindingError("INVALID_BINARY_STL_LENGTH")
    dtype = np.dtype(
        [("normal", "<f4", (3,)), ("triangle", "<f4", (3, 3)), ("attribute", "<u2")]
    )
    triangles = np.frombuffer(data, dtype=dtype, count=count, offset=84)["triangle"]
    if (
        vertices.ndim != 2
        or vertices.shape[1] != 3
        or faces.shape != (count, 3)
        or not np.isfinite(vertices).all()
        or np.any(faces < 0)
        or np.any(faces >= len(vertices))
    ):
        raise BindingError("INVALID_NATIVE_ARRAYS")
    if not np.array_equal(vertices[faces], triangles):
        raise BindingError("NPZ_STL_TRIANGLES_DIFFER")
