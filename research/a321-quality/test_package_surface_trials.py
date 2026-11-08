#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer", "pytest"]
# ///
# How to run: install uv; uv run --with numpy --with pydantic --with typer --with pytest -m pytest test_package_surface_trials.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Focused isolated checks; never invoke the production packaging entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import BinaryIO, Literal, assert_never

import package_surface_trials as package
import prepare_surface_trials as preparation
import pytest
import surface_package_checks as checks


def test_existing_evidence_is_never_overwritten(tmp_path: Path) -> None:
    # Given: an existing evidence file and a replacement source.
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"new")
    target.write_bytes(b"preserved")
    # When / Then: refuse rather than replacing evidence.
    with pytest.raises(FileExistsError):
        package.copy_exclusive(source, target, package.digest(source))
    assert target.read_bytes() == b"preserved"


def test_source_drift_during_copy_refused(tmp_path: Path) -> None:
    # Given: source bytes no longer matching their captured hash.
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"before")
    expected = package.digest(source)
    source.write_bytes(b"after")
    # When / Then: no published copy is accepted as the old evidence.
    with pytest.raises(package.PackageError, match="COPY_CHANGED"):
        package.copy_exclusive(source, target, expected)
    assert not target.exists()
    package.copy_exclusive(source, target, package.digest(source))
    assert target.read_bytes() == b"after"


def test_invalid_case_never_reads_artifacts(tmp_path: Path) -> None:
    # Given: an escaped or unsupported case ID.
    # When / Then: reject before looking for any case artifacts.
    with pytest.raises(package.PackageError, match="INVALID_CASE"):
        package.load_case(tmp_path, "../snappy-06")


def test_unknown_illegal_faces_remain_unknown() -> None:
    # Given: a truncated native meshing log.
    # When / Then: absence of proof is not zero illegal faces.
    assert package.illegal_faces("Stopped during meshing") is None


