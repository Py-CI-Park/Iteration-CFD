#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic>=2", "matplotlib"]
# ///
# How to run: uv run plot_smooth_geometry.py; source-section diagnostics only, no solver.
"""Show geometric seam changes at their actual sub-millimetre scale."""

from __future__ import annotations

from pathlib import Path
from typing import Final

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from pydantic import BaseModel, ConfigDict
from smooth_loft import SOURCE, Source, Transition, linear_rings, transition

ROOT: Final = Path(__file__).resolve().parent


class PlotInput(BaseModel):
    """Use the frozen generation window, including its local thickness limit."""

    model_config = ConfigDict(frozen=True)
    transitions: tuple[Transition, ...]


def main() -> None:
    """Plot two measured wing seam trajectories without changing generated models."""
    source = Source.model_validate_json(SOURCE.read_bytes())
    recorded = PlotInput.model_validate_json(
        (ROOT / "evidence/smooth-r4.json").read_bytes()
    )
    wing = next(part for part in source.parts if part.name == "wing")
    y, rings = np.array(wing.stations_m), np.array(wing.rings_2d_m)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7.5), layout="constrained")
    for row, target in enumerate((6.0, 6.69)):
        seam = min(recorded.transitions, key=lambda item: abs(item.center_m - target))
        i = int(np.argmin(abs(y - seam.center_m)))
        h = seam.half_width_m
        q = np.linspace(y[i] - 1.3 * h, y[i] + 1.3 * h, 1501)
        before = linear_rings(y, rings, q)
        after = before.copy()
        mask = abs(q - y[i]) <= h
        after[mask] = transition(y, rings, i, h, q[mask])
        # Ring 32 is upper interior; LE/TE rings 0/64 are protected and excluded.
        z0, z1 = before[:, 32, 1], after[:, 32, 1]
        axes[row, 0].plot(q, (z0 - z0[0]) * 1000, label="R3 piecewise-linear")
        axes[row, 0].plot(q, (z1 - z0[0]) * 1000, label="R4 local Hermite")
        axes[row, 0].set(
            xlabel="span y [m]",
            ylabel="upper section z offset [mm]",
            title=f"Actual geometry near y={y[i]:.6f} m",
        )
        axes[row, 1].plot(q, np.gradient(z0, q), label="R3 dz/dy")
        axes[row, 1].plot(q, np.gradient(z1, q), label="R4 dz/dy")
        axes[row, 1].set(
            xlabel="span y [m]",
            ylabel="dz/dy [m/m]",
            title="Interior trajectory slope; not LE/TE continuity",
        )
    for ax in axes.flat:
        ax.grid(alpha=0.2)
        ax.legend(fontsize=8)
    fig.suptitle("R3 vs R4 | local wing section geometry only | no CFD solution")
    out = ROOT / "evidence/smooth-r4-sections-verified.png"
    if out.exists():
        raise RuntimeError("PLOT_ALREADY_EXISTS")
    fig.savefig(out, dpi=170)
    plt.close(fig)
    print(out)


if __name__ == "__main__":
    main()
