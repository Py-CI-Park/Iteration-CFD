#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: uv run package_quality.py; package completed CPU candidates and external check logs.
"""Publish compact receipts while retaining large meshes locally and preserving all failed trials."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
from pathlib import Path
from typing import Final

from acceptance import cpu_status
from custody import BoundAudit, verify_binding
from quality_gate import external_status

ROOT: Final = Path(__file__).resolve().parent


def main() -> None:
    """Bind named CPU gates to saved geometry, native logs and exact source hash."""
    results = []
    manifest = []
    for name in ["snappy-01", "snappy-02", "snappy-03"]:
        root = ROOT / "artifacts" / name
        audit_path = ROOT / "evidence" / f"{name}-audit-v5.json"
        if not audit_path.exists():
            continue
        audit = BoundAudit.model_validate_json(audit_path.read_text(encoding="utf8"))
        verify_binding(root, audit)
        inputs = ROOT / "evidence" / f"{name}-inputs"
        inputs.mkdir(exist_ok=True)
        shutil.copyfile(root / "input-manifest.json", inputs / "input-manifest.json")
        for config in (root / "system").glob("*"):
            if config.is_file():
                shutil.copyfile(config, inputs / config.name)
        logs = {}
        for source, label in [
            ("log.snappy", "mesher"),
            ("log.checkMesh-standard", "standard"),
            ("log.checkMesh-extended", "extended"),
        ]:
            path = root / source
            if not path.exists() and label == "extended":
                path = root / "log.checkMesh"
            logs[label] = path.read_text(encoding="utf8") if path.exists() else ""
            if path.exists():
                shutil.copyfile(path, ROOT / "evidence" / f"{name}-{label}.log")
        illegal = re.search(
            r"Finished meshing with (\d+) illegal faces", logs["mesher"]
        )
        illegal_count = (
            int(illegal[1])
            if illegal
            else (
                0 if "Finished meshing without any errors" in logs["mesher"] else None
            )
        )
        extrusion = re.findall(
            r"Extruding (\d+) out of (\d+) faces \(([\d.]+)%\)", logs["mesher"]
        )
        layers = re.findall(
            r"^aircraft\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
            logs["mesher"],
            flags=re.MULTILINE,
        )
        standard = external_status(logs["standard"])
        extended = external_status(logs["extended"])
        results.append(
            {
                "candidate": name,
                "cell_family": "hex_dominant_polyhedra_not_tetrahedra",
                "cpu_status": cpu_status(audit, standard, illegal_count),
                "standard_checkMesh": standard,
                "extended_checkMesh": extended,
                "final_native_illegal_faces": illegal_count,
                "last_extrusion_face_counts": extrusion[-1] if extrusion else None,
                "layer_summary_columns": "faces, mean_layers_over_all_wall_faces, mean_total_thickness_m, percent_of_requested_thickness",
                "layer_summary": layers[-1] if layers else None,
                "max_nonorth_deg": audit.max_nonorth_deg,
                "max_relative_closure": audit.max_relative_closure,
                "engineering_status": "NOT_VALIDATED_GPU_HOLD",
                "gpu_solver_run": False,
            }
        )
        for path in [
            *(root / "constant/polyMesh").glob("*"),
            root / "calculation-wall-v5.stl",
            root / "audited-geometry-v5.npz",
            audit_path,
            root / "input-manifest.json",
            *list(root.glob("log.*")),
            *list((root / "system").glob("*")),
            ROOT / "evidence/external-toolchain.log",
        ]:
            if path.is_file():
                manifest.append(
                    {
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    source = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745":
        raise RuntimeError("R3_SHA_CHANGED")
    (ROOT / "evidence/acceptance.json").write_text(
        json.dumps(
            {
                "reference_sha256": digest,
                "results": results,
                "all_geometry_or_aerodynamics_pass": False,
                "gpu_solver_run": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    (ROOT / "evidence/artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8"
    )
    cache = Path.home() / "AppData/Local/uv/cache/environments-v2"
    environments = []
    for prefix in ["audit-poly", "netgen-clean", "layer-fields", "plot-quality"]:
        for env in sorted(cache.glob(prefix + "-*")):
            versions = {
                d.metadata["Name"]: d.version
                for d in importlib.metadata.distributions(
                    path=[str(env / "Lib/site-packages")]
                )
            }
            environments.append({"script_cache": str(env), "packages": versions})
    (ROOT / "evidence/environment.json").write_text(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "meaning": "observed script environment cache, includes header revisions, not an invented historical launch log",
                "environments": environments,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    print(json.dumps(results))


if __name__ == "__main__":
    main()
