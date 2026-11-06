#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pytest"]
# ///
# How to run: uv run --with numpy --with pytest -m pytest test_poly_io.py.
"""Keep split-hex faces intact and reject malformed serialized connectivity."""

from __future__ import annotations

from pathlib import Path

import pytest
from poly_io import read_faces, read_labels, read_points


def test_variable_face_arity_is_preserved(tmp_path: Path) -> None:
    """Given a five-sided face, the reader must retain all five vertex ids."""
    path = tmp_path / "faces"
    path.write_text("FoamFile {version 2.0;}\n2\n(\n3(0 1 2)\n5(0 2 3 4 5)\n)\n")
    result = read_faces(path)
    assert result.tolist() == [[0, 1, 2, -1, -1], [0, 2, 3, 4, 5]]


def test_bad_face_arity_is_rejected(tmp_path: Path) -> None:
    """Given a declared five-sided face with only four ids, reject instead of truncating."""
    path = tmp_path / "faces"
    path.write_text("1\n(\n5(0 1 2 3)\n)\n")
    with pytest.raises(RuntimeError, match="BAD_FACE_ARITY"):
        read_faces(path)


@pytest.mark.parametrize("row", ["(7)", "(0 nan 1)", "(0 1 inf)"])
def test_bad_point_coordinates_are_rejected(tmp_path: Path, row: str) -> None:
    """Given malformed coordinates, do not broadcast or accept nonfinite values."""
    path = tmp_path / "points"
    path.write_text(f"1\n(\n{row}\n)\n")
    with pytest.raises(RuntimeError, match="BAD_POINT"):
        read_points(path)


def test_negative_serialized_ids_are_rejected(tmp_path: Path) -> None:
    """Given -1 in serialized data, never confuse it with internal padding."""
    path = tmp_path / "faces"
    path.write_text("1\n(\n4(0 1 2 -1)\n)\n")
    with pytest.raises(RuntimeError, match="BAD_FACE"):
        read_faces(path)
    path = tmp_path / "owner"
    path.write_text("1\n(\n-1\n)\n")
    with pytest.raises(RuntimeError, match="NEGATIVE"):
        read_labels(path)


def test_missing_list_end_is_rejected(tmp_path: Path) -> None:
    """Given a complete row in a truncated file, still require the closing delimiter."""
    path = tmp_path / "points"
    path.write_text("1\n(\n(0 1 2)\n")
    with pytest.raises(RuntimeError, match="MISSING_LIST_END"):
        read_points(path)
