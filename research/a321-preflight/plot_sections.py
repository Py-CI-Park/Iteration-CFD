#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "matplotlib"]
# ///
# ─── How to run ───
# uv run plot_sections.py RESEARCH_ROOT
# CPU Agg/SVG plotting only; no Blender renderer or CUDA.
# Original research diagnostic, no GPL source consulted or copied.
"""Overlay actual triangle-plane sections of source and rejected candidates."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection


def sections(vertices, faces, axis: int, value: float):
    """Intersect noncoplanar triangles with a plane; coplanar triangles omitted."""
    tri = vertices[faces]
    tri = tri[
        (tri[:, :, axis].min(axis=1) < value) & (tri[:, :, axis].max(axis=1) > value)
    ]
    lines = []
    for triangle in tri:
        crossings = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            a, b = triangle[i], triangle[j]
            if (a[axis] < value) != (b[axis] < value):
                crossings.append(
                    a + (b - a) * ((value - a[axis]) / (b[axis] - a[axis]))
                )
        if len(crossings) == 2:
            lines.append(np.delete(crossings, axis, axis=1))
    return lines


def main() -> None:
    """Write reproducible visual diagnostic sections for shape review."""
    root = Path(sys.argv[1])
    if root.resolve() != Path(__file__).resolve().parent:
        raise RuntimeError("PLOT_ROOT_MISMATCH")
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    configs = [(0, 5), (0, 20), (0, 35), (1, 5), (1, 10), (1, 15)]
    for filename, label, color in [
        ("trial-v040/source-surface.npz", "extracted source", "#111827"),
        ("trial-v080/trial-surface.npz", "80 mm rejected", "#dc2626"),
        ("trial-v040/trial-surface.npz", "40 mm rejected", "#2563eb"),
    ]:
        with np.load(root / "artifacts" / filename) as data:
            for ax, (axis, location) in zip(axes.flat, configs):
                lines = sections(data["vertices"], data["faces"], axis, location)
                ax.add_collection(
                    LineCollection(
                        lines, colors=color, linewidths=0.65, alpha=0.8, label=label
                    )
                )
                ax.autoscale()
    for ax, (axis, location) in zip(axes.flat, configs):
        ax.set_title(f"{'XYZ'[axis]} = {location} m; actual triangle sections")
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(alpha=0.2)
        ax.set_xlabel("Y [m]" if axis == 0 else "X [m]")
        ax.set_ylabel("Z [m]")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle(
        "A321 CPU surface trials: closure alone does not preserve aircraft geometry\nNo flow solution; no GPU compute",
        fontsize=15,
    )
    fig.tight_layout()
    fig.savefig(root / "evidence" / "sections.svg")
    fig.savefig(root / "artifacts" / "sections.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
