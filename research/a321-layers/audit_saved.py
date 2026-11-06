#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh"]
# ///
# How to run: uv run audit_saved.py; saved polyMesh, alternate vector-area summation.
"""Read saved faces and classify remaining defects without relaxing the original gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from build_layers import jacobian_minimum
from convert_oriented import geometry

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-integration"))
from audit_polymesh import read_rows


def vector_area(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Triangulate from the first vertex; platform precision is measured in the receipt."""
    p = vertices[np.maximum(faces, 0)].astype(np.longdouble)
    sf = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]) / 2
    quad = faces[:, 3] >= 0
    sf[quad] += np.cross(p[quad, 2] - p[quad, 0], p[quad, 3] - p[quad, 0]) / 2
    return sf


def main() -> None:
    """Audit signed incidence, wall identity, closure, angles, volumes and layer Jacobians."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality", action="store_true")
    quality = parser.parse_args().quality
    root = ROOT / (
        "artifacts/quality-exterior-03" if quality else "artifacts/constrained-exact-02"
    )
    pm = root / "case/constant/polyMesh"
    v = read_rows(pm / "points", 3, True)
    f = read_rows(pm / "faces", 4)
    o = read_rows(pm / "owner", 1).ravel()
    n = read_rows(pm / "neighbour", 1).ravel()
    ni = len(n)
    with np.load(root / "hybrid.npz") as d:
        if not np.array_equal(d["vertices"], v):
            raise RuntimeError("SAVED_POINT_MISMATCH")
        tets, prisms, wall = d["tets"], d["prisms"], d["wall_faces"]
        scale, heights = d["layer_scale"], d["heights"]
    centers = np.vstack((v[tets].mean(axis=1), v[prisms].mean(axis=1)))
    closure = np.zeros((len(centers), 3), dtype=np.longdouble)
    area_sum = np.zeros(len(centers), dtype=np.longdouble)
    max_angle = 0.0
    bad_by_type = {"tet_tet": 0, "tet_prism": 0, "prism_prism": 0}
    worst = []
    band_counts = np.zeros(8, dtype=int)
    total_by_type = dict.fromkeys(bad_by_type, 0)
    volume = np.zeros(len(centers))
    for start in range(0, len(f), 100000):
        end = min(start + 100000, len(f))
        sf = vector_area(v, f[start:end])
        own = o[start:end]
        fan_sf, fan_cf = geometry(v, f[start:end])
        np.add.at(volume, own, np.einsum("ij,ij->i", fan_sf, fan_cf - centers[own]) / 3)
        np.add.at(closure, own, sf)
        np.add.at(area_sum, own, np.linalg.norm(sf, axis=1))
        k = max(0, min(end, ni) - start)
        if not k:
            continue
        nei = n[start : start + k]
        np.add.at(
            volume,
            nei,
            -np.einsum("ij,ij->i", fan_sf[:k], fan_cf[:k] - centers[nei]) / 3,
        )
        np.add.at(closure, nei, -sf[:k])
        np.add.at(area_sum, nei, np.linalg.norm(sf[:k], axis=1))
        delta = centers[nei].astype(np.longdouble) - centers[own[:k]].astype(
            np.longdouble
        )
        cosine = np.einsum("ij,ij->i", sf[:k], delta) / (
            np.linalg.norm(sf[:k], axis=1) * np.linalg.norm(delta, axis=1)
        )
        angle = np.degrees(np.arccos(np.clip(cosine, -1, 1)))
        max_angle = max(max_angle, float(angle.max()))
        for label, mask in [
            ("tet_tet", nei < len(tets)),
            ("tet_prism", (own[:k] < len(tets)) & (nei >= len(tets))),
            ("prism_prism", own[:k] >= len(tets)),
        ]:
            bad_by_type[label] += int(np.count_nonzero(mask & (angle > 70)))
            total_by_type[label] += int(mask.sum())
        layer = (own[:k] - len(tets)) // len(wall)
        good = (own[:k] >= len(tets)) & (angle > 70)
        band_counts += np.bincount(layer[good], minlength=8)
        chosen = np.argsort(angle)[-3:]
        worst.extend(
            {
                "face_id": int(start + j),
                "angle_deg": float(angle[j]),
                "owner": int(own[j]),
                "neighbour": int(nei[j]),
                "xyz_m": v[f[start + j][f[start + j] >= 0]].mean(axis=0).tolist(),
            }
            for j in chosen
        )
    relative = np.linalg.norm(closure, axis=1) / np.maximum(abs(volume), 1e-100).astype(
        np.longdouble
    ) ** (np.longdouble(2) / 3)
    wall_saved = f[ni + 768 :, :3]
    a = np.sort(wall_saved, axis=1)
    b = np.sort(wall, axis=1)
    exact_wall = np.array_equal(a[np.lexsort(a.T)], b[np.lexsort(b.T)])
    jac = jacobian_minimum(v, prisms)
    record = {
        "candidate": str(root),
        "points_exact": True,
        "wall_vertex_id_multiset_exact": bool(exact_wall),
        "cells": len(centers),
        "positive_volumes": bool(np.all(volume > 0)),
        "volume_method": "reconstructed from saved faces with shared tested fan geometry, no intermediate volume file",
        "jacobian_nonpositive": int(np.count_nonzero(jac <= 0)),
        "jacobian_min_m3": float(jac.min()),
        "max_nonorth_deg": max_angle,
        "bad_faces_by_type": bad_by_type,
        "internal_faces_by_type": total_by_type,
        "bad_prism_owner_by_band": band_counts.tolist(),
        "worst_faces": sorted(worst, key=lambda x: x["angle_deg"], reverse=True)[:12],
        "longdouble_mantissa_bits": np.finfo(np.longdouble).nmant,
        "max_relative_closure_extended": float(relative.max()),
        "max_absolute_closure_m2": float(np.linalg.norm(closure, axis=1).max()),
        "first_layer_min_m": float(scale.min() * heights[1]),
        "first_layer_median_m": float(np.median(scale) * heights[1]),
        "closure_gate": bool(relative.max() <= 1e-10),
        "nonorth_gate": bool(max_angle <= 70),
        "global_cell_overlap": "NOT_MEASURED",
        "solved_y_plus": "NOT_MEASURED",
        "status": "FIX_FIRST",
        "gpu_compute": False,
        "solver_executed": False,
        "polyMesh_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in pm.iterdir()
            if p.is_file()
        },
    }
    name = (
        "independent-quality-exterior.json"
        if quality
        else "independent-quality-v2.json"
    )
    (ROOT / "evidence" / name).write_text(json.dumps(record, indent=2), encoding="utf8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
