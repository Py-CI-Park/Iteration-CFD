#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
# ─── How to run ───
# Blender -b --disable-autoexec FROZEN.blend --python prepare_surface.py -- OUT VOXEL_METRES
# Blender supplies bpy/bmesh/numpy. CPU-only, no render and no CUDA context.
# Original research adapter; no GPL source consulted or copied.
"""Extract a documented airframe subset and make a voxel-remesh trial on a copy."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from custody import trial_directory
from surface_metrics import measure


def selected(obj: bpy.types.Object) -> bool:
    """Select visible airframe skins; omit engines, gear and decorative seams."""
    groups = {c.name for c in obj.users_collection}
    primary = bool(groups & {"01_Fuselage", "07_Wings", "08_Tail"})
    fairing = obj.name.startswith("Wing_body_fairing")
    panels = "Windows_Doors" in groups and any(
        token in obj.name.lower()
        for token in ("panel", "glass", "glazing", "windshield", "windscreen")
    )
    excluded = obj.name.startswith(
        ("Spoiler_", "Spoiler_seam_", "Sharklet_LE_", "Flap_secondary_slot_")
    )
    return (
        obj.type == "MESH"
        and obj.visible_get()
        and (primary or fairing or panels)
        and not excluded
    )


def arrays(obj: bpy.types.Object):
    """Read world vertices and tessellated triangles from one mesh object."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coords)
    local = coords.reshape(-1, 3)
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    vertices = local @ matrix[:3, :3].T + matrix[:3, 3]
    indices = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", indices)
    return vertices, indices.reshape(-1, 3).astype(np.int64)


def nearest_stats(points, tree: BVHTree) -> dict[str, float]:
    """Deterministic sampled point-to-triangle distances, never a Hausdorff bound."""
    take = np.linspace(0, len(points) - 1, min(12000, len(points)), dtype=np.int64)
    distances = [tree.find_nearest(tuple(points[i]))[3] for i in take]
    return {
        "samples": len(take),
        "p50_m": float(np.percentile(distances, 50)),
        "p95_m": float(np.percentile(distances, 95)),
        "p99_m": float(np.percentile(distances, 99)),
        "max_sample_m": float(max(distances)),
    }


def main() -> None:
    """Write exact extraction, a remeshed native copy, and independent export inputs."""
    args = sys.argv[sys.argv.index("--") + 1 :]
    root, voxel = trial_directory(Path(args[0])), float(args[1])
    source = bpy.data.filepath
    originals = [o for o in bpy.data.objects if selected(o)]
    objects = []
    verts_all, faces_all, offset, rows = [], [], 0, []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in originals:
        evaluated = obj.evaluated_get(deps)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=deps)
        copy = bpy.data.objects.new(obj.name, mesh)
        copy.matrix_world = obj.matrix_world.copy()
        bpy.context.scene.collection.objects.link(copy)
        v, f = arrays(copy)
        metrics = measure(v, f)
        rows.append(
            {
                "name": obj.name,
                "collections": [c.name for c in obj.users_collection],
                "vertex_start": offset,
                "vertex_end": offset + len(v),
                **metrics,
            }
        )
        verts_all.append(v)
        faces_all.append(f + offset)
        offset += len(v)
        objects.append(copy)
    vertices, faces = np.concatenate(verts_all), np.concatenate(faces_all)
    # Coordinate welding is only for topology measurement; extraction coordinates stay exact.
    welded, inverse = np.unique(vertices, axis=0, return_inverse=True)
    exact = measure(welded, inverse[faces])
    source_tree = BVHTree.FromPolygons(
        vertices.tolist(), faces.tolist(), all_triangles=True
    )
    np.savez_compressed(root / "source-surface.npz", vertices=vertices, faces=faces)
    for obj in list(bpy.data.objects):
        if obj not in objects:
            bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    merged = bpy.context.object
    merged.name = "A321_EXTRACTED_AIRFRAME_ENGINES_GEAR_OMITTED"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(root / "extracted.blend"))
    bpy.ops.wm.stl_export(
        filepath=str(root / "extracted.stl"), export_selected_objects=True
    )
    modifier = merged.modifiers.new("CPU_VOXEL_TRIAL", "REMESH")
    modifier.mode = "VOXEL"
    modifier.voxel_size = voxel
    modifier.adaptivity = 0.0
    modifier.use_remove_disconnected = False
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    merged.name = f"A321_SIMPLIFIED_VOXEL_{voxel:.3f}m_NOT_VALIDATED"
    v, f = arrays(merged)
    metrics = measure(v, f)
    trial_tree = BVHTree.FromPolygons(v.tolist(), f.tolist(), all_triangles=True)
    distances = {
        "source_to_trial": nearest_stats(vertices, trial_tree),
        "trial_to_source": nearest_stats(v, source_tree),
    }
    for row in rows:
        row["sampled_source_to_trial"] = nearest_stats(
            vertices[row["vertex_start"] : row["vertex_end"]], trial_tree
        )
    np.savez_compressed(root / "trial-surface.npz", vertices=v, faces=f)
    bpy.ops.wm.save_as_mainfile(filepath=str(root / "candidate.blend"))
    bpy.ops.wm.stl_export(
        filepath=str(root / "candidate.stl"), export_selected_objects=True
    )
    report = {
        "source": source,
        "voxel_m": voxel,
        "selected_objects": rows,
        "source_exact_welded": exact,
        "trial": metrics,
        "sampled_deviation": distances,
        "omissions": [
            "engines and pylons",
            "landing gear",
            "interior",
            "decorative seams",
            "secondary flap slots",
            "zero-thickness spoiler panels",
        ],
        "self_intersections": "UNMEASURED",
        "engineering_status": "NOT_VALIDATED",
        "gpu_compute_used": False,
        "source_native_overwritten": False,
    }
    (root / "preparation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"source": exact, "trial": metrics, "deviation": distances}))


if __name__ == "__main__":
    main()
