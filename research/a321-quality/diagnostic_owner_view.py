#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer"]
# ///
# How to run: uv run diagnostic_owner_view.py; writes an isolated visualization case, never source fields.
"""Render conservative wall-layer diagnostics using the supported volume scalar path."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import typer
from custody import (
    BoundAudit,
    MeshDigests,
    digest,
    require_unchanged,
    snapshot_mesh,
    verify_binding,
)
from hotspot_inputs import (
    layers_on_wall,
    require_seal_identity,
    verify_diagnostic_files,
)
from poly_io import read_labels, read_patches

ROOT = Path(__file__).resolve().parent


def owner_minimum(
    owners: np.ndarray, counts: np.ndarray, cell_count: int
) -> tuple[np.ndarray, np.ndarray]:
    """Conservatively reduce wall-face layers without assigning data to non-wall cells."""
    if (
        len(owners) != len(counts)
        or np.any(owners < 0)
        or np.any(owners >= cell_count)
        or not np.isfinite(counts).all()
        or np.any((counts < 0) | (counts > 8) | (counts != np.floor(counts)))
    ):
        raise RuntimeError("INVALID_OWNER_DIAGNOSTIC")
    minimum = np.full(cell_count, 9, dtype=np.int64)
    maximum = np.full(cell_count, -1, dtype=np.int64)
    np.minimum.at(minimum, owners, counts.astype(np.int64))
    np.maximum.at(maximum, owners, counts.astype(np.int64))
    return np.where(maximum >= 0, minimum, -1), minimum[owners] != maximum[owners]


def main(candidate: str = "snappy-04") -> None:
    """Copy the frozen mesh and attach the minimum native face count per owner cell."""
    if candidate not in {
        "snappy-04",
        "snappy-06",
        "snappy-07",
        "snappy-08",
        "snappy-09",
        "snappy-10",
        "snappy-11",
    }:
        raise RuntimeError("INVALID_DIAGNOSTIC_CANDIDATE")
    case = ROOT / "artifacts" / candidate
    audit = BoundAudit.model_validate_json(
        (ROOT / "evidence" / f"{candidate}-audit-v5.json").read_text()
    )
    verify_binding(case, audit)
    before = snapshot_mesh(case)
    seal = json.loads(
        (ROOT / "evidence" / f"{candidate}-diagnostics-seal.json").read_text()
    )
    require_seal_identity(
        case, before, seal["candidate"], MeshDigests.model_validate(seal["mesh"])
    )
    verify_diagnostic_files(case, seal["inputs"])
    pm = case / "constant/polyMesh"
    patches = read_patches(pm / "boundary")
    wall = next(p for p in patches if p.name == "aircraft")
    owners = read_labels(pm / "owner")[wall.start : wall.start + wall.count]
    counts, _ = layers_on_wall(case, wall.start, wall.count)
    if np.any(owners >= audit.cells):
        raise RuntimeError("INVALID_WALL_OWNER")
    values, ambiguous = owner_minimum(owners, counts, audit.cells)
    require_unchanged(case, before)
    verify_diagnostic_files(case, seal["inputs"])
    target = ROOT / "artifacts" / f"{candidate}-owner-diagnostic"
    target.mkdir(exist_ok=False)
    (target / "constant/polyMesh").mkdir(parents=True)
    for p in pm.iterdir():
        if p.is_file():
            shutil.copyfile(p, target / "constant/polyMesh" / p.name)
    if snapshot_mesh(target) != before:
        raise RuntimeError("DIAGNOSTIC_COPY_CHANGED")
    (target / "system").mkdir()
    (target / "system/controlDict").write_text(
        "FoamFile {version 2.0; format ascii; class dictionary; object controlDict;}\n"
        "application meshDiagnosticOnly; startTime 0; endTime 0; deltaT 1; writeFormat ascii;\n",
        encoding="utf8",
        newline="\n",
    )
    (target / "0").mkdir()
    name = "diagnostic_owner_layer_min"
    with (target / "0" / name).open("x", encoding="utf8", newline="\n") as handle:
        handle.write(
            f"FoamFile {{version 2.0; format ascii; class volScalarField; object {name};}}\n"
        )
        handle.write(
            f"dimensions [0 0 0 0 0 0 0];\ninternalField nonuniform List<scalar>\n{audit.cells}\n(\n"
        )
        np.savetxt(handle, values, fmt="%d")
        handle.write(");\nboundaryField\n{\n")
        for p in patches:
            handle.write(f"{p.name} {{type calculated; value uniform 0;}}\n")
        handle.write("}\n")
    receipt = {
        "source_case": case.name,
        "view_case": target.name,
        "field": name,
        "cells": audit.cells,
        "source_wall_faces": wall.count,
        "wall_owner_cells": len(np.unique(owners)),
        "ambiguous_wall_owner_faces": int(ambiguous.sum()),
        "exact_face_value_matches": int(np.sum(values[owners] == counts)),
        "meaning": "minimum native layer count across source wall faces sharing each volume cell; conservative where values differ",
        "non_wall_value": -1,
        "physics_solution": False,
        "solver_run": False,
        "mesh": before.model_dump(),
        "field_sha256": digest(target / "0" / name),
    }
    receipt_name = (
        "owner-layer-diagnostic.json"
        if candidate == "snappy-04"
        else f"{candidate}-owner-layer-diagnostic.json"
    )
    (ROOT / "evidence" / receipt_name).write_text(
        json.dumps(receipt, indent=2), encoding="utf8"
    )
    print(json.dumps(receipt))


if __name__ == "__main__":
    typer.run(main)
