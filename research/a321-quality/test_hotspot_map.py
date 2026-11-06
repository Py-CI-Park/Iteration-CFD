#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "matplotlib", "typer", "pydantic>=2", "pytest"]
# ///
# How to run: uv run --with numpy --with matplotlib --with typer --with pydantic --with pytest pytest research/a321-quality/test_hotspot_map.py
"""Exercise addressing with reordered and reversed processor faces."""

from pathlib import Path

import numpy as np
import pytest
from custody import digest
from hotspot_inputs import layers_on_wall, signed_addressing, verify_diagnostic_files


def test_same_count_set_substitution_is_rejected(tmp_path: Path) -> None:
    """A valid different ID with identical set length must fail sealed identity."""
    folder = tmp_path / "constant/polyMesh/sets"
    folder.mkdir(parents=True)
    paths = [
        folder / n for n in ("concaveCells", "underdeterminedCells", "lowWeightFaces")
    ]
    for path in paths:
        path.write_text("2\n(\n1\n2\n)\n")
    expected = {p.relative_to(tmp_path).as_posix(): digest(p) for p in paths}
    verify_diagnostic_files(tmp_path, expected)
    paths[0].write_text("2\n(\n1\n3\n)\n")
    with pytest.raises(RuntimeError, match="DIAGNOSTIC_SEAL_MISMATCH"):
        verify_diagnostic_files(tmp_path, expected)


from map_hotspots import band_indices


def test_signed_face_addressing(tmp_path: Path) -> None:
    """Signed one-based addresses preserve identity under orientation reversal."""
    path = tmp_path / "faceProcAddressing"
    path.write_text("3\n(\n-3\n1\n2\n)\n")
    assert signed_addressing(path).tolist() == [2, 0, 1]
    path.write_text("1\n(\n0\n)\n")
    with pytest.raises(RuntimeError, match="INVALID_FACE_ADDRESS"):
        signed_addressing(path)


def test_processor_permutation_and_duplicates(tmp_path: Path) -> None:
    """Map two permuted partitions and reject duplicate reconstructed labels."""
    for idx, addresses, values in [(0, "-13\n11", "8\n0"), (1, "12\n14", "1\n4")]:
        proc = tmp_path / f"processor{idx}"
        mesh = proc / "constant/polyMesh"
        mesh.mkdir(parents=True)
        (proc / "0").mkdir()
        (mesh / "boundary").write_text("aircraft {type wall; nFaces 2; startFace 0;}")
        (mesh / "faceProcAddressing").write_text(f"2\n(\n{addresses}\n)\n")
        (proc / "0/nSurfaceLayers").write_text(
            f"aircraft {{value nonuniform List<scalar> 2 (\n{values}\n);}}"
        )
        (proc / "0/thickness").write_text("aircraft {value uniform 0.005;}")
    layers, thickness = layers_on_wall(tmp_path, 10, 4)
    assert layers.tolist() == [0, 1, 8, 4]
    assert thickness.tolist() == [0.005] * 4
    path = tmp_path / "processor1/constant/polyMesh/faceProcAddressing"
    path.write_text("2\n(\n11\n14\n)\n")
    with pytest.raises(RuntimeError, match="WALL_ADDRESSING_NOT_BIJECTIVE"):
        layers_on_wall(tmp_path, 10, 4)


def test_longitudinal_bins_are_half_open() -> None:
    """Boundaries go to the next bin; out-of-range points remain outside."""
    xyz = np.array([[-1.0, 0, 0], [0.0, 0, 0], [20.0, 0, 0], [45.0, 0, 0]])
    assert band_indices(xyz).tolist() == [-1, 0, 2, -1]
