#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "matplotlib", "scipy"]
# ///
# How to run: uv run visualize_shell.py; CPU Agg only, no Blender renderer.
"""Actual mesh overview and reference section overlays for the shell report."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from profiles import section_points
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Plot every final shell triangle and measured reference envelope sections."""
    with np.load(ROOT / "artifacts/shell-r2/shell.npz") as d:
        v, f = d["vertices"], d["faces"]
    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(
        Poly3DCollection(v[f], facecolor="#a9c8e8", edgecolor="none", alpha=1)
    )
    ax.set_xlim(0, 45)
    ax.set_ylim(-18, 18)
    ax.set_zlim(0, 13)
    ax.set_box_aspect((45, 36, 13))
    ax.view_init(elev=28, azim=-135)
    ax.set_xlabel("X aft [m]")
    ax.set_ylabel("Y starboard [m]")
    ax.set_zlabel("Z up [m]")
    ax.set_title(
        "A321-derived aerodynamic shell R2 | no engines / gear / sharklets\nActual mesh; no flow result; NOT VALIDATED"
    )
    fig.tight_layout()
    fig.savefig(ROOT / "artifacts/overview.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    settings = [
        ("fuselage", 0, 5),
        ("fuselage", 0, 20),
        ("fuselage", 0, 40),
        ("wing", 1, 2),
        ("wing", 1, 10),
        ("vertical", 2, 8),
    ]
    for ax, (name, axis, station) in zip(axes.flat, settings):
        with np.load(ROOT / f"artifacts/reference/{name}.npz") as d:
            points = section_points(d["vertices"], d["faces"], axis, station)
        hull = points[ConvexHull(points).vertices]
        ax.plot(
            *np.vstack((hull, hull[0])).T,
            color="#111827",
            lw=2,
            label="reference convex outer envelope",
        )
        # Select loft triangles from the stored reconstruction rings to avoid fused-body root ambiguity.
        import json

        record = json.loads((ROOT / "evidence/reconstruction-r2.json").read_text())
        part = next(p for p in record["parts"] if p["name"] == name)
        from profiles import loft

        pv, pf = loft(np.array(part["stations_m"]), np.array(part["rings_2d_m"]), axis)
        candidate = section_points(pv, pf, axis, station)
        ch = candidate[ConvexHull(candidate).vertices]
        ax.plot(*np.vstack((ch, ch[0])).T, color="#e11d48", lw=1, label="new shell")
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(alpha=0.2)
        ax.set_title(f"{name} {'XYZ'[axis]}={station} m")
        ax.set_xlabel("m")
        ax.set_ylabel("m")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle(
        "Reference-derived envelopes vs reconstructed shell | sampled sections, not OEM proof"
    )
    fig.tight_layout()
    fig.savefig(ROOT / "artifacts/sections-r2.png", dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    main()
