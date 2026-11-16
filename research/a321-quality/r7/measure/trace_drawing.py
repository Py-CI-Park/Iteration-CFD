#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pymupdf", "shapely"]
# ///
# LICENCE NOTE: this program imports PyMuPDF (AGPL-3.0 or commercial licence). It is a SEPARATE trace tool.
# No other R7 script imports PyMuPDF; the rest of the pipeline reads only the JSON this tool writes.
# How to run: uv run --no-project trace_drawing.py --pdf <A321 AC AMP pdf> --raw-out <.worktmp/r7-trace/raw-trace.json> --meta-out trace-meta.json
"""Trace the fuselage outline from the vector paths of the official A321 general-dimension sheets.

Page 74 (1-based): top view. Page 73: side view. The black outline of the fuselage is drawn as many separate
stroked paths (lines and cubic Beziers, 0.4543 pt wide); the yellow fill is a union silhouette that also holds the
wing, the tail planes and the nacelle. The fuselage outline is therefore taken from the STROKES, which continue
under the wing and the tail planes where the fill edge does not show the fuselage.

How the fuselage strokes are identified (see select_paths): seed at the long straight constant-section lines and
follow endpoint-connected stroked paths (tolerance 0.08 pt); stop at branches into windows and cockpit frames, which
are excluded by drawing index. The raw polylines are Airbus copyright and are written only to the git-excluded
raw output; the committable metadata holds drawing indices, counts, gaps and the SHA-256 of the raw file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pymupdf as fitz
from shapely.geometry import LinearRing, Point, Polygon

EXPECTED_SHA = "50ae7a11b9834cbb1b0f8b862fcb6e85aa7817e77596cd12903033e81456d40d"
BEZIER_STEPS = 64
JOIN_TOL = 0.08  # pt, endpoint matching between stroked paths
YELLOW = (1.0, 1.0, 0.800000011920929)

# Drawing indices (0-based, page.get_drawings() order) that make up the fuselage outline. Found by select_paths()
# from the seeds below; the window/cockpit branches of the side view are excluded in SIDE_EXCLUDE.
TOP_SEEDS = [324]
SIDE_SEEDS = [747, 388, 748, 389]
SIDE_EXCLUDE = {401, 394, 395, 396, 483, 484, 393}  # cockpit window frames branching off the nose outline
TOP_EXPECTED = [2, 26, 27, 28, 29, 53, 54, 55, 61, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 232, 234, 235, 323, 324]
SIDE_EXPECTED = [352, 361, 362, 363, 372, 373, 374, 378, 388, 389, 402, 403, 478, 479, 480, 481, 482, 485, 486, 747, 748]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def flatten_item(item: tuple) -> np.ndarray:
    """Points of one path item (line or cubic Bezier), first point included."""
    if item[0] == "l":
        return np.array([[item[1].x, item[1].y], [item[2].x, item[2].y]])
    if item[0] == "c":
        p = np.array([[q.x, q.y] for q in item[1:5]])
        t = np.linspace(0.0, 1.0, BEZIER_STEPS + 1)[:, None]
        return ((1 - t) ** 3) * p[0] + 3 * ((1 - t) ** 2) * t * p[1] + 3 * (1 - t) * t * t * p[2] + t**3 * p[3]
    raise ValueError(f"unsupported item {item[0]}")


def drawing_polyline(drawing: dict[str, Any]) -> np.ndarray:
    parts: list[np.ndarray] = []
    for item in drawing["items"]:
        pts = flatten_item(item)
        if parts and np.hypot(*(pts[0] - parts[-1][-1])) > JOIN_TOL:
            raise ValueError("discontinuous drawing")
        parts.append(pts if not parts else pts[1:])
    return np.vstack(parts)


def stroke_ends(drawing: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]] | None:
    items = drawing["items"]
    if any(it[0] not in ("l", "c") for it in items):
        return None
    first = items[0][1]
    last = items[-1][2] if items[-1][0] == "l" else items[-1][4]
    return (first.x, first.y), (last.x, last.y)


def select_paths(drawings: list, seeds: list[int], exclude: set[int]) -> list[int]:
    """Endpoint-connected stroked paths reachable from the seeds (documented selection rule)."""
    ends = {i: stroke_ends(d) for i, d in enumerate(drawings) if d["type"] == "s"}
    ends = {i: e for i, e in ends.items() if e is not None}

    def close(p: tuple[float, float], q: tuple[float, float]) -> bool:
        return abs(p[0] - q[0]) < JOIN_TOL and abs(p[1] - q[1]) < JOIN_TOL

    seen = set(seeds)
    todo = list(seeds)
    while todo:
        i = todo.pop()
        for end in ends[i]:
            for j, (a, b) in ends.items():
                if j not in seen and j not in exclude and (close(end, a) or close(end, b)):
                    seen.add(j)
                    todo.append(j)
    return sorted(seen)


def assemble_runs(drawings: list, indices: list[int]) -> list[dict[str, Any]]:
    """Order the selected paths into contiguous runs (open chains or one closed loop)."""
    polys = {i: drawing_polyline(drawings[i]) for i in indices}
    unused = set(indices)
    runs: list[dict[str, Any]] = []

    def match_end(point: np.ndarray, pool: set[int]) -> tuple[int, bool] | None:
        for j in sorted(pool):
            p = polys[j]
            if np.hypot(*(p[0] - point)) < JOIN_TOL:
                return j, False
            if np.hypot(*(p[-1] - point)) < JOIN_TOL:
                return j, True
        return None

    def open_ends(i: int) -> list[bool]:
        """[first end is open, last end is open] among all selected paths."""
        flags = []
        for end in (polys[i][0], polys[i][-1]):
            linked = any(j != i and (np.hypot(*(polys[j][0] - end)) < JOIN_TOL or np.hypot(*(polys[j][-1] - end)) < JOIN_TOL) for j in indices)
            flags.append(not linked)
        return flags

    while unused:
        start = next((i for i in sorted(unused) if any(open_ends(i))), min(unused))
        unused.discard(start)
        order = [start]
        pts = polys[start]
        first_open, last_open = open_ends(start)
        if last_open and not first_open:
            pts = pts[::-1]
        while True:
            hit = match_end(pts[-1], unused)
            if hit is None:
                break
            j, flip = hit
            unused.discard(j)
            order.append(j)
            seg = polys[j][::-1] if flip else polys[j]
            pts = np.vstack([pts, seg[1:]])
        closed = bool(np.hypot(*(pts[0] - pts[-1])) < JOIN_TOL)
        runs.append({"drawing_indices": order, "closed": closed, "points_pt": pts})
    return runs


def arrow_tip(drawing: dict[str, Any]) -> tuple[str, float, float] | None:
    rect = drawing["rect"]
    if max(rect.width, rect.height) >= 12:
        return None
    pts = {(round(q.x, 2), round(q.y, 2)) for it in drawing["items"] for q in it[1:] if hasattr(q, "x")}
    if rect.width > rect.height:
        n0 = sum(1 for x, _ in pts if abs(x - rect.x0) < 0.3)
        return ("H", (rect.y0 + rect.y1) / 2, rect.x0 if n0 == 1 else rect.x1)
    n0 = sum(1 for _, y in pts if abs(y - rect.y0) < 0.3)
    return ("V", (rect.x0 + rect.x1) / 2, rect.y0 if n0 == 1 else rect.y1)


def dimension_tips(page: fitz.Page) -> list[dict[str, Any]]:
    """Arrowhead tips of the dimension lines (axis, line coordinate, sorted tip pairs)."""
    arrows = []
    for d in page.get_drawings():
        if d["type"] == "f" and d["fill"] == (0.0, 0.0, 0.0) and 100 < d["rect"].y0 and d["rect"].y1 < 720:
            tip = arrow_tip(d)
            if tip:
                arrows.append(tip)
    out = []
    for axis in "HV":
        groups: list[list] = []
        for a in sorted((a for a in arrows if a[0] == axis), key=lambda a: a[1]):
            for g in groups:
                if abs(g[0][1] - a[1]) < 2.5:
                    g.append(a)
                    break
            else:
                groups.append([a])
        for g in groups:
            tips = sorted(t[2] for t in g)
            for k in range(0, len(tips) - 1, 2):
                out.append({"axis": axis, "line_pt": g[0][1], "tip_a_pt": tips[k], "tip_b_pt": tips[k + 1]})
    return out


def stroke_width(drawings: list, indices: list[int]) -> float:
    widths = {round(float(drawings[i]["width"]), 6) for i in indices}
    if len(widths) != 1:
        raise ValueError(f"mixed stroke widths {widths}")
    return widths.pop()


def fill_silhouettes(page: fitz.Page) -> list[np.ndarray]:
    out = []
    for d in page.get_drawings():
        if d["fill"] == YELLOW and len(d["items"]) > 100:
            sub: list[tuple[float, float]] = []
            last = None
            for it in d["items"]:
                if it[0] != "l":
                    continue
                a, b = it[1], it[2]
                if last is None or abs(a.x - last.x) > 0.05 or abs(a.y - last.y) > 0.05:
                    if len(sub) > 20:
                        out.append(np.array(sub))
                    sub = [(a.x, a.y)]
                sub.append((b.x, b.y))
                last = b
            if len(sub) > 20:
                out.append(np.array(sub))
    return out


def silhouette_agreement(chain: np.ndarray, fills: list[np.ndarray], keep: np.ndarray) -> dict[str, float]:
    """Distance (pt) from stroke-chain points flagged `keep` to the nearest fill boundary."""
    rings = [LinearRing(f) for f in fills if len(f) > 3]
    dist = np.array([min(r.distance(Point(p)) for r in rings) for p in chain[keep]])
    at = chain[keep][int(np.argmax(dist))]
    return {"n": int(keep.sum()), "max_pt": float(dist.max()), "max_at_xy_pt": [float(at[0]), float(at[1])], "rms_pt": float(np.sqrt(np.mean(dist**2))), "mean_pt": float(dist.mean())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--raw-out", type=Path, required=True)
    ap.add_argument("--meta-out", type=Path, required=True)
    args = ap.parse_args()
    if sha256_file(args.pdf) != EXPECTED_SHA:
        raise SystemExit("PDF_SHA_MISMATCH")
    doc = fitz.open(args.pdf)
    top_page, side_page = doc[73], doc[72]  # pages 74 and 73 (1-based)
    top_dr, side_dr = top_page.get_drawings(), side_page.get_drawings()

    top_idx = select_paths(top_dr, TOP_SEEDS, set())
    side_idx = select_paths(side_dr, SIDE_SEEDS, SIDE_EXCLUDE)
    if top_idx != TOP_EXPECTED or side_idx != SIDE_EXPECTED:
        raise SystemExit(f"SELECTION_CHANGED top={top_idx} side={side_idx}")
    top_runs, side_runs = assemble_runs(top_dr, top_idx), assemble_runs(side_dr, side_idx)

    tips74, tips73 = dimension_tips(top_page), dimension_tips(side_page)
    cl = next(d for d in top_dr if d["type"] == "s" and d.get("dashes") and "16.04" in str(d["dashes"]) and d["rect"].width > 300)
    centreline_y = float((cl["rect"].y0 + cl["rect"].y1) / 2)
    ground_y = next(float(d["rect"].y0) for d in side_dr if d["type"] == "s" and len(d["items"]) == 1 and d["rect"].width > 300 and abs(d["rect"].y0 - 265.6) < 0.2)

    raw = {
        "schema": "r7-raw-trace-v1",
        "note": "Airbus copyright; local use only; never commit. Units: PDF points, page y downward.",
        "pdf_sha256": EXPECTED_SHA,
        "bezier_steps": BEZIER_STEPS,
        "top_view_page74": {"runs": [{**{k: v for k, v in r.items() if k != "points_pt"}, "points_pt": r["points_pt"].tolist()} for r in top_runs],
                            "centreline_y_pt": centreline_y},
        "side_view_page73": {"runs": [{**{k: v for k, v in r.items() if k != "points_pt"}, "points_pt": r["points_pt"].tolist()} for r in side_runs],
                             "ground_y_pt": ground_y},
        "dimension_tips_page74": tips74,
        "dimension_tips_page73": tips73,
    }
    args.raw_out.parent.mkdir(parents=True, exist_ok=True)
    args.raw_out.write_text(json.dumps(raw), encoding="utf-8")
    raw_sha = sha256_file(args.raw_out)

    # agreement of the stroke centre line with the yellow fill edge where the fuselage is the silhouette
    top_chain = top_runs[0]["points_pt"]
    top_fill = fill_silhouettes(top_page)
    xs, ys = top_chain[:, 0], top_chain[:, 1]
    visible = (((xs < 271.0) | ((xs > 321.5) & (xs < 446.0))) & (np.abs(ys - centreline_y) > 4.0))
    side_pts = np.vstack([r["points_pt"] for r in side_runs])
    side_fill = fill_silhouettes(side_page)
    sx = side_pts[:, 0]
    sy = side_pts[:, 1]
    side_parts = {"crown_nose_to_x335pt": (sx < 335.0) & (sy < 240.0), "crown_aft_of_fin_x462_to_477pt": (sx > 462.0) & (sy < 232.0),
                  "belly_nose_to_x245pt": (sx < 245.0) & (sy > 240.0), "belly_x325_to_389pt": (sx > 325.0) & (sx < 389.0) & (sy > 240.0),
                  "belly_tail_upsweep_x440_to_477pt": (sx > 440.0) & (sy > 226.0)}
    agree = {"top_view_fuselage_visible": silhouette_agreement(top_chain, top_fill, visible),
             "side_view_parts": {k: silhouette_agreement(side_pts, side_fill, m) for k, m in side_parts.items() if m.any()}}

    meta = {
        "schema": "r7-trace-meta-v1",
        "pdf_sha256": EXPECTED_SHA,
        "raw_trace_file": "<worktree>/.worktmp/r7-trace/raw-trace.json (git-excluded, Airbus copyright)",
        "raw_trace_sha256": raw_sha,
        "raw_trace_bytes": args.raw_out.stat().st_size,
        "bezier_steps": BEZIER_STEPS,
        "stroke_width_pt_top": stroke_width(top_dr, top_idx),
        "stroke_width_pt_side": stroke_width(side_dr, side_idx),
        "top_view": {"page_1based": 74, "drawing_indices": top_idx,
                     "runs": [{"drawing_indices": r["drawing_indices"], "closed": r["closed"], "n_points": len(r["points_pt"])} for r in top_runs]},
        "side_view": {"page_1based": 73, "drawing_indices": side_idx, "excluded_branches": sorted(SIDE_EXCLUDE),
                      "runs": [{"drawing_indices": r["drawing_indices"], "closed": r["closed"], "n_points": len(r["points_pt"]),
                                "first_pt": r["points_pt"][0].tolist(), "last_pt": r["points_pt"][-1].tolist()} for r in side_runs]},
        "identification_rule": "stroked (black, 0.4543 pt) paths reachable from the long straight constant-section lines by endpoint "
                               "matching (0.08 pt); wing, tail plane, engine, gear, window, door and dimension paths are not "
                               "endpoint-connected to the outline except the excluded cockpit-window branches; selection is asserted "
                               "against the recorded index list on every run",
        "centreline_y_pt": centreline_y,
        "ground_line_y_pt": ground_y,
        "stroke_vs_fill_agreement_pt": agree,
        "dimension_tips_page74": tips74,
        "dimension_tips_page73": tips73,
    }
    args.meta_out.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps({"raw_sha256": raw_sha, "top_runs": meta["top_view"]["runs"], "side_runs": [(r["drawing_indices"], r["closed"]) for r in meta["side_view"]["runs"]], "agree": agree}, indent=1))


if __name__ == "__main__":
    main()
