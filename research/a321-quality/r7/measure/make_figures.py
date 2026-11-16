#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "matplotlib"]
# ///
# How to run: uv run --no-project make_figures.py --out-dir figures
"""SVG figures: fitted normalised outlines versus R3, fit residuals, ring spacing. No Airbus raster and no raw trace is drawn
(only our fitted curves and residual statistics)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import r7_fit as F  # noqa: E402
import r7_fitrun  # noqa: E402
import r7_model as M  # noqa: E402
import r7_profiles as P  # noqa: E402
import r7_r3 as R  # noqa: E402
import r7_rings as RG  # noqa: E402
import r7_trace_io as T  # noqa: E402

plt.rcParams.update({"svg.fonttype": "none", "font.size": 8})
HERE = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=HERE / "figures")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw = T.load_raw()
    r3 = R.load_r3_profile()
    cs = R.constant_section(r3, 1e-3)
    n = P.build_normalisation(raw, cs["crown_z"], cs["belly_z"])
    _, fits = r7_fitrun.run(n)
    model = M.FuselageModel(fits["w"], fits["zc"], fits["zb"], cs["rho_median"])
    x = np.linspace(0.001, 44.509, 6000)
    xs = r3.stations[(r3.stations > 0.2) & (r3.stations < 44.5095)]
    keep = (r3.stations > 0.2) & (r3.stations < 44.5095)

    fig, ax = plt.subplots(2, 1, figsize=(9, 4.6), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax[0].plot(x, fits["w"](x) / 2, "k", lw=1.0, label="R7 fitted half-width (64 interior knots)")
    ax[0].plot(r3.stations[keep], r3.width[keep] / 2, "r.", ms=2, label="R3 ledger ring half-width")
    ax[0].set_ylabel("half-width y [m]"); ax[0].legend(loc="lower center"); ax[0].set_title("Top view: normalised traced half-width (fit) vs R3")
    ax[1].plot(xs, (fits["w"](xs) - r3.width[keep]) * 1000, "b", lw=0.8)
    ax[1].set_ylabel("fit - R3 width [mm]"); ax[1].set_xlabel("x [m]"); ax[1].axhline(0, color="0.6", lw=0.5)
    fig.tight_layout(); fig.savefig(args.out_dir / "fig_outline_top_vs_r3.svg"); plt.close(fig)

    fig, ax = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax[0].plot(x, fits["zc"](x), "k", lw=1.0, label="R7 fitted crown z_c")
    ax[0].plot(x, fits["zb"](x), "g", lw=1.0, label="R7 fitted belly z_b")
    ax[0].plot(r3.stations[keep], r3.crown[keep], "r.", ms=2, label="R3 crown/belly")
    ax[0].plot(r3.stations[keep], r3.belly[keep], "r.", ms=2)
    ax[0].set_aspect("auto"); ax[0].set_ylabel("z [m] (R3 frame)"); ax[0].legend(loc="lower left"); ax[0].set_title("Side view: crown and belly (fit) vs R3")
    ax[1].plot(xs, (fits["zc"](xs) - r3.crown[keep]) * 1000, "b", lw=0.8, label="crown - R3")
    ax[1].plot(xs, (fits["zb"](xs) - r3.belly[keep]) * 1000, "g", lw=0.8, label="belly - R3")
    ax[1].set_ylabel("fit - R3 [mm]"); ax[1].set_xlabel("x [m]"); ax[1].legend(loc="upper left"); ax[1].axhline(0, color="0.6", lw=0.5)
    fig.tight_layout(); fig.savefig(args.out_dir / "fig_outline_side_vs_r3.svg"); plt.close(fig)

    fig, ax = plt.subplots(3, 1, figsize=(9, 5.5), sharex=True)
    for a, (key, label) in zip(ax, (("w", "width W"), ("zc", "crown z_c"), ("zb", "belly z_b")), strict=True):
        xd, yd = F.profile_samples(n, key)
        a.plot(xd, (fits[key](xd) - yd) * 1000, "k", lw=0.5)
        a.set_ylabel(f"{label}: fit - trace [mm]"); a.axhline(0, color="0.6", lw=0.5)
    ax[-1].set_xlabel("x [m]"); ax[0].set_title("LSQ cubic B-spline residuals vs the normalised trace (64 interior knots)")
    fig.tight_layout(); fig.savefig(args.out_dir / "fig_fit_residuals.svg"); plt.close(fig)

    rule = RG.RingRule(128, 1.0e-3)
    st = RG.ring_stations(model, rule)
    dm = np.array([RG.meridian_distance(model, float(st[i]), np.array([st[i + 1]]))[0] for i in range(len(st) - 1)])
    fig, ax = plt.subplots(2, 1, figsize=(9, 4.4), sharex=True)
    ax[0].semilogy(0.5 * (st[1:] + st[:-1]), dm * 1000, "k.-", ms=2, lw=0.5)
    ax[0].semilogy(x, model.perimeter(x) / rule.n_points * 1000, "r", lw=0.7, label="circumferential edge P/N")
    ax[0].set_ylabel("edge length [mm]"); ax[0].legend(); ax[0].set_title(f"Proposed ring spacing: {len(st)} rings, N = {rule.n_points}")
    ax[1].plot(0.5 * (st[2:] + st[1:-1]), np.maximum(dm[1:] / dm[:-1], dm[:-1] / dm[1:]), "k.-", ms=2, lw=0.5)
    ax[1].axhline(1.25, color="r", lw=0.7); ax[1].set_ylabel("meridian growth ratio"); ax[1].set_xlabel("x [m]")
    fig.tight_layout(); fig.savefig(args.out_dir / "fig_ring_spacing.svg"); plt.close(fig)
    print(json.dumps({"figures": sorted(p.name for p in args.out_dir.glob("*.svg"))}))


if __name__ == "__main__":
    main()
