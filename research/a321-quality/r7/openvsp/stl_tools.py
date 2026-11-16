# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""ASCII STL (OpenVSP export) -> binary STL (float32, the format the R6 gate reads), plus a SHA-256 helper."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

_DTYPE = np.dtype([("normal", "<f4", (3,)), ("tri", "<f4", (3, 3)), ("attr", "<u2")])


def read_ascii_stl(path: Path) -> np.ndarray:
    """(n, 3, 3) float64 triangles from an ASCII STL."""
    rows = []
    with path.open("rb") as stream:
        for line in stream:
            parts = line.split()
            if parts and parts[0] == b"vertex":
                rows.append((float(parts[1]), float(parts[2]), float(parts[3])))
    arr = np.asarray(rows, dtype=np.float64)
    if len(arr) % 3:
        raise ValueError(f"vertex count not a multiple of 3 in {path}")
    return arr.reshape(-1, 3, 3)


def write_binary_stl(path: Path, triangles: np.ndarray, header: str) -> None:
    """Binary STL, float32 coordinates, face normals from the winding (right-hand rule); header never starts with 'solid'."""
    tri = np.asarray(triangles, dtype=np.float32)
    n = np.cross((tri[:, 1] - tri[:, 0]).astype(np.float64), (tri[:, 2] - tri[:, 0]).astype(np.float64))
    length = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where(length > 0, n / np.where(length > 0, length, 1.0), 0.0).astype(np.float32)
    rec = np.zeros(len(tri), dtype=_DTYPE)
    rec["normal"], rec["tri"] = n, tri
    head = header.encode("ascii")[:80].ljust(80, b" ")
    with path.open("xb") as stream:
        stream.write(head + len(tri).to_bytes(4, "little") + rec.tobytes())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
