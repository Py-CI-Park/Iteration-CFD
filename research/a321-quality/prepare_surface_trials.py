#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic>=2", "typer>=0.12"]
# ///
# How to run: install uv; uv run prepare_surface_trials.py --candidate 08
# Optional: --surface PATH explicitly selects a receipt-bound input STL.
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Prepare one controlled CPU surface trial without launching any executable."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final, Literal, assert_never

import typer
from pydantic import BaseModel, ConfigDict, Field

ROOT: Final = Path(__file__).resolve().parent
R3_SHA: Final = "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
BASELINE06_SHA: Final = (
    "a4bd8c95305eb5b71fd84c61400bac7c6c41e2e6d73be7cb19debdee8731c346"
)
SYSTEM_FILES: Final = (
    "blockMeshDict",
    "controlDict",
    "decomposeParDict",
    "fvSchemes",
    "fvSolution",
    "snappyHexMeshDict",
    "surfaceFeatureExtractDict",
)
SURFACE: Final = "constant/triSurface/aircraft.stl"
type Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


@dataclass(frozen=True, slots=True)
class TrialError(Exception):
    """A named custody failure leaves no runnable candidate."""

    reason: str

    def __str__(self) -> str:
        return self.reason


class Candidate(StrEnum):
    """The complete approved experimental matrix."""

    C08 = "08"
    C09 = "09"
    C10 = "10"
    C11 = "11"


class BaselineManifest(BaseModel):
    """Only complete, pre-run baseline snapshots are accepted."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    legacy_post_run_snapshot: Literal[False]
    sha256: dict[str, Sha256]


class GeometryReceipt(BaseModel):
    """Parse the parent-owned immutable geometry generation receipt."""

    model_config = ConfigDict(frozen=True, strict=True)
    source_sha256: Sha256
    stl_sha256: Sha256


class TrialManifest(BaseModel):
    """Bind source geometry, baseline identity and every execution input."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    candidate: str
    plan: str
    source_path: str
    source_sha256: Sha256
    baseline06_sha256: Sha256
    canonical_r3_sha256: Sha256
    geometry_receipt_sha256: Sha256 | None
    sha256: dict[str, Sha256]


