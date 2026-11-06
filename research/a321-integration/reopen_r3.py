#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: Blender -b --disable-autoexec R3.blend --python reopen_r3.py
"""Fresh-process Blender readback and selected-object STL re-export."""

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
    """Preserve native while verifying saved shape, no rendering."""
    obj = bpy.data.objects["A321_R3_RESEARCH_NOT_VALIDATED"]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    output = ROOT / "artifacts/r3-reopened.stl"
    if output.exists():
        raise RuntimeError("READBACK_EXISTS")
    bpy.ops.wm.stl_export(filepath=str(output), export_selected_objects=True)
    (ROOT / "evidence/r3-readback.json").write_text(
        json.dumps(
            {
                "surface": measure(*arrays(obj)),
                "native_saved": False,
                "gpu_compute": False,
            },
            indent=2,
        ),
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
