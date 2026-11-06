#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "matplotlib", "typer", "pydantic>=2"]
# ///
# How to run: uv run map_hotspots.py --candidate snappy-03; CPU readback only.
"""Map reconstructed checkMesh sets and processor wall-layer fields to measured coordinates."""

from __future__ import annotations

import csv
import json
from itertools import pairwise
from pathlib import Path
from typing import Final

import matplotlib
import numpy as np
import typer
from custody import BoundAudit, digest, require_unchanged, snapshot_mesh, verify_binding
from hotspot_inputs import (
    checked_ids,
    diagnostic_inputs,
    layers_on_wall,
    verify_diagnostic_files,
)
from matplotlib import pyplot as plt
from numpy.typing import NDArray
from poly_geometry import face_geometry
from poly_io import (
    read_faces,
    read_patches,
    read_points,
)

ROOT: Final = Path(__file__).resolve().parent
SETS: Final = ("underdeterminedCells", "concaveCells", "lowWeightFaces")
EXPECTED_03: Final = (14798, 29759, 2624)
X_BINS: Final = (0, 12, 20, 26, 33, 39, 45)


def band_indices(points: NDArray[np.float64]) -> NDArray[np.int64]:
    """Assign disjoint longitudinal bins, using -1 for outside the chart."""
    bands = np.digitize(points[:, 0], X_BINS) - 1
    return np.where(bands < len(X_BINS) - 1, bands, -1)


