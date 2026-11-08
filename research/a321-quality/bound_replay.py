#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: imported by normalize_zero_sets.py; no engine execution
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI/native diagnostic data. No GPL-licensed source consulted.
"""Validate isolated replay identity and authenticated post-replay zero additions."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from bound_check_models import (
    COMMAND,
    RULES,
    BoundReplay,
    LogBinding,
    NormalizationError,
    NormalizationReceipt,
    ZeroRule,
)
from custody import MeshDigests, digest, snapshot_mesh


def canonical_wsl(path: Path) -> str:
    """Map a resolved Windows drive path to its canonical WSL /mnt identity."""
    resolved = path.resolve()
    value = resolved.as_posix()
    return "/mnt/" + resolved.drive[0].lower() + value[2:] if resolved.drive else value


def checked_body(text: str, case: Path) -> str:
    """Require the exact candidate and constant-only native extended-check command."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    commands = [
        tuple(m.group(1).split()) for m in re.finditer(r"^Exec\s*:\s*(.*)$", text, re.M)
    ]
    cases = [m.group(1).strip() for m in re.finditer(r"^Case\s*:\s*(.*)$", text, re.M)]
    times = [m.group(1).strip() for m in re.finditer(r"^Time\s*=\s*(.*)$", text, re.M)]
    summaries = [
        i
        for i, line in enumerate(lines)
        if re.fullmatch(r"Mesh OK\.|Failed [1-9][0-9]* mesh checks\.", line)
    ]
    if (
        not lines
        or lines[-1] != "End"
        or lines.count("End") != 1
        or commands != [COMMAND]
        or cases != [canonical_wsl(case)]
        or any(time != "constant" for time in times)
        or lines.count("Checking geometry...") != 1
        or len(summaries) != 1
        or summaries[0] != len(lines) - 2
        or re.search(r"FOAM FATAL|FOAM exiting|Segmentation fault|MPI_ABORT", text)
    ):
        reason = "WRONG_OR_INCOMPLETE_CONSTANT_CHECK"
        raise NormalizationError(reason)
    start = lines.index("Checking geometry...")
    if start >= summaries[0]:
        reason = "MISSING_GEOMETRY_CHECK_BODY"
        raise NormalizationError(reason)
    return "\n".join(lines[start + 1 : summaries[0]])


def set_hashes(case: Path) -> Mapping[str, str]:
    """Hash existing local diagnostic bytes, never infer zero from absence."""
    folder = case / "constant/polyMesh/sets"
    paths = sorted(folder.rglob("*")) if folder.exists() else []
    if folder.resolve() != folder or any(p.is_symlink() for p in paths):
        reason = "ALIASED_DIAGNOSTIC_DIRECTORY"
        raise NormalizationError(reason)
    return {p.relative_to(folder).as_posix(): digest(p) for p in paths if p.is_file()}


def bound_body(
    case: Path, evidence: Path, raw: bytes, before: MeshDigests
) -> tuple[str, LogBinding, LogBinding]:
    """Recheck execution identity and current source/clone bytes."""
    sidecar = evidence / f"{case.name}-bound-check.json"
    clone = case.parent / f"{case.name}-bound-check"
    try:
        data = sidecar.read_bytes()
        bound = BoundReplay.model_validate_json(data)
    except (OSError, ValidationError) as error:
        reason = "MISSING_OR_INVALID_BOUND_REPLAY"
        raise NormalizationError(reason) from error
    log = clone / "log.bound-check-extended"
    replay = log.read_bytes()
    body = checked_body(replay.decode("utf8"), clone)
    meshes = (
        bound.source_mesh_before,
        bound.source_mesh_after,
        bound.clone_mesh_before,
        bound.clone_mesh_after,
        snapshot_mesh(clone),
    )
    sets = (
        bound.source_sets_before,
        bound.source_sets_after,
        bound.clone_sets_before,
        bound.clone_sets_after,
        set_hashes(clone),
    )
    current_sets = allowed_source_sets(case, evidence, bound, data, before, body)
    if (
        sidecar.resolve() != sidecar
        or clone.resolve() != clone
        or bound.candidate != case.name
        or bound.source_case != canonical_wsl(case)
        or bound.clone_case != canonical_wsl(clone)
        or bound.command != COMMAND
        or bound.old_log_sha256 != hashlib.sha256(raw).hexdigest()
        or bound.new_log_sha256 != hashlib.sha256(replay).hexdigest()
        or any(mesh != before for mesh in meshes)
        or any(value != bound.source_sets_before for value in sets)
        or current_sets != set_hashes(case)
    ):
        reason = "BOUND_REPLAY_IDENTITY_OR_BYTES_MISMATCH"
        raise NormalizationError(reason)
    return (
        body,
        LogBinding(path=canonical_wsl(log), sha256=bound.new_log_sha256),
        LogBinding(path=sidecar.name, sha256=hashlib.sha256(data).hexdigest()),
    )


