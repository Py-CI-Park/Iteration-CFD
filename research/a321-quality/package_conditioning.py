#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer"]
# ///
# How to run: uv run package_conditioning.py; verify saved CPU data, no mesher/solver invocation.
"""Bind recovered conditioning experiments to current source bytes and publish bounded results."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from acceptance import cpu_status
from custody import (
    BoundAudit,
    MeshDigests,
    digest,
    snapshot_mesh,
    verify_binding,
    verify_input_manifest,
)
from hotspot_inputs import require_seal_identity, verify_diagnostic_files
from native_summary import layer_mean
from quality_gate import external_status

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Keep the highest-coverage candidate a research choice, never a physical acceptance."""
    results = []
    manifest = []
    for name in ("snappy-04", "snappy-06", "snappy-07"):
        case = ROOT / "artifacts" / name
        ap = ROOT / "evidence" / f"{name}-audit-v5.json"
        raw = json.loads(ap.read_text(encoding="utf8"))
        audit = BoundAudit.model_validate(raw)
        verify_binding(case, audit)
        verify_input_manifest(case)
        before = snapshot_mesh(case)
        seal_path = ROOT / "evidence" / f"{name}-diagnostics-seal.json"
        seal = json.loads(seal_path.read_text())
        require_seal_identity(
            case, before, seal["candidate"], MeshDigests.model_validate(seal["mesh"])
        )
        verify_diagnostic_files(case, seal["inputs"])
        mapping_path = ROOT / "evidence" / f"{name}-hotspots.json"
        mapping = json.loads(mapping_path.read_text())
        if mapping["mesh"] != before.model_dump() or mapping[
            "diagnostic_seal_sha256"
        ] != digest(seal_path):
            raise RuntimeError("STALE_CONDITIONING_MAP")
        centers = case / "audited-geometry-v5.npz"
        if digest(centers) != raw["audited_geometry_sha256"]:
            raise RuntimeError("STALE_CONDITIONING_CENTERS")
        mesh_log = (case / "log.snappy").read_text()
        illegal = re.search(r"Finished meshing with (\d+) illegal faces", mesh_log)
        illegal_count = (
            int(illegal[1])
            if illegal
            else (0 if "Finished meshing without any errors" in mesh_log else None)
        )
        standard = external_status((case / "log.checkMesh-standard").read_text())
        extended = external_status((case / "log.checkMesh-extended").read_text())
        results.append(
            {
                "candidate": name,
                "cells": audit.cells,
                "nonorth_deg": audit.max_nonorth_deg,
                "relative_closure": audit.max_relative_closure,
                "nonpositive_volumes": audit.nonpositive_volumes,
                "area_coverage_percent": mapping["covered_area_percent"],
                "full_8_layer_faces": mapping["full_8_layer_faces"],
                "wall_faces": mapping["wall_faces"],
                "zero_layer_faces": mapping["zero_layer_faces"],
                "failure_counts_det_concave_weight": mapping["counts"],
                "mean_layers_native_rounded": layer_mean(mesh_log),
                "standard": standard,
                "extended": extended,
                "native_illegal": illegal_count,
                "named_CPU_gate": cpu_status(audit, standard, illegal_count),
                "p95_R3_to_candidate_m": raw["sampled_surface_distance"][0]["p95_m"],
                "max_sampled_R3_to_candidate_m": raw["sampled_surface_distance"][0][
                    "max_m"
                ],
            }
        )
        files = [
            ap,
            mapping_path,
            seal_path,
            centers,
            case / "input-manifest.json",
            case / "input-manifest.sha256",
            *[case / n for n in seal["inputs"]],
            *list((case / "system").glob("*")),
            *[case / "constant/polyMesh" / n for n in MeshDigests.model_fields],
            *list(case.glob("log.*")),
            ROOT / "artifacts" / f"{name}-hotspot-map/coordinates.csv",
        ]
        runner = case / ".execution.lock/runner.sh"
        if runner.exists():
            files.append(runner)
        elif name != "snappy-04":
            raise RuntimeError("NEW_TRIAL_RUNNER_NOT_FROZEN")
        results[-1]["runner_copy_captured"] = runner.exists()
        evidence_inputs = ROOT / "evidence/conditioning-inputs" / name
        evidence_inputs.mkdir(parents=True, exist_ok=True)
        for p in (case / "system").glob("*"):
            if p.is_file():
                shutil.copyfile(p, evidence_inputs / p.name)
        shutil.copyfile(
            case / "input-manifest.json", evidence_inputs / "input-manifest.json"
        )
        for log in ("log.snappy", "log.checkMesh-standard", "log.checkMesh-extended"):
            shutil.copyfile(
                case / log, ROOT / "evidence" / f"{name}-conditioning-{log[4:]}.log"
            )
        for path in files:
            if not path.is_file():
                raise RuntimeError(f"MISSING_CONDITIONING_EVIDENCE: {path}")
            manifest.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": digest(path),
                }
            )
        if name in ("snappy-04", "snappy-06"):
            rp = (
                ROOT
                / "evidence"
                / (
                    "owner-layer-diagnostic.json"
                    if name == "snappy-04"
                    else f"{name}-owner-layer-diagnostic.json"
                )
            )
            view = json.loads(rp.read_text())
            clone = ROOT / "artifacts" / view["view_case"]
            if view["mesh"] != before.model_dump() or snapshot_mesh(clone) != before:
                raise RuntimeError("STALE_OWNER_VIEW")
            field = clone / "0" / view["field"]
            if (
                digest(field) != view["field_sha256"]
                or view["physics_solution"]
                or view["solver_run"]
            ):
                raise RuntimeError("WRONG_DIAGNOSTIC_FIELD")
            distance_path = ROOT / "evidence" / f"{name}-wall-center-distance.json"
            distance = json.loads(distance_path.read_text())
            if (
                distance["mesh"] != before.model_dump()
                or digest(case / "wall-center-distance.npz") != distance["npz_sha256"]
            ):
                raise RuntimeError("STALE_WALL_DISTANCE")
            for path in (rp, field, distance_path, case / "wall-center-distance.npz"):
                manifest.append(
                    {
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                    }
                )
            results[-1]["layered_center_distance_m"] = distance["summaries_m"][
                "layered_faces"
            ]
    receipt = {
        "trials": results,
        "research_candidate": "snappy-06",
        "reason": "92.76% layer-area coverage and fewer determinant/weight failures with named CPU gates retained; concavity still fails",
        "not": "not first-cell-height, y+ or physical wall-treatment acceptance",
        "engineering_status": "FIX_FIRST_GPU_HOLD",
        "flow_solver_run": False,
        "physical_test_target": {
            "speed_m_s": 30,
            "angle_reference_deg": 0,
            "source": "user selection",
        },
        "recovery": "Saved candidates and hashes verified after computer shutdown; no new generation to recreate completed results",
    }
    (ROOT / "evidence/conditioning-comparison.json").write_text(
        json.dumps(receipt, indent=2), encoding="utf8"
    )
    (ROOT / "evidence/conditioning-artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {
                "files": len(manifest),
                "candidate": "snappy-06",
                "status": receipt["engineering_status"],
            }
        )
    )


if __name__ == "__main__":
    main()
