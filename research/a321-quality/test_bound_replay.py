#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "matplotlib", "pydantic>=2", "typer", "pytest"]
# ///
# How to run: uv run --with pytest --with numpy --with matplotlib --with pydantic
#     --with typer -m pytest test_bound_replay.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI/native diagnostic data. No GPL-licensed source consulted.
"""Reject wrong execution identities and forged post-replay zero additions."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from normalize_zero_sets import (
    NormalizationError,
    NormalizationReceipt,
    bound_body,
    normalize,
    snapshot_mesh,
)
from zero_set_test_support import PASS_MARKERS, bind_fixture, make_case


@pytest.mark.parametrize(
    "mutation",
    (
        "none",
        "extra-set",
        "changed-zero",
        "changed-original",
        "changed-replay",
        "changed-receipt",
        "deleted-zero",
        "forged-zero",
    ),
)
def test_post_addition_binding_allows_only_authenticated_new_zero(
    tmp_path: Path, mutation: str
) -> None:
    # Given a source with two native failing sets, a passed missing weight set,
    # and an immutable historical normalization receipt.
    case = make_case(
        tmp_path, "Face interpolation weight check OK.\nFailed 2 mesh checks.\nEnd\n"
    )
    folder = case / "constant/polyMesh/sets"
    for name in ("underdeterminedCells", "concaveCells"):
        (folder / name).write_text("1\n(\n4\n)\n", encoding="utf8")
    bind_fixture(case)
    evidence = tmp_path / "evidence"
    historical = evidence / "snappy-08-normalized-zero-sets.json"
    historical.write_bytes(b"historical bytes preserved")
    result = normalize(case.name, tmp_path)
    if mutation == "extra-set":
        (folder / "unlistedFaces").write_text("0\n(\n)\n", encoding="utf8")
    if mutation == "changed-zero":
        (folder / "lowWeightFaces").write_text("1\n(\n7\n)\n", encoding="utf8")
    if mutation == "changed-original":
        (folder / "concaveCells").write_text("1\n(\n7\n)\n", encoding="utf8")
    if mutation == "changed-replay":
        replay = case.parent / "snappy-08-bound-check/log.bound-check-extended"
        replay.write_bytes(replay.read_bytes() + b"\n")
    if mutation == "changed-receipt":
        receipt = NormalizationReceipt.model_validate_json(result.read_bytes())
        result.write_text(
            receipt.model_copy(update={"candidate": "snappy-09"}).model_dump_json(),
            encoding="utf8",
        )
    if mutation == "deleted-zero":
        (folder / "lowWeightFaces").unlink()
    if mutation == "forged-zero":
        value = folder / "lowWeightFaces"
        payload = value.read_bytes().replace(b"\n0\n(\n)\n", b"\n1\n(\n7\n)\n")
        payload += b"// }\n0\n(\n)\n"
        value.write_bytes(payload)
        receipt = NormalizationReceipt.model_validate_json(result.read_bytes())
        item = receipt.sets[0].model_copy(
            update={"sha256": hashlib.sha256(payload).hexdigest()}
        )
        result.write_text(
            receipt.model_copy(update={"sets": (item,)}).model_dump_json(),
            encoding="utf8",
        )
    raw = (case / "log.checkMesh-extended").read_bytes()
    # When independently validating after the source acquired its synthetic zero.
    if mutation == "none":
        body, _, _ = bound_body(case, evidence, raw, snapshot_mesh(case))
        assert "Face interpolation weight check OK." in body
    else:
        with pytest.raises(NormalizationError):
            bound_body(case, evidence, raw, snapshot_mesh(case))
    # Then historical evidence is unchanged in every outcome.
    assert historical.read_bytes() == b"historical bytes preserved"


@pytest.mark.parametrize(
    "variant", ("wrong-case", "missing-constant", "time-selector", "wrong-time")
)
def test_foreign_case_or_nonconstant_check_cannot_prove_zero(
    tmp_path: Path, variant: str
) -> None:
    # Given a completed pass log for the wrong case or mesh time selection.
    case = make_case(
        tmp_path, "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n"
    )
    path = case / "log.checkMesh-extended"
    text = path.read_text(encoding="utf8")
    resolved = case.resolve()
    native = resolved.as_posix()
    if resolved.drive:
        native = "/mnt/" + resolved.drive[0].lower() + native[2:]
    case_header = native + "-foreign" if variant == "wrong-case" else native
    text = text.replace("Case : " + native, "Case : " + case_header)
    if variant == "missing-constant":
        text = text.replace(" -constant", "")
    if variant == "time-selector":
        text = text.replace("-constant", "-constant -time 1")
    if variant == "wrong-time":
        text = text.replace("Time = constant", "Time = 1")
    path.write_text(text, encoding="utf8")
    # When the log is offered as proof of a missing diagnostic zero.
    with pytest.raises(NormalizationError):
        normalize(case.name, tmp_path)
    # Then no zero set was manufactured.
    assert list((case / "constant/polyMesh/sets").iterdir()) == []


def test_posthoc_log_without_bound_execution_cannot_prove_zero(tmp_path: Path) -> None:
    # Given a matching completed pass log but no execution-binding sidecar.
    case = make_case(
        tmp_path, "\n".join(marker for _, marker in PASS_MARKERS) + "\nMesh OK.\nEnd\n"
    )
    (tmp_path / "evidence/snappy-08-bound-check.json").unlink()
    # When normalization requires evidence beyond posthoc hashing.
    with pytest.raises(NormalizationError):
        normalize(case.name, tmp_path)
    # Then unknown absence stays unknown.
    assert list((case / "constant/polyMesh/sets").iterdir()) == []
