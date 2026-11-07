#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer", "pytest"]
# ///
# How to run: uv run --with numpy --with pydantic --with typer --with pytest pytest research/a321-quality/test_seal_identity.py
"""Never combine old layer diagnostics with another mesh or candidate name."""

from pathlib import Path

import pytest
from custody import MeshDigests
from hotspot_inputs import require_seal_identity


def test_matching_seal_is_accepted() -> None:
    """Given a matching five-file seal, retain its exact candidate identity."""
    mesh = MeshDigests(points="a", faces="b", owner="c", neighbour="d", boundary="e")
    require_seal_identity(Path("snappy-06"), mesh, "snappy-06", mesh)


@pytest.mark.parametrize(
    "wrong_name,wrong_faces", [("snappy-04", "b"), ("snappy-06", "changed")]
)
def test_stale_name_or_mesh_is_rejected(wrong_name: str, wrong_faces: str) -> None:
    """A valid diagnostic file snapshot must not override reconstructed mesh identity."""
    mesh = MeshDigests(points="a", faces="b", owner="c", neighbour="d", boundary="e")
    sealed = mesh.model_copy(update={"faces": wrong_faces})
    with pytest.raises(RuntimeError, match="DIAGNOSTIC_SEAL_WRONG_MESH"):
        require_seal_identity(Path("snappy-06"), mesh, wrong_name, sealed)
