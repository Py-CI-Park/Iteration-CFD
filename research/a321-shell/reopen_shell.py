#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: Blender -b --disable-autoexec SHELL.blend --python reopen_shell.py
"""Reopen authored native in a new Blender process and measure actual saved geometry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from prepare_surface import arrays
from surface_metrics import measure


def main() -> None:
    """Read only active final shell and export a second independent STL."""
    obj = bpy.data.objects["A321_AERO_SHELL_R2_NOT_OEM_NOT_VALIDATED"]
    mesh = measure(*arrays(obj))
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = ROOT / "artifacts/shell-r2/reopened.stl"
    if path.exists():
        raise RuntimeError("READBACK_ALREADY_EXISTS")
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True)
    (ROOT / "evidence/native-readback-r2.json").write_text(
        json.dumps(
            {
                "file": bpy.data.filepath,
                "surface": mesh,
                "native_saved": False,
                "gpu_compute": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )
    print(json.dumps(mesh))


if __name__ == "__main__":
    main()
