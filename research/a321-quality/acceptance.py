#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2"]
# ///
# How to run: imported by package_quality.py; test_acceptance.py locks numeric limits.
"""Typed numeric acceptance, independent of a mesher's broader 'Mesh OK' message."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from quality_gate import CheckStatus


class NumericAudit(BaseModel):
    """Parse only the measured quantities used for the scoped CPU gate."""

    model_config = ConfigDict(frozen=True, strict=True, allow_inf_nan=False)
    cells: int = Field(gt=0)
    fluid_components: int = Field(gt=0)
    nonpositive_volumes: int = Field(ge=0)
    min_volume_m3: float
    max_nonorth_deg: float = Field(ge=0, le=180)
    max_relative_closure: float = Field(ge=0)
    wall_closed: bool
    wall_winding: bool


class CpuStatus(StrEnum):
    """A scoped mesh gate never implies aerodynamic validation or GPU authorization."""

    PASS = "NAMED_CPU_GATES_PASS"
    FAIL = "FIX_FIRST"


def cpu_status(
    audit: NumericAudit, standard: CheckStatus, illegal_faces: int | None
) -> CpuStatus:
    """Require actual measurements plus unambiguous native quality checks."""
    passed = (
        audit.nonpositive_volumes == 0
        and audit.min_volume_m3 > 0
        and audit.fluid_components == 1
        and audit.wall_closed
        and audit.wall_winding
        and audit.max_nonorth_deg <= 70
        and audit.max_relative_closure <= 1e-10
        and standard == CheckStatus.PASS
        and illegal_faces == 0
    )
    return CpuStatus.PASS if passed else CpuStatus.FAIL