def main(candidate: str = "snappy-03", audit_id: str = "v5") -> None:
    """Create a projection, complete CSV index and per-band counts for one frozen mesh."""
    if candidate not in {"snappy-03", "snappy-04", "snappy-05"} or audit_id != "v5":
        raise RuntimeError("UNSUPPORTED_CANDIDATE")
    case = ROOT / "artifacts" / candidate
    pm = case / "constant/polyMesh"
    audit_path = ROOT / "evidence" / f"{candidate}-audit-{audit_id}.json"
    audit = BoundAudit.model_validate_json(audit_path.read_text(encoding="utf8"))
    verify_binding(case, audit)
    before = snapshot_mesh(case)
    seal_path = ROOT / "evidence" / f"{candidate}-diagnostics-seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf8"))
    if seal["candidate"] != candidate or seal["mesh"] != before.model_dump():
        raise RuntimeError("DIAGNOSTIC_SEAL_WRONG_MESH")
    verify_diagnostic_files(case, seal["inputs"])
    input_paths = diagnostic_inputs(case)
    diagnostics = {p.relative_to(case).as_posix(): digest(p) for p in input_paths}
    centers_file = case / f"audited-geometry-{audit_id}.npz"
    expected = json.loads(audit_path.read_text(encoding="utf8")).get(
        "audited_geometry_sha256"
    )
    if candidate == "snappy-03":
        manifest = json.loads(
            (ROOT / "evidence/artifact-manifest.json").read_text(encoding="utf8")
        )
        expected = next(
            entry["sha256"]
            for entry in manifest
            if Path(entry["path"]).name == centers_file.name
        )
    if digest(centers_file) != expected:
        raise RuntimeError("STALE_CENTER_ARTIFACT")
    with np.load(centers_file) as data:
        centers = data["centers"]
    if len(centers) != audit.cells or not np.isfinite(centers).all():
        raise RuntimeError("AUDITED_CENTER_MISMATCH")
    vertices = read_points(pm / "points")
    faces = read_faces(pm / "faces")
    wall = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
    vectors, wall_xyz = face_geometry(
        vertices, faces[wall.start : wall.start + wall.count]
    )
    areas = np.linalg.norm(vectors, axis=1)
    layers, thickness = layers_on_wall(case, wall.start, wall.count)
    ids = [
        checked_ids(
            pm / "sets" / key, len(faces) if key.endswith("Faces") else len(centers)
        )
        for key in SETS
    ]
    if candidate == "snappy-03" and (
        tuple(map(len, ids)) != EXPECTED_03
        or int(np.sum(layers == 0)) != 22090
        or not np.isclose(
            100 * areas[layers > 0].sum() / areas.sum(), 33.267510422912096
        )
    ):
        raise RuntimeError("BASELINE_RECEIPT_MISMATCH")
    positions = [
        centers[ids[0]],
        centers[ids[1]],
        face_geometry(vertices, faces[ids[2]])[1],
    ]
    bins = band_indices(wall_xyz)
    failure_bins = [band_indices(points) for points in positions]
    rows = []
    for i, (lo, hi) in enumerate(pairwise(X_BINS)):
        mask = bins == i
        total = float(areas[mask].sum())
        missing = float(areas[mask & (layers == 0)].sum())
        rows.append(
            {
                "x_m": [lo, hi],
                "wall_area_m2": total,
                "missing_area_m2": missing,
                "missing_percent": 100 * missing / total if total else None,
                "failures": [int(np.sum(b == i)) for b in failure_bins],
            }
        )
    outside = [int(np.sum((b < 0) | (b >= len(rows)))) for b in failure_bins]
    require_unchanged(case, before)
    verify_diagnostic_files(case, seal["inputs"])
    if diagnostic_inputs(case) != input_paths or any(
        digest(case / name) != expected for name, expected in diagnostics.items()
    ):
        raise RuntimeError("HOTSPOT_INPUT_CHANGED")
    if digest(centers_file) != expected:
        raise RuntimeError("CENTERS_CHANGED_DURING_MAP")
    out = ROOT / "artifacts" / f"{candidate}-hotspot-map"
    out.mkdir(exist_ok=False)
    with (out / "coordinates.csv").open("x", newline="", encoding="utf8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "kind",
                "global_id",
                "x_m",
                "y_m",
                "z_m",
                "layers",
                "total_thickness_m",
                "area_m2",
            )
        )
        for key, labels, xyz in zip(SETS, ids, positions, strict=True):
            writer.writerows(
                (key, int(label), *point, "", "", "")
                for label, point in zip(labels, xyz, strict=True)
            )
        writer.writerows(
            ("aircraft", wall.start + i, *point, int(layers[i]), thickness[i], areas[i])
            for i, point in enumerate(wall_xyz)
        )
    evidence = ROOT / "evidence"
    receipt = {
        "candidate": candidate,
        "mesh": before.model_dump(),
        "diagnostic_seal_sha256": digest(seal_path),
        "diagnostic_seal_is_post_generation_snapshot": True,
        "diagnostics_sha256": diagnostics,
        "audited_centers_sha256": expected,
        "set_order": SETS,
        "counts": list(map(len, ids)),
        "unique_cells_in_two_cell_sets": len(np.union1d(ids[0], ids[1])),
        "outside_chart": outside,
        "wall_faces": wall.count,
        "zero_layer_faces": int(np.sum(layers == 0)),
        "covered_area_percent": float(100 * areas[layers > 0].sum() / areas.sum()),
        "full_8_layer_faces": int(np.sum(layers == 8)),
        "bins": rows,
        "note": "Longitudinal bins are projections, not named anatomical patches. Cell sets can overlap.",
    }
    (evidence / f"{candidate}-hotspots.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf8"
    )
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for ax, key, xyz in zip(
        axes.flat,
        (*SETS, "Wall faces without layers"),
        (*positions, wall_xyz[layers == 0]),
        strict=True,
    ):
        ax.scatter(
            wall_xyz[:, 0],
            wall_xyz[:, 1],
            s=0.35,
            c="#aebfcb",
            alpha=0.30,
            linewidths=0,
        )
        ax.scatter(xyz[:, 0], xyz[:, 1], s=1, c="#a32635", alpha=0.28, linewidths=0)
        ax.set(
            title=f"{key} · {len(xyz):,}",
            xlabel="x (m)",
            ylabel="y (m)",
            aspect="equal",
            xlim=(-1, 46),
            ylim=(-18, 18),
        )
        ax.grid(alpha=0.16)
    fig.suptitle(f"{candidate} | CPU mesh diagnostics · top projection · no flow field")
    fig.savefig(evidence / f"{candidate}-hotspots.png", dpi=150)
    plt.close(fig)
    print(json.dumps(receipt))


if __name__ == "__main__":
    matplotlib.use("Agg")
    typer.run(main)
