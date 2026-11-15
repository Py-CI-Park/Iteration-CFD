#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "matplotlib"]
# ///
# How to run: uv run make_figures.py --reference reference-dimensions.json --models model-measurements.json --out-dir figures
"""Line-only comparison figures: model outlines against our own drawing-derived key lines.

No Airbus raster and no traced outline is drawn. Only numbers from reference-dimensions.json
(our measurements, labelled by origin) and model sections from model-measurements.json.
SVG is written because the repository ignores *.png.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

MODEL = "#1f4fd8"
MODEL_R5 = "#d8421f"
REF = "#222222"
PRINTED = "#0a8a3a"


PNG_DIR: Path | None = None


def save(fig, out: Path) -> None:
    fig.savefig(out, format="svg")
    if PNG_DIR is not None:  # optional preview outside the repository
        fig.savefig(PNG_DIR / (out.stem + ".png"), dpi=110)
    plt.close(fig)


def fuselage_arrays(models: dict[str, Any]) -> np.ndarray:
    return np.array(models["R3_components"]["fuselage"]["profile_x_halfwidth_zmin_zmax"])


def mirror(xs, ys):
    return np.concatenate([xs, xs[::-1]]), np.concatenate([ys, -ys[::-1]])


def top_figure(ref: dict, models: dict, out: Path) -> None:
    top = ref["drawn_planform_and_profile"]["top"]
    fus = fuselage_arrays(models)
    fig, ax = plt.subplots(figsize=(13, 8))
    for name, colour, ls in (("R3", MODEL, "-"), ("R5C", MODEL_R5, "--")):
        asm = models[name]["assembly"]
        w = asm["wing"]["profile"]
        y = np.array([r["y"] for r in w])
        ax.plot([r["le_x"] for r in w], y, color=colour, ls=ls, lw=1.4, label=f"{name} wing LE/TE (sections)")
        ax.plot([r["te_x"] for r in w], y, color=colour, ls=ls, lw=1.4)
        ax.plot([r["le_x"] for r in w], -y, color=colour, ls=ls, lw=1.4)
        ax.plot([r["te_x"] for r in w], -y, color=colour, ls=ls, lw=1.4)
        h = asm["tail"]["ht_rows"]
        yh = np.array([r["y"] for r in h])
        for sgn in (1, -1):
            ax.plot([r["le_x"] for r in h], sgn * yh, color=colour, ls=ls, lw=1.2)
            ax.plot([r["te_x"] for r in h], sgn * yh, color=colour, ls=ls, lw=1.2)
    ax.plot(*mirror(fus[:, 0], fus[:, 1]), color=MODEL, lw=1.4, label="R3 fuselage half-width")
    # drawing-derived key lines (our measurements, page-74 uniform scale)
    le, te = top["wing_outboard_LE_line"], top["wing_outboard_TE_line"]
    for sgn in (1, -1):
        ax.plot([le["x_at_y_m"]["y8.6"], le["x_at_y_m"]["y17.4"]], [sgn * 8.6, sgn * 17.4], color=REF, lw=0.9, ls=":", label="drawing LE/TE fit, y 8.6-17.4 m" if sgn == 1 else None)
        ax.plot([te["x_at_y_m"]["y8.6"], te["x_at_y_m"]["y17.4"]], [sgn * 8.6, sgn * 17.4], color=REF, lw=0.9, ls=":")
        b = top["wing_sharklet_break_line"]
        ax.plot([b["x_le_m"], b["x_te_m"]], [sgn * b["y_m_uniform_scale"]] * 2, color=REF, lw=2.0, label="drawn wing/sharklet break line (y %.2f m at page scale)" % b["y_m_uniform_scale"] if sgn == 1 else None)
        ax.axhline(sgn * 16.29, color=PRINTED, lw=1.0, ls="--", label="printed 16.29 m" if sgn == 1 else None)
        ax.axhline(sgn * 17.90, color=PRINTED, lw=0.8, ls="-.", label="printed 17.90 m (35.80 / 2)" if sgn == 1 else None)
        ax.axhline(sgn * 6.225, xmin=0.82, color=PRINTED, lw=0.8, ls="--")
    ax.axvline(0, color=PRINTED, lw=0.8)
    ax.axvline(44.51, color=PRINTED, lw=0.8, label="printed 44.51 m")
    ax.set_aspect("equal")
    ax.set_xlabel("x from nose [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("Top view: R3 / R5-C sections vs drawing-derived key lines (not OEM data; drawn-scale uncertainty ~1 %)")
    ax.grid(True, lw=0.3)
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    save(fig, out)


def side_figure(ref: dict, models: dict, out: Path) -> None:
    side = ref["drawn_planform_and_profile"]["side"]
    fus = fuselage_arrays(models)
    asm = models["R3"]["assembly"]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    ax.plot(fus[:, 0], fus[:, 3], color=MODEL, label="R3 fuselage crown / belly")
    ax.plot(fus[:, 0], fus[:, 2], color=MODEL)
    vt = asm["tail"]["vt_rows"]
    ax.plot([r["le_x"] for r in vt], [r["z"] for r in vt], color=MODEL, lw=1.4)
    ax.plot([r["te_x"] for r in vt], [r["z"] for r in vt], color=MODEL, lw=1.4)
    ax.axhline(0, color=REF, lw=1.0, label="drawn ground line (z = 0)")
    for z, lab in ((side["crown_z_m"], "drawn crown"), (side["belly_z_m"], "drawn belly"), (side["fin_tip_z_m"], "drawn fin tip")):
        ax.axhline(z, color=REF, lw=0.8, ls=":")
        ax.text(0.3, z + 0.08, f"{lab} z = {z:.2f} (side-sheet scale)", fontsize=7)
    ax.plot([side["fin_tip_x_m"][0], side["fin_tip_x_m"][1]], [side["fin_tip_z_m"]] * 2, color=REF, lw=2.0, label="drawn fin tip chord")
    x_root = side["fin_LE_root_x_m_at_crown_extrapolated"]
    ax.plot([x_root, side["fin_tip_x_m"][0]], [side["crown_z_m"], side["fin_tip_z_m"]], color=REF, lw=0.9, ls="--", label="drawn fin LE (fit)")
    fus_top = models["R3"]["assembly"]["fuselage"]
    ax.axhline(fus_top["crown_z_m"], color=PRINTED, lw=0.9, ls="--", label=f"R3 crown z = {fus_top['crown_z_m']:.3f}; belly {fus_top['belly_z_m']:.3f}")
    ax.set_aspect("equal")
    ax.set_xlabel("x from nose [m]")
    ax.set_ylabel("z above ground line [m]")
    ax.set_title("Side view: R3 vs drawing-derived lines (R3 sits ~0.15 m higher than the drawn ground line; labels 4.14 and 5.87 m are met by R3)")
    ax.grid(True, lw=0.3)
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    save(fig, out)


def front_figure(ref: dict, models: dict, out: Path) -> None:
    front = ref["drawn_planform_and_profile"]["front"]
    fig, ax = plt.subplots(figsize=(13, 6))
    for name, colour, ls in (("R3", MODEL, "-"), ("R5C", MODEL_R5, "--")):
        asm = models[name]["assembly"]
        w = asm["wing"]["profile"]
        y = np.array([r["y"] for r in w])
        for sgn in (1, -1):
            ax.plot(sgn * y, [r["z_max"] for r in w], color=colour, ls=ls, lw=1.3, label=f"{name} wing upper / lower section z" if sgn == 1 else None)
            ax.plot(sgn * y, [r["z_min"] for r in w], color=colour, ls=ls, lw=1.3)
        h = asm["tail"]["ht_rows"]
        yh = np.array([r["y"] for r in h])
        for sgn in (1, -1):
            ax.plot(sgn * yh, [r["z_max"] for r in h], color=colour, ls=ls, lw=1.1)
            ax.plot(sgn * yh, [r["z_min"] for r in h], color=colour, ls=ls, lw=1.1)
    ax.plot([0, 0], [models["R3"]["assembly"]["fuselage"]["belly_z_m"], models["R3"]["assembly"]["highest_z_m"]], color=MODEL, lw=1.0, label="R3 centreline extent (belly to fin tip)")
    ax.axhline(0, color=REF, lw=1.0, label="drawn ground line")
    for sgn in (1, -1):
        ax.plot(sgn * front["sharklet_top_half_span_m_front_scale"], front["sharklet_top_z_m"], "o", color=REF, ms=4, label="drawn sharklet top (front-sheet scale)" if sgn == 1 else None)
        ax.axhline(front["wing_tip_base_line_z_m"], color=REF, lw=0.7, ls=":")
        ax.plot(sgn * front["ht_tip_half_span_m_front_scale"], front["ht_tip_z_m"], "s", color=REF, ms=4, label="drawn HT tip" if sgn == 1 else None)
        ax.axvline(sgn * 17.90, color=PRINTED, lw=0.8, ls="-.", label="printed 17.90 m" if sgn == 1 else None)
        ax.axvline(sgn * 16.29, color=PRINTED, lw=0.8, ls="--", label="printed 16.29 m" if sgn == 1 else None)
    ax.axhline(front["wing_root_lower_ref_line_z_m"], color=REF, lw=0.7, ls=":", label="drawn wing-root lower ref line / wing-tip base line")
    ax.set_aspect("equal")
    ax.set_xlabel("y [m]")
    ax.set_ylabel("z above ground line [m]")
    ax.set_title("Front view: wing and tail section z-extents vs drawing-derived points (no sharklet, nacelles or gear in R3 / R5-C)")
    ax.grid(True, lw=0.3)
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    save(fig, out)


def delta_figure(models: dict, out: Path) -> None:
    rows = models["R3"]["comparison"]
    r5 = {r["item"]: r for r in models["R5C"]["comparison"]}
    items = [r["item"] for r in rows if "sweep" not in r["item"]]
    d3 = [next(r for r in rows if r["item"] == i)["delta"] for i in items]
    d5 = [r5[i]["delta"] for i in items]
    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(items))
    ax.barh(y - 0.2, d3, 0.4, color=MODEL, label="R3 - reference")
    ax.barh(y + 0.2, d5, 0.4, color=MODEL_R5, label="R5-C - reference")
    ax.axvspan(-0.1, 0.1, color="#888888", alpha=0.25, label="reference band +-0.1 m (not a tolerance)")
    ax.set_yticks(y, items, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("delta [m] (model minus reference)")
    ax.legend(fontsize=7)
    ax.grid(True, lw=0.3, axis="x")
    fig.tight_layout()
    save(fig, out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--models", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--png-dir", type=Path, default=None, help="optional preview PNGs (keep outside the repository)")
    args = ap.parse_args()
    global PNG_DIR
    PNG_DIR = args.png_dir
    if PNG_DIR:
        PNG_DIR.mkdir(parents=True, exist_ok=True)
    ref = json.loads(args.reference.read_text(encoding="utf-8"))
    models = json.loads(args.models.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    top_figure(ref, models, args.out_dir / "compare_top.svg")
    side_figure(ref, models, args.out_dir / "compare_side.svg")
    front_figure(ref, models, args.out_dir / "compare_front.svg")
    delta_figure(models, args.out_dir / "compare_deltas.svg")
    print("wrote 4 svg figures to", args.out_dir)


if __name__ == "__main__":
    main()
