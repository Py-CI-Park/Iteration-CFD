# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy"]
# ///
"""Contract 03 M5 / 02d edge flip with the QUAD-SCOPE fold rule and the quality margin.

Derived from research/a321-quality/r6/gen/r6_flip.py. Differences (contract 03 M5):
  - the fold test is the quad scope: the flip is REFUSED if any dihedral of the new set {new diagonal, four outer edges
    against their neighbour triangles} exceeds the maximum of the old set {old edge, same four outer edges} + 1 deg;
    the pair-scope value (new diagonal vs old edge) is recorded for information only and does not refuse;
  - quality margin: min Q_OF of the two new triangles must be >= min Q_OF of the two old triangles.
All other R6 refusals (feature edge, existing diagonal, axis-parallel new diagonal, 02a per-triangle limits, valence,
area ratio) are kept. No vertex is moved or added. Every refusal is returned with its reason and coordinates."""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import numpy as np
from numpy.typing import NDArray

import r7_common

r7_common.add_paths()
import r6_metrics  # noqa: E402

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def axis_parallel_edges(vertices: FloatArray, faces: IntArray) -> list[tuple[int, int]]:
    """Undirected edges whose float32 direction has at least two exactly zero components."""
    v32 = vertices.astype(np.float32)
    e = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    zero = ((v32[e[:, 1]] - v32[e[:, 0]]) == 0).sum(axis=1)
    return [(int(a), int(b)) for (a, b) in e[zero >= 2]]


def _normal(v: FloatArray, tri: tuple[int, int, int]) -> FloatArray:
    n = np.cross(v[tri[1]] - v[tri[0]], v[tri[2]] - v[tri[0]])
    length = np.linalg.norm(n)
    return n / length if length > 0 else np.full(3, np.nan)


def _angle(n1: FloatArray, n2: FloatArray) -> float:
    return float(np.degrees(np.arccos(np.clip(np.dot(n1, n2), -1.0, 1.0))))


