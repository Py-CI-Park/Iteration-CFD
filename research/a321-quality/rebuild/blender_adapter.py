#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "manifold3d", "pydantic", "pytest"]
# ///
# How to run: uv run generate.py; tests: uv run --with pytest --with numpy --with scipy --with pydantic --with manifold3d --with trimesh python -m pytest test_rebuild.py
# SPDX-License-Identifier: GPL-2.0-or-later
# Independently authored adapter executed inside the separate Blender program.
# No GPL implementation source was consulted. See local PROVENANCE.md.
"""Separate Blender CLI adapter; no rendering, modifiers, or CFD execution."""

from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from binding import BindingRejected, bind


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Create or fresh-process reopen the exact receipt-bound R5 triangle mesh."""
    suffix = "b" if "--candidate-b" in sys.argv else "a"
    receipt_path = ROOT / f"evidence/rebuild-r5-{suffix}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf8"))
    source = ROOT / f"artifacts/rebuild-r5-{suffix}"
    stl = source / f"A321_AIRFRAME_REBUILD_R5_{suffix.upper()}.stl"
    npz = source / "shell.npz"
    native = source / f"A321_AIRFRAME_REBUILD_R5_{suffix.upper()}.blend"
    verify = "--verify" in sys.argv or "--verify-hardened" in sys.argv
    mode = "readback-hardened" if verify else "save"
    output = ROOT / "evidence" / f"blender-r5-{suffix}-{mode}.json"
    if output.exists() or (not verify and native.exists()):
        raise FileExistsError(output)
    if sha(npz) != receipt["npz_sha256"]:
        raise BindingRejected("NPZ_HASH_CHANGED")
    for path, digest in receipt["input_sha256"].items():
        if sha(Path(path)) != digest:
            raise BindingRejected("INPUT_CHANGED")
    with np.load(npz) as data:
        v, f = data["vertices"], data["faces"]
    bind(v, f, stl, receipt["stl_sha256"])
    name = f"R5_{suffix.upper()}_GLOBAL_STATION_DRAFT_NOT_OEM_HOLD"
    if verify:
        saved = json.loads(
            (ROOT / f"evidence/blender-r5-{suffix}-save.json").read_text(
                encoding="utf8"
            )
        )
        if sha(native) != saved["native_sha256"]:
            raise BindingRejected("NATIVE_CHANGED_SINCE_SAVE")
        bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
        obj = bpy.data.objects[name]
        if (
            obj.parent is not None
            or len(obj.modifiers)
            or not np.array_equal(np.array(obj.matrix_world), np.eye(4))
        ):
            raise BindingRejected("NATIVE_WORLD_TRANSFORM_PARENT_OR_MODIFIER")
        actual_v = np.array([tuple(p.co) for p in obj.data.vertices])
        actual_f = np.array([tuple(p.vertices) for p in obj.data.polygons])
        if not np.array_equal(v, actual_v) or not np.array_equal(f, actual_f):
            raise BindingRejected("BLEND_NPZ_CHANGED")
        bind(actual_v, actual_f, stl, receipt["stl_sha256"])
    else:
        with native.with_suffix(".blend.lock").open("x", encoding="utf8") as lock:
            lock.write(
                "Exclusive creation reservation; retained to prevent competing writers.\n"
            )
        if native.exists():
            raise FileExistsError(native)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        mesh = bpy.data.meshes.new("R5_A_EXACT_TRIANGULATED_GEOMETRY")
        mesh.from_pydata(v.tolist(), [], f.tolist())
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj["not_oem"] = True
        obj["engineering_status"] = "HOLD_GLOBAL_C1_NOT_CLAIMED"
        obj["stl_sha256"] = receipt["stl_sha256"]
        # Smooth display is metadata; geometry is already reconstructed.
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        bpy.context.scene.unit_settings.system = "METRIC"
        bpy.ops.wm.save_as_mainfile(filepath=str(native))
    result = {
        "status": "PASS_EXACT_READBACK" if verify else "SAVED_NEW_RESEARCH_DRAFT",
        "blender": bpy.app.version_string,
        "native_sha256": sha(native),
        "stl_sha256": sha(stl),
        "npz_sha256": sha(npz),
        "generation_receipt_sha256": sha(receipt_path),
        "triangles": len(f),
        "not_oem": True,
        "engineering_accepted": False,
        "native_STL_exact": True,
        "sourceA_sha256": receipt.get("sourceA_sha256", receipt["stl_sha256"]),
        "contract_sha256": receipt.get(
            "contract_sha256",
            "2c0e9c573f44cd8421f3c0e58f253e5d3e550266ecc540caf6ef3c6b12e1e1be",
        ),
        "render_run": False,
        "GPU_solver_run": False,
    }
    with output.open("x", encoding="utf8") as stream:
        stream.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
