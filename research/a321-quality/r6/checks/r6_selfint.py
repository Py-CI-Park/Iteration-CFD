# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""R6 gate suite: three self-intersection checkers and their comparison.

(a) the existing independent locator (rtree + exact-ish tri-tri, shares-a-vertex pairs excluded),
(b) PyMeshLab per-face selection in a separate process (r6_meshlab_worker.py),
(c) OpenFOAM v1912 surfaceCheck in WSL on a copy of the STL (optional; "not run" is recorded as null).
The checkers differ in scope; a disagreement is reported as a scope difference, never as a false positive.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from r6_mesh import GateError, sha256_file, write_stl

HERE = Path(__file__).resolve().parent
LOCATOR_PATH = HERE.parents[1] / "m3" / "c15-map" / "locate_intersections.py"
WORKER_PATH = HERE / "r6_meshlab_worker.py"
SURFACECHECK_SCRIPT = HERE / "run_surfacecheck_r6.sh"
IntArray = NDArray[np.int64]


def load_locator():
    """Import the existing locator module by path (reused, not copied)."""
    spec = importlib.util.spec_from_file_location("c15_locate_intersections", LOCATOR_PATH)
    if spec is None or spec.loader is None:
        raise GateError(f"Cannot import locator: {LOCATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locator_check(triangles: NDArray[np.float64]) -> dict:
    """Checker (a). Face ids are zero-based binary-STL facet order. Locator progress output is captured."""
    locator = load_locator()
    started = time.perf_counter()
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        pairs, geometries, tested = locator.scan(triangles)
        groups = locator.cluster(pairs, geometries)
    faces = sorted({face for pair in pairs for face in pair})
    return {"checker": "locate_intersections.scan (rtree AABB + plane/interval + coplanar clip; any shared exact vertex excluded)",
            "epsilon_m": locator.EPS, "narrow_phase_pairs": int(tested), "intersecting_pairs": len(pairs),
            "clusters": len(groups), "faces_involved": len(faces), "face_ids": faces,
            "wall_seconds": time.perf_counter() - started}


def meshlab_check(stl: Path, out_json: Path) -> dict:
    """Checker (b), run in its own process with the current interpreter. Fails loudly if pymeshlab is absent."""
    cmd = [sys.executable, str(WORKER_PATH), str(stl), str(out_json)]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=HERE)
    if done.returncode != 0:
        raise GateError(f"PyMeshLab worker failed ({done.returncode}): {done.stderr[-2000:]}")
    return json.loads(out_json.read_text(encoding="utf-8"))


def meshlab_check_triangles(triangles: NDArray[np.float64]) -> dict:
    """Checker (b) on in-memory triangles (tests): writes a temporary STL first."""
    with tempfile.TemporaryDirectory() as tmp:
        stl = Path(tmp) / "case.stl"
        write_stl(stl, triangles)
        return meshlab_check(stl, Path(tmp) / "result.json")


def to_wsl_path(path: Path) -> str:
    """D:\\a\\b -> /mnt/d/a/b."""
    drive, rest = path.resolve().drive, path.resolve().as_posix()[2:]
    return f"/mnt/{drive[0].lower()}{rest}"


SURFACECHECK_PATTERNS = {
    "triangles": r"Triangles\s*:\s*(\d+)", "vertices": r"Vertices\s*:\s*(\d+)",
    "quality_min": r"min\s+(\S+)\s+for triangle\s+(\d+)", "quality_max": r"max\s+(\S+)\s+for triangle\s+(\d+)",
    "unconnected_parts": r"Number of unconnected parts\s*:\s*(\d+)", "zones": r"Number of zones[^:]*:\s*(\d+)",
    "self_intersecting": r"self-intersecting at (\d+) locations",
}


def parse_surfacecheck(text: str) -> dict:
    """Parse a surfaceCheck result.log: counts, min quality, closure, End/FATAL, wall time."""
    out: dict = {"end_reached": bool(re.search(r"^End\s*$", text, re.M)), "fatal": "FOAM FATAL" in text,
                 "nonzero_exit_marker": "SURFACECHECK_EXIT_NONZERO" in text}
    for key in ("triangles", "vertices", "unconnected_parts", "zones"):
        match = re.search(SURFACECHECK_PATTERNS[key], text)
        out[key] = int(match.group(1)) if match else None
    for key in ("quality_min", "quality_max"):
        match = re.search(SURFACECHECK_PATTERNS[key], text)
        out[key] = {"value": float(match.group(1)), "triangle": int(match.group(2))} if match else None
    match = re.search(SURFACECHECK_PATTERNS["self_intersecting"], text)
    if match:
        out["self_intersection_locations"] = int(match.group(1))
    elif "Surface is not self-intersecting" in text:
        out["self_intersection_locations"] = 0
    else:
        out["self_intersection_locations"] = None
    out["illegal_triangles"] = "Surface has no illegal triangles" not in text
    out["closed"] = "Surface is closed" in text
    real = re.search(r"^real\s+([\d.]+)", text, re.M)
    out["checker_real_seconds"] = float(real.group(1)) if real else None
    return out