def flip_axis_parallel(vertices: FloatArray, faces: IntArray, feature_edges: set[tuple[int, int]], limits: dict,
                       fold_margin_deg: float = 1.0) -> tuple[IntArray, dict]:
    """limits: Q_MIN, ANGLE_MIN_DEG, ASPECT_MAX, GRADE_AREA_MAX, VALENCE_MAX (02a values). Returns (new faces, record)."""
    faces = faces.copy()
    v = vertices
    v32 = v.astype(np.float32)
    directed: dict[tuple[int, int], int] = {}
    for fi, (a, b, c) in enumerate(faces):
        directed[(int(a), int(b))] = fi
        directed[(int(b), int(c))] = fi
        directed[(int(c), int(a))] = fi
    edge_set = {(min(u, w), max(u, w)) for (u, w) in directed}
    val = np.zeros(len(v), dtype=np.int64)
    for u, w in edge_set:
        val[u] += 1
        val[w] += 1
    targets = axis_parallel_edges(v, faces)
    flipped, refused = [], []

    def refuse(edge, why):
        refused.append({"edge_vertices": [int(edge[0]), int(edge[1])], "midpoint_m": ((v[edge[0]] + v[edge[1]]) / 2).tolist(), "reason": why})

    def third(face_idx: int, a: int, b: int) -> int:
        return int([x for x in faces[face_idx] if x != a and x != b][0])

    for edge in targets:
        a0, b0 = edge
        if edge in feature_edges:
            refuse(edge, "declared feature edge")
            continue
        if (a0, b0) in directed and (b0, a0) in directed:
            u, w = a0, b0
        else:
            refuse(edge, "edge no longer interior (neighbour changed)")
            continue
        f1, f2 = directed[(u, w)], directed[(w, u)]
        c, d = third(f1, u, w), third(f2, u, w)
        if c == d or (min(c, d), max(c, d)) in edge_set:
            refuse(edge, "other diagonal already exists")
            continue
        if ((v32[d] - v32[c]) == 0).sum() >= 2:
            refuse(edge, "new diagonal is itself exactly axis-parallel")
            continue
        t1, t2 = (u, d, c), (d, w, c)
        quality = r6_metrics.triangle_quality(v, np.array([t1, t2]))
        old_quality = r6_metrics.triangle_quality(v, np.array([tuple(faces[f1]), tuple(faces[f2])]))
        if np.any(quality["q_of"] < limits["Q_MIN"]):
            refuse(edge, f"Q_OF {float(quality['q_of'].min()):.3g} < {limits['Q_MIN']}")
            continue
        if np.any(quality["min_angle_deg"] < limits["ANGLE_MIN_DEG"]):
            refuse(edge, f"min angle {float(quality['min_angle_deg'].min()):.3g} < {limits['ANGLE_MIN_DEG']}")
            continue
        if np.any(quality["aspect"] > limits["ASPECT_MAX"]):
            refuse(edge, f"aspect {float(quality['aspect'].max()):.3g} > {limits['ASPECT_MAX']}")
            continue
        if float(quality["q_of"].min()) < float(old_quality["q_of"].min()):
            refuse(edge, f"quality margin: new min Q_OF {float(quality['q_of'].min()):.4g} < old {float(old_quality['q_of'].min()):.4g}")
            continue
        if val[c] + 1 > limits["VALENCE_MAX"] or val[d] + 1 > limits["VALENCE_MAX"]:
            refuse(edge, f"valence of an opposite vertex would exceed {limits['VALENCE_MAX']}")
            continue
        outer = [(w, c), (c, u), (u, d), (d, w)]
        owner_new = {(w, c): t2, (c, u): t1, (u, d): t1, (d, w): t2}
        owner_old = {(w, c): tuple(faces[f1]), (c, u): tuple(faces[f1]), (u, d): tuple(faces[f2]), (d, w): tuple(faces[f2])}
        areas_new = r6_metrics.face_geometry(v, np.array([t1, t2]))[0]
        if max(areas_new) / max(min(areas_new), 1e-300) > limits["GRADE_AREA_MAX"]:
            refuse(edge, "area ratio between the two new triangles")
            continue
        new_diag = _angle(_normal(v, t1), _normal(v, t2))
        old_diag = _angle(_normal(v, tuple(faces[f1])), _normal(v, tuple(faces[f2])))
        new_max, old_max = new_diag, old_diag
        ok, why = True, ""
        for (p, q) in outer:
            nb = directed.get((q, p))
            if nb is None:
                continue
            nb_tri = tuple(faces[nb])
            nb_area = r6_metrics.face_geometry(v, np.array([nb_tri]))[0][0]
            mine = areas_new[0 if owner_new[(p, q)] == t1 else 1]
            ratio = max(mine, nb_area) / max(min(mine, nb_area), 1e-300)
            if ratio > limits["GRADE_AREA_MAX"]:
                ok, why = False, f"area ratio {ratio:.3g} to a neighbour"
                break
            new_max = max(new_max, _angle(_normal(v, owner_new[(p, q)]), _normal(v, nb_tri)))
            old_max = max(old_max, _angle(_normal(v, owner_old[(p, q)]), _normal(v, nb_tri)))
        if not ok:
            refuse(edge, why)
            continue
        if new_max > old_max + fold_margin_deg:
            refuse(edge, f"fold (quad scope): max dihedral of the new set {new_max:.2f} > old max {old_max:.2f} + {fold_margin_deg}")
            continue
        for key in ((u, w), (w, c), (c, u), (w, u), (u, d), (d, w)):
            directed.pop(key, None)
        faces[f1], faces[f2] = t1, t2
        for fi, t in ((f1, t1), (f2, t2)):
            directed[(t[0], t[1])] = fi
            directed[(t[1], t[2])] = fi
            directed[(t[2], t[0])] = fi
        edge_set.discard((min(u, w), max(u, w)))
        edge_set.add((min(c, d), max(c, d)))
        val[u] -= 1
        val[w] -= 1
        val[c] += 1
        val[d] += 1
        flipped.append({"edge_vertices": [int(u), int(w)], "midpoint_m": ((v[u] + v[w]) / 2).tolist(), "new_diagonal": [int(c), int(d)],
                        "pair_scope_dihedral_old_deg": old_diag, "pair_scope_dihedral_new_deg": new_diag, "pair_scope_info_only_ok": bool(new_diag <= old_diag + fold_margin_deg),
                        "quad_scope_old_max_deg": old_max, "quad_scope_new_max_deg": new_max,
                        "q_of_min_old": float(old_quality["q_of"].min()), "q_of_min_new": float(quality["q_of"].min())})
    record = {"rule": "contract 03 M5: 02d flip, quad-scope fold refusal + quality margin (new min Q_OF >= old min Q_OF)",
              "axis_parallel_edges_found": len(targets), "flipped": len(flipped), "refused": len(refused),
              "axis_parallel_edges_after": len(axis_parallel_edges(v, faces)), "fold_margin_deg": fold_margin_deg,
              "flips_failing_pair_scope_info_only": int(sum(1 for f in flipped if not f["pair_scope_info_only_ok"])),
              "limits_used": limits, "flips": flipped, "refusals": refused}
    return faces, record
