#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run package_evidence.py; hash local generated artifacts and inspect rejected interfaces.
"""Bind generated data to evidence without publishing hundred-megabyte intermediate meshes."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent


def file_record(path: Path) -> dict[str, str | int]:
    """Stream SHA256 so large generated arrays do not need another in-memory copy."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def main() -> None:
    """Package audit metadata, never alter meshes or the reference model."""
    root = ROOT / "artifacts"
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix != ".log":
            records.append(file_record(path))
    models = ROOT.parent / "a321-integration/models"
    records.extend(file_record(p) for p in sorted(models.glob("*R3*")))
    record = {
        "artifact_policy": "generated meshes remain local, ignored by git; regenerate from committed scripts",
        "files": records,
        "gpu_compute": False,
        "solver_run": False,
    }
    (ROOT / "evidence/artifact-manifest.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    with np.load(root / "constrained-exact-02/layers.npz") as d:
        wall_n = int(d["wall_faces"].max() + 1)
        outer = d["vertices"][-wall_n:]
    trials = []
    for name in ["quality-exterior-02", "quality-exterior-03"]:
        with np.load(root / name / "tetgen-raw.npz") as d:
            points = d["vertices"]
        distance, matched = cKDTree(points).query(outer)
        missing = np.flatnonzero(distance != 0)
        trials.append(
            {
                "candidate": name,
                "input_outer_vertices": len(outer),
                "output_vertices": len(points),
                "exact_outer_matches": int(np.count_nonzero(distance == 0)),
                "missing_exact_coordinates": len(missing),
                "max_nearest_distance_m": float(distance.max()),
                "missing_samples": [
                    {
                        "input_id": int(i),
                        "input_xyz_m": outer[i].tolist(),
                        "nearest_xyz_m": points[matched[i]].tolist(),
                        "nearest_distance_m": float(distance[i]),
                    }
                    for i in missing[:8]
                ],
                "interpretation": "exact coordinate membership failed; nearest distance is not a tracked vertex displacement",
            }
        )
    (ROOT / "evidence/interface-failure-diagnosis.json").write_text(
        json.dumps(trials, indent=2), encoding="utf8"
    )
    cache = Path.home() / "AppData/Local/uv/cache/environments-v2"
    environments = []
    for prefix in [
        "build-layers",
        "remesh-surface",
        "exterior-tets",
        "convert-oriented",
        "audit-saved",
        "plot-section",
    ]:
        for env in sorted(cache.glob(prefix + "-*")):
            packages = {
                d.metadata["Name"]: d.version
                for d in importlib.metadata.distributions(
                    path=[str(env / "Lib/site-packages")]
                )
            }
            environments.append({"cached_environment": str(env), "packages": packages})
    (ROOT / "evidence/environment.json").write_text(
        json.dumps(
            {
                "platform": platform.platform(),
                "packaging_python": platform.python_version(),
                "precision_note": "Windows NumPy longdouble mantissa measured as 52; not extended precision",
                "environment_note": "observed uv script caches, including dependency-header revisions; not per-process historical timestamps",
                "script_environments": environments,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    print(json.dumps({"files_hashed": len(records), "trials": trials}, indent=2))


if __name__ == "__main__":
    main()
