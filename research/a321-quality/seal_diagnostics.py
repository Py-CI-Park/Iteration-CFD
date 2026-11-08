#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "numpy", "matplotlib", "typer"]
# ///
# How to run: uv run seal_diagnostics.py --candidate snappy-03
"""Seal the current diagnostic files, explicitly as post-generation snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from custody import digest, snapshot_mesh
from hotspot_inputs import diagnostic_inputs

ROOT = Path(__file__).resolve().parent


def main(candidate: str = "snappy-03") -> None:
    """Capture diagnostic dependencies after complete external geometry checks."""
    if candidate not in {
        "snappy-03",
        "snappy-04",
        "snappy-05",
        "snappy-06",
        "snappy-07",
        "snappy-08",
        "snappy-09",
        "snappy-10",
        "snappy-11",
    }:
        raise RuntimeError("INVALID_CANDIDATE")
    case = ROOT / "artifacts" / candidate
    log = case / "log.checkMesh-extended"
    if candidate == "snappy-03" and not log.exists():
        log = case / "log.checkMesh"
    text = log.read_text(encoding="utf8")
    if not text.rstrip().endswith("End"):
        raise RuntimeError("INCOMPLETE_EXTERNAL_CHECK")
    seal = {
        "candidate": candidate,
        "post_generation_snapshot": True,
        "not_original_launch_freeze": True,
        "mesh": snapshot_mesh(case).model_dump(),
        "inputs": {
            p.relative_to(case).as_posix(): digest(p) for p in diagnostic_inputs(case)
        },
        "external_check_log": {"path": log.name, "sha256": digest(log)},
    }
    path = ROOT / "evidence" / f"{candidate}-diagnostics-seal.json"
    with path.open("x", encoding="utf8") as handle:
        json.dump(seal, handle, indent=2)
    print(path)


if __name__ == "__main__":
    typer.run(main)
