#!/usr/bin/env python
# SPDX-License-Identifier: GPL-2.0-or-later
# Independently authored regression adapter executed in separate Blender.
# No GPL implementation source consulted; see PROVENANCE.md.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: blender --background --factory-startup --disable-autoexec --python test_blender_guards.py
"""Exercise native custody guards with real Blender fixture files, not mocks."""

from __future__ import annotations
import hashlib
import json
import struct
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import blender_adapter as adapter
from binding import BindingRejected


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Each isolated fixture trips exactly one real native binding guard."""
    base = ROOT / "artifacts/native-guard-regressions"
    base.mkdir(exist_ok=False)
    results = []
    for kind in ("transform", "parent", "modifier", "changed_hash", "exclusive_lock"):
        case = base / kind
        source = case / "artifacts/rebuild-r5-a"
        source.mkdir(parents=True)
        evidence = case / "evidence"
        evidence.mkdir()
        vertices = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        faces = np.array([[0, 1, 2]])
        stl = source / "A321_AIRFRAME_REBUILD_R5_A.stl"
        stl.write_bytes(
            b" " * 80
            + struct.pack("<I", 1)
            + struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)
        )
        npz = source / "shell.npz"
        np.savez_compressed(npz, vertices=vertices, faces=faces)
        (evidence / "rebuild-r5-a.json").write_text(
            json.dumps(
                {"stl_sha256": sha(stl), "npz_sha256": sha(npz), "input_sha256": {}}
            )
        )
        adapter.ROOT = case
        if kind == "exclusive_lock":
            (source / "A321_AIRFRAME_REBUILD_R5_A.blend.lock").write_text(
                "Competing creation reservation"
            )
            sys.argv = ["guard"]
            try:
                adapter.main()
            except FileExistsError as exc:
                if ".blend.lock" not in str(exc):
                    raise
                results.append({"case": kind, "status": "PASS_REJECTED_REAL_LOCK"})
            else:
                raise AssertionError("EXCLUSIVE_LOCK_NOT_REJECTED")
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new("fixture")
        mesh.from_pydata(vertices.tolist(), [], faces.tolist())
        obj = bpy.data.objects.new("R5_A_GLOBAL_STATION_DRAFT_NOT_OEM_HOLD", mesh)
        bpy.context.scene.collection.objects.link(obj)
        if kind == "transform":
            obj.location.x = 1
        if kind == "parent":
            parent = bpy.data.objects.new("parent", None)
            bpy.context.scene.collection.objects.link(parent)
            obj.parent = parent
        if kind == "modifier":
            obj.modifiers.new("fixture", "DECIMATE")
        native = source / "A321_AIRFRAME_REBUILD_R5_A.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(native))
        (evidence / "blender-r5-a-save.json").write_text(
            json.dumps(
                {"native_sha256": "0" * 64 if kind == "changed_hash" else sha(native)}
            )
        )
        sys.argv = ["guard", "--verify-hardened"]
        try:
            adapter.main()
        except BindingRejected as exc:
            expected = (
                "NATIVE_CHANGED_SINCE_SAVE"
                if kind == "changed_hash"
                else "NATIVE_WORLD_TRANSFORM_PARENT_OR_MODIFIER"
            )
            if str(exc) != expected:
                raise
            results.append(
                {
                    "case": kind,
                    "status": "PASS_REJECTED_REAL_NATIVE",
                    "reason": str(exc),
                }
            )
        else:
            raise AssertionError(f"GUARD_NOT_REJECTED:{kind}")
    receipt = ROOT / "evidence/blender-native-guard-regressions.json"
    with receipt.open("x", encoding="utf8") as stream:
        stream.write(
            json.dumps(
                {
                    "passed": len(results),
                    "results": results,
                    "scope": "real isolated mini triangle Blender fixtures, no aircraft solve",
                },
                indent=2,
            )
            + "\n"
        )
    print(json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
