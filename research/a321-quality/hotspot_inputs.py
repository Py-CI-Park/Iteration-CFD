#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2"]
# ///
# How to run: imported by map_hotspots.py and seal_diagnostics.py; no writes.
"""Read and validate the diagnostic inputs used by a reconstructed mesh map."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
from custody import digest
from layer_fields import wall_values
from numpy.typing import NDArray
from poly_io import count_list, read_labels, read_patches, require_end

SETS = ("underdeterminedCells", "concaveCells", "lowWeightFaces")


def verify_diagnostic_files(case: Path, expected: Mapping[str, str]) -> None:
    """Reject even a same-count label substitution relative to a sealed snapshot."""
    current = {p.relative_to(case).as_posix() for p in diagnostic_inputs(case)}
    if current != set(expected) or any(
        digest(case / p) != h for p, h in expected.items()
    ):
        raise RuntimeError("DIAGNOSTIC_SEAL_MISMATCH")


def signed_addressing(path: Path) -> NDArray[np.int64]:
    """Read signed, one-based reconstructed face addresses; zero is invalid."""
    with path.open(encoding="utf8") as handle:
        count = count_list(handle)
        data = np.fromiter(
            (int(next(handle)) for _ in range(count)), dtype=np.int64, count=count
        )
        require_end(handle)
    if np.any(data == 0):
        raise RuntimeError("INVALID_FACE_ADDRESS")
    return np.abs(data) - 1


def layers_on_wall(
    case: Path, start: int, count: int
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Join every processor wall value to a unique reconstructed wall-face ID."""
    layers = np.full(count, np.nan)
    thickness = np.full(count, np.nan)
    for proc in sorted(case.glob("processor[0-9]*")):
        pm = proc / "constant/polyMesh"
        patch = next(p for p in read_patches(pm / "boundary") if p.name == "aircraft")
        ids = (
            signed_addressing(pm / "faceProcAddressing")[
                patch.start : patch.start + patch.count
            ]
            - start
        )
        if (
            len(ids) != patch.count
            or np.any((ids < 0) | (ids >= count))
            or len(np.unique(ids)) != len(ids)
            or np.any(np.isfinite(layers[ids]))
        ):
            raise RuntimeError("WALL_ADDRESSING_NOT_BIJECTIVE")
        layers[ids] = wall_values(proc / "0/nSurfaceLayers", patch.count)
        thickness[ids] = wall_values(proc / "0/thickness", patch.count)
    if not np.isfinite(layers).all() or not np.isfinite(thickness).all():
        raise RuntimeError("INCOMPLETE_WALL_LAYER_MAP")
    if np.any((layers < 0) | (layers > 8) | (layers != np.floor(layers))) or np.any(
        thickness < 0
    ):
        raise RuntimeError("INVALID_WALL_LAYER_VALUES")
    return layers, thickness


def checked_ids(path: Path, limit: int) -> NDArray[np.int64]:
    """Return unique in-bounds labels; an absent set is not a measured zero."""
    ids = read_labels(path)
    if np.any(ids >= limit) or len(np.unique(ids)) != len(ids):
        raise RuntimeError(f"INVALID_SET: {path.name}")
    return ids


def diagnostic_inputs(case: Path) -> list[Path]:
    """Collect the exact check sets and decomposed files used in the coordinate join."""
    pm = case / "constant/polyMesh"
    paths = [pm / "sets" / name for name in SETS]
    for proc in sorted(case.glob("processor[0-9]*")):
        paths.extend(
            proc / relative
            for relative in (
                "constant/polyMesh/boundary",
                "constant/polyMesh/faceProcAddressing",
                "0/nSurfaceLayers",
                "0/thickness",
            )
        )
    return paths
