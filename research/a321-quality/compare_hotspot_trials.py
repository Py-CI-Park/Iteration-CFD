#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer"]
# ///
# How to run: uv run compare_hotspot_trials.py; package read-only measured trials.
"""Compare native/independent checks without hiding increased absolute failure counts."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from acceptance import cpu_status
from custody import BoundAudit, digest, verify_binding, verify_input_manifest
from hotspot_inputs import verify_diagnostic_files
from quality_gate import CheckStatus, external_status

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Nominate the improving CPU line only for further research, never for a GPU solve."""
    results = []
    manifest = []
    for name in ("snappy-03", "snappy-04", "snappy-05"):
        case = ROOT / "artifacts" / name
        audit_path = ROOT / "evidence" / f"{name}-audit-v5.json"
        raw = json.loads(audit_path.read_text(encoding="utf8"))
        audit = BoundAudit.model_validate(raw)
        verify_binding(case, audit)
        verify_input_manifest(case)
        mapping = json.loads((ROOT / "evidence" / f"{name}-hotspots.json").read_text())
        seal_path = ROOT / "evidence" / f"{name}-diagnostics-seal.json"
        seal = json.loads(seal_path.read_text())
        if (
            mapping["mesh"] != audit.polyMesh_sha256
            or seal["mesh"] != audit.polyMesh_sha256
        ):
            raise RuntimeError("WRONG_MAP_MESH")
        if digest(seal_path) != mapping["diagnostic_seal_sha256"]:
            raise RuntimeError("STALE_DIAGNOSTIC_SEAL")
        verify_diagnostic_files(case, mapping["diagnostics_sha256"])
        text = (case / "log.snappy").read_text()
        match = re.search(r"Finished meshing with (\d+) illegal faces", text)
        illegal = (
            int(match[1])
            if match
            else (0 if "Finished meshing without any errors" in text else None)
        )
        standard_path = case / "log.checkMesh-standard"
        standard = (
            external_status(standard_path.read_text())
            if standard_path.exists()
            else CheckStatus.MISSING
        )
        extended_path = case / "log.checkMesh-extended"
        extended = external_status(extended_path.read_text())
        item = {
            "candidate": name,
            "cells": audit.cells,
            "faces": raw["faces"],
            "angle_deg": audit.max_nonorth_deg,
            "relative_closure": audit.max_relative_closure,
            "counts": mapping["counts"],
            "covered_area_percent": mapping["covered_area_percent"],
            "cell_failure_rates_percent": [
                100 * n / audit.cells for n in mapping["counts"][:2]
            ],
            "low_weight_fraction_all_faces_percent": 100
            * mapping["counts"][2]
            / raw["faces"],
            "full_8_layer_faces": mapping["full_8_layer_faces"],
            "bins": mapping["bins"],
            "standard": standard,
            "extended": extended,
            "illegal_faces": illegal,
            "cpu_status": cpu_status(audit, standard, illegal),
            "shape_sample_max_m": raw["sampled_surface_distance"][0]["max_m"],
        }
        results.append(item)
        inputs = ROOT / "evidence" / "hotspot-inputs" / name
        inputs.mkdir(parents=True, exist_ok=True)
        for p in (case / "system").glob("*"):
            if p.is_file():
                shutil.copyfile(p, inputs / p.name)
        shutil.copyfile(case / "input-manifest.json", inputs / "input-manifest.json")
        for log_name in (
            "log.snappy",
            "log.checkMesh-standard",
            "log.checkMesh-extended",
        ):
            p = case / log_name
            if p.exists():
                shutil.copyfile(
                    p, ROOT / "evidence" / f"{name}-retest-{log_name[4:]}.log"
                )
        paths = [
            audit_path,
            seal_path,
            ROOT / "evidence" / f"{name}-hotspots.json",
            case / "audited-geometry-v5.npz",
            *list((case / "constant/polyMesh").glob("*")),
            *list((case / "system").glob("*")),
            case / "input-manifest.json",
            *list(case.glob("log.*")),
            *[case / p for p in seal["inputs"]],
            case / f"{name}-hotspot-map/coordinates.csv",
        ]
        paths[-1] = ROOT / "artifacts" / f"{name}-hotspot-map/coordinates.csv"
        for p in paths:
            if p.is_file():
                manifest.append(
                    {"path": str(p), "bytes": p.stat().st_size, "sha256": digest(p)}
                )
    base, refined, _thinner = results
    chosen = (
        refined["cpu_status"] == "NAMED_CPU_GATES_PASS"
        and refined["covered_area_percent"] > base["covered_area_percent"]
    )
    receipt = {
        "trials": results,
        "next_research_candidate": "snappy-04" if chosen else "snappy-03",
        "baseline_preserved": "snappy-03",
        "promotion": "RESEARCH_ONLY_NOT_ENGINEERING_ACCEPTANCE",
        "coverage_change_percentage_points": refined["covered_area_percent"]
        - base["covered_area_percent"],
        "cell_cost_ratio": refined["cells"] / base["cells"],
        "warning": "Failure rates use different refined meshes and do not prove physical error reduction. Counts may overlap.",
        "gpu_solver_run": False,
        "global_approval": "FIX_FIRST_GPU_HOLD",
    }
    (ROOT / "evidence/hotspot-comparison.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf8"
    )
    (ROOT / "evidence/hotspot-artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "next_research_candidate",
                    "coverage_change_percentage_points",
                    "cell_cost_ratio",
                    "global_approval",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
