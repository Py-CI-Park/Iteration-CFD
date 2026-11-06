#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "pytest"]
# ///
# How to run: uv run --with pydantic --with pytest -m pytest test_custody.py.
"""Reject stale acceptance evidence and escaped audit output locations."""

from __future__ import annotations

from pathlib import Path

import pytest
from custody import require_unchanged, snapshot_mesh


def test_mesh_change_during_audit_is_rejected(tmp_path: Path) -> None:
    """Given bytes changed between reading and final digest collection, refuse publication."""
    pm = tmp_path / "constant/polyMesh"
    pm.mkdir(parents=True)
    for name in MESH_FILES:
        (pm / name).write_text("before")
    before = snapshot_mesh(tmp_path)
    (pm / "faces").write_text("during-computation")
    with pytest.raises(RuntimeError, match="CHANGED_DURING_AUDIT"):
        require_unchanged(tmp_path, before)


from custody import (
    MESH_FILES,
    R3_SHA,
    BoundAudit,
    digest,
    trial_directory,
    verify_binding,
)


def test_stale_mesh_receipt_cannot_be_accepted(tmp_path: Path) -> None:
    """Given an audited file that changes afterwards, reject its old receipt."""
    case = tmp_path / "candidate"
    pm = case / "constant/polyMesh"
    pm.mkdir(parents=True)
    for name in MESH_FILES:
        (pm / name).write_text("original")
    audit = BoundAudit(
        candidate=case.name,
        reference_sha256=R3_SHA,
        polyMesh_sha256={name: digest(pm / name) for name in MESH_FILES},
        cells=1,
        fluid_components=1,
        nonpositive_volumes=0,
        min_volume_m3=1.0,
        max_nonorth_deg=65.0,
        max_relative_closure=1e-14,
        wall_closed=True,
        wall_winding=True,
    )
    verify_binding(case, audit)
    (pm / "faces").write_text("changed")
    with pytest.raises(RuntimeError, match="STALE_MESH_AUDIT"):
        verify_binding(case, audit)


def test_escaped_and_nested_audit_paths_are_rejected(tmp_path: Path) -> None:
    """Given an arbitrary CLI path, allow only a direct artifact child."""
    artifacts = tmp_path / "artifacts"
    inside = artifacts / "case"
    inside.mkdir(parents=True)
    assert trial_directory(inside, artifacts) == inside.resolve()
    outside = tmp_path / "external"
    outside.mkdir()
    with pytest.raises(RuntimeError, match="OUTSIDE"):
        trial_directory(outside, artifacts)
    nested = inside / "case"
    nested.mkdir()
    with pytest.raises(RuntimeError, match="OUTSIDE"):
        trial_directory(nested, artifacts)
