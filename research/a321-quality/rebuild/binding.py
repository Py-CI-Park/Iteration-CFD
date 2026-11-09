#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Exact sealed binary STL-to-native correspondence, independently authored."""

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class BindingRejected(RuntimeError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def bind(
    vertices: NDArray[np.float64], faces: NDArray[np.int64], stl: Path, digest: str
) -> None:
    """Reject byte changes and differences in indexed triangle coordinates."""
    raw = stl.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise BindingRejected("STL_HASH_CHANGED")
    if len(raw) < 84:
        raise BindingRejected("INVALID_STL")
    count = int.from_bytes(raw[80:84], "little")
    if len(raw) != 84 + 50 * count or count < 1:
        raise BindingRejected("INVALID_STL")
    dtype = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, offset=84, count=count)["v"]
    if faces.shape != (count, 3) or not np.array_equal(vertices[faces], triangles):
        raise BindingRejected("NATIVE_STL_TRIANGLES_DIFFER")
