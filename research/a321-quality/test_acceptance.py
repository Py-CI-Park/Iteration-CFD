#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "pytest"]
# ///
# How to run: uv run --with pydantic --with pytest -m pytest test_acceptance.py.
"""Lock strict project limits even when an external executable prints Mesh OK."""

from __future__ import annotations

import pytest
from acceptance import CpuStatus, NumericAudit, cpu_status
from pydantic import ValidationError
from quality_gate import CheckStatus


def baseline() -> NumericAudit:
    """A finite positive, closed one-region synthetic measured receipt."""
    return NumericAudit(
        cells=1,
        fluid_components=1,
        nonpositive_volumes=0,
        min_volume_m3=1.0,
        max_nonorth_deg=65.0,
        max_relative_closure=1e-14,
        wall_closed=True,
        wall_winding=True,
    )


def test_mesh_ok_does_not_override_angle_limit() -> None:
    """Given the observed candidate-two angle, reject even with Mesh OK."""
    audit = baseline().model_copy(update={"max_nonorth_deg": 70.14706464318955})
    assert cpu_status(audit, CheckStatus.PASS, 0) == CpuStatus.FAIL


def test_closure_and_native_errors_are_mandatory() -> None:
    """Given a valid numeric case, require both closure and zero final native illegal faces."""
    assert cpu_status(baseline(), CheckStatus.PASS, 0) == CpuStatus.PASS
    assert cpu_status(baseline(), CheckStatus.PASS, 1) == CpuStatus.FAIL
    assert cpu_status(baseline(), CheckStatus.MISSING, 0) == CpuStatus.FAIL
    assert (
        cpu_status(
            baseline().model_copy(update={"max_relative_closure": 1.1e-10}),
            CheckStatus.PASS,
            0,
        )
        == CpuStatus.FAIL
    )


def test_nonfinite_measurements_are_rejected() -> None:
    """Given NaN from a broken audit, fail parsing rather than allowing comparisons to miss it."""
    values = baseline().model_dump()
    values["max_nonorth_deg"] = float("nan")
    with pytest.raises(ValidationError):
        NumericAudit.model_validate(values)