def surfacecheck_run(name: str, stl: Path, threshold: int = 0) -> dict:
    """Checker (c): run the WSL wrapper (copy of the STL in a fresh mktemp attempt dir), parse, drop the copy."""
    original_sha = sha256_file(stl)
    started = time.perf_counter()
    cmd = ["wsl", "-e", "bash", to_wsl_path(SURFACECHECK_SCRIPT), name, to_wsl_path(stl), str(threshold)]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)
    wall = time.perf_counter() - started
    attempt = next((line for line in reversed(done.stdout.splitlines()) if line.startswith("/mnt/")), None)
    if done.returncode != 0 or attempt is None:
        raise GateError(f"surfaceCheck wrapper failed ({done.returncode}): {done.stderr[-1500:]}")
    attempt_dir = HERE / "attempts" / Path(attempt).name
    result = parse_surfacecheck((attempt_dir / "result.log").read_text(encoding="utf-8", errors="replace"))
    obj = attempt_dir / "selfInterPoints.obj"
    result["obj_points_m"] = obj_points(obj.read_text(encoding="utf-8")).tolist() if obj.exists() else []
    copy_sha = (attempt_dir / "copy.sha256").read_text().split()[0]
    (attempt_dir / "input.stl").unlink()
    result.update({"checker": "OpenFOAM v1912 surfaceCheck -checkSelfIntersection (WSL, copy of the STL)",
                   "attempt_dir": attempt_dir.name, "copy_sha256_equals_original": copy_sha == original_sha,
                   "wrapper_wall_seconds": wall, "input_copy_deleted_after_sha_record": True})
    return result


def obj_points(text: str) -> NDArray[np.float64]:
    """Vertex rows ('v x y z') of a surfaceCheck selfInterPoints.obj."""
    rows = [list(map(float, line.split()[1:4])) for line in text.splitlines() if line.startswith("v ")]
    return np.array(rows, dtype=np.float64).reshape(-1, 3)


def points_covered_by_faces(points: NDArray[np.float64], triangles: NDArray[np.float64], face_ids: list[int],
                            radius: float = 1e-4) -> int:
    """How many surfaceCheck OBJ points lie within `radius` (AABB test) of a face in `face_ids`.

    The OBJ prints 6 significant digits, so a 100 um radius absorbs text rounding at x ~ 30 m. It is a
    location-matching radius, not an intersection tolerance.
    """
    from rtree import index

    if not face_ids or len(points) == 0:
        return 0
    chosen = triangles[np.asarray(face_ids)]
    boxes = np.column_stack((chosen.min(axis=1) - radius, chosen.max(axis=1) + radius))
    tree = index.Index(((i, box, None) for i, box in enumerate(boxes)), properties=index.Property(dimension=3))
    return int(sum(1 for p in points if next(tree.intersection(np.concatenate([p, p])), None) is not None))


def agreement(locator: dict | None, meshlab: dict | None, surfacecheck: dict | None, face_count: int) -> dict:
    """Compare the checkers: counts side by side and face-set overlap between (a) and (b)."""
    out: dict = {"locator_faces": None if locator is None else locator["faces_involved"],
                 "meshlab_faces": None if meshlab is None else meshlab["selected_faces"],
                 "surfacecheck_locations": None if surfacecheck is None else surfacecheck["self_intersection_locations"]}
    if locator is not None and meshlab is not None:
        a, b = set(locator["face_ids"]), set(meshlab["selected_face_ids"])
        out.update({"faces_in_both": len(a & b), "faces_only_locator": len(a - b), "faces_only_meshlab": len(b - a)})
    zero = [v == 0 for v in (out["locator_faces"], out["meshlab_faces"], out["surfacecheck_locations"]) if v is not None]
    out["all_run_checkers_report_zero"] = bool(zero) and all(zero)
    out["all_run_checkers_report_nonzero"] = bool(zero) and not any(zero)
    out["note"] = ("scope differs: the locator skips any pair sharing an exact vertex; PyMeshLab selects faces, surfaceCheck "
                   "counts locations; a count mismatch is not a false-positive finding")
    return out
