#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: uv run plan_case.py (writes planning only; never invokes a solver).
"""Lock reference quantities and future wall-resolved boundary-layer feasibility estimates."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Measure wing exposed-hull planform and define explicit non-OEM normalization."""
    record = json.loads((ROOT / "evidence/reconstruction-r2.json").read_text())
    wing = next(p for p in record["parts"] if p["name"] == "wing")
    stations = np.array(wing["stations_m"])
    rings = np.array(wing["rings_2d_m"])
    chords = rings[:, :, 0].max(axis=1) - rings[:, :, 0].min(axis=1)
    area = 2 * float(np.trapezoid(chords, stations))
    mac = 2 * float(np.trapezoid(chords**2, stations)) / area
    speed, nu, rho = 30.0, 1.46e-5, 1.225
    re = speed * mac / nu
    cf = 0.455 / math.log10(re) ** 2.58
    utau = speed * math.sqrt(cf / 2)
    distance = nu / utau
    alpha = math.radians(2)
    result = {
        "status": "PLAN_ONLY_NOT_EXECUTED",
        "geometry": "R2 airframe-only symmetric derivative",
        "normalization": "both mirrored wing hull planforms integrated across Y including covered root; NOT OEM wing reference",
        "reference_area_m2": area,
        "mean_aerodynamic_chord_m": mac,
        "span_m": 2 * float(stations.max()),
        "speed_m_s": speed,
        "density_kg_m3": rho,
        "nu_m2_s": nu,
        "temperature_K": 288.15,
        "alpha_deg": 2,
        "beta_deg": 0,
        "velocity_m_s": [speed * math.cos(alpha), 0, speed * math.sin(alpha)],
        "drag_axis": [math.cos(alpha), 0, math.sin(alpha)],
        "lift_axis": [-math.sin(alpha), 0, math.cos(alpha)],
        "dynamic_pressure_Pa": 0.5 * rho * speed**2,
        "reynolds_mac": re,
        "wall_resolved_estimate": {
            "Cf_flatplate": cf,
            "u_tau_m_s": utau,
            "yplus1_centroid_distance_m": distance,
            "first_layer_thickness_estimate_m": 2 * distance,
            "note": "a priori correlation, not solved y+; expensive at full scale",
        },
        "recommended_next": "CPU prism/layer-capable meshing and independent ofgpu mesh gate; do not run current sliver tet mesh",
        "model_proposal": "lowmach coupled kOmegaSST; wall treatment and actual achieved layer spacing jointly reviewed",
        "boundary_proposal": {
            "inlet": "fixed U,k,omega; p zeroGradient; T fixed",
            "outlet": "p=0 kinematic reference, U zeroGradient with backflow policy review",
            "side_top_bottom": "farfield/slip approximation with inflow consistency review; no physical ground",
            "aircraft": "noSlip, zeroGradient p, isothermal/adiabatic irrelevant-energy choice locked",
        },
        "gpu_compute_authorized": False,
        "gpu_solver_executed": False,
    }
    (ROOT / "evidence/case-plan.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