def allowed_source_sets(
    case: Path,
    evidence: Path,
    bound: BoundReplay,
    data: bytes,
    before: MeshDigests,
    body: str,
) -> Mapping[str, str]:
    """Allow only receipt-bound new zero files; original replay sets stay immutable."""
    expected = dict(bound.source_sets_after)
    path = evidence / f"{case.name}-normalized-zero-sets-bound.json"
    if set_hashes(case) == expected and not path.exists() and not path.is_symlink():
        return expected
    try:
        receipt = NormalizationReceipt.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as error:
        reason = "UNBOUND_POST_REPLAY_SET_CHANGE"
        raise NormalizationError(reason) from error
    proven = tuple(
        r.name
        for r in RULES
        if body.splitlines().count(r.marker) == 1
        and not re.search(r.failure, body, re.I)
    )
    valid = (
        path.resolve() == path
        and receipt.candidate == case.name
        and receipt.mesh == before
        and receipt.bound_replay.path == f"{case.name}-bound-check.json"
        and receipt.bound_replay.sha256 == hashlib.sha256(data).hexdigest()
        and receipt.external_check_log.path == "log.checkMesh-extended"
        and receipt.external_check_log.sha256 == bound.old_log_sha256
        and receipt.replay_check_log.path
        == canonical_wsl(
            case.parent / f"{case.name}-bound-check/log.bound-check-extended"
        )
        and receipt.replay_check_log.sha256 == bound.new_log_sha256
        and receipt.proven_zero_checks == proven
    )
    for item in receipt.sets:
        relative = item.path.removeprefix("constant/polyMesh/sets/")
        rule = next((r for r in RULES if r.name == item.name), None)
        if (
            rule is None
            or relative != item.name
            or relative in expected
            or item.name not in proven
            or item.pass_marker != rule.marker
            or item.path != f"constant/polyMesh/sets/{item.name}"
        ):
            valid = False
            break
        value = case / item.path
        try:
            payload = value.read_bytes()
        except OSError as error:
            reason = "MISSING_AUTHENTICATED_ZERO_ADDITION"
            raise NormalizationError(reason) from error
        if hashlib.sha256(payload).hexdigest() != item.sha256 or payload != empty_set(
            rule
        ).encode("utf8"):
            valid = False
            break
        expected[relative] = item.sha256
    if not valid:
        reason = "INVALID_POST_REPLAY_ZERO_ADDITION"
        raise NormalizationError(reason)
    return expected


def empty_set(rule: ZeroRule) -> str:
    """Serialize an explicit empty set using public FoamFile data syntax."""
    return (
        f"// Synthesized explicit zero; see bound normalization receipt.\n"
        f"FoamFile {{version 2.0; format ascii; class {rule.kind};\n"
        f'location "constant/polyMesh/sets"; object {rule.name};}}\n0\n(\n)\n'
    )