def digest(path: Path) -> str:
    """Hash bytes without loading an entire STL into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def trial_plan(candidate: Candidate) -> tuple[bool, bool, str]:
    """Return derivative use, tighter generation weight and comparison intent."""
    match candidate:
        case Candidate.C08:
            return (
                False,
                True,
                "06 -> 08: R3 unchanged; minFaceWeight 0.02 -> 0.05 only",
            )
        case Candidate.C09:
            return (
                True,
                False,
                "06 -> 09: receipt-bound smooth R4 only; identical system dictionaries",
            )
        case Candidate.C10:
            return (
                True,
                True,
                "09 -> 10: same smooth R4; minFaceWeight 0.02 -> 0.05 only",
            )
        case Candidate.C11:
            return (
                True,
                True,
                "10 -> 11: same smooth R4 and minFaceWeight 0.05; nBufferCellsNoExtrude 1 -> 3 only",
            )
        case unreachable:
            assert_never(unreachable)


def canonical(root: Path) -> Path:
    return root.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"


def checked_baseline(root: Path) -> BaselineManifest:
    """Reject baseline edits, missing or additional dictionary inputs."""
    base = root / "artifacts/snappy-06"
    if digest(canonical(root)) != R3_SHA:
        raise TrialError("CANONICAL_R3_CHANGED")
    if digest(base / "input-manifest.json") != BASELINE06_SHA:
        raise TrialError("BASELINE06_MANIFEST_CHANGED")
    data = BaselineManifest.model_validate_json(
        (base / "input-manifest.json").read_bytes()
    )
    expected = {SURFACE, *(f"system/{name}" for name in SYSTEM_FILES)}
    if set(data.sha256) != expected or {
        p.name for p in (base / "system").iterdir()
    } != set(SYSTEM_FILES):
        raise TrialError("INCOMPLETE_OR_EXTRA_BASELINE_INPUTS")
    sidecar = "".join(f"{value}  {name}\n" for name, value in data.sha256.items())
    if (base / "input-manifest.sha256").read_text(encoding="utf8") != sidecar:
        raise TrialError("BASELINE06_SIDECAR_CHANGED")
    for name, value in data.sha256.items():
        path = base / name
        if path.is_symlink() or digest(path) != value:
            raise TrialError(f"BASELINE06_INPUT_CHANGED: {name}")
    if data.sha256[SURFACE] != R3_SHA:
        raise TrialError("BASELINE_NOT_R3")
    return data


def prepare(
    candidate: Candidate, surface: Path | None = None, *, root: Path = ROOT
) -> Path:
    """Create a fresh case; fail closed without overwriting historical artifacts."""
    root = root.resolve()
    baseline = checked_baseline(root)
    derivative, tighter, plan = trial_plan(candidate)
    base = root / "artifacts/snappy-06"
    default = (
        root / "artifacts/smooth-r4/A321_AIRFRAME_SHELL_R4.stl"
        if derivative
        else canonical(root)
    )
    source = (surface if surface is not None else default).resolve(strict=True)
    source_sha = digest(source)
    receipt_path = root / "evidence/smooth-r4.json"
    receipt_sha: str | None = None
    if derivative:
        receipt = GeometryReceipt.model_validate_json(receipt_path.read_bytes())
        receipt_sha = digest(receipt_path)
        if receipt.source_sha256 != R3_SHA or receipt.stl_sha256 != source_sha:
            raise TrialError("DERIVATIVE_RECEIPT_MISMATCH")
        if source_sha == R3_SHA:
            raise TrialError("DERIVATIVE_IS_UNCHANGED_R3")
    elif source_sha != R3_SHA:
        raise TrialError("R3_SOURCE_CHANGED")
    dictionary = (base / "system/snappyHexMeshDict").read_bytes()
    if dictionary.count(b"minFaceWeight 0.02;") != 1:
        raise TrialError("BASELINE_FACE_WEIGHT_DRIFT")
    if tighter:
        dictionary = dictionary.replace(
            b"minFaceWeight 0.02;", b"minFaceWeight 0.05;", 1
        )
    match candidate:
        case Candidate.C11:
            if dictionary.count(b"nBufferCellsNoExtrude 1;") != 1:
                raise TrialError("BASELINE_LAYER_BUFFER_DRIFT")
            dictionary = dictionary.replace(
                b"nBufferCellsNoExtrude 1;", b"nBufferCellsNoExtrude 3;", 1
            )
        case Candidate.C08 | Candidate.C09 | Candidate.C10:
            pass
        case unreachable:
            assert_never(unreachable)
    output = root / "artifacts" / f"snappy-{candidate.value}"
    output.mkdir(exist_ok=False)
    shutil.copytree(base / "system", output / "system")
    target = output / SURFACE
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    (output / "system/snappyHexMeshDict").write_bytes(dictionary)
    hashes = {name: digest(output / name) for name in baseline.sha256}
    if hashes[SURFACE] != source_sha:
        raise TrialError("SOURCE_CHANGED_DURING_COPY")
    for name in SYSTEM_FILES:
        key = f"system/{name}"
        expected = (
            hashlib.sha256(dictionary).hexdigest()
            if name == "snappyHexMeshDict"
            else baseline.sha256[key]
        )
        if hashes[key] != expected:
            raise TrialError("BASELINE_CHANGED_DURING_COPY")
    if derivative:
        shutil.copyfile(receipt_path, output / "geometry-receipt.json")
        if digest(output / "geometry-receipt.json") != receipt_sha:
            raise TrialError("RECEIPT_CHANGED_DURING_COPY")
        hashes["geometry-receipt.json"] = receipt_sha
    checked_baseline(root)
    data = TrialManifest(
        candidate=output.name,
        plan=plan,
        source_path=source.as_posix(),
        source_sha256=source_sha,
        baseline06_sha256=BASELINE06_SHA,
        canonical_r3_sha256=R3_SHA,
        geometry_receipt_sha256=receipt_sha,
        sha256=hashes,
    )
    with (output / "input-manifest.json").open(
        "x", encoding="utf8", newline="\n"
    ) as stream:
        stream.write(data.model_dump_json(indent=2) + "\n")
    with (output / "input-manifest.sha256").open(
        "x", encoding="utf8", newline="\n"
    ) as stream:
        for name, value in (
            *hashes.items(),
            ("input-manifest.json", digest(output / "input-manifest.json")),
        ):
            stream.write(f"{value}  {name}\n")
    return output


app: Final = typer.Typer(add_completion=False)


@app.command()
def main(
    candidate: Annotated[Candidate, typer.Option("--candidate")],
    surface: Annotated[Path | None, typer.Option("--surface")] = None,
) -> None:
    """Prepare exactly one trial; GPU/solver execution is never authorized."""
    try:
        output = prepare(candidate, surface)
    except (TrialError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(2) from exc
    typer.echo(str(output))


if __name__ == "__main__":
    app()
