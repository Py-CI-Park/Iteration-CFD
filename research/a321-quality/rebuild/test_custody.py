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
"""Source-capture and frozen-R4 custody regressions."""

import hashlib
import json
from pathlib import Path
import pytest
from custody import capture, verify_parent_freeze
from curves import CurveRejected


def test_parse_remains_bound_to_captured_bytes_after_file_changes(
    tmp_path: Path,
) -> None:
    # Given one captured ledger; When the on-disk file changes; Then parsing uses old sealed bytes.
    p = tmp_path / "source.json"
    p.write_text('{"station":1}')
    sealed = capture((p,))
    digest = sealed.digest(p)
    p.write_text('{"station":2}')
    assert json.loads(sealed.blobs[p])["station"] == 1
    assert sealed.digest(p) == digest
    assert hashlib.sha256(p.read_bytes()).hexdigest() != digest


def test_changed_r4_rejected_against_parent_freeze(tmp_path: Path) -> None:
    # Given parent's original R4 digest; When a changed R4 is captured; Then reject it.
    model = tmp_path / "r4.stl"
    model.write_bytes(b"original")
    original = hashlib.sha256(model.read_bytes()).hexdigest()
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({"inputs": [{"path": "r4.stl", "sha256": original}]}))
    pin = hashlib.sha256(freeze.read_bytes()).hexdigest()
    model.write_bytes(b"changed")
    sealed = capture((model, freeze))
    with pytest.raises(CurveRejected, match="PARENT_M1_INPUT_CHANGED"):
        verify_parent_freeze(sealed, freeze, tmp_path, pin)


def test_frozen_r4_accepted_when_exact(tmp_path: Path) -> None:
    # Given matching frozen R4; When captured and checked; Then permit exact input identity.
    model = tmp_path / "r4.stl"
    model.write_bytes(b"original")
    original = hashlib.sha256(model.read_bytes()).hexdigest()
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({"inputs": [{"path": "r4.stl", "sha256": original}]}))
    pin = hashlib.sha256(freeze.read_bytes()).hexdigest()
    verify_parent_freeze(capture((model, freeze)), freeze, tmp_path, pin)
