#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: imported by normalize_zero_sets.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI/native diagnostic data. No GPL-licensed source consulted.
"""Strict immutable schemas for bound native-check evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict

from custody import MeshDigests

CANDIDATES: Final = frozenset({"snappy-08", "snappy-09", "snappy-10", "snappy-11"})
COMMAND: Final = ("checkMesh", "-constant", "-allTopology", "-allGeometry")


class NormalizationError(RuntimeError):
    """Refuse incomplete, stale, unbound or contradictory diagnostic evidence."""

    def __init__(self, reason: str) -> None:
        """Preserve a machine-readable refusal reason."""
        self.reason: str = reason
        super().__init__(reason)


class FrozenModel(BaseModel):
    """Strict immutable evidence boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, strict=True, extra="forbid"
    )


@dataclass(frozen=True, slots=True)
class ZeroRule:
    """Exact native pass marker and corresponding contradictory output."""

    name: str
    kind: Literal["cellSet", "faceSet"]
    marker: str
    failure: str


RULES: Final = (
    ZeroRule(
        "underdeterminedCells",
        "cellSet",
        "Cell determinant check OK.",
        r"small determinant|under-determined cells|underdeterminedCells",
    ),
    ZeroRule(
        "concaveCells",
        "cellSet",
        "Concave cell check OK.",
        r"Concave cells \(using face planes\) found|concave cells to set|concaveCells",
    ),
    ZeroRule(
        "lowWeightFaces",
        "faceSet",
        "Face interpolation weight check OK.",
        r"small interpolation weight|low interpolation weights to set|lowWeightFaces",
    ),
)


class LogBinding(FrozenModel):
    """Identity of immutable external evidence."""

    path: str
    sha256: str


class NormalizedSet(FrozenModel):
    """A zero synthesized by this operation, not attributed to the native executable."""

    name: str
    path: str
    pass_marker: str
    sha256: str
    synthesized: Literal[True] = True
    count: Literal[0] = 0


class BoundReplay(FrozenModel):
    """Execution receipt emitted by the stdlib clone runner."""

    schema_version: Literal[1]
    candidate: str
    source_case: str
    clone_case: str
    command: tuple[str, ...]
    old_log_sha256: str
    new_log_sha256: str
    source_mesh_before: MeshDigests
    source_mesh_after: MeshDigests
    clone_mesh_before: MeshDigests
    clone_mesh_after: MeshDigests
    source_sets_before: dict[str, str]
    source_sets_after: dict[str, str]
    clone_sets_before: dict[str, str]
    clone_sets_after: dict[str, str]
    returncode: Literal[0]
    status: Literal["BOUND_REPLAY_COMPLETE"]


class NormalizationReceipt(FrozenModel):
    """Separate bound follow-up; legacy normalization receipts remain historical."""

    schema_version: Literal[2] = 2
    candidate: str
    external_check_log: LogBinding
    replay_check_log: LogBinding
    bound_replay: LogBinding
    mesh: MeshDigests
    sets: tuple[NormalizedSet, ...]
    proven_zero_checks: tuple[str, ...]
    status: Literal["DIAGNOSTICS_ONLY_NOT_MESH_ACCEPTANCE"] = (
        "DIAGNOSTICS_ONLY_NOT_MESH_ACCEPTANCE"
    )
