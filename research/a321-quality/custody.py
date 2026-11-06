#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: imported by candidate preparation and packaging; tests use isolated temporary directories.
"""Bind acceptance to current bytes and confine generated data to this study."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

from acceptance import NumericAudit
from pydantic import BaseModel, ConfigDict

R3_SHA: Final = "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
MESH_FILES: Final = ("points", "faces", "owner", "neighbour", "boundary")


class MeshDigests(BaseModel):
    """A frozen digest for every file constituting the measured polyMesh."""

    model_config = ConfigDict(frozen=True, strict=True)
    points: str
    faces: str
    owner: str
    neighbour: str
    boundary: str


def snapshot_mesh(case: Path) -> MeshDigests:
    """Capture byte identity before reading the measured arrays."""
    return MeshDigests(
        **{name: digest(case / "constant/polyMesh" / name) for name in MESH_FILES}
    )


def require_unchanged(case: Path, before: MeshDigests) -> None:
    """Reject concurrent geometry mutation before any audit result is published."""
    if snapshot_mesh(case) != before:
        raise RuntimeError("MESH_CHANGED_DURING_AUDIT")


def digest(path: Path) -> str:
    """Hash a file incrementally without duplicating large mesh buffers."""
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def trial_directory(path: Path, artifacts: Path) -> Path:
    """Require a direct child of the resolved study artifact root, rejecting escapes and aliases."""
    resolved = path.resolve()
    if resolved.parent != artifacts.resolve() or not resolved.is_dir():
        raise RuntimeError("TRIAL_OUTSIDE_STUDY")
    return resolved


class BoundAudit(NumericAudit):
    """An audit receipt must name its candidate, original reference and five serialized arrays."""

    candidate: str
    reference_sha256: str
    polyMesh_sha256: dict[str, str]


def verify_binding(case: Path, audit: BoundAudit) -> None:
    """Reject stale geometry receipts before any acceptance state is emitted."""
    if audit.candidate != case.name or audit.reference_sha256 != R3_SHA:
        raise RuntimeError("AUDIT_IDENTITY_MISMATCH")
    if set(audit.polyMesh_sha256) != set(MESH_FILES):
        raise RuntimeError("INCOMPLETE_MESH_DIGESTS")
    for name in MESH_FILES:
        if digest(case / "constant/polyMesh" / name) != audit.polyMesh_sha256[name]:
            raise RuntimeError("STALE_MESH_AUDIT")


def write_input_manifest(case: Path, legacy_snapshot: bool = False) -> None:
    """Capture an immutable configuration/input snapshot, explicitly labeling historical snapshots."""
    source = case / "constant/triSurface/aircraft.stl"
    if digest(source) != R3_SHA:
        raise RuntimeError("R3_INPUT_CHANGED")
    files = [source, *sorted((case / "system").glob("*"))]
    payload = {
        "legacy_post_run_snapshot": legacy_snapshot,
        "sha256": {
            p.relative_to(case).as_posix(): digest(p) for p in files if p.is_file()
        },
    }
    with (case / "input-manifest.json").open("x", encoding="utf8") as handle:
        json.dump(payload, handle, indent=2)
    with (case / "input-manifest.sha256").open(
        "x", encoding="utf8", newline="\n"
    ) as handle:
        for relative, value in payload["sha256"].items():
            handle.write(f"{value}  {relative}\n")


def verify_input_manifest(case: Path) -> None:
    """Verify every recorded input before deriving or executing a new candidate."""
    data = json.loads((case / "input-manifest.json").read_text(encoding="utf8"))
    if digest(case / "constant/triSurface/aircraft.stl") != R3_SHA:
        raise RuntimeError("R3_INPUT_CHANGED")
    for relative, expected in data["sha256"].items():
        path = (case / relative).resolve()
        if not path.is_relative_to(case.resolve()) or digest(path) != expected:
            raise RuntimeError("INPUT_MANIFEST_MISMATCH")
