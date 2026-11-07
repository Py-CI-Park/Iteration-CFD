#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree", "pydantic>=2", "typer"]
# ///
# How to run: uv run measure_wall_centers.py --candidate snappy-06
"""Measure wall-adjacent cell-center distance, not an inferred first-layer thickness."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh
import typer
from custody import (
    BoundAudit,
    MeshDigests,
    digest,
    require_unchanged,
    snapshot_mesh,
    verify_binding,
)
from hotspot_inputs import (
    layers_on_wall,
    require_seal_identity,
    verify_diagnostic_files,
)
from poly_io import read_faces, read_labels, read_patches, read_points
from wall_surface import triangulate_wall

ROOT = Path(__file__).resolve().parent


def main(candidate: str = "snappy-06") -> None:
    """Use exact saved cell moments and float64 triangulated wall geometry."""
    if candidate not in {"snappy-04", "snappy-06", "snappy-07"}:
        raise RuntimeError("INVALID_CANDIDATE")
    case = ROOT / "artifacts" / candidate
    pm = case / "constant/polyMesh"
    audit_path = ROOT / "evidence" / f"{candidate}-audit-v5.json"
    raw = json.loads(audit_path.read_text())
    verify_binding(case, BoundAudit.model_validate(raw))
    before = snapshot_mesh(case)
    npz = case / "audited-geometry-v5.npz"
    expected = raw.get("audited_geometry_sha256")
    if digest(npz) != expected:
        raise RuntimeError("STALE_CENTERS")
    seal = json.loads(
        (ROOT / "evidence" / f"{candidate}-diagnostics-seal.json").read_text()
    )
    require_seal_identity(
        case, before, seal["candidate"], MeshDigests.model_validate(seal["mesh"])
    )
    verify_diagnostic_files(case, seal["inputs"])
    with np.load(npz) as data:
        centers = data["centers"]
    v = read_points(pm / "points")
    f = read_faces(pm / "faces")
    patch = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
    owner = read_labels(pm / "owner")[patch.start : patch.start + patch.count]
    layers, _ = layers_on_wall(case, patch.start, patch.count)
    surface = triangulate_wall(v, f[patch.start : patch.start + patch.count])
    surface.remove_unreferenced_vertices()
    distance = []
    for start in range(0, len(owner), 2000):
        _, d, _ = trimesh.proximity.closest_point(
            surface, centers[owner[start : start + 2000]]
        )
        distance.append(d)
    d = np.concatenate(distance)
    if not np.isfinite(d).all() or np.any(d <= 0):
        raise RuntimeError("INVALID_CENTER_WALL_DISTANCE")
    result = {
        "candidate": candidate,
        "definition": "Euclidean distance from each wall-adjacent owner center to nearest point of the explicit float64 calculation-wall triangles",
        "not": "not first-layer thickness, not solved wall-distance field, not y+",
        "sampling": "all wall faces, repeated owner counts retained and explicitly face-weighted",
        "wall_faces": len(owner),
        "layered_faces": int(np.sum(layers > 0)),
        "summaries_m": {},
    }
    for name, mask in (
        ("all_faces", np.ones(len(d), dtype=bool)),
        ("layered_faces", layers > 0),
        ("unlayered_faces", layers == 0),
    ):
        values = d[mask]
        result["summaries_m"][name] = (
            {
                "count": len(values),
                "min": float(values.min()),
                "median": float(np.median(values)),
                "p95": float(np.quantile(values, 0.95)),
                "max": float(values.max()),
            }
            if len(values)
            else {"count": 0}
        )
    require_unchanged(case, before)
    verify_diagnostic_files(case, seal["inputs"])
    if digest(npz) != expected:
        raise RuntimeError("CENTERS_CHANGED")
    out = case / "wall-center-distance.npz"
    with out.open("xb") as handle:
        np.savez_compressed(
            handle,
            wall_face_ids=np.arange(patch.start, patch.start + patch.count),
            owner=owner,
            layers=layers,
            distance_m=d,
        )
    result["npz_sha256"] = digest(out)
    result["mesh"] = before.model_dump()
    (ROOT / "evidence" / f"{candidate}-wall-center-distance.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    typer.run(main)
