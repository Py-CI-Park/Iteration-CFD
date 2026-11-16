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
"""Binary STL read/write and exact-coordinate welding for the R6 generator tools (numpy only)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

_DTYPE = np.dtype([("normal", "<f4", (3,)), ("tri", "<f4", (3, 3)), ("attr", "<u2")])


def read_stl(path: Path) -> NDArray[np.float32]:
    """(n, 3, 3) float32 triangles of a binary STL; refuses ASCII or truncated files."""
    data = path.read_bytes()
    count = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + 50 * count:
        raise ValueError(f"not a binary STL: {path}")
    return np.frombuffer(data, dtype=_DTYPE, count=count, offset=84)["tri"].copy()


def write_stl(path: Path, triangles: NDArray, name: str) -> None:
    """Binary STL with float32 coordinates, per-facet normals, header = free text (never "solid ...")."""
    tri = np.asarray(triangles, dtype=np.float32)
    n = np.cross((tri[:, 1] - tri[:, 0]).astype(np.float64), (tri[:, 2] - tri[:, 0]).astype(np.float64))
    length = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where(length > 0, n / np.where(length > 0, length, 1.0), 0.0).astype(np.float32)
    rec = np.zeros(len(tri), dtype=_DTYPE)
    rec["normal"], rec["tri"] = n, tri
    header = f"r6 binary stl {name}".encode("ascii")[:80].ljust(80, b" ")  # must not start with "solid" (OpenFOAM would parse ASCII)
    with path.open("xb") as stream:
        stream.write(header + len(tri).to_bytes(4, "little") + rec.tobytes())


def weld(triangles: NDArray) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    """Exact-coordinate weld (value equality, -0.0 == +0.0): vertices (m,3) and faces (n,3)."""
    flat = np.asarray(triangles, dtype=np.float64).reshape(-1, 3) + 0.0
    unique, inverse = np.unique(flat, axis=0, return_inverse=True)
    return unique, inverse.reshape(-1, 3).astype(np.int64)
