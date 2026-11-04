#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# Blender --background --disable-autoexec source.blend --python inventory.py -- OUT
# bpy is supplied by Blender; never run this adapter in a system Python.
# Original research adapter; no GPL source consulted or copied.
"""Read the native scene into a manifest without saving or modifying it."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from custody import output_file


class ObjectRow(TypedDict):
    name: str
    collections: list[str]
    visible: bool
    vertices: int
    polygons: int
    bounds: list[list[float]]


def main() -> None:
    """Record all mesh metadata and world-space bounds on the CPU."""
    out = output_file(Path(sys.argv[sys.argv.index("--") + 1]))
    rows: list[ObjectRow] = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        rows.append(
            {
                "name": obj.name,
                "collections": [c.name for c in obj.users_collection],
                "visible": obj.visible_get(),
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "bounds": [
                    [min(p[i] for p in points) for i in range(3)],
                    [max(p[i] for p in points) for i in range(3)],
                ],
            }
        )
    result = {
        "source": bpy.data.filepath,
        "blender": bpy.app.version_string,
        "unit_system": bpy.context.scene.unit_settings.system,
        "unit_scale": bpy.context.scene.unit_settings.scale_length,
        "objects": rows,
        "gpu_compute_used": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"INVENTORY {len(rows)} mesh objects -> {out}")


if __name__ == "__main__":
    main()
