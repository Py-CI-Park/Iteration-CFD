#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pymupdf", "shapely", "pillow"]
# ///
# How to run: uv run extract_drawing_dims.py --pdf <A321 AC AMP pdf> --out reference-dimensions.json
"""Measure the printed dimensions and the drawn planform of the official
A321 general-dimension sheets (PDF pages 73 and 74, 1-based).

Only our own measurements are written (numbers and a few key points). The
Airbus page renders stay in the scratch directory and are never copied to the
repository. The PDF is read from a path given on the command line; its SHA-256
is verified before use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import pymupdf as fitz  # PyMuPDF
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Polygon

EXPECTED_SHA = "50ae7a11b9834cbb1b0f8b862fcb6e85aa7817e77596cd12903033e81456d40d"
YELLOW = (1.0, 1.0, 0.800000011920929)
DPI = 400
FT_PER_M = 3.280839895

# Reading of each printed dimension (ours, not Airbus wording): measure, axis, confidence.
READING: dict[tuple[int, str], tuple[str, str]] = {
    (73, "4.14"): ("fuselage max height, crown line to belly line (side view)", "high"),
    (73, "5.87"): ("fin tip above the fuselage crown line (side view)", "high"),
    (73, "5.07"): ("nose to nose-gear axis, x (side view)", "medium"),
    (73, "16.90"): ("nose-gear axis to main-gear axis, x (side view)", "medium"),
    (73, "35.80"): ("overall span including sharklets (front view)", "high"),
    (73, "12.45"): ("horizontal tail span tip to tip (front view)", "high"),
    (73, "2.43"): ("sharklet height above the wing-tip base line (front view)", "medium"),
    (73, "3.79"): ("sharklet top above the lower wing-root reference line (front view)", "medium"),
    (73, "0.50"): ("nose-gear wheel spacing (front view)", "low"),
    (73, "7.59"): ("main-gear leg spacing, between gear axes (front view)", "medium"),
    (73, "8.97"): ("main-gear overall width over outer wheels (front view)", "medium"),
    (73, "0.93"): ("main-gear dual-wheel spacing (front view)", "low"),
    (74, "44.51"): ("overall length, nose to tail-cone tip (top view)", "high"),
    (74, "5.75"): ("engine axis lateral offset from centreline, y (top view)", "high"),
    (74, "6.07"): ("wing root chord at the fuselage side, x (top view)", "medium"),
    (74, "3.95"): ("fuselage max width (top view)", "high"),
    (74, "4.87"): ("spanwise station of an inboard trailing-edge flap-track fairing, y (top view)", "low"),
    (74, "8.30"): ("spanwise station of a mid trailing-edge flap-track fairing, y (top view)", "low"),
    (74, "11.91"): ("spanwise station of an outboard trailing-edge flap-track fairing, y (top view)", "low"),
    (74, "16.29"): ("half-span to the wing/sharklet break line, y (top view)", "high"),
    (74, "1.61"): ("lateral extent of the sharklet beyond the break line, y (top view)", "medium"),
    (74, "3.22"): ("junction leading edge to sharklet aft tip, x (top view); extension rules at the break-line LE and the aft tip", "medium"),
    (74, "1.64"): ("wing chord at the wing/sharklet junction (tip chord), x (top view); extension rules coincide with the break-line ends", "high"),
    (74, "27.72"): ("nose to the sharklet trailing tip, x (top view)", "medium"),
    (74, "15.40"): ("nose to the nacelle front, x (top view)", "high"),
    (74, "3.31"): ("horizontal tail root chord at the fuselage side, x (top view); both extension rules end at the fuselage side, not at the tip", "medium"),
    (74, "1.24"): ("horizontal tail tip chord, x (top view)", "medium"),
}


# Labels the nearest-pair rule mis-assigns (checked by eye on the 400 dpi render): page-74 tail dimensions.
FORCED: dict[str, tuple[float, float]] = {"3.31": (446.82, 473.72), "1.24": (474.4, 483.73)}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def arrow_tip(drawing: dict[str, Any]) -> tuple[str, float, float] | None:
    """Return (axis, line_coordinate, tip_coordinate) for a small black arrowhead."""
    rect = drawing["rect"]
    if max(rect.width, rect.height) >= 12:
        return None
    pts = {(round(q.x, 2), round(q.y, 2)) for it in drawing["items"] for q in it[1:] if hasattr(q, "x")}
    if rect.width > rect.height:
        n0 = sum(1 for x, _ in pts if abs(x - rect.x0) < 0.3)
        return ("H", (rect.y0 + rect.y1) / 2, rect.x0 if n0 == 1 else rect.x1)
    n0 = sum(1 for _, y in pts if abs(y - rect.y0) < 0.3)
    return ("V", (rect.x0 + rect.x1) / 2, rect.y0 if n0 == 1 else rect.y1)


def page_arrows_and_labels(page: fitz.Page) -> tuple[list, list]:
    arrows = []
    for d in page.get_drawings():
        if d["type"] == "f" and d["fill"] == (0.0, 0.0, 0.0) and 100 < d["rect"].y0 and d["rect"].y1 < 720:
            tip = arrow_tip(d)
            if tip:
                arrows.append(tip)
    words = page.get_text("words")
    labels = []
    for i, w in enumerate(words[:-1]):
        if re.fullmatch(r"\d+\.\d\d", w[4]) and words[i + 1][4] == "m":
            labels.append((w[4], (w[0] + words[i + 1][2]) / 2, (w[1] + w[3]) / 2))
    return arrows, labels


def dimension_pairs(arrows: list) -> list[dict[str, Any]]:
    """Group arrows by dimension line, then pair sorted tips two by two."""
    pairs: list[dict[str, Any]] = []
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
                pairs.append({"axis": axis, "line": g[0][1], "a": tips[k], "b": tips[k + 1]})
    return pairs


def assign_labels(pairs: list, labels: list) -> list[dict[str, Any]]:
    """Greedy unique assignment of each label to the nearest dimension pair."""
    cand = []
    for li, (_, lx, ly) in enumerate(labels):
        for pi, p in enumerate(pairs):
            mid = (p["a"] + p["b"]) / 2
            px, py = (mid, p["line"]) if p["axis"] == "H" else (p["line"], mid)
            cand.append((float(np.hypot(lx - px, ly - py)), li, pi))
    out: list[dict[str, Any]] = []
    for label, tips in FORCED.items():
        li = next((i for i, lab in enumerate(labels) if lab[0] == label), None)
        pi = next((i for i, p in enumerate(pairs) if abs(p["a"] - tips[0]) < 0.3 and abs(p["b"] - tips[1]) < 0.3), None)
        if li is not None and pi is not None:
            cand = [c for c in cand if c[1] != li and c[2] != pi]
            out.append({**pairs[pi], "label": label, "assign_dist_pt": -1.0})
    used_l: set[int] = {next(i for i, lab in enumerate(labels) if lab[0] == o["label"]) for o in out}
    used_p: set[int] = {i for i, p in enumerate(pairs) if any(p is o or (p["a"], p["b"], p["line"]) == (o["a"], o["b"], o["line"]) for o in out)}
    for dist, li, pi in sorted(cand):
        if li in used_l or pi in used_p:
            continue
        used_l.add(li)
        used_p.add(pi)
        out.append({**pairs[pi], "label": labels[li][0], "assign_dist_pt": dist})
    return out


def subpaths(drawing: dict[str, Any]) -> list[np.ndarray]:
    subs: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    last = None
    for it in drawing["items"]:
        if it[0] != "l":
            continue
        a, b = it[1], it[2]
        if last is None or abs(a.x - last.x) > 0.05 or abs(a.y - last.y) > 0.05:
            if cur:
                subs.append(cur)
            cur = [(a.x, a.y)]
        cur.append((b.x, b.y))
        last = b
    if cur:
        subs.append(cur)
    return [np.array(s) for s in subs]


def yellow_subpaths(page: fitz.Page) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for d in page.get_drawings():
        if d["fill"] == YELLOW:
            out.extend(s for s in subpaths(d) if len(s) > 20)
    return sorted(out, key=lambda s: -len(s))


def pick_subpath(page: fitz.Page, y_min: float, y_max: float) -> np.ndarray:
    """Longest filled outline whose vertical extent lies within [y_min, y_max] page points."""
    for sub in yellow_subpaths(page):
        if sub[:, 1].min() > y_min and sub[:, 1].max() < y_max:
            return sub
    raise SystemExit(f"no outline in y range {y_min}-{y_max}")


def raster_vertical_lines(png: Path, y_pt: float, x_lo_pt: float, x_hi_pt: float) -> list[float]:
    """Centres (pt) of dark vertical rules on a pixel row of the 400 dpi render."""
    px = DPI / 72.0
    img = np.asarray(Image.open(png).convert("L"))
    row = img[int(round(y_pt * px)), int(x_lo_pt * px) : int(x_hi_pt * px)] < 100
    centres, run = [], []
    for i, v in enumerate(row):
        if v:
            run.append(i)
        elif run:
            centres.append((np.mean(run) + int(x_lo_pt * px) + 0.5) / px)
            run = []
    return centres


def horizontal_extent_at(poly: Polygon, y: float, x0: float, x1: float) -> tuple[float, float] | None:
    seg = LineString([(x0, y), (x1, y)]).intersection(poly)
    if seg.is_empty:
        return None
    xs = [c[0] for g in getattr(seg, "geoms", [seg]) for c in g.coords]
    return min(xs), max(xs)


def robust_line(ys: np.ndarray, xs: np.ndarray) -> tuple[float, float]:
    """Fit x = a*y + b, rejecting spikes (flap-track fairings) iteratively."""
    keep = np.ones(len(ys), bool)
    for _ in range(6):
        a, b = np.polyfit(ys[keep], xs[keep], 1)
        res = np.abs(xs - (a * ys + b))
        keep = res < max(0.05, 2.5 * float(np.std(res[keep])))
    return float(a), float(b)


def top_view(page: fitz.Page, s: float, x0: float, cl: float) -> dict[str, Any]:
    outline = yellow_subpaths(page)[0]
    poly = Polygon(outline).buffer(0)

    def X(x: float) -> float:
        return (x - x0) / s

    def Y(y: float) -> float:
        return (y - cl) / s

    res: dict[str, Any] = {}
    minx, miny, maxx, maxy = poly.bounds
    res["outline_extent_x_m"] = [X(minx), X(maxx)]
    res["outline_half_span_incl_sharklet_m_uniform_scale"] = {"lower": Y(maxy), "upper": -Y(miny)}
    # fuselage width at X ~ 8 m
    ext = LineString([(x0 + 8.0 * s, miny - 5), (x0 + 8.0 * s, maxy + 5)]).intersection(poly)
    ys = [c[1] for c in ext.coords] if hasattr(ext, "coords") else [c[1] for g in ext.geoms for c in g.coords]
    res["fuselage_width_at_x8_m"] = (max(ys) - min(ys)) / s
    # wing: LE/TE vs Y (lower half), engine nacelle excluded by region
    rows = []
    for yy in np.arange(2.2, 17.45, 0.05):
        e = horizontal_extent_at(poly, cl + yy * s, x0 + 12 * s, x0 + 30 * s)
        if e:
            rows.append((yy, X(e[0]), X(e[1])))
    arr = np.array(rows)
    out_sel = arr[(arr[:, 0] > 8.6) & (arr[:, 0] < 17.4)]
    a_le, b_le = robust_line(out_sel[:, 0], out_sel[:, 1])
    a_te, b_te = robust_line(out_sel[:, 0], out_sel[:, 2])
    res["wing_outboard_LE_line"] = {"x_at_y_m": {"y8.6": a_le * 8.6 + b_le, "y17.4": a_le * 17.4 + b_le},
                                    "sweep_deg": float(np.degrees(np.arctan(a_le))), "fit_y_range_m": [8.6, 17.4]}
    res["wing_outboard_TE_line"] = {"x_at_y_m": {"y8.6": a_te * 8.6 + b_te, "y17.4": a_te * 17.4 + b_te},
                                    "sweep_deg": float(np.degrees(np.arctan(a_te))), "fit_y_range_m": [8.6, 17.4]}
    root = arr[np.argmin(np.abs(arr[:, 0] - 2.2))]
    res["wing_at_y2.2m"] = {"LE_x_m": root[1], "TE_x_m": root[2], "chord_m": root[2] - root[1]}
    res["wing_root_TE_inboard_straight_x_m"] = X(321.35)
    # wing/sharklet break line: horizontal stroke at the 16.29 extension line crossing the wing
    brk = [d for d in page.get_drawings() if d["type"] == "s" and len(d["items"]) == 1 and d["items"][0][0] == "l"
           and abs(d["items"][0][1].y - d["items"][0][2].y) < 0.01 and 501.9 < d["items"][0][1].y < 502.2
           and d["rect"].x0 > 320 and d["rect"].x1 < 360]
    xs_b = sorted(v for d in brk for v in (d["rect"].x0, d["rect"].x1))
    res["wing_sharklet_break_line"] = {"y_pt": 502.03, "x_le_m": X(xs_b[0]), "x_te_m": X(xs_b[-1]), "chord_m": (xs_b[-1] - xs_b[0]) / s,
                                       "y_m_uniform_scale": Y(502.03), "segments_found": len(brk)}
    e_brk = horizontal_extent_at(poly, 502.03, x0 + 22 * s, x0 + 30 * s)
    res["wing_sharklet_break_line"]["outline_le_te_at_break_y_m"] = [X(e_brk[0]), X(e_brk[1])] if e_brk else None
    res["wing_sharklet_break_line"]["line_ends_minus_outline_m"] = (
        [res["wing_sharklet_break_line"]["x_le_m"] - X(e_brk[0]), res["wing_sharklet_break_line"]["x_te_m"] - X(e_brk[1])] if e_brk else None)
    res["wing_LE_TE_fit_at_y16.29_m"] = {"le": a_le * 16.29 + b_le, "te": a_te * 16.29 + b_te}
    res["wing_LE_TE_fit_at_y16.24_m"] = {"le": a_le * 16.24 + b_le, "te": a_te * 16.24 + b_te}
    res["wing_LE_TE_fit_at_break_y_m"] = {"y": Y(502.03), "le": a_le * Y(502.03) + b_le, "te": a_te * Y(502.03) + b_te}
    # horizontal tail (x beyond 430 pt, lower half only)
    ht = []
    for yy in np.arange(2.2, 6.3, 0.05):
        e = horizontal_extent_at(poly, cl + yy * s, x0 + 36 * s, x0 + 46 * s)
        if e and e[1] - e[0] > 0.2 * s:
            ht.append((yy, X(e[0]), X(e[1])))
    ht_arr = np.array(ht)
    a_h, b_h = robust_line(ht_arr[:, 0], ht_arr[:, 1])
    tail_pts = outline[(outline[:, 0] > x0 + 36 * s) & (outline[:, 1] > cl + 1 * s)]
    res["horizontal_tail"] = {"half_span_outline_m_uniform_scale": Y(float(tail_pts[:, 1].max())),
                              "LE_x_at_y": {"y2.2": a_h * 2.2 + b_h, "y6.1": a_h * 6.1 + b_h},
                              "LE_sweep_deg": float(np.degrees(np.arctan(a_h))),
                              "tip_TE_x_m": X(float(tail_pts[:, 0].max())),
                              "chord_at_y2.2_m": float(ht_arr[0, 2] - ht_arr[0, 1]), "chord_at_tip_m": float(ht_arr[-1, 2] - ht_arr[-1, 1])}
    return res


def side_view(page: fitz.Page) -> dict[str, Any]:
    sub = pick_subpath(page, 100, 300)
    poly = Polygon(sub).buffer(0)
    minx, miny, maxx, maxy = poly.bounds
    s = (maxx - minx) / 44.51
    ground = [d["rect"].y0 for d in page.get_drawings() if d["type"] == "s" and len(d["items"]) == 1
              and d["items"][0][0] == "l" and abs(d["items"][0][1].y - d["items"][0][2].y) < 0.01
              and d["rect"].width > 200 and 260 < d["rect"].y0 < 270]
    gy = ground[0] if ground else maxy

    def vert(x_pt: float) -> tuple[float, float]:
        ext = LineString([(x_pt, miny - 5), (x_pt, maxy + 5)]).intersection(poly)
        ys = [c[1] for g in getattr(ext, "geoms", [ext]) for c in g.coords]
        return min(ys), max(ys)

    top, bot = vert(minx + 30 * s)  # X = 30 m: aft of the main gear and wing fairing, forward of the tail upsweep
    fin_pts = sub[sub[:, 1] < miny + 1.0]
    z_of = (gy - sub[:, 1]) / s
    x_of = (sub[:, 0] - minx) / s
    sel = (z_of > 7.2) & (z_of < 11.6) & (x_of > 35.0) & (x_of < 42.5)
    a, b = np.polyfit(z_of[sel], x_of[sel], 1)  # X = a*z + b along the fin leading edge
    crown_z = (gy - top) / s
    x_root_le = a * crown_z + b
    fin_le_at_h = {f"h{h:g}": float(a * (crown_z + h) + b) for h in (2.0, 5.0)}
    return {
        "scale_pt_per_m": s, "length_pt": maxx - minx, "nose_x_pt": minx, "ground_y_pt": gy,
        "crown_z_m": (gy - top) / s, "belly_z_m": (gy - bot) / s, "fuselage_height_m": (bot - top) / s,
        "fin_tip_z_m": (gy - miny) / s, "fin_tip_above_crown_m": (top - miny) / s,
        "fin_tip_x_m": [(fin_pts[:, 0].min() - minx) / s, (fin_pts[:, 0].max() - minx) / s],
        "fin_LE_root_x_m_at_crown_extrapolated": x_root_le, "fin_LE_x_at_height_above_crown_m": fin_le_at_h,
        "fin_LE_sweep_from_vertical_deg": float(np.degrees(np.arctan(a))),
        "fin_LE_fit_z_range_m": [7.2, 11.6], "fin_LE_fit_points": int(sel.sum()),
        "tail_tip_x_m": (maxx - minx) / s,
    }


def front_view(page: fitz.Page) -> dict[str, Any]:
    sub = pick_subpath(page, 400, 600)
    minx, miny, maxx, maxy = sub[:, 0].min(), sub[:, 1].min(), sub[:, 0].max(), sub[:, 1].max()
    s = (maxx - minx) / 35.80
    ground = [d["rect"].y0 for d in page.get_drawings() if d["type"] == "s" and len(d["items"]) == 1
              and d["items"][0][0] == "l" and abs(d["items"][0][1].y - d["items"][0][2].y) < 0.01
              and d["rect"].width > 250 and 500 < d["rect"].y0 < 530]
    gy = ground[0] if ground else maxy
    tip_pts = sub[(sub[:, 0] > 400) & (sub[:, 1] < 470)]
    top_pt = tip_pts[np.argmin(tip_pts[:, 1])] if len(tip_pts) else None
    ht_tip = sub[(sub[:, 0] > 233) & (sub[:, 0] < 240) & (sub[:, 1] < 490)]
    return {"sharklet_top_half_span_m_front_scale": (top_pt[0] - (minx + maxx) / 2) / s if top_pt is not None else None,
            "ht_tip_half_span_m_front_scale": (336.6 - (minx + maxx) / 2) / s,
            "ht_tip_z_m": (gy - float(ht_tip[:, 1].mean())) / s if len(ht_tip) else None, "ht_tip_points_found": int(len(ht_tip)),
            "scale_pt_per_m": s, "span_pt": maxx - minx, "centre_x_pt": (minx + maxx) / 2, "ground_y_pt": gy,
            "outline_top_z_m": (gy - miny) / s, "outline_min_x_pt": minx, "outline_max_x_pt": maxx}


def measure_dimensions(page: fitz.Page, pn: int, ref_scale: float) -> list[dict[str, Any]]:
    arrows, labels = page_arrows_and_labels(page)
    items = assign_labels(dimension_pairs(arrows), labels)
    rows = []
    for it in sorted(items, key=lambda r: float(r["label"]), reverse=True):
        v = float(it["label"])
        drawn = abs(it["b"] - it["a"])
        reading, conf = READING.get((pn, it["label"]), ("unclassified", "low"))
        rows.append({
            "label_m": it["label"], "value_m": v, "value_ft_computed": round(v * FT_PER_M, 2), "page": pn, "axis_on_page": it["axis"],
            "measures": reading, "confidence": conf,
            "tips_pt": [round(it["a"], 2), round(it["b"], 2)], "drawn_length_pt": round(drawn, 2), "implied_pt_per_m": round(drawn / v, 3),
            "ratio_to_view_scale": round(drawn / v / ref_scale, 3),
            "label_assignment_distance_pt": round(it["assign_dist_pt"], 1),
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--render-dir", type=Path, required=True, help="scratch dir for 400 dpi renders (not in the repo)")
    args = ap.parse_args()
    t0 = time.time()
    sha = sha256_of(args.pdf)
    if sha != EXPECTED_SHA:
        raise SystemExit(f"SHA mismatch: {sha}")
    args.render_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(args.pdf)
    renders = {}
    for pn in (73, 74, 94):
        png = args.render_dir / f"page-{pn:03d}-{DPI}dpi.png"
        if not png.exists():
            doc[pn - 1].get_pixmap(dpi=DPI).save(png)
        renders[pn] = png
    p73, p74 = doc[72], doc[73]
    # --- top view scale: 44.51 m extension lines, vector then raster
    top_dims = measure_dimensions(p74, 74, 1.0)
    len_dim = next(r for r in top_dims if r["label_m"] == "44.51")
    pairs74 = assign_labels(dimension_pairs(page_arrows_and_labels(p74)[0]), page_arrows_and_labels(p74)[1])
    ln = next(p for p in pairs74 if p["label"] == "44.51")
    x0_pt, x1_pt = ln["a"], ln["b"]
    s_top = (x1_pt - x0_pt) / 44.51
    ras = raster_vertical_lines(renders[74], 250.0, x0_pt - 6, x1_pt + 6)
    ras_len_pt = ras[-1] - ras[0] if len(ras) >= 2 else None
    cl_y = next(p for p in dimension_pairs(page_arrows_and_labels(p74)[0]) if p["axis"] == "V" and abs(p["line"] - 499.45) < 1)["a"]
    # --- front view: 35.80 m
    front = front_view(p73)
    dims73 = measure_dimensions(p73, 73, front["scale_pt_per_m"])
    ras_span = raster_vertical_lines(renders[73], 400.0, front["outline_min_x_pt"] - 8, front["outline_max_x_pt"] + 8)
    side = side_view(p73)
    t379 = next(r for r in dims73 if r["label_m"] == "3.79")["tips_pt"]
    t243 = next(r for r in dims73 if r["label_m"] == "2.43")["tips_pt"]
    fs, fg = front["scale_pt_per_m"], front["ground_y_pt"]
    front["sharklet_top_z_m"] = (fg - t379[0]) / fs
    front["wing_tip_base_line_z_m"] = (fg - t243[1]) / fs
    front["wing_root_lower_ref_line_z_m"] = (fg - t379[1]) / fs
    front["wing_dihedral_rise_root_to_tip_m_from_labels"] = 3.79 - 2.43
    dims74 = measure_dimensions(p74, 74, s_top)
    top = top_view(p74, s_top, x0_pt, cl_y)
    sk = next(r for r in dims74 if r["label_m"] == "16.29")
    sk2 = next(r for r in dims74 if r["label_m"] == "1.61")
    result = {
        "schema": "r6-reference-dimensions-v1",
        "status": "OWN_MEASUREMENTS_NOT_OEM_ENGINEERING_DATA",
        "source": {"title": "Airbus A321 Aircraft Characteristics - Airport and Maintenance Planning, Jul 01/26, A321neo-ACF / A321neo-XLR",
                   "sha256": sha, "pages_1based": [73, 74, 94],
                   "figure": "FIGURE-2-2-0-991-012-A01 General Aircraft Dimensions sheets 1 and 2",
                   "note": "Both sheets state: RELATED TO AIRCRAFT ATTITUDE AND WEIGHT. Page 94 is the leading-edge-slat ground-clearance table; it carries no outline geometry and is not used.",
                   "pdf_copied_to_repo": False, "page_renders_in_repo": False},
        "scale": {
            "top_view_page74": {"method_vector": "arrowhead tips of the 44.51 m dimension line (nose and tail-cone extension rules)",
                                "pt_per_m": s_top, "px_per_m_at_400dpi": s_top * DPI / 72.0,
                                "raster_cross_check_pt": ras_len_pt, "raster_rules_found_pt": [round(v, 2) for v in ras],
                                "raster_pt_per_m": (ras_len_pt / 44.51) if ras_len_pt else None,
                                "centreline_y_pt": cl_y, "nose_x_pt": x0_pt},
            "side_view_page73": {"method": "outline nose to tail extent divided by 44.51 m", **{k: side[k] for k in ("scale_pt_per_m", "length_pt")}},
            "front_view_page73": {"method": "outline wingtip-to-wingtip extent divided by 35.80 m", "pt_per_m": front["scale_pt_per_m"],
                                  "span_pt": front["span_pt"], "raster_rules_found_pt": [round(v, 2) for v in ras_span]},
            "note": "page 73 holds the side view (to the 44.51 m scale) and the front view (35.80 m); 44.51 m itself is printed on page 74",
        },
        "dimensions": dims74 + dims73,
        "drawn_planform_and_profile": {"unit": "m, uniform page-74 scale, origin at nose and centreline", "top": top, "side": side, "front": front},
        "sharklet_16_29_evidence": {
            "printed_16.29_m": 16.29, "printed_1.61_m": 1.61, "printed_35.80_m_half": 17.90, "sum_16.29_plus_1.61": 17.90,
            "drawn_16.29_dim_pt": sk["drawn_length_pt"], "drawn_1.61_dim_pt": sk2["drawn_length_pt"],
            "drawn_16.29_at_page74_scale_m": sk["drawn_length_pt"] / s_top, "drawn_1.61_at_page74_scale_m": sk2["drawn_length_pt"] / s_top,
            "break_line": top["wing_sharklet_break_line"],
            "closure_checks_printed_set": {
                "half_span_16.29_plus_1.61": 16.29 + 1.61, "half_of_35.80": 35.80 / 2,
                "junction_LE_x_from_27.72_minus_3.22_m": 27.72 - 3.22,
                "planform_fit_LE_x_at_y16.29_m": top["wing_LE_TE_fit_at_y16.29_m"]["le"],
                "planform_fit_TE_x_at_y16.29_m": top["wing_LE_TE_fit_at_y16.29_m"]["te"],
                "planform_fit_chord_at_y16.29_m": top["wing_LE_TE_fit_at_y16.29_m"]["te"] - top["wing_LE_TE_fit_at_y16.29_m"]["le"],
                "printed_tip_chord_1.64_m": 1.64,
                "drawn_break_line_LE_x_m": top["wing_sharklet_break_line"]["x_le_m"],
                "drawn_break_line_chord_m": top["wing_sharklet_break_line"]["chord_m"],
            },
            "reading": ("The printed set closes at a junction at y=16.29 m: 16.29+1.61=17.90=35.80/2, and the page planform LE/TE lines evaluated at "
                        "y=16.29 m give chord ~1.64 m and LE x ~24.50 m = 27.72-3.22. The drawn break line itself is artwork at y=%.2f m (page scale) "
                        "and the sharklet is drawn %.2f m long (printed 1.61): the tip artwork is not to scale by ~0.5 m, while 3.95 and 5.75 scale at 1.00." %
                        (top["wing_sharklet_break_line"]["y_m_uniform_scale"], sk2["drawn_length_pt"] / s_top)),
            "outline_half_span_incl_sharklet_m": top["outline_half_span_incl_sharklet_m_uniform_scale"],
        },
        "wall_time_s": round(time.time() - t0, 1),
    }
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=float) + "\n", encoding="utf-8")
    print(f"wrote {args.out} in {result['wall_time_s']} s")


if __name__ == "__main__":
    main()
