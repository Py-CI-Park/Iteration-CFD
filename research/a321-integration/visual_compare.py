#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "matplotlib"]
# ///
# How to run: uv run visual_compare.py (CPU plot, no renderer).
"""Show measured R2 notch and R3 local interpolation in planform and span curves."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Plot actual saved profile envelopes; this is geometry, not flow data."""
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    data = []
    for path, name, color in [
        (
            ROOT.parent / "a321-shell/evidence/reconstruction-r2.json",
            "R2 baseline",
            "#dc2626",
        ),
        (ROOT / "evidence/reconstruction-r3.json", "R3 trial", "#2563eb"),
    ]:
        rec = json.loads(path.read_text())
        p = next(p for p in rec["parts"] if p["name"] == "wing")
        y = np.array(p["stations_m"])
        r = np.array(p["rings_2d_m"])
        front = r[:, :, 0].min(axis=1)
        back = r[:, :, 0].max(axis=1)
        axes[0].plot(y, front, color=color, label=name)
        axes[0].plot(y, back, color=color)
        axes[1].plot(y, back, color=color, label=name)
        axes[2].plot(y, front, color=color, label=name)
        slope = np.diff(back) / np.diff(y)
        data.append(
            {
                "candidate": name,
                "minimum_trailing_dx_dy": float(slope.min()),
                "maximum_trailing_dx_dy": float(slope.max()),
            }
        )
    axes[0].set_title("Starboard wing planform envelope")
    axes[0].set_xlabel("Y span [m]")
    axes[0].set_ylabel("X aft [m]")
    axes[1].set_xlim(5.7, 6.9)
    axes[1].set_title("Flap seam notch repair")
    axes[1].set_xlabel("Y [m]")
    axes[1].set_ylabel("Trailing X [m]")
    axes[2].set_xlim(0, 3)
    axes[2].set_title("Root leading edge extrapolation")
    axes[2].set_xlabel("Y [m]")
    axes[2].set_ylabel("Leading X [m]")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("Measured geometry change | not OEM repair / not CFD results")
    fig.tight_layout()
    fig.savefig(ROOT / "evidence/r2-r3-comparison.png", dpi=145)
    plt.close(fig)
    (ROOT / "evidence/r2-r3-comparison.json").write_text(
        json.dumps(data, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    main()
