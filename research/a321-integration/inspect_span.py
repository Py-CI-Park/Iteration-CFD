#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
# How to run: uv run inspect_span.py; CPU plots only.
"""Measure lifting-surface span discontinuities that can appear as grooves."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Plot original reconstructed section chord/camber/thickness across span."""
    record = json.loads(
        (ROOT.parent / "a321-shell/evidence/reconstruction-r2.json").read_text()
    )
    fig, axes = plt.subplots(3, 2, figsize=(14, 9))
    receipts = []
    for column, name in enumerate(["wing", "horizontal"]):
        part = next(p for p in record["parts"] if p["name"] == name)
        stations = np.array(part["stations_m"])
        rings = np.array(part["rings_2d_m"])
        lo, hi = rings[:, :, 0].min(axis=1), rings[:, :, 0].max(axis=1)
        zmin, zmax = rings[:, :, 1].min(axis=1), rings[:, :, 1].max(axis=1)
        values = [
            (lo, "leading X"),
            (hi, "trailing X"),
            (zmax - zmin, "vertical thickness"),
        ]
        for row, (array, label) in enumerate(values):
            axes[row, column].plot(stations, array, marker=".", ms=2)
            axes[row, column].set_title(f"{name}: {label}")
            axes[row, column].set_xlabel("Y [m]")
            axes[row, column].set_ylabel("m")
            axes[row, column].grid(alpha=0.25)
        derivative = np.diff(hi) / np.diff(stations)
        worst = np.argsort(np.abs(np.diff(derivative)))[-8:]
        receipts.append(
            {
                "part": name,
                "largest_trailing_slope_changes": [
                    {
                        "y": float(stations[i + 1]),
                        "change": float(np.diff(derivative)[i]),
                    }
                    for i in worst
                ],
                "min_thickness_m": float((zmax - zmin).min()),
                "max_thickness_m": float((zmax - zmin).max()),
            }
        )
    fig.tight_layout()
    fig.savefig(ROOT / "evidence/span-r2.png", dpi=140)
    plt.close(fig)
    (ROOT / "evidence/span-r2.json").write_text(
        json.dumps(receipts, indent=2), encoding="utf8"
    )
    print(json.dumps(receipts))


if __name__ == "__main__":
    main()
