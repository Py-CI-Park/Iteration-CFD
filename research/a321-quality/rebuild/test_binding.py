#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Binary STL custody regression tests."""

import hashlib
from pathlib import Path
import struct
import numpy as np
import pytest


def test_bound_triangle_change_rejected(tmp_path: Path) -> None:
    # Given a sealed binary triangle; When native coordinates differ; Then refuse.
    import binding

    stl = tmp_path / "single.stl"
    data = (
        b" " * 80
        + struct.pack("<I", 1)
        + struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)
    )
    stl.write_bytes(data)
    v = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 1.0]])
    with pytest.raises(binding.BindingRejected, match="TRIANGLES"):
        binding.bind(v, np.array([[0, 1, 2]]), stl, hashlib.sha256(data).hexdigest())
