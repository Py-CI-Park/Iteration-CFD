#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "matplotlib", "pydantic>=2", "typer", "pytest"]
# ///
# How to run: uv run --with numpy --with matplotlib --with pydantic
#     --with typer --with pytest python -B -m pytest test_normalize_zero_sets.py -q
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: isolated fixtures using native binary messages; no GPL source.
"""Keep absent unknown sets distinct from explicitly passed native diagnostics."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from normalize_zero_sets import (
    NormalizationError,
    NormalizationReceipt,
    normalize,
)
from poly_io import read_labels
from zero_set_test_support import PASS_MARKERS, bind_fixture, make_case


@pytest.mark.parametrize(("set_name", "marker"), PASS_MARKERS)
def test_absent_set_becomes_explicit_zero_only_when_named_check_passes(
    tmp_path: Path, set_name: str, marker: str
) -> None:
    # Given one explicitly passed check and two native nonempty failure sets.
    case = make_case(tmp_path, f"    {marker}\nFailed 2 mesh checks.\n\nEnd\n")
    folder = case / "constant/polyMesh/sets"
    for other, _ in PASS_MARKERS:
        if other != set_name:
            (folder / other).write_text("1\n(\n4\n)\n", encoding="utf8")
    bind_fixture(case)
    before = {p: p.read_bytes() for p in case.rglob("*") if p.is_file()}
    # When normalizing the missing passed diagnostic.
    receipt_path = normalize(case.name, tmp_path)
    # Then an actual empty native set exists, with a separately bound receipt.
    assert (folder / set_name).is_file(), "explicit passed zero must become a real set"
    assert read_labels(folder / set_name).tolist() == []
    receipt = NormalizationReceipt.model_validate_json(
        receipt_path.read_text(encoding="utf8")
    )
    assert receipt.candidate == case.name
    assert (
        receipt.external_check_log.sha256
        == hashlib.sha256(before[case / "log.checkMesh-extended"]).hexdigest()
    )
    assert receipt.sets[0].name == set_name
    assert receipt.sets[0].synthesized is True
    assert receipt.sets[0].count == 0
    assert all(p.read_bytes() == value for p, value in before.items())


BAD_LOGS = (
    "Face interpolation weight check OK.\nMesh OK.\n",
    "Face interpolation weight check OK.\nMesh OK.\nEnd\ntrailing output\n",
    "Mesh OK.\nEnd\n",
    "***Faces with small interpolation weight (< 0.05) found, number: 2\n"
    "Failed 1 mesh checks.\nEnd\n",
    "Face interpolation weight check OK.\n"
    "***Faces with small interpolation weight (< 0.05) found, number: 2\n"
    "Failed 1 mesh checks.\nEnd\n",
    "Face interpolation weight check OK.\nFace interpolation weight check OK.\n"
    "Mesh OK.\nEnd\n",
    "Face interpolation weight check OK.\nFOAM FATAL ERROR\nMesh OK.\nEnd\n",
    "Face interpolation weight check OK.\nEnd\n",
    "Face interpolation weight check OK.\nMesh OK.\nEnd\n"
    "Exec : checkMesh -allTopology -allGeometry\nChecking geometry...\n"
    "Face interpolation weight check OK.\nMesh OK.\nEnd\n",
)


@pytest.mark.parametrize("text", BAD_LOGS)
def test_unproven_absent_weight_set_is_rejected_without_any_writes(
    tmp_path: Path, text: str
) -> None:
    # Given a missing weight set and incomplete, unknown or contradictory output.
    case = make_case(tmp_path, text)
    folder = case / "constant/polyMesh/sets"
    for name in ("underdeterminedCells", "concaveCells"):
        (folder / name).write_text("1\n(\n4\n)\n", encoding="utf8")
    bind_fixture(case)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # When normalization is requested.
    with pytest.raises(
        NormalizationError,
        match="WRONG_OR_INCOMPLETE_CONSTANT_CHECK|ABSENT_SET_IS_UNKNOWN_OR_FAILED",
    ):
        normalize(case.name, tmp_path)
    # Then absent remains unknown and no input or evidence is changed.
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "candidate", ("snappy-08", "snappy-09", "snappy-10", "snappy-11")
)
def test_all_three_explicit_passes_create_readable_zero_sets(
    tmp_path: Path, candidate: str
) -> None:
    # Given a completed all-pass native check without a sets directory.
    case = make_case(
        tmp_path,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
        candidate,
    )
    folder = case / "constant/polyMesh/sets"
    folder.rmdir()
    # When normalization materializes explicit zero diagnostics.
    result = normalize(candidate, tmp_path)
    # Then all three zeros are explicit and individually attributed.
    receipt = NormalizationReceipt.model_validate_json(
        result.read_text(encoding="utf8")
    )
    assert len(receipt.sets) == 3
    for entry in receipt.sets:
        path = case / entry.path
        assert read_labels(path).size == 0
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry.sha256


def test_any_unknown_missing_set_blocks_partial_synthesis(tmp_path: Path) -> None:
    # Given a passed determinant check but unknown absent concavity/weight sets.
    case = make_case(tmp_path, "Cell determinant check OK.\nMesh OK.\nEnd\n")
    # When preflighting all missing dependencies.
    with pytest.raises(NormalizationError, match="ABSENT_SET_IS_UNKNOWN_OR_FAILED"):
        normalize(case.name, tmp_path)
    # Then even the proven determinant zero has not been partially written.
    assert list((case / "constant/polyMesh/sets").iterdir()) == []
    assert not (
        tmp_path / "evidence/snappy-08-normalized-zero-sets-bound.json"
    ).exists()


def test_existing_native_sets_are_never_overwritten(tmp_path: Path) -> None:
    # Given native nonempty diagnostic sets and a completed failing check.
    case = make_case(tmp_path, "Failed 3 mesh checks.\nEnd\n")
    folder = case / "constant/polyMesh/sets"
    for name, _ in PASS_MARKERS:
        (folder / name).write_bytes(b"1\n(\n4\n)\n")
    bind_fixture(case)
    before = {p: p.read_bytes() for p in folder.iterdir()}
    # When normalization finds no absent dependencies.
    result = normalize(case.name, tmp_path)
    # Then the receipt synthesizes nothing and native diagnostic bytes remain.
    receipt = NormalizationReceipt.model_validate_json(
        result.read_text(encoding="utf8")
    )
    assert receipt.sets == ()
    assert {p: p.read_bytes() for p in folder.iterdir()} == before


@pytest.mark.parametrize("candidate", ("snappy-06", "snappy-12", "../snappy-08"))
def test_normalizer_rejects_every_candidate_outside_exact_new_allowlist(
    tmp_path: Path, candidate: str
) -> None:
    # Given a name outside the explicitly authorized candidates.
    # When attempting to normalize it, before any case is inspected.
    with pytest.raises(NormalizationError, match="INVALID_NORMALIZATION_CANDIDATE"):
        normalize(candidate, tmp_path)
    # Then no path was created.
    assert list(tmp_path.iterdir()) == []


def test_receipt_directory_cannot_redirect_outside_study(tmp_path: Path) -> None:
    # Given evidence redirected through a real directory link outside the study.
    import os
    import subprocess

    study = tmp_path / "study"
    outside = tmp_path / "outside"
    outside.mkdir()
    case = make_case(
        study,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
        binding=False,
    )
    evidence = study / "evidence"
    evidence.rmdir()
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(evidence), str(outside)],
            check=True,
            capture_output=True,
        )
    else:
        evidence.symlink_to(outside, target_is_directory=True)
    # When normalization checks its publication destination.
    with pytest.raises(NormalizationError, match="ALIASED_EVIDENCE_DIRECTORY"):
        normalize(case.name, study)
    # Then it neither writes outside nor synthesizes any source diagnostic.
    assert list(outside.iterdir()) == []
    assert list((case / "constant/polyMesh/sets").iterdir()) == []


def test_owned_truncated_set_is_removed_after_io_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given a short-write fault before a newly created set can be bound to evidence.
    import normalize_zero_sets

    case = make_case(
        tmp_path,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
    )

    def short_write_fault(path: Path) -> str:
        _ = path.write_bytes(b"FoamFile\n")
        message = "simulated short-write I/O failure"
        raise OSError(message)

    monkeypatch.setattr(normalize_zero_sets, "digest", short_write_fault)
    # When publication fails after creating a truncated owned diagnostic.
    with pytest.raises(OSError, match="short-write"):
        normalize(case.name, tmp_path)
    # Then it leaves neither an orphan set nor a normalization receipt.
    assert list((case / "constant/polyMesh/sets").iterdir()) == []
    assert not (
        tmp_path / "evidence/snappy-08-normalized-zero-sets-bound.json"
    ).exists()


def test_existing_candidate_lock_blocks_concurrent_publication(tmp_path: Path) -> None:
    # Given another normalizer already owns this candidate's publication interval.
    case = make_case(
        tmp_path,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
    )
    (case / ".normalize-zero-sets.lock").mkdir()
    # When a second normalizer attempts to publish.
    with pytest.raises(NormalizationError, match="NORMALIZATION_IN_PROGRESS"):
        normalize(case.name, tmp_path)
    # Then no zero sets or receipt can be published by the second normalizer.
    assert list((case / "constant/polyMesh/sets").iterdir()) == []
    assert not (
        tmp_path / "evidence/snappy-08-normalized-zero-sets-bound.json"
    ).exists()


def test_existing_receipt_blocks_new_synthesis(tmp_path: Path) -> None:
    # Given explicit passes but an already published normalization receipt.
    case = make_case(
        tmp_path,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
    )
    record = tmp_path / "evidence/snappy-08-normalized-zero-sets-bound.json"
    record.write_text("preserved receipt", encoding="utf8")
    # When attempting a second publication.
    with pytest.raises(NormalizationError, match="RECEIPT_ALREADY_EXISTS"):
        normalize(case.name, tmp_path)
    # Then neither existing evidence nor absent source diagnostics were altered.
    assert record.read_text(encoding="utf8") == "preserved receipt"
    assert list((case / "constant/polyMesh/sets").iterdir()) == []


def test_cli_normalizes_only_an_isolated_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given the real CLI bound to a temporary case, never a research artifact.
    import typer
    from typer.testing import CliRunner

    import normalize_zero_sets

    make_case(
        tmp_path,
        "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n",
    )
    monkeypatch.setattr(normalize_zero_sets, "ROOT", tmp_path)
    app = typer.Typer()
    app.command()(normalize_zero_sets.main)
    # When running the CLI surface.
    result = CliRunner().invoke(app, ["--candidate", "snappy-08"])
    # Then the explicit normalization receipt is published successfully.
    assert result.exit_code == 0, result.output
    assert (tmp_path / "evidence/snappy-08-normalized-zero-sets-bound.json").is_file()


@pytest.mark.parametrize(
    "candidate", ("snappy-08", "snappy-09", "snappy-10", "snappy-11", "snappy-12")
)
def test_existing_pipeline_candidate_guards_remain_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, candidate: str
) -> None:
    # Given the existing pipelines with an empty fixture root.
    import diagnostic_owner_view
    import map_hotspots
    import seal_diagnostics

    for module in (diagnostic_owner_view, map_hotspots, seal_diagnostics):
        monkeypatch.setattr(module, "ROOT", tmp_path)
        # When checking the name guard, accepted names reach missing-input I/O.
        if candidate == "snappy-12":
            with pytest.raises(RuntimeError, match="CANDIDATE"):
                module.main(candidate)
        else:
            with pytest.raises(FileNotFoundError):
                module.main(candidate)
    # Then no pipeline creates outputs from missing inputs.
    assert list(tmp_path.iterdir()) == []
