#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer"]
# ///
# How to run: install uv; AFTER parent audit/seal/map completion: uv run package_surface_trials.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Package byte-bound CPU research evidence; never execute mesh or flow programs."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from acceptance import CpuStatus, cpu_status
from custody import BoundAudit, MeshDigests, digest, snapshot_mesh, verify_binding
from hotspot_inputs import require_seal_identity, verify_diagnostic_files
from native_summary import layer_mean
from prepare_surface_trials import (
    BASELINE06_SHA,
    R3_SHA,
    SURFACE,
    SYSTEM_FILES,
    Candidate,
    GeometryReceipt,
    TrialManifest,
    checked_baseline,
    trial_plan,
)
from pydantic import Field, TypeAdapter
from quality_gate import CheckStatus, external_status
from surface_package_checks import (
    Artifact,
    Distance,
    FileRef,
    Frozen,
    PackageError as PackageError,
    confine,
    copy_exclusive,
    illegal_faces,
    require,
    verify_normalization as verify_normalization,
    verify_bound_normalization,
)

ROOT: Final = Path(__file__).resolve().parent
NAMES: Final = ("snappy-06", "snappy-08", "snappy-09", "snappy-10", "snappy-11")
RUNNER_SHAS: Final = (
    "4a72f2ea517f3fba96f693d8dce0b6ff253eaed039e43b15b45129b213fa6cfe",
    "b719887de39ec7747de0a4ed4d8d28cfae23ccd6a305413e26b80b1df6325903",
)


class Audit(BoundAudit):
    audited_geometry_sha256: str
    sampled_surface_distance: list[Distance]
    wall_faces: int = Field(gt=0)
    solver_run: Literal[False]
    gpu_compute: Literal[False]


class Seal(Frozen):
    candidate: str
    mesh: MeshDigests
    inputs: dict[str, str]
    external_check_log: FileRef
    post_generation_snapshot: Literal[True]


class MapReceipt(Frozen):
    candidate: str
    mesh: MeshDigests
    diagnostic_seal_sha256: str
    diagnostics_sha256: dict[str, str]
    audited_centers_sha256: str
    set_order: tuple[
        Literal["underdeterminedCells"],
        Literal["concaveCells"],
        Literal["lowWeightFaces"],
    ]
    counts: tuple[int, int, int]
    wall_faces: int = Field(gt=0)
    zero_layer_faces: int = Field(ge=0)
    full_8_layer_faces: int = Field(ge=0)
    covered_area_percent: float = Field(ge=0, le=100)


class Result(MapReceipt):
    audit: Audit
    mean_layers_native_rounded: float
    standard: CheckStatus
    extended: CheckStatus
    native_illegal: int | None
    named_CPU_gate: CpuStatus
    distances_R3_to_wall: list[Distance]
    normalization_receipt: FileRef | None
    historical_normalization_receipt: FileRef | None


class ComparisonReport(Frozen):
    trials: list[Result]
    artifact_path_base: Literal["research/"] = "research/"
    geometry_only: tuple[tuple[str, str], ...] = (
        ("snappy-06", "snappy-09"),
        ("snappy-08", "snappy-10"),
    )
    weight_only: tuple[tuple[str, str], ...] = (
        ("snappy-06", "snappy-08"),
        ("snappy-09", "snappy-10"),
    )
    mixed: tuple[tuple[str, str], ...] = (("snappy-06", "snappy-10"),)
    layer_termination_only: tuple[tuple[str, str], ...] = (("snappy-10", "snappy-11"),)
    R4_global_surface_distance_receipt: FileRef
    R4_global_distance_scope: str = "Separate sampled geometry receipt; lacks embedded source hashes; reference only, not R3-to-mesh-wall distance"
    engineering_status: Literal["FIX_FIRST_GPU_HOLD"] = "FIX_FIRST_GPU_HOLD"
    physical_acceptance: Literal[False] = False
    flow_solver_run: Literal[False] = False
    gpu_compute: Literal[False] = False
    GPU_solver_run: Literal[False] = False


