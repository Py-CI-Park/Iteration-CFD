# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""R6 gate suite: STL loading, exact-coordinate weld, edge topology and orientation.

Everything here is a measurement. Nothing in this module grades a surface.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


class GateError(RuntimeError):
    """A malformed input or a violated custody contract."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)


def sha256_file(path: Path) -> str:
    """SHA256 of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_stl(path: Path) -> FloatArray:
    """Binary STL facets as float64 (N,3,3), original facet order, no reordering."""
    raw = path.read_bytes()
    count = int.from_bytes(raw[80:84], "little")
    if len(raw) != 84 + count * 50:
        raise GateError(f"Not a size-consistent binary STL: {path}")
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, count=count, offset=84)["vertices"].astype(np.float64)
    if not np.isfinite(triangles).all():
        raise GateError(f"Non-finite STL coordinates: {path}")
    return triangles


def write_stl(path: Path, triangles: FloatArray) -> None:
    """Write a binary STL (used by tests and synthetic fixtures; never on an input path)."""
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    record = np.zeros(len(triangles), dtype=dtype)
    record["vertices"] = triangles.astype(np.float32)
    with path.open("xb") as stream:
        stream.write(b"r6_gate synthetic".ljust(80, b"\0"))
        stream.write(len(triangles).to_bytes(4, "little"))
        stream.write(record.tobytes())


def weld(triangles: FloatArray) -> tuple[FloatArray, IntArray]:
    """Weld by exact coordinate value (not by bytes: -0.0 and +0.0 merge). Face order is kept.

    Coordinates are taken as float32 because STL stores float32; the weld is exact on
    those values. No degenerate face is dropped, so welded face i is STL facet i.
    """
    flat = triangles.reshape(-1, 3).astype(np.float32) + np.float32(0.0)
    unique, inverse = np.unique(flat, axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3).astype(np.int64)
    return unique.astype(np.float64), faces


@dataclass(frozen=True)
class EdgeTable:
    """Distinct undirected edges of a welded mesh with their incident faces."""

    count: IntArray  # incident face corners per edge
    vertices: IntArray  # (E,2) lo, hi vertex ids
    face_a: IntArray  # first incident face
    face_b: IntArray  # second incident face (valid when count >= 2, else -1)
    direction_sum: IntArray  # sum of +1 (lo->hi) / -1 (hi->lo) over incident corners


def build_edges(faces: IntArray, vertex_count: int) -> EdgeTable:
    """Collect undirected edges; faces with a repeated vertex index contribute no edge."""
    keep = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0])
    ids = np.flatnonzero(keep)
    tri = faces[ids]
    start = np.concatenate([tri[:, 0], tri[:, 1], tri[:, 2]])
    end = np.concatenate([tri[:, 1], tri[:, 2], tri[:, 0]])
    owner = np.concatenate([ids, ids, ids])
    lo, hi = np.minimum(start, end), np.maximum(start, end)
    sign = np.where(start < end, 1, -1)
    keys = lo * np.int64(vertex_count) + hi
    order = np.argsort(keys, kind="stable")
    keys, lo, hi, sign, owner = keys[order], lo[order], hi[order], sign[order], owner[order]
    first = np.flatnonzero(np.concatenate([[True], keys[1:] != keys[:-1]]))
    counts = np.diff(np.concatenate([first, [len(keys)]]))
    second = np.where(counts >= 2, first + 1, first)
    return EdgeTable(
        count=counts.astype(np.int64), vertices=np.column_stack([lo[first], hi[first]]),
        face_a=owner[first], face_b=np.where(counts >= 2, owner[second], -1).astype(np.int64),
        direction_sum=np.add.reduceat(sign, first).astype(np.int64),
    )


def vertex_components(faces: IntArray, vertex_count: int) -> tuple[int, IntArray]:
    """Connected components by shared vertices (every face edge links its endpoints)."""
    pairs = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(vertex_count, vertex_count))
    count, labels = connected_components(graph, directed=False)
    return int(count), labels.astype(np.int64)


