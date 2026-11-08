#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "typer>=0.12", "pytest>=8"]
# ///
# How to run: install uv; uv run --with pydantic --with typer --with pytest -m pytest test_surface_trials.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Isolated custody tests; no real mesher or solver is executed."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def trial_module():
    """Load preparation when exercising its behavior."""
    return importlib.import_module("prepare_surface_trials")


@pytest.fixture
def study(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trial_module) -> Path:
    """Create a small pinned substitute for real geometry."""
    root = tmp_path / "a321-quality"
    base = root / "artifacts/snappy-06"
    (base / "system").mkdir(parents=True)
    surface = base / "constant/triSurface/aircraft.stl"
    surface.parent.mkdir(parents=True)
    surface.write_bytes(b"reference triangles")
    canonical = root.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(surface.read_bytes())
    for name in trial_module.SYSTEM_FILES:
        (base / "system" / name).write_bytes(
            b"minFaceWeight 0.02;\nnBufferCellsNoExtrude 1;\n"
            if name == "snappyHexMeshDict"
            else b"frozen\n"
        )
    files = [surface, *sorted((base / "system").iterdir())]
    payload = {
        "legacy_post_run_snapshot": False,
        "sha256": {
            p.relative_to(base).as_posix(): trial_module.digest(p) for p in files
        },
    }
    manifest = base / "input-manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf8")
    (base / "input-manifest.sha256").write_text(
        "".join(f"{v}  {k}\n" for k, v in payload["sha256"].items()), encoding="utf8"
    )
    monkeypatch.setattr(trial_module, "R3_SHA", trial_module.digest(surface))
    monkeypatch.setattr(trial_module, "BASELINE06_SHA", trial_module.digest(manifest))
    return root


@pytest.mark.parametrize(
    "candidate,weight", [("08", "0.05"), ("09", "0.02"), ("10", "0.05"), ("11", "0.05")]
)
def test_only_declared_dictionary_change(
    study: Path, trial_module, candidate: str, weight: str
) -> None:
    # Given: a sealed baseline and a frozen derivative receipt.
    r4 = study / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl"
    r4.parent.mkdir()
    r4.write_bytes(b"smooth derivative triangles")
    receipt = study / "evidence/smooth-r4.json"
    receipt.parent.mkdir()
    receipt.write_text(
        json.dumps(
            {
                "source_sha256": trial_module.R3_SHA,
                "stl_sha256": trial_module.digest(r4),
            }
        ),
        encoding="utf8",
    )
    # When: one candidate is prepared.
    output = trial_module.prepare(trial_module.Candidate(candidate), root=study)
    # Then: only the declared dictionary token differs.
    baseline = study / "artifacts/snappy-06"
    for file in trial_module.SYSTEM_FILES:
        expected = (baseline / "system" / file).read_bytes()
        if file == "snappyHexMeshDict":
            expected = expected.replace(
                b"minFaceWeight 0.02;", f"minFaceWeight {weight};".encode()
            )
            if candidate == "11":
                expected = expected.replace(
                    b"nBufferCellsNoExtrude 1;", b"nBufferCellsNoExtrude 3;", 1
                )
        assert (output / "system" / file).read_bytes() == expected
    manifest = trial_module.TrialManifest.model_validate_json(
        (output / "input-manifest.json").read_bytes()
    )
    assert manifest.source_sha256 == trial_module.digest(
        output / "constant/triSurface/aircraft.stl"
    )
    assert manifest.baseline06_sha256 == trial_module.BASELINE06_SHA
    assert manifest.canonical_r3_sha256 == trial_module.R3_SHA
    assert "input-manifest.json" in (output / "input-manifest.sha256").read_text()


@pytest.mark.parametrize(
    "drift", ["system", "manifest", "canonical", "extra-system", "sidecar"]
)
def test_input_drift_refused_before_creation(
    study: Path, trial_module, drift: str
) -> None:
    # Given: one input altered after sealing.
    paths = {
        "system": study / "artifacts/snappy-06/system/fvSchemes",
        "manifest": study / "artifacts/snappy-06/input-manifest.json",
        "canonical": study.parent
        / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl",
        "extra-system": study / "artifacts/snappy-06/system/extra",
        "sidecar": study / "artifacts/snappy-06/input-manifest.sha256",
    }
    paths[drift].write_bytes(b"changed")
    # When / Then: refuse before creating a case.
    with pytest.raises(trial_module.TrialError):
        trial_module.prepare(trial_module.Candidate.C08, root=study)
    assert not (study / "artifacts/snappy-08").exists()


def test_nooverwrite_preserves_existing_trial(study: Path, trial_module) -> None:
    # Given: an existing user-owned trial.
    output = study / "artifacts/snappy-08"
    output.mkdir()
    sentinel = output / "sentinel"
    sentinel.write_bytes(b"preserve")
    # When / Then: refuse without changing its content.
    with pytest.raises(FileExistsError):
        trial_module.prepare(trial_module.Candidate.C08, root=study)
    assert sentinel.read_bytes() == b"preserve"


@pytest.mark.parametrize("receipt_state", ["missing", "wrong-source", "wrong-output"])
def test_derivative_requires_matching_receipt(
    study: Path, trial_module, receipt_state: str
) -> None:
    # Given: a derivative without matching generation provenance.
    r4 = study / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl"
    r4.parent.mkdir()
    r4.write_bytes(b"derivative")
    if receipt_state != "missing":
        receipt = study / "evidence/smooth-r4.json"
        receipt.parent.mkdir()
        receipt.write_text(
            json.dumps(
                {
                    "source_sha256": "0" * 64
                    if receipt_state == "wrong-source"
                    else trial_module.R3_SHA,
                    "stl_sha256": "0" * 64
                    if receipt_state == "wrong-output"
                    else trial_module.digest(r4),
                }
            ),
            encoding="utf8",
        )
    # When / Then: no case may be created.
    with pytest.raises((trial_module.TrialError, FileNotFoundError)):
        trial_module.prepare(trial_module.Candidate.C09, root=study)
    assert not (study / "artifacts/snappy-09").exists()


def test_cli_rejects_arbitrary_candidate(trial_module) -> None:
    # Given / When: the CLI receives an unapproved candidate.
    result = CliRunner().invoke(trial_module.app, ["--candidate", "12"])
    # Then: parsing fails before preparing anything.
    assert result.exit_code == 2
    assert all(choice in result.output for choice in ("08", "09", "10", "11"))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
