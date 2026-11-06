#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "trimesh", "matplotlib", "scipy", "networkx"]
# ///
# How to run: uv run plot_section.py; actual mesh cuts, no exaggerated displacement.
"""Plot the nine real layer surfaces at y=10m, including a metric zoom."""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Intersect each saved layer surface with one fixed spanwise plane."""
    with np.load(ROOT / "artifacts/constrained-exact-02/layers.npz") as d:
        levels = d["vertices"].reshape(9, -1, 3)
        faces = d["wall_faces"]
    paths = []
    for vertices in levels:
        cut = trimesh.Trimesh(vertices, faces, process=False).section(
            plane_origin=[0, 10, 0], plane_normal=[0, 1, 0]
        )
        if cut is None:
            raise RuntimeError("MISSING_WING_SECTION")
        paths.append(cut.discrete)
    reference = np.vstack(paths[0])
    point = reference[np.argmax(reference[:, 2])]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout="constrained")
    for level, curves in enumerate(paths):
        for curve_id, curve in enumerate(curves):
            for axis in axes:
                axis.plot(
                    curve[:, 0],
                    curve[:, 2],
                    color=plt.cm.viridis(level / 8),
                    lw=0.8,
                    label=f"wall + {level}" if curve_id == 0 else None,
                )
    for axis in axes:
        axis.set(xlabel="X (m)", ylabel="Z (m)")
        axis.set_aspect("equal")
        axis.grid(alpha=0.25)
    axes[0].set_title("Actual R3 wall and 8 prism layers, Y=10 m")
    axes[1].set(
        xlim=(point[0] - 0.012, point[0] + 0.012),
        ylim=(point[2] - 0.008, point[2] + 0.016),
        title="24 mm metric window; no thickness exaggeration",
    )
    axes[1].legend(fontsize=7, loc="lower right")
    fig.suptitle(
        "Local Jacobian positive; full mesh remains FIX_FIRST (nonorthogonality/closure)",
        fontsize=11,
    )
    fig.savefig(ROOT / "evidence/layer-section.png", dpi=180)
    fig.savefig(ROOT / "evidence/layer-section.svg")
    svg = ROOT / "evidence/layer-section.svg"
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text(encoding="utf8").splitlines())
        + "\n",
        encoding="utf8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
