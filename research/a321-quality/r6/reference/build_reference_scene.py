#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: GPL-2.0-or-later
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
# How to run: blender.exe -b --factory-startup --python build_reference_scene.py --python-exit-code 1 -- \
#   --repo <repo root> --pages-dir <scratch page renders> --reference reference-dimensions.json --out-dir <scratch out>
# Independently authored separate Blender adapter. No GPL implementation consulted.
"""Place R3 and R5-C against the official A321 general-dimension sheets and render overlays.

The page renders (Airbus raster) are read from --pages-dir at run time; the .blend and the
overlay PNGs are written to --out-dir. Nothing from the sheets is written into the repository.
Metres throughout; model axes are x nose-to-tail, y span, z up. Cycles on the CPU, emission
only, so no light, no GPU. The sheets are drawn "related to attitude and weight": alignment
is on the nose and centreline (top, side) and on the ground line (side, front).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

R3 = "research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl"
R5C = "research/a321-quality/models/A321_AIRFRAME_REBUILD_R5_C.stl"
PAGE_W_PT, PAGE_H_PT = 612.0, 791.0
STL_DTYPE = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--pages-dir", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--samples", type=int, default=16)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return ap.parse_args(argv)


def read_binary_stl(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    count = int(np.frombuffer(raw, "<u4", 1, 80)[0])
    if len(raw) != 84 + 50 * count:
        raise SystemExit(f"{path.name}: not a binary STL of the declared size")
    return np.frombuffer(raw, STL_DTYPE, count, 84)["v"].astype(np.float32)


def make_model(name: str, path: Path) -> bpy.types.Object:
    tris = read_binary_stl(path)
    n = len(tris)
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(n * 3)
    mesh.vertices.foreach_set("co", tris.reshape(-1))
    mesh.loops.add(n * 3)
    mesh.loops.foreach_set("vertex_index", np.arange(n * 3, dtype=np.int32))
    mesh.polygons.add(n)
    mesh.polygons.foreach_set("loop_start", np.arange(0, n * 3, 3, dtype=np.int32))
    mesh.polygons.foreach_set("loop_total", np.full(n, 3, dtype=np.int32))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def emission_material(name: str, rgb: tuple[float, float, float]) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out, em = nt.nodes.new("ShaderNodeOutputMaterial"), nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def image_material(name: str, png: Path) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out, em, tex = (nt.nodes.new(t) for t in ("ShaderNodeOutputMaterial", "ShaderNodeEmission", "ShaderNodeTexImage"))
    tex.image = bpy.data.images.load(str(png), check_existing=True)
    tex.interpolation = "Linear"
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def image_plane(name: str, png: Path, scale_pt_per_m: float, anchor_pt: tuple[float, float], anchor_m: tuple[float, float],
                matrix_basis: Matrix) -> bpy.types.Object:
    """Plane showing a whole page, in metres; anchor_pt (page point) lands on anchor_m (u, v) in the plane's own axes."""
    w, h = PAGE_W_PT / scale_pt_per_m, PAGE_H_PT / scale_pt_per_m
    verts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new(name="UVMap")
    for loop, (u, v) in zip(mesh.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[loop.index].uv = (u, v)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(image_material(name + "_mat", png))
    # page centre in plane coordinates: x grows right, y grows up; page y_pt grows down
    cu = anchor_m[0] + (PAGE_W_PT / 2 - anchor_pt[0]) / scale_pt_per_m
    cv = anchor_m[1] - (PAGE_H_PT / 2 - anchor_pt[1]) / scale_pt_per_m
    obj.matrix_world = matrix_basis @ Matrix.Translation((cu, cv, 0.0))
    return obj


def basis(ux, uy, uz, offset) -> Matrix:
    m = Matrix([[ux[0], uy[0], uz[0], offset[0]], [ux[1], uy[1], uz[1], offset[1]], [ux[2], uy[2], uz[2], offset[2]], [0, 0, 0, 1]])
    return m


def setup_render(scene: bpy.types.Scene, width: int, height: int, samples: int) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.display_settings.display_device = "sRGB"


def make_camera(name: str, location, euler_deg, ortho_scale: float) -> bpy.types.Object:
    cam = bpy.data.cameras.new(name)
    cam.type = "ORTHO"
    cam.ortho_scale = ortho_scale
    cam.clip_start, cam.clip_end = 0.1, 400.0
    obj = bpy.data.objects.new(name, cam)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = tuple(math.radians(a) for a in euler_deg)
    return obj


def render_to(scene: bpy.types.Scene, cam: bpy.types.Object, path: Path, transparent: bool) -> None:
    scene.camera = cam
    scene.render.film_transparent = transparent
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def load_raw(path: Path) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    arr = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return arr


def save_raw(arr: np.ndarray, path: Path) -> None:
    h, w, _ = arr.shape
    img = bpy.data.images.new("overlay_tmp", w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(arr.reshape(-1))
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def edge_of(mask: np.ndarray) -> np.ndarray:
    inner = mask.copy()
    inner[1:-1, 1:-1] = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
    return mask & ~inner


def composite(drawing: np.ndarray, silhouette: np.ndarray, rgb: tuple[float, float, float]) -> np.ndarray:
    mask = silhouette[..., 3] > 0.5
    out = drawing.copy()
    col = np.array(rgb, np.float32)
    out[mask, :3] = out[mask, :3] * 0.62 + col * 0.38
    thick = edge_of(mask)
    for _ in range(1):
        thick = thick | np.roll(thick, 1, 0) | np.roll(thick, 1, 1)
    out[thick & mask, :3] = col * 0.8
    out[..., 3] = 1.0
    return out


def main() -> None:
    t0 = time.time()
    args = parse_args()
    ref = json.loads(args.reference.read_text(encoding="utf-8"))
    sc = ref["scale"]
    s_top = sc["top_view_page74"]["pt_per_m"]
    nose_top, cl_top = sc["top_view_page74"]["nose_x_pt"], sc["top_view_page74"]["centreline_y_pt"]
    side = ref["drawn_planform_and_profile"]["side"]
    front = ref["drawn_planform_and_profile"]["front"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    models = {"R3": make_model("R3", args.repo / R3), "R5C": make_model("R5C", args.repo / R5C)}
    colours = {"R3": (0.05, 0.25, 1.0), "R5C": (1.0, 0.15, 0.05)}
    for k, o in models.items():
        o.data.materials.append(emission_material(k + "_sil", (1, 1, 1)))
    pages = {pn: args.pages_dir / f"page-{pn:03d}-400dpi.png" for pn in (73, 74)}
    # top view: plane in XY below the aircraft, image right = +x, image up = +y
    top_plane = image_plane("plane_top", pages[74], s_top, (nose_top, cl_top), (0.0, 0.0), basis((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, -20)))
    # side view: plane in XZ behind the aircraft (y = +20), seen from -y; image right = +x, up = +z
    side_plane = image_plane("plane_side", pages[73], side["scale_pt_per_m"], (side["nose_x_pt"], side["ground_y_pt"]), (0.0, 0.0),
                             basis((1, 0, 0), (0, 0, 1), (0, -1, 0), (0, 20, 0)))
    # front view: plane in YZ beyond the tail (x = +60), seen from -x; image right = -y, up = +z
    front_plane = image_plane("plane_front", pages[73], front["scale_pt_per_m"], (front["centre_x_pt"], front["ground_y_pt"]), (0.0, 0.0),
                              basis((0, -1, 0), (0, 0, 1), (-1, 0, 0), (60, 0, 0)))
    planes = {"top": top_plane, "side": side_plane, "front": front_plane}
    w = args.width
    views = {  # name: (camera location, euler deg, ortho scale m, height px)
        "top": ((23.5, 0.0, 100.0), (0, 0, 0), 54.0, int(w * 0.80)),
        "side": ((22.25, -100.0, 6.5), (90, 0, 0), 52.0, int(w * 0.50)),
        "front": ((-100.0, 0.0, 7.0), (90, 0, -90), 46.0, int(w * 0.50)),
    }
    manifest = {"images": {}, "blend": None}
    for view, (loc, eul, ortho, h) in views.items():
        setup_render(scene, w, h, args.samples)
        cam = make_camera("cam_" + view, loc, eul, ortho)
        for p in planes.values():
            p.hide_render = True
        for o in models.values():
            o.hide_render = True
        planes[view].hide_render = False
        drawing_png = args.out_dir / f"pass_{view}_drawing.png"
        render_to(scene, cam, drawing_png, transparent=False)
        planes[view].hide_render = True
        drawing = load_raw(drawing_png)
        for name, obj in models.items():
            for o in models.values():
                o.hide_render = True
            obj.hide_render = False
            sil_png = args.out_dir / f"pass_{view}_{name}_silhouette.png"
            render_to(scene, cam, sil_png, transparent=True)
            out = args.out_dir / f"overlay_{view}_{name}.png"
            save_raw(composite(drawing, load_raw(sil_png), colours[name]), out)
            manifest["images"][f"{view}_{name}"] = str(out)
    for p in planes.values():
        p.hide_render = False
    for o in models.values():
        o.hide_render = False
    blend = args.out_dir / "a321_reference_scene.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    manifest["blend"] = str(blend)
    manifest["wall_time_s"] = round(time.time() - t0, 1)
    (args.out_dir / "scene-manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("scene built", manifest["wall_time_s"], "s")


if __name__ == "__main__":
    main()
