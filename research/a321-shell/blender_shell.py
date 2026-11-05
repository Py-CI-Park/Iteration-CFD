#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: Blender -b --factory-startup --disable-autoexec --python blender_shell.py
"""Author loft solids and validated CPU-union surface in a separate Blender scene."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from surface_metrics import measure


def main() -> None:
    """Save native shell without opening/saving reference native or using a renderer."""
    root = ROOT / "artifacts/shell-r2"
    output = root / "A321_AIRFRAME_SHELL_R2.blend"
    if output.exists():
        raise RuntimeError("NATIVE_OUTPUT_EXISTS")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    sources = bpy.data.collections.new("REFERENCE_SECTION_LOFTS_HIDDEN")
    bpy.context.scene.collection.children.link(sources)
    for name in [
        "fuselage",
        "wing",
        "wing-port",
        "horizontal",
        "horizontal-port",
        "vertical",
    ]:
        bpy.ops.wm.stl_import(filepath=str(root / f"{name}.stl"))
        obj = bpy.context.object
        obj.name = f"LOFT_{name}"
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        sources.objects.link(obj)
        obj.hide_set(True)
        obj.hide_render = True
    sources.hide_viewport = True
    sources.hide_render = True
    with np.load(root / "shell.npz") as data:
        vertices, faces = data["vertices"], data["faces"]
    mesh = bpy.data.meshes.new("A321_AIRFRAME_SHELL_R2_TRIANGLES")
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    obj = bpy.data.objects.new("A321_AERO_SHELL_R2_NOT_OEM_NOT_VALIDATED", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj["baseline_sha256"] = (
        "1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c"
    )
    obj["engineering_status"] = "NOT_VALIDATED"
    obj["omissions"] = (
        "engines,pylons,gear,sharklets,individual flap/slat slots,doors,windows,interior"
    )
    for p in mesh.polygons:
        p.use_smooth = True
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    # Viewport orientation only; no render invocation.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_location = (22, 0, 4)
                area.spaces.active.region_3d.view_distance = 65
                area.spaces.active.region_3d.view_rotation = Quaternion(
                    (0.86, 0.36, -0.14, -0.33)
                ).normalized()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    bpy.ops.wm.stl_export(
        filepath=str(root / "blender-export.stl"), export_selected_objects=True
    )
    obj.select_set(False)
    # Geometry loaded from NPZ and authored with bpy; final native metrics use the same triangles.
    record = {
        "blender": bpy.app.version_string,
        "native": str(output),
        "mesh": measure(vertices, faces),
        "gpu_compute": False,
        "render_executed": False,
        "source_native_saved": False,
    }
    (ROOT / "evidence/blender-authoring-r2.json").write_text(
        json.dumps(record, indent=2), encoding="utf8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()
