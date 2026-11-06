#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "typer"]
# ///
# How to run: uv run layer_fields.py --case <case-directory>. Reads mesher diagnostics, no flow solver.
"""Read actual wall-face layer counts instead of treating requested layer count as achieved."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

import numpy as np
import typer
from poly_geometry import face_geometry
from poly_io import read_faces, read_patches, read_points

ROOT: Final = Path(__file__).resolve().parent


def wall_values(path: Path, count: int) -> np.ndarray:
    """Parse only the named aircraft patch diagnostic value list."""
    text = path.read_text(encoding="utf8")
    section = re.search(r"\baircraft\s*\{([^{}]*)\}", text, flags=re.DOTALL)
    if section is None:
        raise RuntimeError("MISSING_AIRCRAFT_FIELD")
    match = re.search(
        r"value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)",
        section[1],
        flags=re.DOTALL,
    )
    if match:
        values = np.fromstring(match[2], sep=" ")
        if len(values) != count or int(match[1]) != count:
            raise RuntimeError("FIELD_PATCH_SIZE_MISMATCH")
        return values
    uniform = re.search(r"value\s+uniform\s+([^;]+);", section[1])
    if uniform is None:
        raise RuntimeError("UNSUPPORTED_FIELD_VALUES")
    return np.full(count, float(uniform[1]))


def main(case: Path = ROOT / "artifacts/snappy-03") -> None:
    """Aggregate distributed wall diagnostics with both face count and face area weights."""
    counts = []
    thickness = []
    areas = []
    for process in sorted(case.glob("processor[0-9]*")):
        pm = process / "constant/polyMesh"
        patch = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
        faces = read_faces(pm / "faces")[patch.start : patch.start + patch.count]
        vertices = read_points(pm / "points")
        sf, _ = face_geometry(vertices, faces)
        areas.append(np.linalg.norm(sf, axis=1))
        counts.append(wall_values(process / "0/nSurfaceLayers", patch.count))
        thickness.append(wall_values(process / "0/thickness", patch.count))
    n = np.concatenate(counts)
    area = np.concatenate(areas)
    height = np.concatenate(thickness)
    unique, number = np.unique(n, return_counts=True)
    result = {
        "candidate": case.name,
        "wall_faces": len(n),
        "layer_count_histogram": {
            str(x): int(y) for x, y in zip(unique, number, strict=True)
        },
        "faces_with_layers": int(np.count_nonzero(n > 0)),
        "face_coverage_percent": float(100 * np.mean(n > 0)),
        "area_coverage_percent": float(100 * area[n > 0].sum() / area.sum()),
        "mean_layers_face_weighted": float(n.mean()),
        "mean_layers_area_weighted": float(np.average(n, weights=area)),
        "native_thickness_min_on_layered_faces_m": float(height[n > 0].min()),
        "native_thickness_median_on_layered_faces_m": float(np.median(height[n > 0])),
        "interpretation": "nSurfaceLayers/thickness are native mesher diagnostic fields; not flow solution or solved y+",
        "actual_first_layer_distribution": "NOT_DERIVED_FROM_NATIVE_TOTAL_THICKNESS",
        "gpu_compute": False,
        "solver_run": False,
    }
    (ROOT / "evidence" / f"{case.name}-layer-fields.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    typer.run(main)
