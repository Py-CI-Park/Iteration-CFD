#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_quality_gate.py.
"""Never turn a successful process exit or incomplete log into quality PASS."""

from __future__ import annotations

from quality_gate import CheckStatus, external_status


def test_failed_check_log_is_failure_despite_normal_end() -> None:
    """Given checkMesh's normal exit with failed checks, retain FAIL."""
    assert external_status("Failed 4 mesh checks.\nEnd\n") == CheckStatus.FAIL


def test_explicit_mesh_ok_marker_is_required() -> None:
    """Given an explicit success marker, accept only its bounded external check."""
    assert external_status("Checks complete\nMesh OK.\nEnd\n") == CheckStatus.PASS
    assert external_status("Create mesh\n") == CheckStatus.FAIL
    assert external_status("") == CheckStatus.MISSING