def verify_trial_inputs(root: Path, name: str) -> list[Path]:
    """Bind current inputs to their complete manifest and original execution copies."""
    require(name in NAMES, "INVALID_CASE")
    baseline = checked_baseline(root)
    case = root / "artifacts" / name
    files = [case / "input-manifest.json", case / "input-manifest.sha256"]
    if name == "snappy-06":
        return [*files, *(case / key for key in baseline.sha256)]
    data = TrialManifest.model_validate_json(files[0].read_bytes())
    derivative, tighter, plan = trial_plan(Candidate(name[-2:]))
    require(
        data.candidate == name
        and data.plan == plan
        and data.baseline06_sha256 == BASELINE06_SHA
        and data.canonical_r3_sha256 == R3_SHA,
        "TRIAL_IDENTITY",
    )
    expected: set[str] = set(baseline.sha256)
    if derivative:
        expected.add("geometry-receipt.json")
    require(
        set(data.sha256) == expected
        and {p.name for p in (case / "system").iterdir()} == set(SYSTEM_FILES),
        "TRIAL_INPUT_SET",
    )
    lines = (
        "".join(f"{sha}  {key}\n" for key, sha in data.sha256.items())
        + f"{digest(files[0])}  input-manifest.json\n"
    )
    require(files[1].read_text(encoding="utf8") == lines, "MANIFEST_PIN")
    for key, sha in data.sha256.items():
        path = case / key
        require(
            path.resolve().is_relative_to(case.resolve())
            and not path.is_symlink()
            and digest(path) == sha,
            "CURRENT_INPUT_DRIFT",
        )
    require(data.sha256[SURFACE] == data.source_sha256, "SURFACE_SOURCE_HASH")
    if derivative:
        receipt_path = root / "evidence/smooth-r4.json"
        receipt = GeometryReceipt.model_validate_json(receipt_path.read_bytes())
        require(
            data.geometry_receipt_sha256
            == digest(receipt_path)
            == digest(case / "geometry-receipt.json"),
            "GEOMETRY_RECEIPT_DRIFT",
        )
        require(
            receipt.source_sha256 == R3_SHA
            and receipt.stl_sha256 == data.source_sha256 != R3_SHA,
            "DERIVATIVE_HASH",
        )
        require(
            digest(root / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl")
            == receipt.stl_sha256,
            "CANONICAL_R4_DRIFT",
        )
    else:
        require(
            data.source_sha256 == R3_SHA and data.geometry_receipt_sha256 is None,
            "R3_INPUT_CHANGED",
        )
    for item in SYSTEM_FILES:
        content = (root / "artifacts/snappy-06/system" / item).read_bytes()
        if tighter and item == "snappyHexMeshDict":
            require(content.count(b"minFaceWeight 0.02;") == 1, "BASELINE_WEIGHT")
            content = content.replace(b"minFaceWeight 0.02;", b"minFaceWeight 0.05;", 1)
        if name == "snappy-11" and item == "snappyHexMeshDict":
            require(
                content.count(b"nBufferCellsNoExtrude 1;") == 1, "BASELINE_LAYER_BUFFER"
            )
            content = content.replace(
                b"nBufferCellsNoExtrude 1;", b"nBufferCellsNoExtrude 3;", 1
            )
        require(
            (case / "system" / item).read_bytes() == content, "UNDECLARED_CONFIG_CHANGE"
        )
    for filename in ("input-manifest.json", "input-manifest.sha256"):
        original = case / filename
        captured = case / ".execution.lock" / filename
        require(captured.read_bytes() == original.read_bytes(), "EXECUTION_COPY_DRIFT")
        files.append(captured)
    runner = case / ".execution.lock/runner.sh"
    expected_runner = RUNNER_SHAS[1] if name == "snappy-11" else RUNNER_SHAS[0]
    require(digest(runner) == expected_runner, "UNAPPROVED_FROZEN_RUNNER")
    files.append(runner)
    return [*files, *(case / key for key in data.sha256)]


def load_case(root: Path, name: str) -> tuple[Result, list[Path]]:
    """Verify independent audit, sealed diagnostics and their exact mapped mesh."""
    require(name in NAMES, "INVALID_CASE")
    case, evidence = root / "artifacts" / name, root / "evidence"
    files = verify_trial_inputs(root, name)
    ap, sp, mp = (
        evidence / f"{name}-{suffix}.json"
        for suffix in ("audit-v5", "diagnostics-seal", "hotspots")
    )
    audit, seal, mapping = (
        Audit.model_validate_json(ap.read_bytes()),
        Seal.model_validate_json(sp.read_bytes()),
        MapReceipt.model_validate_json(mp.read_bytes()),
    )
    verify_binding(case, audit)
    before = snapshot_mesh(case)
    require_seal_identity(case, before, seal.candidate, seal.mesh)
    verify_diagnostic_files(case, seal.inputs)
    normalization, historical = None, None
    if name != "snappy-06":
        normalization, historical, normalized_files = verify_bound_normalization(
            case, evidence, before, seal.inputs
        )
        files.extend(normalized_files)
    centers = case / "audited-geometry-v5.npz"
    require(
        mapping.candidate == name
        and mapping.mesh == before
        and mapping.diagnostic_seal_sha256 == digest(sp),
        "STALE_MAP",
    )
    require(
        mapping.diagnostics_sha256 == seal.inputs
        and mapping.audited_centers_sha256
        == audit.audited_geometry_sha256
        == digest(centers),
        "STALE_DIAGNOSTICS",
    )
    require(
        mapping.wall_faces == audit.wall_faces
        and mapping.zero_layer_faces + mapping.full_8_layer_faces <= mapping.wall_faces
        and min(mapping.counts) >= 0,
        "INVALID_MAP_COUNTS",
    )
    require(
        seal.external_check_log.path == "log.checkMesh-extended"
        and digest(case / seal.external_check_log.path)
        == seal.external_check_log.sha256,
        "STALE_EXTERNAL_LOG",
    )
    logs = sorted(case.glob("log.*"))
    native = (case / "log.snappy").read_text(encoding="utf8")
    illegal = illegal_faces(native)
    require(illegal is not None, "INCOMPLETE_OR_AMBIGUOUS_NATIVE_MESH_LOG")
    standard, extended = (
        external_status((case / f"log.checkMesh-{kind}").read_text(encoding="utf8"))
        for kind in ("standard", "extended")
    )
    distances = [
        d for d in audit.sampled_surface_distance if d.direction == "R3_to_calculation"
    ]
    require(len(distances) == 1, "MISSING_R3_TO_WALL_DISTANCE")
    result = Result(
        candidate=mapping.candidate,
        mesh=mapping.mesh,
        diagnostic_seal_sha256=mapping.diagnostic_seal_sha256,
        diagnostics_sha256=mapping.diagnostics_sha256,
        audited_centers_sha256=mapping.audited_centers_sha256,
        set_order=mapping.set_order,
        counts=mapping.counts,
        wall_faces=mapping.wall_faces,
        zero_layer_faces=mapping.zero_layer_faces,
        full_8_layer_faces=mapping.full_8_layer_faces,
        covered_area_percent=mapping.covered_area_percent,
        audit=audit,
        mean_layers_native_rounded=layer_mean(native),
        standard=standard,
        extended=extended,
        native_illegal=illegal,
        named_CPU_gate=cpu_status(audit, standard, illegal),
        distances_R3_to_wall=distances,
        normalization_receipt=normalization,
        historical_normalization_receipt=historical,
    )
    files.extend(
        [
            ap,
            sp,
            mp,
            centers,
            *logs,
            *(case / key for key in seal.inputs),
            *(case / "constant/polyMesh" / key for key in MeshDigests.model_fields),
            root / "artifacts" / f"{name}-hotspot-map/coordinates.csv",
            evidence / f"{name}-hotspots.png",
        ]
    )
    require(snapshot_mesh(case) == before, "MESH_CHANGED_DURING_PACKAGE")
    return result, files


def main() -> None:
    """Run only after parent completes all three independent audit/map/seal sequences."""
    evidence = ROOT / "evidence"
    confine(evidence, ROOT)
    outputs = [
        evidence / "surface-comparison.json",
        evidence / "surface-artifact-manifest.json",
    ]
    require(
        not any(
            p.exists()
            for p in [*outputs, *(evidence / "surface-inputs" / n for n in NAMES[1:])]
        ),
        "OUTPUT_EXISTS",
    )
    results: list[Result] = []
    paths: list[Path] = []
    for name in NAMES:
        result, files = load_case(ROOT, name)
        results.append(result)
        paths.extend(files)
    geometry = evidence / "smooth-r4.json"
    metrics = evidence / "smooth-r4-surface-metrics.json"
    paths.extend(
        [
            geometry,
            metrics,
            ROOT / "run_surface_trial.sh",
            ROOT / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl",
            ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl",
        ]
    )
    artifacts = [
        Artifact(
            path=p.relative_to(ROOT.parent).as_posix(),
            bytes=p.stat().st_size,
            sha256=digest(p),
        )
        for p in dict.fromkeys(paths)
    ]
    pinned = {ROOT.parent / item.path: item.sha256 for item in artifacts}
    copies: list[tuple[Path, Path]] = []
    for name in NAMES[1:]:
        case, dest = ROOT / "artifacts" / name, evidence / "surface-inputs" / name
        copies.extend((case / "system" / f, dest / "system" / f) for f in SYSTEM_FILES)
        copies.extend(
            (case / f, dest / f)
            for f in (
                "input-manifest.json",
                "input-manifest.sha256",
                ".execution.lock/runner.sh",
                ".execution.lock/input-manifest.json",
                ".execution.lock/input-manifest.sha256",
            )
        )
        copies.append(
            (
                evidence / f"{name}-normalized-zero-sets-bound.json",
                dest / "normalized-zero-sets-bound.json",
            )
        )
        legacy = evidence / f"{name}-normalized-zero-sets.json"
        if legacy.exists():
            copies.append((legacy, dest / "normalized-zero-sets.json"))
        if name != "snappy-08":
            copies.append(
                (case / "geometry-receipt.json", dest / "geometry-receipt.json")
            )
        copies.extend(
            (log, evidence / f"{name}-surface-{log.name[4:]}.log")
            for log in sorted(case.glob("log.*"))
        )
    require(not any(dst.exists() for _, dst in copies), "OUTPUT_EXISTS")
    for src, dst in copies:
        confine(dst, ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        confine(dst, ROOT)
        copy_exclusive(src, dst, pinned[src])
        artifacts.append(
            Artifact(
                path=dst.relative_to(ROOT.parent).as_posix(),
                bytes=dst.stat().st_size,
                sha256=digest(dst),
            )
        )
    for previous in results:
        current, _ = load_case(ROOT, previous.candidate)
        require(current == previous, "RESULT_CHANGED_DURING_PACKAGE")
    require(
        all(digest(path) == sha for path, sha in pinned.items()),
        "SOURCE_CHANGED_DURING_PACKAGE",
    )
    report = ComparisonReport(
        trials=results,
        R4_global_surface_distance_receipt=FileRef(
            path=metrics.relative_to(ROOT.parent).as_posix(), sha256=pinned[metrics]
        ),
    )
    for output in outputs:
        confine(output, ROOT)
    with outputs[0].open("x", encoding="utf8", newline="\n") as stream:
        _ = stream.write(report.model_dump_json(indent=2) + "\n")
    artifacts.append(
        Artifact(
            path=outputs[0].relative_to(ROOT.parent).as_posix(),
            bytes=outputs[0].stat().st_size,
            sha256=digest(outputs[0]),
        )
    )
    with outputs[1].open("x", encoding="utf8", newline="\n") as stream:
        _ = stream.write(
            TypeAdapter(list[Artifact]).dump_json(artifacts, indent=2).decode() + "\n"
        )


if __name__ == "__main__":
    main()
