#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest", "rtree"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""One declared CPU simplify operation on sealed R5-A; all outputs fresh."""

from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import manifold3d as mf
import numpy as np
import trimesh
from pydantic import BaseModel, ConfigDict
from cleanup import cleanup_tolerance
from curves import CurveRejected
from generate import ROOT, QUALITY, CONTRACT, R3, Contract, sha, require_fresh
from geometry import topology


class AReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)
    input_sha256: dict[str, str]
    stl_sha256: str
    npz_sha256: str


class Pin(BaseModel):
    model_config = ConfigDict(frozen=True)
    path: str
    sha256: str


class Freeze(BaseModel):
    model_config = ConfigDict(frozen=True)
    inputs: list[Pin]


def sampled(source: trimesh.Trimesh, target: trimesh.Trimesh) -> dict[str, float | int]:
    """Area-weighted samples plus uniformly selected vertex indices; exact target triangle queries."""
    points, _ = trimesh.sample.sample_surface(source, 4000, seed=20261108)
    points = np.concatenate(
        (
            points,
            source.vertices[np.linspace(0, len(source.vertices) - 1, 2000, dtype=int)],
        )
    )
    _, distances, _ = trimesh.proximity.closest_point(target, points)
    return {
        "samples": len(points),
        "max_m": float(distances.max()),
        "p95_m": float(np.quantile(distances, 0.95)),
        "median_m": float(np.median(distances)),
    }


def main() -> None:
    """Freeze then simplify within the declared tolerance, retaining failures."""
    started = datetime.now(timezone.utc).isoformat()
    output = ROOT / "artifacts/rebuild-r5-b"
    record_path = ROOT / "evidence/rebuild-r5-b.json"
    require_fresh(output)
    require_fresh(record_path)
    a_receipt = ROOT / "evidence/rebuild-r5-a.json"
    a_bytes = a_receipt.read_bytes()
    a = AReceipt.model_validate_json(a_bytes)
    contract_bytes = CONTRACT.read_bytes()
    contract = Contract.model_validate_json(contract_bytes)
    freeze = Freeze.model_validate_json(
        (QUALITY / "evidence/r5-m1-freeze.json").read_bytes()
    )
    repo = QUALITY.parent.parent
    for pin in freeze.inputs:
        if sha(repo / pin.path) != pin.sha256:
            raise CurveRejected("M1_FROZEN_INPUT_CHANGED")
    for path, digest in a.input_sha256.items():
        if sha(Path(path)) != digest:
            raise CurveRejected("A_SEALED_INPUT_CHANGED")
    code_freeze = ROOT / "evidence/rebuild-r5-b-code-freeze.json"
    pins = json.loads(code_freeze.read_text(encoding="utf-8-sig"))
    for pin in pins["files"]:
        if sha(ROOT / pin["path"]) != pin["sha256"]:
            raise CurveRejected("B_PRE_EXECUTION_CODE_CHANGED")
    astl = ROOT / "artifacts/rebuild-r5-a/A321_AIRFRAME_REBUILD_R5_A.stl"
    anpz = astl.parent / "shell.npz"
    if sha(astl) != a.stl_sha256 or sha(anpz) != a.npz_sha256:
        raise CurveRejected("A_GEOMETRY_CHANGED")
    with np.load(anpz) as data:
        av, af = data["vertices"], data["faces"]
    original = trimesh.Trimesh(av, af, process=False)
    solid = mf.Manifold(mf.Mesh(av.astype(np.float32), af.astype(np.uint32)))
    tolerance = cleanup_tolerance(1e-6)
    current = float(solid.get_tolerance())
    if current > tolerance:
        raise CurveRejected(f"INTERNAL_TOLERANCE_EXCEEDS_CEILING:{current}")
    clean = solid.simplify(tolerance)
    packed = clean.to_mesh()
    mesh = trimesh.Trimesh(
        packed.vert_properties[:, :3], packed.tri_verts, process=False
    )
    topo = topology(mesh)
    reference = trimesh.load_mesh(R3, process=True)
    volume = float(abs(mesh.volume - reference.volume) / abs(reference.volume))
    bbox = float(np.abs(mesh.bounds - reference.bounds).max())
    a_to_b = sampled(original, mesh)
    b_to_a = sampled(mesh, original)
    checks = {
        "kernel": str(clean.status()) == "Error.NoError",
        "bbox": bbox <= contract.limits.bounds_max_m,
        "volume": volume <= contract.limits.relative_volume_change_max,
        "topology": topo.closed
        and topo.winding
        and topo.positive_volume
        and topo.components == 1
        and topo.vertex_link_failures == 0
        and topo.degenerate_faces == 0
        and topo.duplicate_faces == 0,
        "sampled_cleanup_distance": max(a_to_b["max_m"], b_to_a["max_m"]) <= tolerance,
        "sources_unchanged": all(sha(Path(p)) == d for p, d in a.input_sha256.items()),
        "A_unchanged": sha(astl) == a.stl_sha256 and sha(anpz) == a.npz_sha256,
        "code_unchanged": all(
            sha(ROOT / p["path"]) == p["sha256"] for p in pins["files"]
        ),
    }
    output.mkdir(parents=True, exist_ok=False)
    stl = output / "A321_AIRFRAME_REBUILD_R5_B.stl"
    mesh.export(stl)
    npz = output / "shell.npz"
    np.savez_compressed(npz, vertices=mesh.vertices, faces=mesh.faces)
    result = {
        "status": "CLEANUP_INTERNAL_PASS_M3_OPEN"
        if all(checks.values())
        else "CLEANUP_INTERNAL_FAIL_RETAINED",
        "sourceA_sha256": a.stl_sha256,
        "sourceA_receipt_sha256": sha(a_receipt),
        "contract_sha256": sha(CONTRACT),
        "code_freeze_sha256": sha(code_freeze),
        "method_supplement_sha256": pins["method_supplement_sha256"],
        "input_sha256": a.input_sha256,
        "stl_sha256": sha(stl),
        "npz_sha256": sha(npz),
        "method": "single manifold3d simplify(1e-6), no regeneration, no tolerance relaxation",
        "requested_tolerance_m": tolerance,
        "kernel_current_tolerance_m": current,
        "checks": checks,
        "A_to_B_sampled_m": a_to_b,
        "B_to_A_sampled_m": b_to_a,
        "sampling_scope": "6000 points/direction (4000 area-weighted seed20261108 + 2000 vertex-index samples), exact closest triangle; NOT a continuous/global Hausdorff bound",
        "station_constraint_scope": "A parametric ledger unchanged; cleanup surface tolerance sampled only; no new proof of every continuous original station constraint",
        "triangles_before": len(af),
        "triangles_after": len(mesh.faces),
        "topology": asdict(topo),
        "surface_area_m2": float(mesh.area),
        "volume_m3": float(mesh.volume),
        "relative_volume_change_vs_R3": volume,
        "bbox_max_change_vs_R3_m": bbox,
        "not_oem": True,
        "engineering_accepted": False,
        "GPU_solver_run": False,
        "CFD_solver_run": False,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "independent_self_intersection": "PENDING_SEPARATE_CLI",
    }
    with record_path.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
