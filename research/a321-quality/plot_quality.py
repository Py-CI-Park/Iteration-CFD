#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh", "matplotlib"]
# ///
# How to run: uv run plot_quality.py; real geometric cuts, no flow computation.
"""Plot the actual computational-wall section and nearby cell-face intersections."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib
import numpy as np
import trimesh
from poly_io import read_faces, read_patches, read_points
from wall_surface import triangulate_wall

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Keep real dimensions and distinguish the reference skin from calculated mesh faces."""
    root = ROOT / "artifacts/snappy-03"
    pm = root / "constant/polyMesh"
    v = read_points(pm / "points")
    f = read_faces(pm / "faces")
    patch = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
    wall = triangulate_wall(v, f[patch.start : patch.start + patch.count])
    wall_cut = trimesh.intersections.mesh_plane(wall, [0, 1, 0], [0, 10, 0])
    reference = trimesh.load_mesh(
        ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl", process=True
    )
    reference_cut = trimesh.intersections.mesh_plane(reference, [0, 1, 0], [0, 10, 0])
    p = v[np.maximum(f, 0)]
    lo = np.where((f >= 0)[:, :, None], p, np.inf).min(axis=1)
    hi = np.where((f >= 0)[:, :, None], p, -np.inf).max(axis=1)
    selected = (
        (lo[:, 1] <= 10)
        & (hi[:, 1] >= 10)
        & (lo[:, 0] < 25)
        & (hi[:, 0] > 20)
        & (lo[:, 2] < 4.8)
        & (hi[:, 2] > 3.2)
    )
    geometry = triangulate_wall(v, f[selected])
    cut = trimesh.intersections.mesh_plane(geometry, [0, 1, 0], [0, 10, 0])
    peak = wall_cut.reshape(-1, 3)[np.argmax(wall_cut.reshape(-1, 3)[:, 2])]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for axis in axes:
        axis.add_collection(
            LineCollection(
                cut[:, :, [0, 2]],
                colors="#4997b6",
                linewidths=0.5,
                label="actual cell-face intersections",
            )
        )
        axis.add_collection(
            LineCollection(
                wall_cut[:, :, [0, 2]],
                colors="black",
                linewidths=1.2,
                label="calculation wall",
            )
        )
        axis.add_collection(
            LineCollection(
                reference_cut[:, :, [0, 2]],
                colors="#d35c41",
                linewidths=0.7,
                linestyles="dashed",
                label="preserved R3 reference",
            )
        )
        axis.set_aspect("equal")
        axis.set(xlabel="X (m)", ylabel="Z (m)")
        axis.grid(alpha=0.2)
    axes[0].set(
        xlim=(20.9, 24.6),
        ylim=(3.45, 4.35),
        title="Actual Y=10 m wing section and fluid mesh",
    )
    axes[1].set(
        xlim=(peak[0] - 0.03, peak[0] + 0.03),
        ylim=(peak[2] - 0.02, peak[2] + 0.04),
        title="60 mm metric window; no thickness exaggeration",
    )
    axes[1].legend(fontsize=7, loc="upper right")
    fig.suptitle(
        "snappy-03 hex/poly control; named numeric gates pass, engineering/GPU HOLD",
        fontsize=11,
    )
    fig.savefig(ROOT / "evidence/mesh-section.png", dpi=170)
    print(ROOT / "evidence/mesh-section.png")


if __name__ == "__main__":
    main()
