#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Capture once, parse the same bytes, and enforce the parent's frozen input ledger."""

from __future__ import annotations
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from pydantic import BaseModel, ConfigDict
from curves import CurveRejected


@dataclass(frozen=True, slots=True)
class Captured:
    blobs: Mapping[Path, bytes]

    def digest(self, path: Path) -> str:
        return hashlib.sha256(self.blobs[path]).hexdigest()


class Pin(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    sha256: str


class Freeze(BaseModel):
    model_config = ConfigDict(frozen=True)
    inputs: list[Pin]


def capture(paths: tuple[Path, ...]) -> Captured:
    """Every file is read exactly once, with immutable captured byte values."""
    return Captured(MappingProxyType({path: path.read_bytes() for path in paths}))


def verify_parent_freeze(
    captured: Captured, freeze_path: Path, repo: Path, expected_sha: str
) -> None:
    """Reject changed R4 and all other M1 inputs using the pre-existing parent ledger."""
    if captured.digest(freeze_path) != expected_sha:
        raise CurveRejected("PARENT_M1_FREEZE_CHANGED")
    frozen = Freeze.model_validate_json(captured.blobs[freeze_path])
    for pin in frozen.inputs:
        path = repo / pin.path
        if path not in captured.blobs or captured.digest(path) != pin.sha256:
            raise CurveRejected(f"PARENT_M1_INPUT_CHANGED:{pin.path}")
