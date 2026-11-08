#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer"]
# ///
# How to run: imported by package_surface_trials.py; focused tests use temporary files only.
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Read-only provenance checks and ownership-safe exclusive evidence copying."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal, override

from custody import MeshDigests, digest, snapshot_mesh
from normalize_zero_sets import (
    COMMAND,
    RULES,
    BoundReplay,
    NormalizationError,
    NormalizationReceipt,
    NormalizedSet,
    canonical_wsl,
    checked_body,
    set_hashes,
)
from poly_io import read_labels
from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True, slots=True)
class PackageError(Exception):
    """A stale or incomplete research record cannot be published."""

    reason: str

    @override
    def __str__(self) -> str:
        return self.reason


class Frozen(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, strict=True, allow_inf_nan=False
    )


class FileRef(Frozen):
    path: str
    sha256: str


class Artifact(FileRef):
    bytes: int


class Distance(Frozen):
    direction: str
    samples: int = Field(gt=0)
    p95_m: float = Field(ge=0)
    max_m: float = Field(ge=0)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise PackageError(reason)


def confine(path: Path, root: Path) -> None:
    """Reject traversal and junction/symlink destinations outside the study."""
    require(path.resolve().is_relative_to(root.resolve()), "PATH_ESCAPE")


def illegal_faces(text: str) -> int | None:
    """Only one complete, nonfatal native invocation proves a meshing result."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    execs = [
        match.group(1)
        for match in re.finditer(r"^Exec\s*:\s*(.*)$", text, flags=re.MULTILINE)
    ]
    markers = [
        i for i, line in enumerate(lines) if line.startswith("Finished meshing with")
    ]
    timings = [
        i
        for i, line in enumerate(lines)
        if re.fullmatch(r"Finished meshing in = [\d.eE+-]+ s\.", line)
    ]
    if (
        lines.count("End") != 1
        or len(execs) != 1
        or not execs[0].split()
        or execs[0].split()[0] != "snappyHexMesh"
        or len(markers) != 1
        or len(timings) != 1
        or re.search(
            r"FOAM FATAL|FOAM exiting|Segmentation fault|MPI_ABORT|^Killed\b",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )
    ):
        return None
    end = lines.index("End")
    if not markers[0] < timings[0] < end or lines[end + 1 :] not in (
        [],
        ["Finalising parallel run"],
    ):
        return None
    marker = re.fullmatch(
        r"Finished meshing (?:without any errors|with (\d+) illegal faces(?: \(concave, zero area or negative cell pyramid volume\))?)",
        lines[markers[0]],
    )
    if marker is None:
        return None
    return int(marker[1]) if marker[1] is not None else 0


def copy_exclusive(source: Path, target: Path, expected: str) -> None:
    """Rollback only the file identity created by this call, preserving older evidence."""
    owned: os.stat_result | None = None
    try:
        with source.open("rb") as incoming, target.open("xb") as outgoing:
            owned = os.fstat(outgoing.fileno())
            shutil.copyfileobj(incoming, outgoing)
        require(digest(source) == expected == digest(target), "COPY_CHANGED")
    except (OSError, PackageError) as failure:
        if owned is not None:
            try:
                current = target.stat(follow_symlinks=False)
            except FileNotFoundError:
                raise failure
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino):
                target.unlink(missing_ok=True)
        raise


class LegacyNormalization(Frozen):
    """Historical subset; never reinterpret it as a new bound execution receipt."""

    candidate: str
    mesh: MeshDigests
    external_check_log: FileRef
    sets: tuple[NormalizedSet, ...]
    status: Literal["DIAGNOSTICS_ONLY_NOT_MESH_ACCEPTANCE"]


def checked_zero_records(
    case: Path, records: tuple[NormalizedSet, ...], diagnostics: Mapping[str, str]
) -> None:
    """Check sealed bytes and counted emptiness without imposing a serializer version."""
    require(
        len({item.name for item in records}) == len(records), "DUPLICATE_NORMALIZED_SET"
    )
    rules = {rule.name: rule for rule in RULES}
    for item in records:
        require(item.name in rules, "UNKNOWN_NORMALIZED_SET")
        rule = rules[item.name]
        relative = f"constant/polyMesh/sets/{rule.name}"
        require(
            item.path == relative and item.pass_marker == rule.marker,
            "NORMALIZED_SET_IDENTITY",
        )
        target = case / relative
        confine(target, case)
        require(
            item.sha256 == diagnostics.get(relative) == digest(target),
            "NORMALIZED_SET_DIGEST",
        )
        require(len(read_labels(target)) == 0, "NORMALIZED_SET_NOT_EMPTY")


def verify_normalization(
    case: Path, receipt_path: Path, current: MeshDigests, diagnostics: Mapping[str, str]
) -> FileRef:
    """Preserve legacy provenance without asserting it supplies current bound execution."""
    receipt = LegacyNormalization.model_validate_json(receipt_path.read_bytes())
    require(
        receipt.candidate == case.name and receipt.mesh == current,
        "NORMALIZATION_IDENTITY",
    )
    log = case / "log.checkMesh-extended"
    require(
        receipt.external_check_log.path == log.name
        and receipt.external_check_log.sha256 == digest(log),
        "NORMALIZATION_LOG_DRIFT",
    )
    checked_zero_records(case, receipt.sets, diagnostics)
    return FileRef(
        path=receipt_path.relative_to(case.parent.parent.parent).as_posix(),
        sha256=digest(receipt_path),
    )


def verify_bound_normalization(
    case: Path, evidence: Path, current: MeshDigests, diagnostics: Mapping[str, str]
) -> tuple[FileRef, FileRef | None, list[Path]]:
    """Reconcile current normalized diagnostics with the immutable constant-only clone replay."""
    path = evidence / f"{case.name}-normalized-zero-sets-bound.json"
    receipt = NormalizationReceipt.model_validate_json(path.read_bytes())
    require(
        receipt.candidate == case.name and receipt.mesh == current,
        "BOUND_NORMALIZATION_IDENTITY",
    )
    source_log = case / "log.checkMesh-extended"
    require(
        receipt.external_check_log.path == source_log.name
        and receipt.external_check_log.sha256 == digest(source_log),
        "BOUND_SOURCE_LOG_DRIFT",
    )
    sidecar = evidence / f"{case.name}-bound-check.json"
    clone = case.parent / f"{case.name}-bound-check"
    replay_log = clone / "log.bound-check-extended"
    require(
        receipt.bound_replay.path == sidecar.name
        and receipt.bound_replay.sha256 == digest(sidecar),
        "BOUND_REPLAY_RECEIPT_DRIFT",
    )
    require(
        receipt.replay_check_log.path == canonical_wsl(replay_log)
        and receipt.replay_check_log.sha256 == digest(replay_log),
        "BOUND_REPLAY_LOG_DRIFT",
    )
    bound = BoundReplay.model_validate_json(sidecar.read_bytes())
    require(
        bound.candidate == case.name
        and bound.source_case == canonical_wsl(case)
        and bound.clone_case == canonical_wsl(clone)
        and bound.command == COMMAND,
        "BOUND_EXECUTION_IDENTITY",
    )
    require(
        bound.old_log_sha256 == digest(source_log)
        and bound.new_log_sha256 == digest(replay_log),
        "BOUND_EXECUTION_LOG_DRIFT",
    )
    require(
        all(
            mesh == current
            for mesh in (
                bound.source_mesh_before,
                bound.source_mesh_after,
                bound.clone_mesh_before,
                bound.clone_mesh_after,
                snapshot_mesh(clone),
            )
        ),
        "BOUND_MESH_DRIFT",
    )
    try:
        body = checked_body(replay_log.read_text(encoding="utf8"), clone)
    except NormalizationError as failure:
        raise PackageError("BOUND_INCOMPLETE_LOG") from failure
    proven = tuple(
        rule.name
        for rule in RULES
        if body.splitlines().count(rule.marker) == 1
        and not re.search(rule.failure, body, re.IGNORECASE)
    )
    require(receipt.proven_zero_checks == proven, "BOUND_PROVEN_CHECKS_DRIFT")
    checked_zero_records(case, receipt.sets, diagnostics)
    prior_sets = dict(set_hashes(case))
    for item in receipt.sets:
        require(
            item.name in proven and item.name not in bound.source_sets_before,
            "BOUND_SYNTHESIS_IDENTITY",
        )
        _ = prior_sets.pop(item.name)
    require(
        all(
            sets == prior_sets
            for sets in (
                bound.source_sets_before,
                bound.source_sets_after,
                bound.clone_sets_before,
                bound.clone_sets_after,
                set_hashes(clone),
            )
        ),
        "BOUND_SET_DRIFT",
    )
    files = [
        path,
        sidecar,
        replay_log,
        *(clone / "constant/polyMesh" / key for key in MeshDigests.model_fields),
        *(clone / "constant/polyMesh/sets" / key for key in bound.clone_sets_after),
    ]
    legacy_path = evidence / f"{case.name}-normalized-zero-sets.json"
    historical = None
    if legacy_path.exists():
        historical = verify_normalization(case, legacy_path, current, diagnostics)
        legacy = LegacyNormalization.model_validate_json(legacy_path.read_bytes())
        require(
            all(item.name in proven for item in legacy.sets), "LEGACY_ZERO_NOT_REPROVEN"
        )
        files.append(legacy_path)
    return (
        FileRef(
            path=path.relative_to(evidence.parent.parent).as_posix(),
            sha256=digest(path),
        ),
        historical,
        files,
    )
