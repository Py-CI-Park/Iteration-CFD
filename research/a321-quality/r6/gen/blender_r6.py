#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run (three separate Blender processes):
#   blender.exe -b --factory-startup --disable-autoexec --python blender_r6.py --python-exit-code 1 -- --build  --tag r6-a --npz-dir D --out-dir O
#   blender.exe -b --factory-startup --disable-autoexec --python blender_r6.py --python-exit-code 1 -- --verify --npz-dir D --out-dir O
#   blender.exe -b --factory-startup --disable-autoexec --python blender_r6.py --python-exit-code 1 -- --render --npz-dir D --out-dir O --fig-dir F
# Independently authored separate Blender adapter. No GPL implementation consulted.
"""Build the four R6 mesh objects from npz arrays, save .blend, export STLs; verify in a fresh process; render.

No boolean, remesh, decimate or merge-by-distance is used on the candidate objects. Renders happen in a
separate process on unsaved temporary copies (wireframe close-ups use a Wireframe modifier on a cropped copy).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

NAMES = ("fuselage", "wing", "horizontal", "vertical")
CONTRACT = "r6-geometry-contract-02"
TAG = "r6-a"
BLEND = "r6-a.blend"
STL_DTYPE = np.dtype([("normal", "<f4", (3,)), ("tri", "<f4", (3, 3)), ("attr", "<u2")])


def parse_args() -> dict:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out: dict = {"mode": None}
    it = iter(argv)
    for a in it:
        if a in ("--build", "--verify", "--render"):
            out["mode"] = a[2:]
        elif a == "--tag":
            out["tag"] = next(it)
        elif a in ("--npz-dir", "--out-dir", "--fig-dir"):
            out[a[2:].replace("-", "_")] = Path(next(it))
    return out


def load_npz(npz_dir: Path, name: str) -> tuple[np.ndarray, np.ndarray]:
    with np.load(npz_dir / f"{name}.npz") as data:
        return data["vertices"].astype(np.float32), data["faces"].astype(np.int64)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_object(name: str, vertices: np.ndarray, faces: np.ndarray) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj["r6_contract"] = CONTRACT
    obj["r6_candidate"] = TAG
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_arrays(obj: bpy.types.Object) -> tuple[np.ndarray, np.ndarray]:
    """World-space vertex coordinates (float32 as stored) and triangle vertex indices of an object."""
    mesh = obj.data
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(obj.matrix_world, dtype=np.float64)
    world = (co.astype(np.float64) @ mw[:3, :3].T + mw[:3, 3]).astype(np.float32)
    loops = np.empty(len(mesh.loops), dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", loops)
    sizes = np.array([p.loop_total for p in mesh.polygons])
    if not np.all(sizes == 3):
        raise RuntimeError("NON_TRIANGLE_POLYGON")
    return world, loops.reshape(-1, 3)


def read_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    count = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + 50 * count:
        raise RuntimeError(f"BAD_STL_SIZE {path}")
    return np.frombuffer(data, dtype=STL_DTYPE, count=count, offset=84)["tri"].copy()


def build(args: dict) -> None:
    out: Path = args["out_dir"]
    out.mkdir(parents=True, exist_ok=True)
    clear_scene()
    objs = {}
    for name in NAMES:
        vertices, faces = load_npz(args["npz_dir"], name)
        objs[name] = make_object(name, vertices, faces)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / BLEND))
    for name, obj in objs.items():
        if len(obj.modifiers) or obj.parent is not None:
            raise RuntimeError("MODIFIER_OR_PARENT")
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.wm.stl_export(filepath=str(out / f"{name}.stl"), export_selected_objects=True, ascii_format=False,
                              apply_modifiers=False, global_scale=1.0, forward_axis="Y", up_axis="Z")
    print("BUILD_OK", {n: (len(o.data.vertices), len(o.data.polygons)) for n, o in objs.items()}, bpy.app.version_string)


def verify(args: dict) -> None:
    out: Path = args["out_dir"]
    bpy.ops.wm.open_mainfile(filepath=str(out / BLEND), load_ui=False, use_scripts=False)
    report = {"blender": bpy.app.version_string, "objects": {}}
    for name in NAMES:
        obj = bpy.data.objects[name]
        world, tris = mesh_arrays(obj)
        vertices, faces = load_npz(args["npz_dir"], name)
        stl = read_stl(out / f"{name}.stl")
        blender_tris = world[tris]
        item = {
            "custom_property": obj.get("r6_contract"),
            "modifiers": len(obj.modifiers), "parent": obj.parent is not None,
            "matrix_world_identity": bool(np.array_equal(np.array(obj.matrix_world), np.eye(4))),
            "vertices": len(world), "triangles": len(tris), "stl_triangles": len(stl),
            "world_equals_npz": bool(np.array_equal(world, vertices)),
            "triangles_equal_npz": bool(np.array_equal(tris, faces)),
            "triangles_equal_stl_in_order": bool(np.array_equal(blender_tris, stl)),
        }
        if not item["triangles_equal_stl_in_order"]:
            key = lambda t: np.sort(t.reshape(len(t), -1).view([("", t.dtype)] * 9).ravel())  # noqa: E731
            item["triangles_equal_stl_as_set"] = bool(np.array_equal(key(blender_tris), key(stl)))
        report["objects"][name] = item
    ok = all(v["custom_property"] == CONTRACT and v["modifiers"] == 0 and not v["parent"] and v["matrix_world_identity"]
             and v["world_equals_npz"] and v["triangles_equal_npz"]
             and (v["triangles_equal_stl_in_order"] or v.get("triangles_equal_stl_as_set", False))
             and v["triangles"] == v["stl_triangles"] for v in report["objects"].values())
    report["status"] = "PASS_G7_NATIVE_BINDING" if ok else "FAIL_G7_NATIVE_BINDING"
    (out / "g7-readback.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(report["status"])
    if not ok:
        raise RuntimeError(report["status"])


def setup_render(width: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = width, int(width * 0.55)
    scene.render.image_settings.file_format = "PNG"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.92, 0.95, 1.0)
    scene.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(40), math.radians(20), math.radians(30))
    scene.collection.objects.link(sun)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    cam.data.type = "ORTHO"
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def material(color: tuple[float, float, float, float], wire: bool = False) -> bpy.types.Material:
    mat = bpy.data.materials.new("m")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.6
    if wire:
        bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.05, 1.0)
    return mat


def shoot(cam: bpy.types.Object, loc: tuple, rot_deg: tuple, scale: float, path: Path) -> None:
    cam.location = Vector(loc)
    cam.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    cam.data.ortho_scale = scale
    cam.data.clip_end = 1000.0
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def crop_wire(name: str, vertices: np.ndarray, faces: np.ndarray, lo: np.ndarray, hi: np.ndarray, thick: float):
    """Temporary cropped copy (faces inside the box) with a Wireframe modifier; never saved."""
    centroid = vertices[faces].mean(axis=1)
    keep = np.all((centroid >= lo) & (centroid <= hi), axis=1)
    if not keep.any():
        return None
    sub = faces[keep]
    used, inverse = np.unique(sub, return_inverse=True)
    obj = make_object(f"wire_{name}", vertices[used], inverse.reshape(-1, 3))
    mod = obj.modifiers.new("wire", "WIREFRAME")
    mod.thickness = thick
    mod.use_even_offset = False
    obj.data.materials.append(material((0, 0, 0, 1), wire=True))
    return obj


def render(args: dict) -> None:
    fig: Path = args["fig_dir"]
    fig.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args["out_dir"] / BLEND), load_ui=False, use_scripts=False)
    colors = {"fuselage": (0.75, 0.78, 0.82, 1), "wing": (0.35, 0.55, 0.85, 1), "horizontal": (0.85, 0.55, 0.3, 1), "vertical": (0.4, 0.75, 0.45, 1)}
    for name in NAMES:
        bpy.data.objects[name].data.materials.append(material(colors[name]))
    cam = setup_render(1600)
    cx, cz = 22.25, 4.0
    shoot(cam, (cx, 0, 100), (0, 0, 0), 48.0, fig / "ortho-top.png")
    shoot(cam, (cx, -100, cz), (90, 0, 0), 48.0, fig / "ortho-side.png")
    shoot(cam, (-100, 0, cz), (90, 0, 90), 40.0, fig / "ortho-front.png")
    for name in NAMES:
        bpy.data.objects[name].hide_render = True
    arrays = {n: load_npz(args["npz_dir"], n) for n in NAMES}
    spots = [("nose", "fuselage", (-0.1, -1.0, 3.0), (2.0, 1.0, 4.0), 3.0), ("tail", "fuselage", (43.5, -1.0, 4.0), (44.6, 1.0, 6.0), 1.6),
             ("wing-root", "wing", (16.0, -1.0, 2.5), (22.0, 1.0, 4.8), 7.0), ("wing-tip", "wing", (24.0, 14.5, 3.0), (26.5, 16.4, 4.8), 3.0),
             ("tail-vertical", "vertical", (41.5, -0.3, 11.0), (43.8, 0.3, 12.0), 3.0)]
    for label, name, lo, hi, scale in spots:
        v, f = arrays[name]
        lo_a, hi_a = np.array(lo), np.array(hi)
        obj = crop_wire(name, v, f, lo_a, hi_a, max(scale * 4e-4, 1e-4))
        if obj is None:
            continue
        mid = (lo_a + hi_a) / 2
        shoot(cam, (mid[0], mid[1] - 60, mid[2]), (90, 0, 0), scale, fig / f"wire-{label}-side.png")
        shoot(cam, (mid[0], mid[1], mid[2] + 60), (0, 0, 0), scale, fig / f"wire-{label}-top.png")
        bpy.data.objects.remove(obj)
    print("RENDER_OK")


def main() -> None:
    global TAG, BLEND
    args = parse_args()
    TAG = args.get("tag", "r6-a")
    BLEND = f"{TAG}.blend"
    {"build": build, "verify": verify, "render": render}[args["mode"]](args)


if __name__ == "__main__":
    main()
