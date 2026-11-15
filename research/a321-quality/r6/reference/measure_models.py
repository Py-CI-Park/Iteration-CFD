#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "trimesh"]
# ///
# How to run: uv run measure_models.py --repo <repo root> --reference reference-dimensions.json --out model-measurements.json
"""Measure R3 (assembly and components) and R5-C against the official-sheet reference.

Geometry is read only; the SHA-256 of every input is recorded before and after.
Axes of the models: x nose to tail, y span, z up, metres.
Deltas are model minus reference. The +-0.1 m figure is a reference band for
reading the drawings, not an engineering tolerance (the sheets are marked
"related to aircraft attitude and weight").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh import intersections

BAND_M = 0.1
Y_ROOT = 2.2  # just outside the fuselage side (half-width 1.975 m); same station as the drawing probe
WING_X_MAX = 32.0
TAIL_X_MIN = 34.0

INPUTS = {
    "R3": "research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl",
    "R3_fuselage": "research/a321-integration/artifacts/shell-r3/fuselage.stl",
    "R3_wing": "research/a321-integration/artifacts/shell-r3/wing.stl",
    "R3_horizontal": "research/a321-integration/artifacts/shell-r3/horizontal.stl",
    "R3_vertical": "research/a321-integration/artifacts/shell-r3/vertical.stl",
    "R5C": "research/a321-quality/models/A321_AIRFRAME_REBUILD_R5_C.stl",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def section(mesh: trimesh.Trimesh, axis: int, value: float) -> np.ndarray:
    """Points of the plane section axis=value (segment end points), shape (N, 3)."""
    normal = np.zeros(3)
    normal[axis] = 1.0
    origin = np.zeros(3)
    origin[axis] = value
    seg = intersections.mesh_plane(mesh, normal, origin, return_faces=False)
    return np.asarray(seg).reshape(-1, 3) if len(seg) else np.empty((0, 3))


def wing_station(mesh: trimesh.Trimesh, y: float) -> dict[str, float] | None:
    p = section(mesh, 1, y)
    p = p[p[:, 0] < WING_X_MAX]
    if len(p) == 0:
        return None
    le, te = float(p[:, 0].min()), float(p[:, 0].max())
    return {"y": y, "le_x": le, "te_x": te, "chord": te - le, "z_min": float(p[:, 2].min()), "z_max": float(p[:, 2].max())}


def ht_station(mesh: trimesh.Trimesh, y: float) -> dict[str, float] | None:
    p = section(mesh, 1, y)
    p = p[p[:, 0] > TAIL_X_MIN]
    if len(p) == 0:
        return None
    le, te = float(p[:, 0].min()), float(p[:, 0].max())
    return {"y": y, "le_x": le, "te_x": te, "chord": te - le, "z_min": float(p[:, 2].min()), "z_max": float(p[:, 2].max())}


def vt_station(mesh: trimesh.Trimesh, z: float) -> dict[str, float] | None:
    p = section(mesh, 2, z)
    p = p[p[:, 0] > TAIL_X_MIN]
    if len(p) == 0:
        return None
    le, te = float(p[:, 0].min()), float(p[:, 0].max())
    return {"z": z, "le_x": le, "te_x": te, "chord": te - le, "thickness_y": float(p[:, 1].max() - p[:, 1].min())}


def fuselage_station(mesh: trimesh.Trimesh, x: float) -> dict[str, float] | None:
    p = section(mesh, 0, x)
    if len(p) == 0:
        return None
    return {"x": x, "half_width": float(np.abs(p[:, 1]).max()), "z_min": float(p[:, 2].min()), "z_max": float(p[:, 2].max())}


def series(fn, mesh, values) -> list[dict[str, float]]:
    return [r for r in (fn(mesh, float(v)) for v in values) if r]


def fit_sweep(rows: list[dict[str, float]], key: str, y0: float, y1: float, frac: float = 0.0) -> float:
    """Sweep (deg) of the line at fraction `frac` of the chord between y0 and y1 (least squares)."""
    sel = [r for r in rows if y0 <= r["y"] <= y1]
    ys = np.array([r["y"] for r in sel])
    xs = np.array([r["le_x"] + frac * r["chord"] for r in sel])
    return float(np.degrees(np.arctan(np.polyfit(ys, xs, 1)[0])))


def interp(rows: list[dict[str, float]], key: str, at: float, y_key: str = "y") -> float:
    return float(np.interp(at, [r[y_key] for r in rows], [r[key] for r in rows]))


def measure_wing(mesh: trimesh.Trimesh, y_tip: float) -> dict[str, Any]:
    ys = np.concatenate([np.arange(Y_ROOT, y_tip - 0.3, 0.25), np.arange(y_tip - 0.3, y_tip - 0.001, 0.05)])
    rows = series(wing_station, mesh, ys)
    y_end = rows[-1]["y"]
    return {
        "y_tip_station_m": y_end, "root": rows[0], "tip": rows[-1], "profile": rows,
        "LE_sweep_deg_outboard_y8.6_to_tip": fit_sweep(rows, "le_x", 8.6, y_end),
        "quarter_chord_sweep_deg_outboard_y8.6_to_tip": fit_sweep(rows, "le_x", 8.6, y_end, 0.25),
        "quarter_chord_sweep_deg_root_to_tip": fit_sweep(rows, "le_x", rows[0]["y"], y_end, 0.25),
        "TE_sweep_deg_outboard_y8.6_to_tip": float(np.degrees(np.arctan(np.polyfit(
            [r["y"] for r in rows if r["y"] >= 8.6], [r["te_x"] for r in rows if r["y"] >= 8.6], 1)[0]))),
        "dihedral_deg_root_to_tip": float(np.degrees(np.arctan2(
            (rows[-1]["z_min"] + rows[-1]["z_max"]) / 2 - (rows[0]["z_min"] + rows[0]["z_max"]) / 2, y_end - rows[0]["y"]))),
    }


def measure_tail(mesh: trimesh.Trimesh) -> dict[str, Any]:
    ht_y_max = float(np.abs(mesh.vertices[mesh.vertices[:, 0] > TAIL_X_MIN][:, 1]).max())
    ys = np.concatenate([np.arange(Y_ROOT, ht_y_max - 0.2, 0.25), np.arange(ht_y_max - 0.2, ht_y_max - 0.001, 0.04)])
    ht_rows = series(ht_station, mesh, ys)
    tail_v = mesh.vertices[mesh.vertices[:, 0] > TAIL_X_MIN]
    z_top = float(tail_v[:, 2].max())
    zs = np.concatenate([np.arange(6.2, z_top - 0.3, 0.25), np.arange(z_top - 0.3, z_top - 0.001, 0.05)])
    vt_rows = series(vt_station, mesh, zs)
    return {
        "ht_half_span_m": ht_y_max, "ht_rows": ht_rows,
        "ht_root": ht_rows[0], "ht_tip": ht_rows[-1],
        "ht_LE_sweep_deg": fit_sweep(ht_rows, "le_x", ht_rows[0]["y"], ht_rows[-1]["y"]),
        "vt_tip_z_m": z_top, "vt_rows": vt_rows,
        "vt_rows_note": "stations from z=6.2; the LE below the crown is on the filleted root and is not used for comparison",
        "vt_tip_x_range_m": [vt_rows[-1]["le_x"], vt_rows[-1]["te_x"]], "vt_tip_station_z_m": vt_rows[-1]["z"],
    }


def measure_fuselage(mesh: trimesh.Trimesh) -> dict[str, Any]:
    xs = np.concatenate([np.arange(0.5, 15.6, 0.5), np.arange(27.0, 34.6, 0.5)])
    rows = series(fuselage_station, mesh, xs)
    x30 = fuselage_station(mesh, 30.0)
    return {
        "max_width_m": 2 * max(r["half_width"] for r in rows),
        "max_height_m": max(r["z_max"] - r["z_min"] for r in rows),
        "at_x30": x30, "crown_z_m": x30["z_max"] if x30 else None, "belly_z_m": x30["z_min"] if x30 else None,
        "centreline_z_m": (x30["z_min"] + x30["z_max"]) / 2 if x30 else None,
        "stations_sampled_m": "0.5-15.5 and 27-34.5 (wing, tail and tail upsweep excluded)", "profile": rows,
    }


def vt_le_line(vt_rows: list[dict[str, float]], crown_z: float) -> dict[str, float]:
    """Straight LE fit over heights 1.2 to 5.6 m above the crown, same range as the drawing fit."""
    sel = [r for r in vt_rows if crown_z + 1.2 <= r["z"] <= crown_z + 5.6]
    a, b = np.polyfit([r["z"] for r in sel], [r["le_x"] for r in sel], 1)
    return {"vt_LE_x_at_h2_above_crown_m": float(a * (crown_z + 2.0) + b), "vt_LE_x_at_h5_above_crown_m": float(a * (crown_z + 5.0) + b),
            "vt_LE_sweep_from_vertical_deg": float(np.degrees(np.arctan(a))), "vt_LE_fit_points": len(sel)}


def ht_chord_at(rows: list[dict[str, float]], y: float) -> float:
    a, b = np.polyfit([r["y"] for r in rows], [r["chord"] for r in rows], 1)
    return float(a * y + b)


def measure_assembly(mesh: trimesh.Trimesh, y_tip: float) -> dict[str, Any]:
    b = mesh.bounds
    fus = measure_fuselage(mesh)
    tail = measure_tail(mesh)
    wing = measure_wing(mesh, y_tip)
    root = wing["root"]
    z_low = float(b[0, 2])
    return {
        "triangles": int(len(mesh.faces)), "bounds_m": b.tolist(),
        "length_m": float(b[1, 0] - b[0, 0]), "half_span_m": float(max(abs(b[0, 1]), abs(b[1, 1]))),
        "lowest_z_m": z_low, "highest_z_m": float(b[1, 2]),
        "fuselage": {k: v for k, v in fus.items() if k != "profile"}, "fuselage_profile": fus["profile"],
        "wing": wing, "tail": tail,
        "vt_tip_above_crown_m": tail["vt_tip_z_m"] - fus["crown_z_m"],
        "vt_tip_above_fuselage_centreline_m": tail["vt_tip_z_m"] - fus["centreline_z_m"],
        "vt_tip_above_lowest_point_m": tail["vt_tip_z_m"] - z_low,
        "nose_to_wing_root_LE_x_m_at_y2.2": root["le_x"], "nose_to_wing_root_TE_x_m_at_y2.2": root["te_x"],
        "nose_to_ht_root_LE_x_m_at_y2.2": tail["ht_root"]["le_x"],
        **vt_le_line(tail["vt_rows"], fus["crown_z_m"]),
        "ht_root_chord_extrapolated_to_y1.475_m": ht_chord_at(tail["ht_rows"], 1.475),
    }


def measure_component(mesh: trimesh.Trimesh, name: str) -> dict[str, Any]:
    b = mesh.bounds
    base = {"triangles": int(len(mesh.faces)), "bounds_m": b.tolist(), "watertight": bool(mesh.is_watertight)}
    if name == "fuselage":
        rows = series(fuselage_station, mesh, np.concatenate([[0.05], np.arange(0.5, 44.0, 0.5), [44.45]]))
        return {**base, "profile_x_halfwidth_zmin_zmax": [[r["x"], r["half_width"], r["z_min"], r["z_max"]] for r in rows]}
    if name == "wing":
        w = measure_wing(mesh, float(b[1, 1]))
        return {**base, **{k: v for k, v in w.items() if k != "profile"}}
    return base


def reference_rows(ref: dict[str, Any]) -> dict[str, dict[str, Any]]:
    dims = {(d["page"], d["label_m"]): d["value_m"] for d in ref["dimensions"]}
    top = ref["drawn_planform_and_profile"]["top"]
    side = ref["drawn_planform_and_profile"]["side"]
    front = ref["drawn_planform_and_profile"]["front"]
    return {
        "fuselage_belly_z_m": dict(value=side["belly_z_m"], kind="drawn", src="p73 side outline at x=30 m, z above drawn ground line"),
        "vt_tip_z_side_sheet_m": dict(value=side["fin_tip_z_m"], kind="drawn", src="p73 side outline, z above drawn ground line"),
        "vt_tip_z_front_sheet_m": dict(value=front["outline_top_z_m"], kind="drawn", src="p73 front outline, z above drawn ground line"),
        "wing_tip_lower_z_m": dict(value=front["wing_tip_base_line_z_m"], kind="drawn", src="p73 front view, wing-tip base line (2.43 m reference)"),
        "wing_root_lower_z_m": dict(value=front["wing_root_lower_ref_line_z_m"], kind="drawn", src="p73 front view, wing-root lower reference line (3.79 m reference)"),
        "ht_tip_z_mid_m": dict(value=front["ht_tip_z_m"], kind="drawn", src="p73 front outline, HT tip"),
        "length_m": dict(value=dims[(74, "44.51")], kind="printed", src="p74 44.51"),
        "half_span_to_sharklet_break_m": dict(value=dims[(74, "16.29")], kind="printed", src="p74 16.29"),
        "half_span_incl_sharklet_m": dict(value=dims[(73, "35.80")] / 2, kind="printed", src="p73 35.80 / 2"),
        "ht_half_span_m": dict(value=dims[(73, "12.45")] / 2, kind="printed", src="p73 12.45 / 2"),
        "fuselage_max_width_m": dict(value=dims[(74, "3.95")], kind="printed", src="p74 3.95"),
        "fuselage_max_height_m": dict(value=dims[(73, "4.14")], kind="printed", src="p73 4.14 (drawn by scale: %.2f)" % side["fuselage_height_m"]),
        "vt_tip_above_crown_m": dict(value=dims[(73, "5.87")], kind="printed", src="p73 5.87 (drawn by scale: %.2f)" % side["fin_tip_above_crown_m"]),
        "vt_tip_above_lowest_point_m": dict(value=dims[(73, "4.14")] + dims[(73, "5.87")], kind="printed", src="p73 4.14 + 5.87 (belly = lowest fuselage point; gear omitted)"),
        "wing_root_chord_m": dict(value=dims[(74, "6.07")], kind="printed", src="p74 6.07 (drawn at y=2.2 by scale: %.2f)" % top["wing_at_y2.2m"]["chord_m"]),
        "ht_tip_chord_m": dict(value=dims[(74, "1.24")], kind="printed", src="p74 1.24 (reading: HT tip chord)"),
        "nose_to_wing_root_LE_x_m": dict(value=top["wing_at_y2.2m"]["LE_x_m"], kind="drawn", src="p74 outline at y=2.2 m, uniform scale"),
        "nose_to_wing_root_TE_x_m": dict(value=top["wing_at_y2.2m"]["TE_x_m"], kind="drawn", src="p74 outline at y=2.2 m, uniform scale"),
        "wing_tip_chord_m": dict(value=dims[(74, "1.64")], kind="printed", src="p74 1.64 (junction chord; drawn break line measures %.2f)" % top["wing_sharklet_break_line"]["chord_m"]),
        "ht_root_chord_extrapolated_to_y1.475_m": dict(value=dims[(74, "3.31")], kind="printed", src="p74 3.31 (reading: HT root chord at the fuselage side)"),
        "nose_to_ht_root_LE_x_m": dict(value=top["horizontal_tail"]["LE_x_at_y"]["y2.2"], kind="drawn", src="p74 outline fit at y=2.2 m"),
        "ht_LE_sweep_deg": dict(value=top["horizontal_tail"]["LE_sweep_deg"], kind="drawn", src="p74 outline fit"),
        "wing_LE_sweep_deg_outboard": dict(value=top["wing_outboard_LE_line"]["sweep_deg"], kind="drawn", src="p74 outline fit y 8.6-17.4"),
        "vt_LE_x_at_h2_above_crown_m": dict(value=side["fin_LE_x_at_height_above_crown_m"]["h2"], kind="drawn", src="p73 side outline fin LE line, 2 m above the crown line"),
        "vt_LE_x_at_h5_above_crown_m": dict(value=side["fin_LE_x_at_height_above_crown_m"]["h5"], kind="drawn", src="p73 side outline fin LE line, 5 m above the crown line"),
        "vt_LE_sweep_from_vertical_deg": dict(value=side["fin_LE_sweep_from_vertical_deg"], kind="drawn", src="p73 side outline fin LE line"),
        "vt_tip_TE_x_m": dict(value=side["fin_tip_x_m"][1], kind="drawn", src="p73 side outline fin tip trailing corner"),
    }


def model_value(asm: dict[str, Any], key: str) -> float:
    w, t, f = asm["wing"], asm["tail"], asm["fuselage"]
    table = {
        "length_m": asm["length_m"], "half_span_to_sharklet_break_m": asm["half_span_m"], "half_span_incl_sharklet_m": asm["half_span_m"],
        "ht_half_span_m": t["ht_half_span_m"], "fuselage_max_width_m": f["max_width_m"], "fuselage_max_height_m": f["max_height_m"],
        "vt_tip_above_crown_m": asm["vt_tip_above_crown_m"], "vt_tip_above_lowest_point_m": asm["vt_tip_above_lowest_point_m"],
        "wing_root_chord_m": w["root"]["chord"], "ht_tip_chord_m": t["ht_tip"]["chord"],
        "nose_to_wing_root_LE_x_m": asm["nose_to_wing_root_LE_x_m_at_y2.2"], "nose_to_wing_root_TE_x_m": asm["nose_to_wing_root_TE_x_m_at_y2.2"],
        "wing_tip_chord_m": w["tip"]["chord"], "nose_to_ht_root_LE_x_m": asm["nose_to_ht_root_LE_x_m_at_y2.2"],
        "ht_LE_sweep_deg": t["ht_LE_sweep_deg"], "wing_LE_sweep_deg_outboard": w["LE_sweep_deg_outboard_y8.6_to_tip"],
        "vt_LE_x_at_h2_above_crown_m": asm["vt_LE_x_at_h2_above_crown_m"], "vt_LE_x_at_h5_above_crown_m": asm["vt_LE_x_at_h5_above_crown_m"],
        "vt_LE_sweep_from_vertical_deg": asm["vt_LE_sweep_from_vertical_deg"],
        "ht_root_chord_extrapolated_to_y1.475_m": asm["ht_root_chord_extrapolated_to_y1.475_m"],
        "fuselage_belly_z_m": f["belly_z_m"], "vt_tip_z_side_sheet_m": t["vt_tip_z_m"], "vt_tip_z_front_sheet_m": t["vt_tip_z_m"],
        "wing_tip_lower_z_m": w["tip"]["z_min"], "wing_root_lower_z_m": w["root"]["z_min"],
        "ht_tip_z_mid_m": (t["ht_tip"]["z_min"] + t["ht_tip"]["z_max"]) / 2, "vt_tip_TE_x_m": t["vt_tip_x_range_m"][1],
    }
    return float(table[key])


def compare(refs: dict[str, dict[str, Any]], asm: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, r in refs.items():
        v = model_value(asm, key)
        delta = v - r["value"]
        is_z = "_z_" in key or key.endswith("_z_m") or "z_mid" in key
        band = bool(abs(delta) <= BAND_M) if (r["kind"] == "printed" and "sweep" not in key) else None
        if r["kind"] == "printed":
            note = "printed row; matches of the length/span/chord numbers are by construction (R3 ledger station_last values are the printed numbers)"
        elif is_z:
            note = "datum/attitude: sheets are ground-referenced, models are not; side and front sheets differ by ~0.13 m on the fin tip"
        else:
            note = "drawn row: the sheet's own printed-vs-drawn ratios run 0.79-1.08, so +-0.1 m is tighter than the reference; informational"
        rows.append({"item": key, "reference": round(r["value"], 4), "reference_kind": r["kind"], "reference_source": r["src"],
                     "model": round(v, 4), "delta": round(delta, 4), "within_band_0.1": band, "note": note})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    t0 = time.time()
    paths = {k: args.repo / v for k, v in INPUTS.items()}
    sha_before = {k: sha256_of(p) for k, p in paths.items()}
    ref = json.loads(args.reference.read_text(encoding="utf-8"))
    refs = reference_rows(ref)
    out: dict[str, Any] = {"schema": "r6-model-measurements-v1", "band_m": BAND_M, "axes": "x nose-to-tail, y span, z up (m)",
                           "band_note": "reference band for reading drawings, not an engineering tolerance"}
    meshes = {k: trimesh.load(p, process=False) for k, p in paths.items()}
    for name in ("R3", "R5C"):
        asm = measure_assembly(meshes[name], float(max(abs(meshes[name].bounds[:, 1]))))
        out[name] = {"assembly": asm, "comparison": compare(refs, asm)}
    out["R3_components"] = {n.removeprefix("R3_"): measure_component(meshes[n], n.removeprefix("R3_")) for n in INPUTS if n.startswith("R3_")}
    sha_after = {k: sha256_of(p) for k, p in paths.items()}
    out["input_sha256"] = {"before": sha_before, "after": sha_after, "unchanged": sha_before == sha_after}
    out["wall_time_s"] = round(time.time() - t0, 1)
    args.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out} in {out['wall_time_s']} s; inputs unchanged: {out['input_sha256']['unchanged']}")


if __name__ == "__main__":
    main()
