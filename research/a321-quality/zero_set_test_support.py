#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "typer"]
# ///
# How to run: imported by the two zero-set regression test modules
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI/native diagnostic data. No GPL-licensed source consulted.
"""Explicit temporary replay fixtures; never run the native checker."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from normalize_zero_sets import BoundReplay, canonical_wsl, set_hashes, snapshot_mesh

PASS_MARKERS = (
    ("underdeterminedCells", "Cell determinant check OK."),
    ("concaveCells", "Concave cell check OK."),
    ("lowWeightFaces", "Face interpolation weight check OK."),
)


def make_case(
    root: Path, text: str, candidate: str = "snappy-08", *, binding: bool = True
) -> Path:
    """Build isolated placeholder arrays and native-format diagnostic inputs."""
    case = root / "artifacts" / candidate
    pm = case / "constant/polyMesh"
    (pm / "sets").mkdir(parents=True)
    (root / "evidence").mkdir(exist_ok=True)
    for name in ("points", "faces", "owner", "neighbour", "boundary"):
        (pm / name).write_bytes(b"frozen source array\n")
    (case / "log.checkMesh-extended").write_text(
        "Exec : checkMesh -constant -allTopology -allGeometry\n"
        f"Case : {canonical_wsl(case)}\nTime = constant\nChecking geometry...\n" + text,
        encoding="utf8",
    )
    if binding:
        bind_fixture(case)
    return case


def bind_fixture(case: Path) -> None:
    """Build explicit fixture-only replay evidence; never execute checkMesh."""
    clone = case.parent / f"{case.name}-bound-check"
    pm = clone / "constant/polyMesh"
    pm.mkdir(parents=True, exist_ok=True)
    for name in ("points", "faces", "owner", "neighbour", "boundary"):
        shutil.copyfile(case / "constant/polyMesh" / name, pm / name)
    source_sets = case / "constant/polyMesh/sets"
    if source_sets.exists():
        shutil.copytree(source_sets, pm / "sets", dirs_exist_ok=True)
    old = (case / "log.checkMesh-extended").read_bytes()
    new = old.replace(canonical_wsl(case).encode(), canonical_wsl(clone).encode())
    (clone / "log.bound-check-extended").write_bytes(new)
    mesh = snapshot_mesh(case)
    sets = dict(set_hashes(case))
    receipt = BoundReplay(
        schema_version=1,
        candidate=case.name,
        source_case=canonical_wsl(case),
        clone_case=canonical_wsl(clone),
        command=("checkMesh", "-constant", "-allTopology", "-allGeometry"),
        old_log_sha256=hashlib.sha256(old).hexdigest(),
        new_log_sha256=hashlib.sha256(new).hexdigest(),
        source_mesh_before=mesh,
        source_mesh_after=mesh,
        clone_mesh_before=mesh,
        clone_mesh_after=mesh,
        source_sets_before=sets,
        source_sets_after=sets,
        clone_sets_before=sets,
        clone_sets_after=sets,
        returncode=0,
        status="BOUND_REPLAY_COMPLETE",
    )
    (case.parent.parent / "evidence" / f"{case.name}-bound-check.json").write_text(
        receipt.model_dump_json(indent=2), encoding="utf8"
    )
