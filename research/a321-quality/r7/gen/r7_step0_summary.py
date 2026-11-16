#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Collect the step-0 barrel gate results (03a L9) from the scratch outputs into one tracked JSON.

Inputs (scratch, .worktmp/r7-gen): barrels-01/{B0a,B0b}.stl + barrel-params.json + barrel-manifest.json,
step0/sc-{control,B0a,B0b}.json (r7_sc.py), step0/gate-{B0a,B0b}.json (r6_gate.py locator + PyMeshLab).

How to run: uv run --no-project r7_step0_summary.py --barrels <dir> --step0 <dir> --out <new json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import r7_common


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--barrels", type=Path, required=True)
    ap.add_argument("--step0", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--extra", type=Path, nargs="*", default=[], help="information-only surfaceCheck result jsons to attach")
    args = ap.parse_args()
    params = json.loads((args.barrels / "barrel-params.json").read_text(encoding="utf-8"))
    manifest = json.loads((args.barrels / "barrel-manifest.json").read_text(encoding="utf-8"))
    control = json.loads((args.step0 / "sc-control.json").read_text(encoding="utf-8"))
    out = {"contract": "r7-geometry-contract-03a L9", "frozen_parameters": params, "positive_control": {"stl": "r6-c attempt01 fuselage.stl", "surfaceCheck_locations": control["locations"], "expected": 48, "valid": control["valid"],
                                                                                                         "wall_s": control["wrapper_wall_seconds_date_measured"]}, "barrels": {}}
    all_zero = True
    for k in ("B0a", "B0b"):
        sc = json.loads((args.step0 / f"sc-{k}.json").read_text(encoding="utf-8"))
        g = json.loads((args.step0 / f"gate-{k}.json").read_text(encoding="utf-8"))[k]
        si = g["self_intersection"]
        m = manifest[k]
        row = {"stl_sha256": r7_common.sha256_file(args.barrels / f"{k}.stl"), "rings": m["rows"], "triangles": m["triangles"], "vertices": m["vertices"], "leaning_strips": m["leaning_strips"], "strips_total": m["strips_total"],
               "length_between_full_rings_m": m["length_between_full_rings_m"], "plateau_stations": m["plateau_station_count"], "taper_stations": m["taper_station_count"],
               "flip": m["flip"], "closure": {kk: g["closure_orientation"][kk] for kk in ("watertight_manifold", "boundary_edges", "nonmanifold_edges", "connected_components", "euler_characteristic", "winding_consistent", "outward_normals")},
               "surfaceCheck_locations": sc["locations"], "surfaceCheck_valid": sc["valid"], "surfaceCheck_wall_s": sc["wrapper_wall_seconds_date_measured"],
               "locator_pairs": si["locator"]["intersecting_pairs"], "locator_wall_s": si["locator"]["wall_seconds"], "pymeshlab_selected_faces": si["meshlab"]["selected_faces"], "pymeshlab_wall_s": si["meshlab"]["wall_seconds"],
               "gate_wall_s": g["wall_seconds"], "quality_q_of_min": g["quality"]["q_of"]["min"]}
        row["all_zero"] = row["surfaceCheck_locations"] == 0 and row["surfaceCheck_valid"] and row["locator_pairs"] == 0 and row["pymeshlab_selected_faces"] == 0
        all_zero &= row["all_zero"]
        out["barrels"][k] = row
    out["step0_pass"] = bool(all_zero and control["locations"] == 48)
    for extra in args.extra:
        out.setdefault("information_only", {})[extra.stem] = {k: v for k, v in json.loads(extra.read_text(encoding="utf-8")).items() if k != "obj_points_m"}
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("step0_pass", out["step0_pass"])


if __name__ == "__main__":
    main()
