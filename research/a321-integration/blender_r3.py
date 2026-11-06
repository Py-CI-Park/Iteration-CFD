#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: Blender -b --factory-startup --disable-autoexec --python blender_r3.py
"""Author the local gap-repair candidate in Blender, leaving R2/source untouched."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Quaternion

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from surface_metrics import measure


def main() -> None:
    """Save a separate research model and export exact selected mesh."""
    out = ROOT / "models"
    out.mkdir(exist_ok=True)
    path = out / "A321_AIRFRAME_SHELL_R3.blend"
    if path.exists():
        raise RuntimeError("R3_ALREADY_EXISTS")
    with np.load(ROOT / "artifacts/shell-r3/shell.npz") as d:
        v, f = d["vertices"], d["faces"]
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    m = bpy.data.meshes.new("R3_local_gap_repair")
    m.from_pydata(v.tolist(), [], f.tolist())
    m.update()
    obj = bpy.data.objects.new("A321_R3_RESEARCH_NOT_VALIDATED", m)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    obj["baseline"] = "G1B SHA1fd3cfd0; R2 branch6d4bfed"
    obj["assumption"] = (
        "root leading edge extrapolation; flap gap trailing edge interpolation"
    )
    for p in m.polygons:
        p.use_smooth = True
    bpy.context.scene.unit_settings.system = "METRIC"
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_location = (22, 0, 4)
                view.view_distance = 65
                view.view_rotation = Quaternion((0.86, 0.36, -0.14, -0.33)).normalized()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    bpy.ops.wm.stl_export(
        filepath=str(out / "A321_AIRFRAME_SHELL_R3.stl"), export_selected_objects=True
    )
    (ROOT / "evidence/blender-r3.json").write_text(
        json.dumps(
            {
                "blender": bpy.app.version_string,
                "surface": measure(v, f),
                "gpu_compute": False,
                "render": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
