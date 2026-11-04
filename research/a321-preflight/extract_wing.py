#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# ─── How to run ───
# Blender -b --disable-autoexec FROZEN.blend --python extract_wing.py -- OUT
# Native object extraction only; no geometry repair, render, or CUDA execution.
# Original research adapter; no GPL source consulted or copied.
"""Extract an unchanged closed wing-box subsystem, explicitly not a full wing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from custody import trial_directory
from prepare_surface import arrays
from surface_metrics import measure


def main() -> None:
    """Save one exact native mesh object and its evaluated STL representation."""
    root = trial_directory(Path(sys.argv[sys.argv.index("--") + 1]))
    source = bpy.data.filepath
    obj = bpy.data.objects["Wing_fixed_box_STARBOARD"]
    before = measure(*arrays(obj))
    for other in list(bpy.data.objects):
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.hide_render = False
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(root / "wing-fixed-box.blend"))
    bpy.ops.wm.stl_export(
        filepath=str(root / "wing-fixed-box.stl"), export_selected_objects=True
    )
    result = {
        "source": source,
        "object": obj.name,
        "before": before,
        "after": measure(*arrays(obj)),
        "geometry_coordinates_modified": False,
        "role": "isolated starboard fixed wing-box subsystem, not complete wing or aircraft",
        "missing": [
            "slats",
            "flaps",
            "aileron",
            "sharklet",
            "fuselage interference",
            "engine/pylon",
        ],
        "status": "CPU_SURFACE_CANDIDATE_NOT_VALIDATED",
        "gpu_compute_used": False,
    }
    (root / "extraction.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
