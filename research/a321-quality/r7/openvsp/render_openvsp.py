# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Orthographic top / side / front renders of the OpenVSP CompGeom union (numpy + matplotlib, offline, flat shading).

Run (venv interpreter): .worktmp/venvs/openvsp313/Scripts/python.exe -I research/a321-quality/r7/openvsp/render_openvsp.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stl_tools  # noqa: E402,F401

STL = HERE.parents[3] / ".worktmp" / "r7-openvsp" / "openvsp_union.stl"
OUT = HERE / "figures"


def read_binary(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    n = int.from_bytes(raw[80:84], "little")
    dt = np.dtype([("n", "<f4", (3,)), ("t", "<f4", (3, 3)), ("a", "<u2")])
    return np.frombuffer(raw, dtype=dt, count=n, offset=84)["t"].astype(np.float64)


def render(tri: np.ndarray, axes: tuple[int, int], depth_axis: int, depth_sign: float, title: str, path: Path, edges: bool,
           window: tuple[float, float, float, float] | None = None) -> None:
    normal = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-30)
    light = np.array([0.4, -0.3, 0.85])
    light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.abs(normal @ light)
    facing = normal[:, depth_axis] * depth_sign > -0.05  # draw faces looking towards the viewer (and edge-on ones)
    order = np.argsort(depth_sign * tri[:, :, depth_axis].mean(axis=1))
    order = order[facing[order]]
    polys = tri[order][:, :, list(axes)]
    colors = np.repeat(shade[order, None], 3, axis=1) * np.array([0.55, 0.65, 0.85])
    fig, ax = plt.subplots(figsize=(14, 6.5 if axes != (1, 2) else 8), dpi=130)
    pc = PolyCollection(polys, facecolors=np.clip(colors, 0, 1), edgecolors=("k" if edges else "none"), linewidths=0.05 if edges else 0)
    ax.add_collection(pc)
    lo, hi = tri.reshape(-1, 3).min(axis=0), tri.reshape(-1, 3).max(axis=0)
    ax.set_xlim(lo[axes[0]] - 1, hi[axes[0]] + 1)
    ax.set_ylim(lo[axes[1]] - 1, hi[axes[1]] + 1)
    if window is not None:
        ax.set_xlim(window[0], window[1])
        ax.set_ylim(window[2], window[3])
    ax.set_aspect("equal")
    ax.set_xlabel("xyz"[axes[0]] + " [m]")
    ax.set_ylabel("xyz"[axes[1]] + " [m]")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    tri = read_binary(STL)
    # top: look down -z (viewer at +z); side: viewer at -y looking +y so x runs right and z up; front: viewer at +x looking -x
    render(tri, (0, 1), 2, +1.0, "OpenVSP A321 union, top view (CompGeom, %d triangles)" % len(tri), OUT / "openvsp_top.png", False)
    render(tri, (0, 2), 1, -1.0, "OpenVSP A321 union, side view", OUT / "openvsp_side.png", False)
    render(tri, (1, 2), 0, +1.0, "OpenVSP A321 union, front view (from +x)", OUT / "openvsp_front.png", False)
    # junction close-up with mesh edges drawn: wing root and tail region, top view
    sel = tri[(tri.mean(axis=1)[:, 0] > 15) & (tri.mean(axis=1)[:, 0] < 26) & (np.abs(tri.mean(axis=1)[:, 1]) < 4.5)]
    render(sel, (0, 1), 2, +1.0, "wing leading-edge root junction, top view with mesh edges", OUT / "openvsp_wing_root_mesh.png", True, (16.6, 19.4, 1.2, 3.4))
    sel = tri[(tri.mean(axis=1)[:, 0] > 34) & (np.abs(tri.mean(axis=1)[:, 1]) < 3)]
    render(sel, (0, 1), 2, +1.0, "tail cone with horizontal-tail root, top view with mesh edges", OUT / "openvsp_tail_mesh.png", True, (38.0, 44.6, -1.6, 3.2))
    print("rendered", [p.name for p in sorted(OUT.glob("openvsp_*.png"))])


if __name__ == "__main__":
    main()
