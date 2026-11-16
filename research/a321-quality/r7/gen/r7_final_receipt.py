#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Consolidated R7-a receipt: current SHA-256 of every deliverable and of the r7/gen sources, step-0 and attempt01 commands and
date-measured wall times, and the note on the two-phase run. Also refreshes the artifact hashes inside R7A_GATE_TABLE.json.

How to run: uv run --no-project r7_final_receipt.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

R = Path(__file__).resolve().parents[1]
G = R / "gen"
A = R / "candidates/r7-a/attempt01"
REPO = R.parents[2]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    first = json.loads((A / "receipt.json").read_text(encoding="utf-8"))
    step0 = json.loads((G / "step0-results.json").read_text(encoding="utf-8"))
    files = [p for p in sorted(A.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and p.name != "receipt.json" and not p.name.startswith("receipt-partial")]
    deliverables = {str(p.relative_to(R)).replace("\\", "/"): sha(p) for p in files}
    for name in ("R7A_REPORT_KO.md", "R7A_GATE_TABLE.json", "step0-results.json", "r7a-curves-rings-record.json"):
        deliverables[f"gen/{name}"] = sha(G / name)
    deliverables.update({str(p.relative_to(R)).replace("\\", "/"): sha(p) for p in sorted((G / "step0-logs").iterdir())})
    sources = {p.name: sha(p) for p in sorted(G.iterdir()) if p.is_file() and p.suffix in (".py", ".sh")}
    receipt = {
        "tag": "r7-a", "attempt": "attempt01", "contract": ["r7-geometry-contract-03", "r7-geometry-contract-03a"], "date_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note_two_phase_run": "attempt01/receipt.json is the first full pipeline run (build, Blender, gate, surfaceCheck, junctions, A3, dense G4R, evaluator, render; 2026-11-16 18:52:10-18:57:26). Afterwards r7_check.py was patched (A1 loop-end gap computed from the edge mesh), "
                              "run_r7.py --only eval regenerated gate-table.json (receipt-partial-*.json), and r7_diag.py / r7_wing_gap.py were run. No geometry file changed after the first run: fuselage.stl SHA below equals the first receipt's.",
        "fuselage_stl_equal_to_first_receipt": first["artifact_sha256"]["fuselage.stl"] == deliverables["candidates/r7-a/attempt01/fuselage.stl"],
        "step0": {"pass": step0["step0_pass"], "positive_control_locations": step0["positive_control"]["surfaceCheck_locations"],
                  "commands": ["uv run --no-project r7_barrel.py --out-dir .worktmp/r7-gen/barrels-01", "uv run --no-project r7_sc.py --name control-r6c-fuselage|B0a|B0b --stl <stl> --out step0/sc-*.json",
                               "uv run --no-project r6_gate.py --surface B0a|B0b=<stl> --checkers locator,meshlab --log-dir --out step0/gate-*.json (cwd r6/checks)", "uv run --no-project r7_step0_summary.py --barrels barrels-01 --step0 step0 --out step0-results.json --extra sc-B0a-quad-info.json"],
                  "wall_times_s": {"barrel_build_both_date_measured": "2026-11-16 18:20:26 -> 18:21:05", "surfaceCheck_control": step0["positive_control"]["wall_s"], "surfaceCheck_B0a": step0["barrels"]["B0a"]["surfaceCheck_wall_s"], "surfaceCheck_B0b": step0["barrels"]["B0b"]["surfaceCheck_wall_s"],
                                   "r6_gate_B0a_B0b": [step0["barrels"]["B0a"]["gate_wall_s"], step0["barrels"]["B0b"]["gate_wall_s"]], "step0_checkers_total_date_measured": "18:23:03 -> 18:24:32"},
                  "barrel_stl_sha256": {k: v["stl_sha256"] for k, v in step0["barrels"].items()}},
        "attempt01_first_run_steps": first["steps"], "attempt01_commands": ["uv run --no-project run_r7.py", "uv run --no-project run_r7.py --only eval", "uv run --no-project r7_diag.py --attempt <dir> --out diag/diag.json", "uv run --no-project r7_wing_gap.py --attempt <dir> --out diag/wing-gap.json"],
        "inputs_sha256_before_after_first_run": {"unchanged": first["inputs_unchanged"], "before": first["inputs_sha256_before"]},
        "deliverables_sha256": deliverables, "r7_gen_sources_sha256": sources,
    }
    (G / "R7A_RECEIPT.json").write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    gt = json.loads((G / "R7A_GATE_TABLE.json").read_text(encoding="utf-8"))
    gt["artifact_sha256"] = {k: v for k, v in deliverables.items() if k.endswith((".stl", ".blend", "gate-table.json", "feature-manifest.json"))}
    gt["artifact_sha256_note"] = "current values; full list in R7A_RECEIPT.json"
    (G / "R7A_GATE_TABLE.json").write_text(json.dumps(gt, indent=1), encoding="utf-8")
    print("receipt written", len(deliverables), "deliverables", len(sources), "sources; fuselage unchanged:", receipt["fuselage_stl_equal_to_first_receipt"])


if __name__ == "__main__":
    main()
