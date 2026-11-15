# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Merge the baseline run outputs into baselines.json and print markdown tables.

Pass 1 (logs/report-*.json) supplies everything; pass 2 (logs/pass2/report-*.json, final station-exclusion
code plus ring-derived demonstration features) overrides station_kink and smoothness.
Also cross-checks the gate against surfaceCheck's own log and hashes every input again.

How to run: uv run --no-project assemble_baselines.py   (from this directory)
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np

from r6_mesh import sha256_file

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORDER = ["r3_union", "r3_union_artifact_copy", "r3_fuselage", "r3_wing", "r3_horizontal", "r3_vertical", "r4", "r5_c", "r5_a"]
HANDOFF_SC = {"r3_union": 72, "r4": 86, "r5_c": 15, "r5_a": 4184}  # HANDOFF_20261109_KO.md section 5-6 records


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def input_paths() -> dict[str, Path]:
    pairs = [line.strip().split("=", 1) for line in (HERE / "baseline_inputs.txt").read_text().splitlines() if line.strip()]
    return {n: ROOT / p for n, p in pairs}


def surface_z_stats(obj_dir: str) -> dict:
    """Where surfaceCheck's points sit: counts near the fuselage belly (z<2.03) and crown (z>6.08)."""
    obj = HERE / "attempts" / obj_dir / "selfInterPoints.obj"
    pts = np.array([list(map(float, ln.split()[1:4])) for ln in obj.read_text().splitlines() if ln.startswith("v ")]).reshape(-1, 3)
    belly, crown = int(np.sum(pts[:, 2] < 2.03)), int(np.sum(pts[:, 2] > 6.08))
    return {"points": len(pts), "belly_z_lt_2.03": belly, "crown_z_gt_6.08": crown, "other": len(pts) - belly - crown,
            "x_min": float(pts[:, 0].min()), "x_max": float(pts[:, 0].max())}


def crosscheck(report: dict) -> dict:
    """The gate's own numbers against surfaceCheck's log for the same file."""
    sc, topo, q = report["self_intersection"]["surfacecheck"], report["closure_orientation"], report["quality"]
    worst = q["worst_ten_triangles"][0]
    return {
        "welded_vertices_equal": sc["vertices"] == topo["welded_vertices"], "triangles_equal": sc["triangles"] == report["triangles"],
        "parts_equal_components": sc["unconnected_parts"] == topo["connected_components"],
        "zones_equal_1_when_consistent": sc["zones"] == (1 if topo["winding_consistent"] and topo["connected_components"] == 1 else None),
        "surfacecheck_closed_equals_gate_watertight": sc["closed"] == topo["watertight_manifold"],
        "min_quality_surfacecheck": sc["quality_min"], "min_quality_gate": {"value": worst["q_of"], "triangle": worst["triangle"]},
        "min_quality_triangle_equal": sc["quality_min"]["triangle"] == worst["triangle"],
        "min_quality_relative_diff": abs(sc["quality_min"]["value"] - worst["q_of"]) / sc["quality_min"]["value"],
    }


def main() -> None:
    paths = input_paths()
    before = {ln.split()[1]: ln.split()[0] for ln in (HERE / "logs" / "input-sha256-before.txt").read_text().splitlines()}
    after = {n: sha256_file(p) for n, p in paths.items()}
    (HERE / "logs" / "input-sha256-after.txt").write_text("".join(f"{after[n]}  {n}  {paths[n].relative_to(ROOT).as_posix()}\n" for n in ORDER), encoding="utf-8")
    out: dict = {"sha256_before": before, "sha256_after": after, "sha256_all_equal": all(before[n] == after[n] for n in ORDER), "surfaces": {}}
    for name in ORDER:
        base = read(HERE / "logs" / f"report-{name}.json")[name]
        two = read(HERE / "logs" / "pass2" / f"report-{name}.json")[name] if (HERE / "logs" / "pass2" / f"report-{name}.json").exists() else None
        if two is not None:
            base["station_kink"], base["smoothness"] = two["station_kink"], two["smoothness"]
            if "deviation_to_reference" in two["geometry"]:
                base["geometry"] = two["geometry"]
        base["crosscheck_vs_surfacecheck"] = crosscheck(base)
        follow = HERE / "logs" / f"followup-{name}.json"
        if follow.exists():
            f = read(follow)
            f.pop("meshlab_face_midpoints_m", None)
            base["self_intersection"]["followup_obj_matching"] = f
            base["self_intersection"]["surfacecheck_point_positions"] = surface_z_stats(f["attempt_dir"])
        base["self_intersection"]["surfacecheck"].pop("obj_points_m", None)
        base["handoff_recorded_surfacecheck_locations"] = HANDOFF_SC.get(name)
        out["surfaces"][name] = base
    with (HERE / "baselines.json").open("w", encoding="utf-8") as stream:
        json.dump(out, stream, indent=1, allow_nan=False)
    print("sha_all_equal", out["sha256_all_equal"], "surfaces", len(out["surfaces"]))
    for name in ORDER:
        c = out["surfaces"][name]["crosscheck_vs_surfacecheck"]
        print(name, {k: v for k, v in c.items() if k.endswith("equal") or "equal" in k or "diff" in k})


if __name__ == "__main__":
    main()
