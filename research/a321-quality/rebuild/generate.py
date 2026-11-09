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
"""Generate an immutable R5-A global station-curve draft, with failure evidence."""

from __future__ import annotations
from dataclasses import asdict
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import manifold3d as mf
import numpy as np
import trimesh
from pydantic import BaseModel, ConfigDict
from curves import CurveRejected, rebuild
from geometry import loft, topology
from custody import capture, verify_parent_freeze

ROOT = Path(__file__).resolve().parent
QUALITY = ROOT.parent
SOURCE = QUALITY.parent / "a321-integration/evidence/reconstruction-r3.json"
R3 = QUALITY.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
CONTRACT = QUALITY / "plans/r5-geometry-contract-01.json"
FREEZE = QUALITY / "evidence/r5-m1-freeze.json"


class Part(BaseModel):
    """Frozen measured section-envelope boundary."""

    model_config = ConfigDict(frozen=True)
    name: Literal["fuselage", "wing", "horizontal", "vertical"]
    axis: Literal[0, 1, 2]
    stations_m: list[float]
    rings_2d_m: list[list[list[float]]]


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)
    parts: list[Part]


class Limits(BaseModel):
    model_config = ConfigDict(frozen=True)
    station_point_max_m: float
    bounds_max_m: float
    between_station_sample_max_m: dict[str, float]
    relative_volume_change_max: float


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True)
    source_R3_sha256: str
    source_ledger_sha256: str
    limits: Limits


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_fresh(output: Path) -> None:
    """Refuse to change any already-created candidate."""
    if output.exists():
        raise FileExistsError(output)


