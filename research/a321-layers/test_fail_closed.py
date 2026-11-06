#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "trimesh", "meshpy", "pytest"]
# ///
# How to run: uv run --with numpy --with scipy --with trimesh --with meshpy --with pytest -m pytest test_fail_closed.py
"""Rejected generators must neither overwrite a frozen mesh nor signal process success."""

import json
import sys
from pathlib import Path

import exterior_tets
import numpy as np
import pytest


def test_existing_mesh_is_not_overwritten(tmp_path: Path, monkeypatch):
    root = tmp_path / "artifacts/constrained-exact-02"
    root.mkdir(parents=True)
    mesh = root / "hybrid.npz"
    mesh.write_bytes(b"frozen")
    monkeypatch.setattr(exterior_tets, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["exterior_tets.py"])
    with pytest.raises(RuntimeError, match="ALREADY_EXISTS"):
        exterior_tets.main()
    assert mesh.read_bytes() == b"frozen"


def test_mesher_rejection_writes_receipt_and_exits_nonzero(tmp_path: Path, monkeypatch):
    root = tmp_path / "artifacts/constrained-exact-02"
    root.mkdir(parents=True)
    (tmp_path / "evidence").mkdir()
    v = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0.1], [1, 0, 0.1], [0, 1, 0.1]], float
    )
    np.savez(
        root / "layers.npz",
        vertices=v,
        prisms=np.array([[0, 1, 2, 3, 4, 5]]),
        wall_faces=np.array([[0, 1, 2]]),
        heights=np.array([0.0, 0.1]),
        scale=np.ones(3),
    )
    monkeypatch.setattr(exterior_tets, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["exterior_tets.py"])

    def reject(*args, **kwargs):
        raise RuntimeError("CONTROLLED_MESHER_REJECTION")

    monkeypatch.setattr(exterior_tets.tet, "build", reject)
    with pytest.raises(SystemExit) as error:
        exterior_tets.main()
    assert error.value.code == 2
    assert (
        json.loads((tmp_path / "evidence/exterior-tets.json").read_text())["status"]
        == "EXTERIOR_BUILD_FAILED"
    )
    assert not (root / "hybrid.npz").exists()
