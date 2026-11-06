#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2"]
# ///
# How to run: uv run replay_baseline_checks.py; isolated CPU checkMesh only.
"""Recompute baseline check sets on copied geometry to verify diagnostic identities."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from custody import require_unchanged, snapshot_mesh
from poly_io import read_labels

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Never let native set writes touch the preserved snappy-03 case."""
    case = ROOT / "artifacts/snappy-03"
    target = ROOT / "artifacts/snappy-03-check-replay"
    target.mkdir(exist_ok=False)
    before = snapshot_mesh(case)
    (target / "constant/polyMesh").mkdir(parents=True)
    for path in (case / "constant/polyMesh").iterdir():
        if path.is_file():
            shutil.copyfile(path, target / "constant/polyMesh" / path.name)
    shutil.copytree(case / "system", target / "system")
    wsl_path = "/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/artifacts/snappy-03-check-replay"
    cmd = [
        "wsl.exe",
        "-d",
        "Ubuntu",
        "--",
        "env",
        "FOAM_ETC=/usr/share/openfoam/etc",
        "WM_PROJECT_DIR=/usr/share/openfoam",
        "WM_PROJECT_VERSION=v1912",
        "checkMesh",
        "-case",
        wsl_path,
        "-constant",
        "-allTopology",
        "-allGeometry",
    ]
    with (target / "log.checkMesh").open("x", encoding="utf8") as handle:
        code = subprocess.run(
            cmd, stdout=handle, stderr=subprocess.STDOUT, check=False
        ).returncode
    text = (target / "log.checkMesh").read_text(encoding="utf8")
    if code != 0 or not text.rstrip().endswith("End"):
        raise RuntimeError("BASELINE_REPLAY_INCOMPLETE")
    comparison = {}
    for name in ("underdeterminedCells", "concaveCells", "lowWeightFaces"):
        original = read_labels(case / "constant/polyMesh/sets" / name)
        replayed = read_labels(target / "constant/polyMesh/sets" / name)
        comparison[name] = bool(np.array_equal(np.sort(original), np.sort(replayed)))
    if not all(comparison.values()):
        raise RuntimeError("BASELINE_SET_ID_MISMATCH")
    require_unchanged(case, before)
    (ROOT / "evidence/snappy-03-check-replay.json").write_text(
        json.dumps(
            {
                "command": cmd,
                "exit_code": code,
                "sets_identical": comparison,
                "mesh": before.model_dump(),
                "solver_run": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    print(json.dumps(comparison))


if __name__ == "__main__":
    main()