def face_geometry(vertices: FloatArray, faces: IntArray) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return (area, unit normals with NaN for zero area, edge lengths (N,3) opposite a,b,c)."""
    a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
    cross = np.cross(b - a, c - a)
    length = np.linalg.norm(cross, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        normal = np.where(length[:, None] > 0, cross / length[:, None], np.nan)
    sides = np.column_stack([np.linalg.norm(b - c, axis=1), np.linalg.norm(c - a, axis=1), np.linalg.norm(a - b, axis=1)])
    return 0.5 * length, normal, sides


def signed_volume_by_component(vertices: FloatArray, faces: IntArray, labels: IntArray, count: int) -> FloatArray:
    """Signed volume of each connected component (positive = outward normals when closed)."""
    origin = vertices.mean(axis=0)
    a, b, c = (vertices[faces[:, k]] - origin for k in range(3))
    per_face = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    return np.bincount(labels[faces[:, 0]], weights=per_face, minlength=count)


def component_rows(vertices: FloatArray, faces: IntArray, edges: EdgeTable, labels: IntArray, count: int,
                   volumes: FloatArray) -> list[dict]:
    """Per-component V, E, F, Euler characteristic, genus (if closed orientable), signed volume."""
    v_count = np.bincount(labels, minlength=count)
    e_count = np.bincount(labels[edges.vertices[:, 0]], minlength=count)
    f_count = np.bincount(labels[faces[:, 0]], minlength=count)
    rows = []
    for k in range(count):
        chi = int(v_count[k] - e_count[k] + f_count[k])
        rows.append({"vertices": int(v_count[k]), "edges": int(e_count[k]), "faces": int(f_count[k]),
                     "euler": chi, "genus_if_closed_orientable": (2 - chi) / 2,
                     "signed_volume_m3": float(volumes[k])})
    return rows


def closure_and_orientation(vertices: FloatArray, faces: IntArray) -> tuple[dict, EdgeTable]:
    """Metrics 1 and 2: closure, manifoldness, components, Euler/genus, winding, outward volume."""
    edges = build_edges(faces, len(vertices))
    used = np.zeros(len(vertices), bool)
    used[faces.ravel()] = True
    ncomp, labels = vertex_components(faces, len(vertices))
    area, _, _ = face_geometry(vertices, faces)
    repeated = int(np.sum((faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 2] == faces[:, 0])))
    boundary = int(np.sum(edges.count == 1))
    nonmanifold = int(np.sum(edges.count > 2))
    inconsistent = int(np.sum((edges.count == 2) & (np.abs(edges.direction_sum) == 2)))
    volumes = signed_volume_by_component(vertices, faces, labels, ncomp)
    closed = boundary == 0 and nonmanifold == 0 and repeated == 0
    return {
        "welded_vertices": int(len(vertices)), "unused_vertices": int(np.sum(~used)), "faces": int(len(faces)),
        "distinct_edges": int(len(edges.count)), "boundary_edges": boundary, "nonmanifold_edges": nonmanifold,
        "edges_used_exactly_twice": int(np.sum(edges.count == 2)),
        "faces_with_repeated_vertex_index": repeated, "zero_area_faces": int(np.sum(area == 0)),
        "watertight_manifold": bool(closed), "connected_components": ncomp,
        "euler_characteristic": int(len(vertices) - len(edges.count) + len(faces)),
        "components": component_rows(vertices, faces, edges, labels, ncomp, volumes),
        "winding_inconsistent_edges": inconsistent, "winding_consistent": bool(inconsistent == 0),
        "outward_normals": bool(closed and inconsistent == 0 and bool(np.all(volumes > 0))),
        "signed_volume_total_m3": float(volumes.sum()), "components_with_nonpositive_volume": int(np.sum(volumes <= 0)),
    }, edges
