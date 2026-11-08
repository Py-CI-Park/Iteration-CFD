#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic>=2", "pytest"]
# ///
# How to run: install uv, then uv run smooth_loft.py (CPU geometry only).
"""Locally round R3 wing section seams; protected outlines remain piecewise linear."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal

import manifold3d as mf
import numpy as np
import trimesh
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict

ROOT: Final = Path(__file__).resolve().parent
SOURCE: Final = ROOT.parent / "a321-integration/evidence/reconstruction-r3.json"
REFERENCE: Final = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
R3_SHA: Final = "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
LEDGER_SHA: Final = "405aec921c5f492a6841c89102cb0215141a920906baed94298c5c2d3fef15cb"
CAP_M: Final = 0.01
FloatArray = NDArray[np.float64]
sys.path.insert(0, str(ROOT.parent / "a321-shell"))
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from profiles import loft
from surface_metrics import measure
from audit_shell import vertex_links


@dataclass(frozen=True, slots=True)
class GeometryRejected(RuntimeError):
    """A bounded geometry or custody contract failed."""

    reason: str

    def __str__(self) -> str:
        return self.reason


class Part(BaseModel):
    """Typed immutable station ledger boundary."""

    model_config = ConfigDict(frozen=True)
    name: str
    axis: Literal[0, 1, 2]
    stations_m: list[float]
    rings_2d_m: list[list[list[float]]]


class Source(BaseModel):
    """Only the required portion of the immutable source ledger."""

    model_config = ConfigDict(frozen=True)
    parts: list[Part]


@dataclass(frozen=True, slots=True)
class Transition:
    center_m: float
    half_width_m: float
    max_displacement_m: float
    slope_jump_before: float
    slope_jump_after: float


@dataclass(frozen=True, slots=True)
class SmoothWing:
    stations: FloatArray
    rings: FloatArray
    transitions: tuple[Transition, ...]


def linear_rings(y: FloatArray, rings: FloatArray, q: FloatArray) -> FloatArray:
    """Evaluate the original PL loft's section parameterization."""
    i = np.clip(np.searchsorted(y, q, side="right") - 1, 0, len(y) - 2)
    t = ((q - y[i]) / (y[i + 1] - y[i]))[:, None, None]
    return rings[i] * (1 - t) + rings[i + 1] * t