@pytest.fixture
def study(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create tiny isolated custody inputs, never production case artifacts."""
    root = tmp_path / "a321-quality"
    base = root / "artifacts/snappy-06"
    (base / "system").mkdir(parents=True)
    surface = base / preparation.SURFACE
    surface.parent.mkdir(parents=True)
    surface.write_bytes(b"reference")
    canonical = preparation.canonical(root)
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(surface.read_bytes())
    for name in preparation.SYSTEM_FILES:
        content = (
            b"minFaceWeight 0.02; nBufferCellsNoExtrude 1;"
            if name == "snappyHexMeshDict"
            else b"frozen"
        )
        (base / "system" / name).write_bytes(content)
    hashes = {
        p.relative_to(base).as_posix(): package.digest(p)
        for p in [surface, *sorted((base / "system").iterdir())]
    }
    manifest = base / "input-manifest.json"
    manifest.write_text(
        json.dumps({"legacy_post_run_snapshot": False, "sha256": hashes}),
        encoding="utf8",
    )
    (base / "input-manifest.sha256").write_text(
        "".join(f"{v}  {k}\n" for k, v in hashes.items()), encoding="utf8"
    )
    for module in (package, preparation):
        monkeypatch.setattr(module, "R3_SHA", package.digest(surface))
        monkeypatch.setattr(module, "BASELINE06_SHA", package.digest(manifest))
    derivative = root / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl"
    derivative.parent.mkdir()
    derivative.write_bytes(b"derivative")
    receipt = root / "evidence/smooth-r4.json"
    receipt.parent.mkdir()
    receipt.write_text(
        json.dumps(
            {
                "source_sha256": package.digest(surface),
                "stl_sha256": package.digest(derivative),
            }
        ),
        encoding="utf8",
    )
    runner = root / "run_surface_trial.sh"
    runner.write_bytes(b"historical-runner")
    historical = package.digest(runner)
    runner.write_bytes(b"new-runner")
    monkeypatch.setattr(package, "RUNNER_SHAS", (historical, package.digest(runner)))
    return root


def prepared(study: Path, candidate: preparation.Candidate) -> Path:
    """Capture the manifest copies normally written by the runner without executing it."""
    case = preparation.prepare(candidate, root=study)
    lock = case / ".execution.lock"
    lock.mkdir()
    for name in ("input-manifest.json", "input-manifest.sha256"):
        (lock / name).write_bytes((case / name).read_bytes())
    (lock / "runner.sh").write_bytes(
        b"new-runner"
        if candidate == preparation.Candidate.C11
        else b"historical-runner"
    )
    return case


@pytest.mark.parametrize("candidate", list(preparation.Candidate))
def test_current_inputs_match_execution_freeze(
    study: Path, candidate: preparation.Candidate
) -> None:
    # Given: a complete execution freeze made without launching a mesh program.
    case = prepared(study, candidate)
    # When: the packager validates this candidate's custody boundary.
    files = package.verify_trial_inputs(study, case.name)
    # Then: both current and original captured manifests are represented.
    assert case / "input-manifest.json" in files
    assert case / ".execution.lock/input-manifest.json" in files


@pytest.mark.parametrize(
    "relative",
    [
        "system/fvSchemes",
        "constant/triSurface/aircraft.stl",
        ".execution.lock/input-manifest.json",
        ".execution.lock/runner.sh",
    ],
)
def test_input_or_execution_drift_is_refused(study: Path, relative: str) -> None:
    # Given: a current input or frozen launch copy altered after generation.
    case = prepared(study, preparation.Candidate.C11)
    (case / relative).write_bytes(b"altered")
    # When / Then: publishing is refused before any evidence output exists.
    with pytest.raises(package.PackageError):
        package.verify_trial_inputs(study, case.name)
    assert not (study / "evidence/surface-comparison.json").exists()


def test_historical_trial_cannot_accept_new_runner(study: Path) -> None:
    # Given: an old trial with its captured runner replaced by the approved new version.
    case = prepared(study, preparation.Candidate.C08)
    (case / ".execution.lock/runner.sh").write_bytes(b"new-runner")
    # When / Then: approval for 11 cannot rewrite launch history for 08.
    with pytest.raises(package.PackageError, match="FROZEN_RUNNER"):
        package.verify_trial_inputs(study, case.name)


def test_destination_escape_is_refused(tmp_path: Path) -> None:
    # Given: a destination resolving outside the study.
    # When / Then: refuse it before creating any output.
    with pytest.raises(package.PackageError, match="PATH_ESCAPE"):
        package.confine(tmp_path.parent / "escaped", tmp_path)


@pytest.mark.parametrize(
    "suffix",
    [
        "",
        "\nEnd\nFOAM FATAL ERROR",
        "\nEnd\nEnd",
        "\nEnd\nExec : snappyHexMesh\nFinished meshing without any errors\nEnd",
        "\nFinished meshing with 4 illegal faces\nEnd",
    ],
)
def test_invalid_native_completion_never_becomes_zero(suffix: str) -> None:
    # Given: a success marker with an incomplete, fatal, concatenated or ambiguous ending.
    text = (
        "Exec : snappyHexMesh -parallel -overwrite\nFinished meshing without any errors"
        + suffix
    )
    # When / Then: this is not proof of zero illegal faces.
    assert package.illegal_faces(text) is None


@pytest.mark.parametrize("count", [0, 7])
def test_single_complete_native_meshing_log_is_parsed(count: int) -> None:
    # Given: one native run, its completion and the observed optional parallel trailer.
    marker = (
        "Finished meshing without any errors"
        if count == 0
        else f"Finished meshing with {count} illegal faces"
    )
    text = f"Exec : snappyHexMesh -parallel -overwrite\n{marker}\nFinished meshing in = 1.5 s.\nEnd\nFinalising parallel run\n"
    # When / Then: only the explicit single result is returned.
    assert package.illegal_faces(text) == count


def normalization_case(tmp_path: Path) -> tuple[Path, Path]:
    """Create synthetic normalization provenance; never run the normalizer or package main."""
    case = tmp_path / "artifacts/snappy-11"
    folder = case / "constant/polyMesh/sets"
    folder.mkdir(parents=True)
    for name in package.MeshDigests.model_fields:
        (folder.parent / name).write_bytes(name.encode())
    native = case / "log.checkMesh-extended"
    native.write_text(
        f"Exec : checkMesh -constant -allTopology -allGeometry\nCase : {case.as_posix()}\nChecking geometry...\nCell determinant check OK.\nMesh OK.\nEnd\n",
        encoding="utf8",
    )
    from normalize_zero_sets import RULES, empty_set

    rule = RULES[0]
    target = folder / rule.name
    target.write_text(empty_set(rule), encoding="utf8", newline="\n")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    receipt = evidence / "snappy-11-normalized-zero-sets.json"
    payload = {
        "candidate": case.name,
        "mesh": package.snapshot_mesh(case).model_dump(),
        "external_check_log": {"path": native.name, "sha256": package.digest(native)},
        "sets": [
            {
                "name": rule.name,
                "path": target.relative_to(case).as_posix(),
                "pass_marker": rule.marker,
                "sha256": package.digest(target),
                "synthesized": True,
                "count": 0,
            }
        ],
        "status": "DIAGNOSTICS_ONLY_NOT_MESH_ACCEPTANCE",
    }
    receipt.write_text(json.dumps(payload), encoding="utf8")
    return case, receipt


@pytest.mark.parametrize("drift", ["candidate", "mesh", "log", "set"])
def test_normalization_provenance_drift_is_refused(
    tmp_path: Path, drift: Literal["candidate", "mesh", "log", "set"]
) -> None:
    # Given: an altered candidate, sealed mesh/log, or synthesized zero set.
    case, receipt = normalization_case(tmp_path)
    payload = json.loads(receipt.read_text(encoding="utf8"))
    match drift:
        case "candidate":
            payload["candidate"] = "snappy-10"
        case "mesh":
            payload["mesh"]["points"] = "0" * 64
        case "log":
            payload["external_check_log"]["sha256"] = "0" * 64
        case "set":
            payload["sets"][0]["sha256"] = "0" * 64
        case unreachable:
            assert_never(unreachable)
    receipt.write_text(json.dumps(payload), encoding="utf8")
    # When / Then: normalization provenance cannot be silently dropped from packaging.
    with pytest.raises(package.PackageError):
        package.verify_normalization(
            case,
            receipt,
            package.snapshot_mesh(case),
            {
                "constant/polyMesh/sets/underdeterminedCells": package.digest(
                    case / "constant/polyMesh/sets/underdeterminedCells"
                )
            },
        )


def test_partial_io_failure_removes_only_its_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a write failing after the destination was exclusively created.
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"source")

    def fail_copy(incoming: BinaryIO, outgoing: BinaryIO) -> None:
        _ = outgoing.write(incoming.read(2))
        raise OSError(5, "simulated write failure")

    monkeypatch.setattr(checks.shutil, "copyfileobj", fail_copy)
    # When / Then: the partial copy is removed; the original survives.
    with pytest.raises(OSError):
        package.copy_exclusive(source, target, package.digest(source))
    assert not target.exists() and source.read_bytes() == b"source"


def test_posthash_failure_preserves_replacement_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: the created destination is replaced by a different file before posthash.
    source, target = tmp_path / "source", tmp_path / "target"
    source.write_bytes(b"source")
    expected = package.digest(source)

    def replace_during_hash(path: Path) -> str:
        if path == source:
            target.unlink()
            target.write_bytes(b"other-owner")
        return "0" * 64

    monkeypatch.setattr(checks, "digest", replace_during_hash)
    # When / Then: refusal must preserve the replacement identity.
    with pytest.raises(package.PackageError):
        package.copy_exclusive(source, target, expected)
    assert target.read_bytes() == b"other-owner"


@pytest.mark.parametrize(
    "insert", ["FOAM FATAL ERROR", "Finished meshing with 7 illegal faces"]
)
def test_bad_marker_inside_otherwise_complete_native_log_is_unknown(
    insert: str,
) -> None:
    # Given: a complete invocation containing a fatal or contradictory completion.
    text = f"Exec : snappyHexMesh -parallel -overwrite\nFinished meshing without any errors\n{insert}\nFinished meshing in = 1.5 s.\nEnd\n"
    # When / Then: all other completion evidence cannot hide the bad marker.
    assert package.illegal_faces(text) is None


def test_normalization_receipt_is_returned_as_hash_bound_reference(
    tmp_path: Path,
) -> None:
    # Given: valid synthetic normalization provenance.
    case, receipt = normalization_case(tmp_path)
    path = case / "constant/polyMesh/sets/underdeterminedCells"
    before = path.read_bytes()
    # When: validating provenance without changing any diagnostic bytes.
    result = package.verify_normalization(
        case,
        receipt,
        package.snapshot_mesh(case),
        {path.relative_to(case).as_posix(): package.digest(path)},
    )
    # Then: the receipt is available for the report/manifest and bytes remain untouched.
    assert result.sha256 == package.digest(receipt) and path.read_bytes() == before


@pytest.fixture
def bound_case(tmp_path: Path) -> tuple[Path, Path]:
    """Build a completed replay around an immutable historical zero serializer."""
    from normalize_zero_sets import COMMAND, canonical_wsl

    case, legacy = normalization_case(tmp_path)
    target = case / "constant/polyMesh/sets/underdeterminedCells"
    target.write_text(
        "// legacy serializer\nFoamFile {class cellSet; object underdeterminedCells;}\n0\n(\n)\n",
        encoding="utf8",
    )
    old = json.loads(legacy.read_text(encoding="utf8"))
    old["sets"][0]["sha256"] = package.digest(target)
    legacy.write_text(json.dumps(old), encoding="utf8")
    clone = case.parent / f"{case.name}-bound-check"
    (clone / "constant/polyMesh/sets").mkdir(parents=True)
    for name in package.MeshDigests.model_fields:
        (clone / "constant/polyMesh" / name).write_bytes(
            (case / "constant/polyMesh" / name).read_bytes()
        )
    (clone / target.relative_to(case)).write_bytes(target.read_bytes())
    replay = clone / "log.bound-check-extended"
    replay.write_text(
        f"Exec : {' '.join(COMMAND)}\nCase : {canonical_wsl(clone)}\nTime = constant\nChecking geometry...\nCell determinant check OK.\nMesh OK.\nEnd\n",
        encoding="utf8",
    )
    mesh, sets = (
        package.snapshot_mesh(case).model_dump(),
        {target.name: package.digest(target)},
    )
    sidecar = legacy.parent / f"{case.name}-bound-check.json"
    binding = {
        "schema_version": 1,
        "candidate": case.name,
        "source_case": canonical_wsl(case),
        "clone_case": canonical_wsl(clone),
        "command": list(COMMAND),
        "old_log_sha256": package.digest(case / "log.checkMesh-extended"),
        "new_log_sha256": package.digest(replay),
        "returncode": 0,
        "status": "BOUND_REPLAY_COMPLETE",
    }
    binding.update(
        {
            prefix + "_mesh_" + epoch: mesh
            for prefix in ("source", "clone")
            for epoch in ("before", "after")
        }
    )
    binding.update(
        {
            prefix + "_sets_" + epoch: sets
            for prefix in ("source", "clone")
            for epoch in ("before", "after")
        }
    )
    sidecar.write_text(json.dumps(binding), encoding="utf8")
    receipt = legacy.parent / f"{case.name}-normalized-zero-sets-bound.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "candidate": case.name,
                "mesh": mesh,
                "external_check_log": old["external_check_log"],
                "replay_check_log": {
                    "path": canonical_wsl(replay),
                    "sha256": package.digest(replay),
                },
                "bound_replay": {
                    "path": sidecar.name,
                    "sha256": package.digest(sidecar),
                },
                "sets": [],
                "proven_zero_checks": ["underdeterminedCells"],
                "status": "DIAGNOSTICS_ONLY_NOT_MESH_ACCEPTANCE",
            }
        ),
        encoding="utf8",
    )
    return case, receipt


@pytest.mark.parametrize("drift", [False, True])
def test_bound_replay_preserves_legacy_format_and_rejects_clone_drift(
    bound_case: tuple[Path, Path], drift: bool
) -> None:
    # Given: legacy bytes differ from today's serializer, with independently replayed proof.
    case, receipt = bound_case
    target = case / "constant/polyMesh/sets/underdeterminedCells"
    before = target.read_bytes()
    if drift:
        (case.parent / f"{case.name}-bound-check/constant/polyMesh/points").write_bytes(
            b"changed"
        )
    # When / Then: accept preserved legacy bytes only while the bound clone still matches.
    if drift:
        with pytest.raises(package.PackageError, match="BOUND_MESH_DRIFT"):
            checks.verify_bound_normalization(
                case,
                receipt.parent,
                package.snapshot_mesh(case),
                {target.relative_to(case).as_posix(): package.digest(target)},
            )
    else:
        ref, historical, files = checks.verify_bound_normalization(
            case,
            receipt.parent,
            package.snapshot_mesh(case),
            {target.relative_to(case).as_posix(): package.digest(target)},
        )
        assert (
            ref.sha256 == package.digest(receipt)
            and historical is not None
            and receipt in files
        )
    assert target.read_bytes() == before


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
