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
"""Independent manifold checks on closed and pinched examples."""

import numpy as np
import trimesh
from geometry import topology


def test_closed_box_when_manifold() -> None:
    # Given closed box; When checked; Then every vertex has one cyclic link.
    result = topology(trimesh.creation.box())
    assert result.closed and result.winding and result.vertex_link_failures == 0


def test_pinched_vertex_when_two_closed_shells_touch() -> None:
    # Given shells sharing one point; When checked; Then reject disconnected link.
    a = trimesh.creation.box()
    b = trimesh.creation.box()
    b.apply_translation([1, 1, 1])
    mesh = trimesh.util.concatenate((a, b))
    mesh.merge_vertices()
    assert topology(mesh).vertex_link_failures == 1