def generate() -> None:
    """Freeze inputs, construct every part, then retain both success and failure."""
    out = ROOT / "artifacts/rebuild-r5-a"
    evidence = ROOT / "evidence/rebuild-r5-a.json"
    require_fresh(out)
    require_fresh(evidence)
    started = datetime.now(timezone.utc).isoformat()
    preserved = (
        SOURCE,
        R3,
        CONTRACT,
        FREEZE,
        QUALITY / "models/A321_AIRFRAME_SHELL_R4.stl",
        QUALITY / "models/A321_AIRFRAME_SHELL_R4.blend",
    )
    captured = capture(preserved)
    verify_parent_freeze(
        captured,
        FREEZE,
        QUALITY.parent.parent,
        "b2f65c0f29dd43ef2fe85c5c88773329f4ef763799d3ab5e91b5ab8fdf038a65",
    )
    sealed = {str(p): captured.digest(p) for p in preserved}
    if (
        sealed[str(CONTRACT)]
        != "2c0e9c573f44cd8421f3c0e58f253e5d3e550266ecc540caf6ef3c6b12e1e1be"
    ):
        raise CurveRejected("CONTRACT_HASH_MISMATCH")
    contract = Contract.model_validate_json(captured.blobs[CONTRACT])
    if (
        sealed[str(SOURCE)] != contract.source_ledger_sha256
        or sealed[str(R3)] != contract.source_R3_sha256
    ):
        raise CurveRejected("SEALED_SOURCE_MISMATCH")
    source = Source.model_validate_json(captured.blobs[SOURCE])
    solids = []
    reports = []
    for part in source.parts:
        stations = np.array(part.stations_m)
        rings = np.array(part.rings_2d_m)
        cap = contract.limits.between_station_sample_max_m[part.name]
        reconstructed = rebuild(stations, rings, cap, subdivisions=2)
        mesh = loft(reconstructed.stations, reconstructed.rings, part.axis)
        # Float32 per-part boundaries match the original union input precision.
        for mirror in [False, True] if part.name in ("wing", "horizontal") else [False]:
            item = mesh.copy()
            if mirror:
                item.apply_transform(np.diag([1, -1, 1, 1]))
            solid = mf.Manifold(
                mf.Mesh(item.vertices.astype(np.float32), item.faces.astype(np.uint32))
            )
            if solid.status() != mf.Error.NoError:
                raise CurveRejected(f"PART_KERNEL_FAILED:{part.name}:{solid.status()}")
            solids.append(solid)
        reports.append(
            {
                "part": part.name,
                "original_stations": len(stations),
                "generated_stations": len(reconstructed.stations),
                "ring_points": rings.shape[1],
                "sample_departure_m": reconstructed.max_departure_m,
                "sample_departure_cap_m": cap,
                "source_station_float32_error_m": reconstructed.station_error_m,
                "analytic_slope_jump_before": reconstructed.slope_jump_before,
                "analytic_near_station_slope_jump_after": reconstructed.slope_jump_after,
                "actually_changed_sample_points": reconstructed.changed_points,
            }
        )
        print(json.dumps(reports[-1]), flush=True)
    union = solids[0]
    for solid in solids[1:]:
        union = union + solid
    packed = union.to_mesh()
    mesh = trimesh.Trimesh(
        packed.vert_properties[:, :3], packed.tri_verts, process=False
    )
    topo = topology(mesh)
    old = trimesh.load_mesh(R3, process=True)
    bounds_error = float(np.abs(mesh.bounds - old.bounds).max())
    volume_delta = float(abs(mesh.volume - old.volume) / abs(old.volume))
    checks = {
        "station_constraints": all(
            p["source_station_float32_error_m"] <= contract.limits.station_point_max_m
            for p in reports
        ),
        "sample_departure_caps": all(
            p["sample_departure_m"] <= p["sample_departure_cap_m"] for p in reports
        ),
        "bounds": bounds_error <= contract.limits.bounds_max_m,
        "volume": volume_delta <= contract.limits.relative_volume_change_max,
        "closed_oriented_single": topo.closed
        and topo.winding
        and topo.positive_volume
        and topo.components == 1,
        "vertex_links": topo.vertex_link_failures == 0,
        "no_degenerate_duplicate": topo.degenerate_faces == 0
        and topo.duplicate_faces == 0,
        "positive_coordinate_changes": all(
            p["actually_changed_sample_points"] > 0 for p in reports
        ),
        "sources_unchanged": all(
            sha(Path(p)) == digest for p, digest in sealed.items()
        ),
    }
    out.mkdir(parents=True, exist_ok=False)
    stl = out / "A321_AIRFRAME_REBUILD_R5_A.stl"
    mesh.export(stl)
    npz = out / "shell.npz"
    np.savez_compressed(npz, vertices=mesh.vertices, faces=mesh.faces)
    reread = trimesh.load_mesh(stl, process=True)
    checks["stl_readback_closed_winding"] = bool(
        reread.is_watertight and reread.is_winding_consistent
    )
    evidence.parent.mkdir(exist_ok=True)
    record = {
        "status": "DRAFT_INTERNAL_GATES_PASS_M3_OPEN"
        if all(checks.values())
        else "FAILED_CONTRACT_DRAFT_RETAINED",
        "not_oem": True,
        "engineering_accepted": False,
        "GPU_solver_run": False,
        "CFD_solver_run": False,
        "method": "global corresponding-point PCHIP trajectories with PL shoulder controls at 2%/98%; original polygonal section rings preserved; symmetric wing/tail CPU union",
        "C1_scope": "analytic length/span ring-point trajectories only; polygonal chordwise sections, STL and Boolean seams are NOT globally C1",
        "feature_scope": "all original station-ring points incl LE/TE fixed within float32 tolerance; no new wing/body fillet; between-station planform/LE/TE departure subject to same caps, intentional outline kinks NOT independently classified",
        "constraints_scope": "source section controls before Boolean union; internal buried stations need not be surface vertices; source rings are envelopes, not OEM airfoils",
        "sampling_scope": "all generated stations; not continuous bound nor Hausdorff bound",
        "independent_self_intersection": "PENDING_SEPARATE_CLI",
        "native_STL_binding": "PENDING_SEPARATE_BLENDER",
        "input_sha256": sealed,
        "stl_sha256": sha(stl),
        "npz_sha256": sha(npz),
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "parts": reports,
        "checks": checks,
        "surface_topology": asdict(topo),
        "triangles": len(mesh.faces),
        "volume_m3": float(mesh.volume),
        "R3_volume_m3": float(old.volume),
        "relative_volume_change": volume_delta,
        "bounds_max_error_m": bounds_error,
        "bounds_m": mesh.bounds.tolist(),
        "kernel_status": str(union.status()),
        "kernel_components": len(union.decompose()),
        "construction_parameters": {
            "shoulder_fraction": 0.02,
            "subdivisions_per_control_interval": 2,
        },
    }
    with evidence.open("x", encoding="utf8") as f:
        f.write(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {"status": record["status"], "checks": checks, "triangles": len(mesh.faces)}
        ),
        flush=True,
    )


if __name__ == "__main__":
    generate()
