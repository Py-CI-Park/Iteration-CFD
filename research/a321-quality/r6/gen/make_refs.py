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
"""Deviation references for the full-span wing and horizontal tail.

The R3 wing and horizontal STLs are starboard halves with a planar cap at y = 0. R6 builds one continuous
full-span surface, so the reference is the R3 half plus its mirror image with every cap triangle at y = 0
removed (an open reference surface; the gate sampler only needs closest-point queries). Declared in the receipt.

How to run: python make_refs.py --out-dir <new dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import r6_io
import r6_ledger


def cap_stripped_mirror(tri: np.ndarray) -> np.ndarray:
    """Half surface without y = 0 cap triangles, joined with its mirror image through y = 0."""
    on_plane = np.all(tri[:, :, 1] == 0.0, axis=1)
    half = tri[~on_plane]
    mirrored = half * np.array([1.0, -1.0, 1.0], dtype=np.float32)
    return np.concatenate([half, mirrored[:, ::-1]])  # reversed winding keeps the mirror outward


def volume(tri: np.ndarray) -> float:
    t = tri.astype(np.float64)
    return float(np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    receipt: dict = {"note": "R3 half + mirror, y=0 cap triangles removed", "files": {}}
    for name in ("wing", "horizontal"):
        src = r6_ledger.R3_DIR / f"{name}.stl"
        tri = r6_io.read_stl(src)
        out = cap_stripped_mirror(tri)
        path = args.out_dir / f"ref-{name}-fullspan.stl"
        r6_io.write_stl(path, out, f"ref {name}")
        receipt["files"][name] = {
            "source": str(src), "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest(),
            "triangles_in": int(len(tri)), "cap_triangles_removed": int(len(tri) - len(out) // 2),
            "triangles_out": int(len(out)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "r3_half_volume_m3": volume(tri)}
    (args.out_dir / "refs-receipt.json").write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print(json.dumps(receipt["files"], indent=1))


if __name__ == "__main__":
    main()
