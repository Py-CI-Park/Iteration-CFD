#!/usr/bin/env -S uv run --script
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "scipy", "trimesh", "rtree"]
# ///
# How to run: uv run --no-project test_r7_measure.py   (needs .worktmp/r7-trace/raw-trace.json and r7-measure.json)
"""Invariant checks on the phase-A measurement code and its outputs (plain asserts, no pytest)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import r7_embed as E
import r7_fitrun
import r7_model as M
import r7_profiles as P
import r7_r3 as R
import r7_trace_io as T

HERE = Path(__file__).resolve().parent


def synthetic_model() -> M.FuselageModel:
    """Barrel of width 3.95, height 4.14 and rho 0.5 with closed ends given by sqrt profiles (analytic stand-in)."""
    s = lambda x: np.sqrt(np.clip(1 - ((x - 22.2) / 22.2) ** 2, 0, 1))
    return M.FuselageModel(lambda x: 3.95 * s(x), lambda x: 4.02 + 2.07 * s(x), lambda x: 4.02 - 2.07 * s(x), 0.5)


def test_ring_vertices() -> None:
    m = synthetic_model()
    ring = m.ring(22.2, 128)
    assert ring.shape == (128, 3)
    assert abs(ring[:, 1].min() + 1.975) < 1e-9 and abs(ring[:, 1].max() - 1.975) < 1e-9, "max-width vertices"
    assert (np.abs(ring[:, 1]) < 1e-12).sum() == 2, "crown and belly vertices at y = 0"
    assert abs(ring[:, 2].max() - 6.09) < 1e-9 and abs(ring[:, 2].min() - 1.95) < 1e-9
    assert np.abs(m.implicit(ring)).max() < 1e-9, "ring points lie on the analytic surface"
    assert m.implicit(np.array([[22.2, 0.0, 4.02]]))[0] < 0 < m.implicit(np.array([[22.2, 0.0, 6.5]]))[0]


def test_distance_sign_and_value() -> None:
    m = synthetic_model()
    d = m.signed_distance_estimate(np.array([[22.2, 0.0, 6.0]]))[0]
    assert 0.05 < d < 0.12, d  # 0.09 m below the crown of an ellipse of semi-axes 1.975 x 2.07
    assert abs(E.exact_distance(m, np.array([22.2, 0.0, 6.0])) - d) < 5e-3
    assert abs(E.exact_distance(m, np.array([22.2, 0.0, 4.02])) - 1.975) < 1e-3  # centre: nearest wall is the side
    assert E.exact_distance(m, np.array([22.2, 0.0, 6.5])) < 0


def test_normalisation_and_outputs() -> None:
    raw = T.load_raw()
    r3 = R.load_r3_profile()
    cs = R.constant_section(r3, 1e-3)
    n = P.build_normalisation(raw, cs["crown_z"], cs["belly_z"])
    x = np.linspace(0, P.LENGTH_M, 44511)
    assert abs(n.width(x).max() - P.WIDTH_M) < 1e-5
    assert abs((n.crown(x) - n.belly(x)).max() - P.HEIGHT_M) < 1e-5
    assert abs(cs["rho_median"] - 0.5) < 1e-3
    out = json.loads((HERE / "r7-measure.json").read_text(encoding="utf-8"))
    assert out["trace"]["raw_trace_sha256"] == raw.sha256
    assert all(v["sha_ok"] for v in out["embedment"].values()), "reused component SHA changed"
    assert [out["embedment"][k]["junction"]["n_loops"] for k in ("wing", "horizontal", "vertical")] == [2, 2, 1]
    assert out["no_surface_generated"] is True


def test_fit_reproduces_extremes() -> None:
    raw = T.load_raw()
    r3 = R.load_r3_profile()
    cs = R.constant_section(r3, 1e-3)
    n = P.build_normalisation(raw, cs["crown_z"], cs["belly_z"])
    report, fits = r7_fitrun.run(n)
    x = np.linspace(0.001, 44.509, 90001)
    assert fits["w"](x).max() < 3.95 + 5e-4, "width overshoot above the printed maximum stays below 0.5 mm"
    assert report["curves"]["w"]["candidates"]["64"]["residual"]["max_abs_m"] < 0.01


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
