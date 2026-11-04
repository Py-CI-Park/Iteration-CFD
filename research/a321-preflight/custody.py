#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# Imported by research adapters; tests: python -m pytest test_custody.py
"""Constrain writes to new research outputs and reject protected inputs."""

from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parent


def output_file(path: Path) -> Path:
    """Permit only new artifacts/evidence below this study root."""
    target = path.resolve()
    if target.is_relative_to((ROOT / "artifacts/input").resolve()):
        raise RuntimeError("PROTECTED_INPUT")
    allowed = any(
        target.is_relative_to((ROOT / folder).resolve())
        for folder in ("artifacts", "evidence")
    )
    if not allowed:
        raise RuntimeError("OUTPUT_OUTSIDE_ALLOWED_ROOT")
    if target.exists():
        raise RuntimeError("OUTPUT_ALREADY_EXISTS")
    return target


def trial_directory(path: Path) -> Path:
    """Require a fresh directory below artifacts, excluding frozen input."""
    target = output_file(path)
    if not target.is_relative_to((ROOT / "artifacts").resolve()):
        raise RuntimeError("TRIAL_OUTSIDE_ARTIFACTS")
    target.mkdir(parents=True, exist_ok=False)
    return target
