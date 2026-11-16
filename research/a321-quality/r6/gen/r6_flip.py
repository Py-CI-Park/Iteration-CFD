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
"""Contract 02d edge flip: flip every edge exactly parallel to a coordinate axis to the other diagonal of its two triangles.

A flip is made only when
  - the edge is not a declared feature edge (both ends consecutive on a feature polyline);
  - the new diagonal is not itself exactly axis-parallel and does not already exist;
  - both new triangles meet the per-triangle 02a limits (Q_OF min, minimum angle, aspect ratio maximum);
  - the new vertex valences of the two opposite vertices stay <= the 02a valence maximum;
  - the area ratio of each new triangle to every neighbour across the four outer quad edges stays <= the 02a limit;
  - no fold: the dihedral across the new diagonal is <= the dihedral across the old edge + fold_margin_deg
    (reading of 02d "new dihedral <= old maximum of the pair + 1 deg": the pair is the two triangles, the dihedral is theirs).
    The stricter reading (maximum over the new diagonal and the four outer quad edges, new vs old) is evaluated for every
    allowed flip and recorded as `quad_scope_ok`; it is not used to refuse.
No vertex is moved or added. Every refusal is returned with its reason and the edge coordinates.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
import r6_metrics

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
    valence = np.zeros(len(v), dtype=np.int64)
    for u, w in edge_set:
        valence[u] += 1
        valence[w] += 1
    targets = axis_parallel_edges(v, faces)
    flipped, refused = [], []

    def refuse(edge, why):
        refused.append({"edge_vertices": [int(edge[0]), int(edge[1])], "midpoint_m": ((v[edge[0]] + v[edge[1]]) / 2).tolist(), "reason": why})

    def third(face_idx: int, a: int, b: int) -> int:
        return int([x for x in faces[face_idx] if x != a and x != b][0])

    def outer_neighbour(p: int, q: int) -> int | None:
        return directed.get((q, p))

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
        if np.any(quality["q_of"] < limits["Q_MIN"]):
            refuse(edge, f"Q_OF {float(quality['q_of'].min()):.3g} < {limits['Q_MIN']}")
            continue
        if np.any(quality["min_angle_deg"] < limits["ANGLE_MIN_DEG"]):
            refuse(edge, f"min angle {float(quality['min_angle_deg'].min()):.3g} < {limits['ANGLE_MIN_DEG']}")
            continue
        if np.any(quality["aspect"] > limits["ASPECT_MAX"]):
            refuse(edge, f"aspect {float(quality['aspect'].max()):.3g} > {limits['ASPECT_MAX']}")
            continue
        if valence[c] + 1 > limits["VALENCE_MAX"] or valence[d] + 1 > limits["VALENCE_MAX"]:
            refuse(edge, f"valence of an opposite vertex would exceed {limits['VALENCE_MAX']}")
            continue
        outer = [(w, c), (c, u), (u, d), (d, w)]  # directed outer edges of the old quad, shared with t2, t1, t1, t2 after the flip
        owner_new = {(w, c): t2, (c, u): t1, (u, d): t1, (d, w): t2}
        owner_old = {(w, c): tuple(faces[f1]), (c, u): tuple(faces[f1]), (u, d): tuple(faces[f2]), (d, w): tuple(faces[f2])}
        areas_new = r6_metrics.face_geometry(v, np.array([t1, t2]))[0]
        ok, why = True, ""
        if max(areas_new) / max(min(areas_new), 1e-300) > limits["GRADE_AREA_MAX"]:
            refuse(edge, "area ratio between the two new triangles")
            continue
        new_diag = _angle(_normal(v, t1), _normal(v, t2))
        old_diag = _angle(_normal(v, tuple(faces[f1])), _normal(v, tuple(faces[f2])))
        new_max, old_max = new_diag, old_diag
        for (p, q) in outer:
            nb = outer_neighbour(p, q)
            if nb is None:
                continue
            nb_tri = tuple(faces[nb])
            nb_area = r6_metrics.face_geometry(v, np.array([nb_tri]))[0][0]
            mine = areas_new[0 if owner_new[(p, q)] == t1 else 1]
            if max(mine, nb_area) / max(min(mine, nb_area), 1e-300) > limits["GRADE_AREA_MAX"]:
                ok, why = False, f"area ratio {max(mine, nb_area) / max(min(mine, nb_area), 1e-300):.3g} to a neighbour"
                break
            new_max = max(new_max, _angle(_normal(v, owner_new[(p, q)]), _normal(v, nb_tri)))
            old_max = max(old_max, _angle(_normal(v, owner_old[(p, q)]), _normal(v, nb_tri)))
        if not ok:
            refuse(edge, why)
            continue
        if new_diag > old_diag + fold_margin_deg:
            refuse(edge, f"fold: dihedral across the new diagonal {new_diag:.2f} > old {old_diag:.2f} + {fold_margin_deg}")
            continue
        quad_ok = bool(new_max <= old_max + fold_margin_deg)
        for key in ((u, w), (w, c), (c, u), (w, u), (u, d), (d, w)):
            directed.pop(key, None)
        faces[f1], faces[f2] = t1, t2
        for fi, t in ((f1, t1), (f2, t2)):
            directed[(t[0], t[1])] = fi
            directed[(t[1], t[2])] = fi
            directed[(t[2], t[0])] = fi
        edge_set.discard((min(u, w), max(u, w)))
        edge_set.add((min(c, d), max(c, d)))
        valence[u] -= 1
        valence[w] -= 1
        valence[c] += 1
        valence[d] += 1
        flipped.append({"edge_vertices": [int(u), int(w)], "midpoint_m": ((v[u] + v[w]) / 2).tolist(), "new_diagonal": [int(c), int(d)], "dihedral_old_deg": old_diag, "dihedral_new_deg": new_diag,
                        "quad_scope_ok": quad_ok, "quad_scope_old_max_deg": old_max, "quad_scope_new_max_deg": new_max})
    record = {"axis_parallel_edges_found": len(targets), "flipped": len(flipped), "refused": len(refused),
              "axis_parallel_edges_after": len(axis_parallel_edges(v, faces)), "fold_margin_deg": fold_margin_deg,
              "flips_failing_stricter_quad_scope": int(sum(1 for f in flipped if not f["quad_scope_ok"])),
              "limits_used": limits, "flips": flipped, "refusals": refused}
    return faces, record
