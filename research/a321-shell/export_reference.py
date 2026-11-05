#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# How to run: Blender -b --disable-autoexec FROZEN.blend --python export_reference.py
"""Export exact world-coordinate reference triangles from pinned Blender native."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "a321-preflight"))
from prepare_surface import arrays


def main() -> None:
    """Freeze named visible source objects for deterministic CPU section reconstruction."""
    expected = "1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c"
    source = Path(bpy.data.filepath)
    with source.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != expected:
        raise RuntimeError("BASELINE_SHA_MISMATCH")
    out = ROOT / "artifacts/reference"
    out.mkdir(parents=True, exist_ok=False)
    groups: dict[str, list[bpy.types.Object]] = {
        k: [] for k in ("fuselage", "wing", "horizontal", "vertical")
    }
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.visible_get():
            continue
        name = obj.name
        if name.startswith("Fuselage_") and any(
            c.name == "01_Fuselage" for c in obj.users_collection
        ):
            groups["fuselage"].append(obj)
        if (
            "STARBOARD" in name
            and not name.startswith(
                ("Spoiler", "Flap_secondary", "Flap_track", "Sharklet")
            )
            and any(c.name == "07_Wings" for c in obj.users_collection)
        ):
            groups["wing"].append(obj)
        if name in ("Horizontal_stabilizer_STARBOARD", "Elevator_STARBOARD"):
            groups["horizontal"].append(obj)
        if name in ("Vertical_stabilizer", "Rudder"):
            groups["vertical"].append(obj)
    ledger = []
    for group, objects in groups.items():
        vertices, faces, offset = [], [], 0
        for obj in objects:
            v, f = arrays(obj)
            vertices.append(v)
            faces.append(f + offset)
            offset += len(v)
        v, f = np.concatenate(vertices), np.concatenate(faces)
        np.savez_compressed(out / f"{group}.npz", vertices=v, faces=f)
        ledger.append(
            {
                "group": group,
                "objects": [o.name for o in objects],
                "triangles": len(f),
                "bounds_m": [v.min(axis=0).tolist(), v.max(axis=0).tolist()],
            }
        )
    record = {
        "source_path": str(source),
        "source_sha256": digest,
        "source_bytes": source.stat().st_size,
        "blender": bpy.app.version_string,
        "axis": "X aft,Y starboard,Z up",
        "unit": "m",
        "groups": ledger,
        "gpu_compute": False,
    }
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/baseline.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    print(json.dumps(record))


if __name__ == "__main__":
    main()