def transition(
    y: FloatArray, rings: FloatArray, i: int, h: float, q: FloatArray
) -> FloatArray:
    """Cubic Hermite between PL segments, with exact protected LE/TE points."""
    if not 0 < i < len(y) - 1 or not 0 < h < min(y[i] - y[i - 1], y[i + 1] - y[i]):
        raise GeometryRejected("TRANSITION_OUTSIDE_NEIGHBOR_SEGMENTS")
    a, b = y[i] - h, y[i] + h
    if np.any((q < a - 1e-12) | (q > b + 1e-12)):
        raise GeometryRejected("QUERY_OUTSIDE_TRANSITION")
    left, right = linear_rings(y, rings, np.array([a, b]))
    dl, dr = (
        (rings[i] - rings[i - 1]) / (y[i] - y[i - 1]),
        (rings[i + 1] - rings[i]) / (y[i + 1] - y[i]),
    )
    t = ((q - a) / (b - a))[:, None, None]
    result = (2 * t**3 - 3 * t**2 + 1) * left + (t**3 - 2 * t**2 + t) * (b - a) * dl
    result += (-2 * t**3 + 3 * t**2) * right + (t**3 - t**2) * (b - a) * dr
    original = linear_rings(y, rings, q)
    result[:, [0, rings.shape[1] // 2]] = original[:, [0, rings.shape[1] // 2]]
    if np.linalg.norm(result - original, axis=2).max() > CAP_M + 1e-12:
        raise GeometryRejected("DISPLACEMENT_CAP_EXCEEDED")
    return result


def smooth_wing(y: FloatArray, rings: FloatArray) -> SmoothWing:
    """Round source-repair seam neighbors without clipping excessive corrections."""
    if (
        not np.isfinite(rings).all()
        or not np.isfinite(y).all()
        or np.any(np.diff(y) <= 0)
    ):
        raise GeometryRejected("INVALID_STATION_LEDGER")
    if rings.shape != (len(y), 128, 2):
        raise GeometryRejected("EXPECTED_R3_128_POINT_COSINE_RINGS")
    chosen = np.flatnonzero(
        ((y > 2.1) & (y < 2.7)) | ((y > 5.85) & (y < 6.25)) | ((y > 6.45) & (y < 6.95))
    )
    interior = np.ones(rings.shape[1], dtype=bool)
    interior[[0, rings.shape[1] // 2]] = False
    windows: list[tuple[int, float]] = []
    for i in chosen:
        dl = (rings[i] - rings[i - 1]) / (y[i] - y[i - 1])
        dr = (rings[i + 1] - rings[i]) / (y[i + 1] - y[i])
        jump = float(np.linalg.norm(dr[interior] - dl[interior], axis=1).max())
        if jump < 1e-6:
            continue
        # Hermite departure from the original V is bounded by h*|dr-dl|/4.
        h = min(0.4 * min(y[i] - y[i - 1], y[i + 1] - y[i]), 0.99 * 4 * CAP_M / jump)
        edge = np.linalg.norm(rings[i] - np.roll(rings[i], 1, axis=0), axis=1)
        local_cap = 0.1 * np.minimum(edge, np.roll(edge, -1))[interior]
        local_jump = np.linalg.norm((dr - dl)[interior], axis=1)
        h = min(h, float(np.min(4 * local_cap / np.maximum(local_jump, 1e-15))))
        windows.append((int(i), h))
    if not windows:
        raise GeometryRejected("NO_MEASURABLE_SEAM")
    q = np.unique(
        np.concatenate([y] + [y[i] + np.linspace(-h, h, 9) for i, h in windows])
    )
    result = linear_rings(y, rings, q)
    records = []
    for i, h in windows:
        mask = np.abs(q - y[i]) <= h + 1e-12
        result[mask] = transition(y, rings, i, h, q[mask])
        eps = h * 1e-5
        sample = np.array([y[i] - eps, y[i], y[i] + eps])
        before, after = (
            linear_rings(y, rings, sample),
            transition(y, rings, i, h, sample),
        )
        jumps = [
            float(
                np.linalg.norm(np.diff(v, n=2, axis=0)[0, interior] / eps, axis=1).max()
            )
            for v in (before, after)
        ]
        d = np.linalg.norm(result[mask] - linear_rings(y, rings, q[mask]), axis=2)
        records.append(Transition(float(y[i]), h, float(d.max()), *jumps))
    if any(
        t.max_displacement_m <= 0
        or t.slope_jump_after >= max(1e-7, t.slope_jump_before * 0.001)
        for t in records
    ):
        raise GeometryRejected("NO_POSITIVE_SMOOTHING_IMPROVEMENT")
    return SmoothWing(q, result, tuple(records))


def generate(output: Path, evidence: Path) -> None:
    """Publish a fresh CPU union only after topology and bounded shape checks."""
    if output.exists() or evidence.exists():
        raise GeometryRejected("OUTPUT_EXISTS_NO_OVERWRITE")
    source_bytes, reference_bytes = SOURCE.read_bytes(), REFERENCE.read_bytes()
    if hashlib.sha256(reference_bytes).hexdigest() != R3_SHA:
        raise GeometryRejected("R3_CANONICAL_HASH_MISMATCH")
    if hashlib.sha256(source_bytes).hexdigest() != LEDGER_SHA:
        raise GeometryRejected("R3_LEDGER_HASH_MISMATCH")
    source = Source.model_validate_json(source_bytes)
    solids = []
    sections = []
    transitions: tuple[Transition, ...] = ()
    for part in source.parts:
        y, rings = np.array(part.stations_m), np.array(part.rings_2d_m)
        if part.name == "wing":
            changed = smooth_wing(y, rings)
            transitions = changed.transitions
            old = linear_rings(y, rings, changed.stations)
            v0, f0 = loft(changed.stations, old, part.axis)
            y, rings = changed.stations, changed.rings
            v, f = loft(y, rings, part.axis)
            n0 = np.cross(v0[f0[:, 1]] - v0[f0[:, 0]], v0[f0[:, 2]] - v0[f0[:, 0]])
            n1 = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
            flips = int(np.count_nonzero(np.einsum("ij,ij->i", n0, n1) <= 0))
            if flips:
                raise GeometryRejected(f"WING_NORMAL_FLIPS:{flips}")
            for s, a, b in zip(y, old, rings, strict=True):
                delta = float(np.linalg.norm(b - a, axis=1).max())
                area_a = (
                    abs(
                        np.sum(
                            a[:, 0] * np.roll(a[:, 1], -1)
                            - a[:, 1] * np.roll(a[:, 0], -1)
                        )
                    )
                    / 2
                )
                area_b = (
                    abs(
                        np.sum(
                            b[:, 0] * np.roll(b[:, 1], -1)
                            - b[:, 1] * np.roll(b[:, 0], -1)
                        )
                    )
                    / 2
                )
                sections.append(
                    {
                        "span_m": float(s),
                        "max_displacement_m": delta,
                        "LE_TE_max_displacement_m": float(
                            np.linalg.norm(b[[0, 64]] - a[[0, 64]], axis=1).max()
                        ),
                        "chord_delta_m": float(np.ptp(b[:, 0]) - np.ptp(a[:, 0])),
                        "section_area_delta_m2": float(area_b - area_a),
                    }
                )
        else:
            v, f = loft(y, rings, part.axis)
        part_mesh = trimesh.Trimesh(v, f, process=False)
        for mirror in [False, True] if part.name in ("wing", "horizontal") else [False]:
            item = part_mesh.copy()
            if mirror:
                item.apply_transform(np.diag([1, -1, 1, 1]))
            solid = mf.Manifold(
                mf.Mesh(item.vertices.astype(np.float32), item.faces.astype(np.uint32))
            )
            if solid.status() != mf.Error.NoError:
                raise GeometryRejected(f"INVALID_PART:{part.name}:{solid.status()}")
            solids.append(solid)
    final = solids[0]
    for solid in solids[1:]:
        final = final + solid
    packed = final.to_mesh()
    mesh = trimesh.Trimesh(
        packed.vert_properties[:, :3], packed.tri_verts, process=False
    )
    metrics = measure(mesh.vertices, mesh.faces)
    bad_links = len(vertex_links(mesh.faces, len(mesh.vertices)))
    components = len(final.decompose())
    if (
        final.status() != mf.Error.NoError
        or components != 1
        or bad_links
        or not metrics["closed_oriented"]
        or not mesh.is_volume
    ):
        raise GeometryRejected("FINAL_TOPOLOGY_REJECTED")
    if SOURCE.read_bytes() != source_bytes or REFERENCE.read_bytes() != reference_bytes:
        raise GeometryRejected("SOURCE_CHANGED_DURING_GENERATION")
    output.mkdir(parents=True, exist_ok=False)
    stl = output / "A321_AIRFRAME_SHELL_R4.stl"
    mesh.export(stl)
    np.savez_compressed(output / "shell.npz", vertices=mesh.vertices, faces=mesh.faces)
    reread = trimesh.load_mesh(stl, process=True)
    if (
        not reread.is_watertight
        or not reread.is_winding_consistent
        or not reread.is_volume
    ):
        raise GeometryRejected("STL_READBACK_REJECTED")
    record = {
        "status": "HOLD_NOT_ENGINEERING_ACCEPTED",
        "source_sha256": R3_SHA,
        "source_ledger_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "method": "local Hermite span rounding; LE/TE points protected exactly; outline kinks retained",
        "cap_m": CAP_M,
        "transitions": [asdict(t) for t in transitions],
        "sections": sections,
        "surface": metrics,
        "vertex_link_failures": bad_links,
        "kernel_components": components,
        "kernel_status": str(final.status()),
        "wing_corresponding_triangle_normal_flips": 0,
        "stl_readback_closed_winding_volume": True,
        "source_unchanged": True,
        "geometry_displacement_positive": max(s["max_displacement_m"] for s in sections)
        > 0,
        "self_intersection_exhaustive": "NOT_RUN; manifold construction is not independent proof",
        "global_bidirectional_surface_distance": "NOT_MEASURED",
        "C1_scope": "analytic interior ring trajectories in windows; tessellation PL; protected LE/TE excluded",
        "mesh_run": False,
        "GPU_solver_run": False,
        "gpu_compute": False,
    }
    with evidence.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {k: record[k] for k in ("status", "stl_sha256", "transitions", "surface")},
            indent=2,
        )
    )


if __name__ == "__main__":
    generate(ROOT / "artifacts/smooth-r4", ROOT / "evidence/smooth-r4.json")
