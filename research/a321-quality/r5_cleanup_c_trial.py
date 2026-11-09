#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public manifold/STL APIs only; no GPL implementation source consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy","scipy","trimesh","manifold3d","rtree"]
# ///
# How to run: uv run r5_cleanup_c_trial.py; isolated CPU cleanup, no CFD/GPU.
"""Run a code-sealed R5-C small-tolerance cleanup without modifying A."""
from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Final

import manifold3d as mf
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT: Final = Path(__file__).resolve().parent

@dataclass(frozen=True, slots=True)
class CleanupRejected(RuntimeError):
    """A cleanup experiment cannot change its frozen limits."""
    reason: str
    def __str__(self) -> str:
        return self.reason

def check_tolerance(requested: float, actual: float) -> None:
    """Do not allow the library to substitute a larger effective tolerance."""
    if not math.isfinite(actual) or actual < 0 or actual > requested:
        raise CleanupRejected("EFFECTIVE_TOLERANCE_EXCEEDS_DECLARATION")

def digest(path: Path) -> str:
    """Hash bytes without materializing a large STL."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle,"sha256").hexdigest()

def main() -> None:
    """Freeze inputs/code first, generate one distinct candidate and measure it."""
    a=ROOT/"rebuild/artifacts/rebuild-r5-a"
    out=ROOT/"rebuild/artifacts/rebuild-r5-c"
    evidence=ROOT/"evidence/r5-cleanup-c.json"
    if evidence.exists():
        raise CleanupRejected("RECEIPT_EXISTS")
    out.mkdir(exist_ok=False)
    source=ROOT/"rebuild/evidence/rebuild-r5-a.json"
    contract=ROOT/"plans/r5-geometry-contract-01.json"
    supplement=ROOT/"plans/r5-cleanup-c-contract.json"
    r3=ROOT.parent/"a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
    paths=[source,contract,supplement,a/"shell.npz",a/"A321_AIRFRAME_REBUILD_R5_A.stl",r3,Path(__file__)]
    payload={str(p):p.read_bytes() for p in paths}
    sealed={p:hashlib.sha256(data).hexdigest() for p,data in payload.items()}
    if sealed[str(source)]!="67baf88f7f7437fa4a7d5fbc3cb4677a5ef49fb83f9cf38f969d56e62daa6856":
        raise CleanupRejected("A_RECEIPT_CHANGED")
    raw=json.loads(payload[str(source)])
    if digest(a/"shell.npz")!=raw["npz_sha256"] or digest(a/"A321_AIRFRAME_REBUILD_R5_A.stl")!=raw["stl_sha256"]:
        raise CleanupRejected("A_INPUT_CHANGED")
    if digest(r3)!="2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745":
        raise CleanupRejected("R3_CHANGED")
    if digest(contract)!="2c0e9c573f44cd8421f3c0e58f253e5d3e550266ecc540caf6ef3c6b12e1e1be":
        raise CleanupRejected("CONTRACT_CHANGED")
    requested=6e-6
    if json.loads(payload[str(supplement)])["requested_tolerance_m"]!=requested:
        raise CleanupRejected("C_PLAN_PARAMETER_MISMATCH")
    freeze={"captured_utc":datetime.now(timezone.utc).isoformat(),"input_sha256":sealed,
            "requested_tolerance_m":requested,"command":"uv run research/a321-quality/r5_cleanup_c_trial.py",
            "manifold3d_version":version("manifold3d")}
    with (out/"run-inputs.json").open("x",encoding="utf8") as handle:
        json.dump(freeze,handle,indent=2)
    shutil.copyfile(Path(__file__),out/"executed-code.py")
    with np.load(io.BytesIO(payload[str(a/"shell.npz")]),allow_pickle=False) as data:
        vertices,faces=data["vertices"],data["faces"]
    original=trimesh.Trimesh(vertices,faces,process=False)
    solid=mf.Manifold(mf.Mesh(vertices.astype(np.float32),faces.astype(np.uint32)))
    effective_before=solid.get_tolerance()
    check_tolerance(requested,effective_before)
    cleaned=solid.simplify(requested)
    effective_after=cleaned.get_tolerance()
    check_tolerance(requested,effective_after)
    packed=cleaned.to_mesh()
    mesh=trimesh.Trimesh(packed.vert_properties[:,:3],packed.tri_verts,process=False)
    ref=trimesh.load_mesh(io.BytesIO(payload[str(r3)]),file_type="stl",process=True)
    bbox_error=float(np.max(abs(mesh.bounds-ref.bounds)))
    volume_change=float(abs(mesh.volume-ref.volume)/abs(ref.volume))
    subsets=cKDTree(vertices).query(mesh.vertices)[0]
    distances=[]
    for label,left,right in [("A_to_B",original,mesh),("B_to_A",mesh,original)]:
        points=left.sample(2000,seed=20261108)
        _,d,_=trimesh.proximity.closest_point(right,points)
        distances.append({"direction":label,"samples":2000,"maximum_m":float(d.max()),"p95_m":float(np.quantile(d,.95))})
    checks={"kernel":cleaned.status()==mf.Error.NoError,"single_component":len(cleaned.decompose())==1,
            "closed":bool(mesh.is_watertight),"winding":bool(mesh.is_winding_consistent),
            "positive_volume":bool(mesh.is_volume),"bbox_contract":bbox_error<=1e-5,
            "volume_contract":volume_change<=.01,
            "sample_departure":all(d["maximum_m"]<=requested for d in distances),
            "original_vertices_subset":bool(np.all(subsets==0)),
            "sources_unchanged":all(digest(Path(p))==h for p,h in sealed.items())}
    stl=out/"A321_AIRFRAME_REBUILD_R5_B.stl"
    mesh.export(stl)
    np.savez_compressed(out/"shell.npz",vertices=mesh.vertices,faces=mesh.faces)
    record={**freeze,"status":"CLEANUP_INTERNAL_PASS_M3_OPEN" if all(checks.values()) else "CLEANUP_INTERNAL_FAIL",
            "effective_tolerance_before_m":effective_before,"effective_tolerance_after_m":effective_after,
            "checks":checks,"input_triangles":len(faces),"output_triangles":len(mesh.faces),
            "bbox_error_m":bbox_error,"relative_R3_volume_change":volume_change,
            "distances":distances,"stl_sha256":digest(stl),"npz_sha256":digest(out/"shell.npz"),
            "global_Hausdorff_bound":"NOT_INDEPENDENTLY_MEASURED",
            "self_intersection":"PENDING_INDEPENDENT_CLI","native":"NOT_YET_SAVED",
            "engineering_accepted":False,"GPU_solver_run":False,"CFD_solver_run":False}
    with evidence.open("x",encoding="utf8") as handle:
        json.dump(record,handle,indent=2)
    print(json.dumps({k:record[k] for k in ["status","input_triangles","output_triangles","checks"]}))

if __name__=="__main__":
    try:
        main()
    except CleanupRejected as error:
        failure=ROOT/"evidence/r5-cleanup-c-failure.json"
        with failure.open("x",encoding="utf8") as handle:
            json.dump({"status":"REFUSED_OR_FAILED_CONTRACT","reason":str(error),"GPU_solver_run":False},handle,indent=2)
        raise
