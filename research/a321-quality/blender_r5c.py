#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: Blender --background --factory-startup --disable-autoexec --python blender_r5c.py
# Add -- --verify in a fresh Blender process for native readback.
# Independently authored separate Blender adapter. No GPL implementation consulted.
"""Save and independently reopen a research derivative without rendering or solving."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Final

import bpy
import numpy as np
from mathutils import Quaternion

ROOT: Final = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from native_surface_binding import bind_arrays

R3: Final = ROOT.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
R3_SHA: Final = "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
NAME: Final = "A321_R5_C_CLEANUP_RESEARCH_HOLD"


def main() -> None:
    """Keep geometry, native output and immutable reference identities distinct."""
    source = ROOT / "rebuild/artifacts/rebuild-r5-c"
    models = ROOT / "models"
    native = models / "A321_AIRFRAME_REBUILD_R5_C.blend"
    stl = models / "A321_AIRFRAME_REBUILD_R5_C.stl"
    receipt_path = ROOT / "evidence/r5-cleanup-c.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf8"))
    if hashlib.sha256(R3.read_bytes()).hexdigest() != R3_SHA:
        raise RuntimeError("R3_CHANGED")
    with np.load(source / "shell.npz") as data:
        vertices, faces = data["vertices"], data["faces"]
    bind_arrays(
        vertices, faces, source / "A321_AIRFRAME_REBUILD_R5_B.stl", receipt["stl_sha256"]
    )
    supplementary = ROOT / "evidence/blender-r5c-stl-binding.json"
    npz_sha = hashlib.sha256((source / "shell.npz").read_bytes()).hexdigest()
    if supplementary.exists():
        pinned = json.loads(supplementary.read_text(encoding="utf8"))
        if pinned["npz_sha256"] != npz_sha:
            raise RuntimeError("PINNED_NPZ_CHANGED")
    if "--verify" in sys.argv or "--verify-stl" in sys.argv:
        bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
        obj = bpy.data.objects[NAME]
        if obj.parent is not None or len(obj.modifiers) or not np.array_equal(np.array(obj.matrix_world), np.eye(4)):
            raise RuntimeError("NATIVE_WORLD_TRANSFORM_OR_MODIFIER")
        saved = json.loads((ROOT / "evidence/blender-r5c.json").read_text(encoding="utf8"))
        if hashlib.sha256(native.read_bytes()).hexdigest() != saved["native_sha256"]:
            raise RuntimeError("NATIVE_SAVE_SHA_CHANGED")
        actual_v = np.array([tuple(v.co) for v in obj.data.vertices])
        actual_f = np.array([tuple(p.vertices) for p in obj.data.polygons])
        if not np.array_equal(vertices, actual_v) or not np.array_equal(
            faces, actual_f
        ):
            raise RuntimeError("NATIVE_GEOMETRY_READBACK_CHANGED")
        bind_arrays(actual_v, actual_f, stl, receipt["stl_sha256"])
        output = (
            supplementary
            if "--verify-stl" in sys.argv
            else ROOT / "evidence/blender-r5c-readback.json"
        )
        result = {
            "status": "PASS_EXACT_NATIVE_COORDINATES_AND_TRIANGLES",
            "vertices": len(actual_v),
            "triangles": len(actual_f),
            "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        }
    else:
        if native.exists() or stl.exists():
            raise RuntimeError("R4_MODEL_ALREADY_EXISTS")
        models.mkdir(exist_ok=True)
        (models / ".r5c-native-create.lock").mkdir(exist_ok=False)
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete(use_global=False)
        mesh = bpy.data.meshes.new("R4_LOCAL_HERMITE_GEOMETRY")
        mesh.from_pydata(vertices.tolist(), [], faces.tolist())
        mesh.update()
        obj = bpy.data.objects.new(NAME, mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        obj["reference_sha256"] = R3_SHA
        obj["engineering_status"] = "HOLD"
        obj["method"] = "controlled cleanup of R5-A, not whole chordwise CAD reconstruction"
        obj["scope"] = (
            "local wing interior seam rounding only; protected outlines retained"
        )
        for polygon in mesh.polygons:
            polygon.use_smooth = True
        scene = bpy.context.scene
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = 1.0
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    view = area.spaces.active.region_3d
                    view.view_location = (22, 0, 4)
                    view.view_distance = 65
                    view.view_rotation = Quaternion(
                        (0.86, 0.36, -0.14, -0.33)
                    ).normalized()
        bpy.ops.wm.save_as_mainfile(filepath=str(native))
        shutil.copyfile(source / "A321_AIRFRAME_REBUILD_R5_B.stl", stl)
        if hashlib.sha256(stl.read_bytes()).hexdigest() != receipt["stl_sha256"]:
            raise RuntimeError("R4_STL_COPY_MISMATCH")
        output = ROOT / "evidence/blender-r5c.json"
        result = {
            "status": "SEPARATE_RESEARCH_MODEL_SAVED",
            "vertices": len(vertices),
            "triangles": len(faces),
            "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
            "stl_sha256": receipt["stl_sha256"],
        }
    if output.exists():
        raise RuntimeError("BLENDER_RECEIPT_ALREADY_EXISTS")
    result.update(
        {
            "blender": bpy.app.version_string,
            "R3_sha256": R3_SHA,
            "GPU_solver_run": False,
            "render_run": False,
            "npz_sha256": npz_sha,
            "generation_receipt_sha256": hashlib.sha256(
                receipt_path.read_bytes()
            ).hexdigest(),
            "stl_sha256": receipt["stl_sha256"],
            "native_to_STL_triangle_coordinates_exact": True,
            "binding_scope": "post-generation native/STL correspondence; frozen generation and trial inputs unchanged",
        }
    )
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
