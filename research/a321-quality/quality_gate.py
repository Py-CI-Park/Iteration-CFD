#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# How to run: imported by package_quality.py; test_quality_gate.py locks failure semantics.
"""Keep named numeric gates, external checks, and engineering readiness separate."""

from __future__ import annotations

import re
from enum import StrEnum


class CheckStatus(StrEnum):
    """External executable exit status is insufficient evidence of mesh acceptance."""

    PASS = "PASS"
    FAIL = "FAIL"
    MISSING = "MISSING"


def external_status(log: str) -> CheckStatus:
    """Require an explicit success marker and reject failures even when the process exits zero."""
    if not log:
        return CheckStatus.MISSING
    if re.search(r"FOAM FATAL|Failed \d+ mesh checks", log):
        return CheckStatus.FAIL
    if re.search(r"^\s*Mesh OK\.\s*$", log, flags=re.MULTILINE):
        return CheckStatus.PASS
    return CheckStatus.FAIL
