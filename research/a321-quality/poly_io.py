#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: imported by audit_poly.py; counted ASCII polyMesh only.
"""Read general polygon ASCII arrays without truncating split-hex faces to four points."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import numpy as np
from numpy.typing import NDArray


def count_list(handle: TextIO) -> int:
    """Find the counted-list boundary outside the OpenFOAM header."""
    for line in handle:
        if line.strip().isdigit():
            count = int(line)
            if next(handle).strip() != "(":
                raise RuntimeError("MISSING_LIST_START")
            return count
    raise RuntimeError("MISSING_LIST_COUNT")


def read_points(path: Path) -> NDArray[np.float64]:
    """Read all coordinates in their serialized double precision."""
    with path.open(encoding="utf8") as handle:
        output = np.empty((count_list(handle), 3))
        for i in range(len(output)):
            values = np.fromstring(next(handle).strip().strip("()"), sep=" ")
            if len(values) != 3 or not np.all(np.isfinite(values)):
                raise RuntimeError("BAD_POINT_COORDINATES")
            output[i] = values
        require_end(handle)
    return output


def read_labels(path: Path) -> NDArray[np.int64]:
    """Read a signed label list without materializing Python integer objects."""
    with path.open(encoding="utf8") as handle:
        output = np.empty(count_list(handle), dtype=np.int64)
        for i in range(len(output)):
            output[i] = int(next(handle))
            if output[i] < 0:
                raise RuntimeError("NEGATIVE_CELL_LABEL")
        require_end(handle)
    return output


def read_faces(path: Path) -> NDArray[np.int64]:
    """Allow up to sixteen vertices per polygon and reject malformed arity."""
    with path.open(encoding="utf8") as handle:
        output = np.full((count_list(handle), 16), -1, dtype=np.int64)
        width = 0
        for i in range(len(output)):
            line = next(handle).strip()
            n = int(line[: line.index("(")])
            values = np.fromstring(
                line[line.index("(") + 1 : line.index(")")], dtype=np.int64, sep=" "
            )
            if (
                len(values) != n
                or n < 3
                or n > 16
                or np.any(values < 0)
                or len(np.unique(values)) != n
            ):
                raise RuntimeError("BAD_FACE_ARITY")
            output[i, :n] = values
            width = max(width, n)
        require_end(handle)
    return output[:, :width].copy()


def require_end(handle: TextIO) -> None:
    """Reject truncated lists before returning parsed data."""
    for line in handle:
        if line.strip():
            if line.strip() not in (")", ");"):
                raise RuntimeError("MISSING_LIST_END")
            return
    raise RuntimeError("MISSING_LIST_END")


@dataclass(frozen=True, slots=True)
class Patch:
    """One complete serialized patch interval."""

    name: str
    kind: str
    count: int
    start: int


def read_patches(path: Path) -> list[Patch]:
    """Parse public boundary dictionary fields including optional intervening metadata."""
    matches = re.findall(
        r"(\w+)\s*\{\s*type\s+(\w+);[^{}]*?nFaces\s+(\d+);\s*startFace\s+(\d+);",
        path.read_text(),
        flags=re.DOTALL,
    )
    return [
        Patch(name, kind, int(count), int(start))
        for name, kind, count, start in matches
    ]
