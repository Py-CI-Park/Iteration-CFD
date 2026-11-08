#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "typer"]
# ///
# How to run: uv run normalize_zero_sets.py --candidate snappy-11
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI/native diagnostic data. No GPL-licensed source consulted.
"""Normalize proven zeros after an immutable isolated constant-check replay."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

import typer

from bound_check_models import CANDIDATES, RULES
from bound_check_models import COMMAND as COMMAND
from bound_check_models import BoundReplay as BoundReplay
from bound_check_models import FrozenModel as FrozenModel
from bound_check_models import LogBinding as LogBinding
from bound_check_models import NormalizationError as NormalizationError
from bound_check_models import NormalizationReceipt as NormalizationReceipt
from bound_check_models import NormalizedSet as NormalizedSet
from bound_check_models import ZeroRule as ZeroRule
from bound_replay import allowed_source_sets as allowed_source_sets
from bound_replay import bound_body as bound_body
from bound_replay import canonical_wsl as canonical_wsl
from bound_replay import checked_body as checked_body
from bound_replay import empty_set as empty_set
from bound_replay import set_hashes as set_hashes
from custody import MeshDigests as MeshDigests
from custody import digest, require_unchanged, snapshot_mesh, trial_directory

ROOT: Final = Path(__file__).resolve().parent


def normalize(candidate: str, root: Path) -> Path:
    """Serialize one candidate's preflight, publication and rollback."""
    if candidate not in CANDIDATES:
        reason = "INVALID_NORMALIZATION_CANDIDATE"
        raise NormalizationError(reason)
    study = root.resolve()
    case = trial_directory(study / "artifacts" / candidate, study / "artifacts")
    evidence = study / "evidence"
    if (
        evidence.resolve() != evidence
        or not evidence.is_dir()
        or case.name != candidate
    ):
        reason = "ALIASED_EVIDENCE_DIRECTORY"
        raise NormalizationError(reason)
    lock = case / ".normalize-zero-sets.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        reason = "NORMALIZATION_IN_PROGRESS"
        raise NormalizationError(reason) from error
    try:
        return normalize_locked(case, candidate, evidence)
    finally:
        lock.rmdir()


def normalize_locked(case: Path, candidate: str, evidence: Path) -> Path:
    """Validate source and bound clone, then publish a fresh separate follow-up."""
    destination = evidence / f"{candidate}-normalized-zero-sets-bound.json"
    if destination.exists() or destination.is_symlink():
        reason = "NORMALIZATION_RECEIPT_ALREADY_EXISTS"
        raise NormalizationError(reason)
    folder = case / "constant/polyMesh/sets"
    log = case / "log.checkMesh-extended"
    raw = log.read_bytes()
    _ = checked_body(raw.decode("utf8"), case)
    before = snapshot_mesh(case)
    body, replay_log, binding = bound_body(case, evidence, raw, before)
    proven = tuple(
        r
        for r in RULES
        if body.splitlines().count(r.marker) == 1
        and not re.search(r.failure, body, re.I)
    )
    pending: list[ZeroRule] = []
    for rule in RULES:
        path = folder / rule.name
        if (
            path.is_symlink()
            or (path.exists() and not path.is_file())
            or (not path.exists() and rule not in proven)
        ):
            reason = f"ABSENT_SET_IS_UNKNOWN_OR_FAILED:{rule.name}"
            raise NormalizationError(reason)
        if not path.exists():
            pending.append(rule)
    records: list[NormalizedSet] = []
    created: list[Path] = []
    receipt_created = False
    try:
        folder.mkdir(exist_ok=True)
        for rule in pending:
            path = folder / rule.name
            with path.open("x", encoding="utf8", newline="\n") as handle:
                created.append(path)
                _ = handle.write(empty_set(rule))
            records.append(
                NormalizedSet(
                    name=rule.name,
                    path=path.relative_to(case).as_posix(),
                    pass_marker=rule.marker,
                    sha256=digest(path),
                )
            )
        require_unchanged(case, before)
        if log.read_bytes() != raw or digest(evidence / binding.path) != binding.sha256:
            reason = "EVIDENCE_CHANGED_DURING_NORMALIZATION"
            raise NormalizationError(reason)
        receipt = NormalizationReceipt(
            candidate=candidate,
            mesh=before,
            sets=tuple(records),
            external_check_log=LogBinding(
                path=log.name, sha256=hashlib.sha256(raw).hexdigest()
            ),
            replay_check_log=replay_log,
            bound_replay=binding,
            proven_zero_checks=tuple(r.name for r in proven),
        )
        with destination.open("x", encoding="utf8", newline="\n") as handle:
            receipt_created = True
            _ = handle.write(receipt.model_dump_json(indent=2) + "\n")
    except (OSError, RuntimeError):
        if receipt_created:
            destination.unlink()
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return destination


def main(candidate: str = "snappy-11") -> None:
    """Require a completed clone replay before explicit diagnostic normalization."""
    typer.echo(normalize(candidate, ROOT))


if __name__ == "__main__":
    typer.run(main)
