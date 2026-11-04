#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# ─── How to run ───
# Blender -b --disable-autoexec candidate.blend --python reopen_candidate.py -- OUT
# Original readback adapter; does not save native or invoke a renderer.
"""Verify saved Blender geometry through a fresh Blender process."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from custody import output_file
from prepare_surface import arrays
from surface_metrics import measure


def main() -> None:
    """Measure the single saved candidate and export it for byte comparison."""
    root = Path(sys.argv[sys.argv.index("--") + 1])
    receipt_path = output_file(root / "reopened.json")
    export_path = output_file(root / "reopened.stl")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(meshes) != 1:
        raise RuntimeError("EXPECTED_SINGLE_RESEARCH_OBJECT")
    vertices, faces = arrays(meshes[0])
    result = {
        "file": bpy.data.filepath,
        "object": meshes[0].name,
        "blender": bpy.app.version_string,
        "surface": measure(vertices, faces),
        "gpu_compute_used": False,
        "native_saved": False,
    }
    receipt_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.wm.stl_export(filepath=str(export_path), export_selected_objects=True)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
