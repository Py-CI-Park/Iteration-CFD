#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy"]
# ///
# How to run: imported by build_layers.py; unit tests in test_normals.py.
"""Find a local feasible outward extrusion direction for every incident face fan."""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def constrained_directions(
    normals: np.ndarray, incident: list[np.ndarray]
) -> np.ndarray:
    """Minimize direction norm with n_face dot d >=1; normalize after constraint solve."""
    result = []
    for indices in incident:
        fan = normals[indices]
        initial = fan.mean(axis=0)
        initial /= max(np.linalg.norm(initial), 1e-100)
        projections = fan @ initial
        if projections.min() > 0.35:
            result.append(initial)
            continue
        optimum = minimize(
            lambda d: 0.5 * np.dot(d, d),
            initial,
            jac=lambda d: d,
            constraints=[
                {
                    "type": "ineq",
                    "fun": lambda d, n=fan: n @ d - 1.0,
                    "jac": lambda d, n=fan: n,
                }
            ],
            method="SLSQP",
            options={"maxiter": 80, "ftol": 1e-10},
        )
        if not optimum.success or (fan @ optimum.x).min() < 0.999:
            raise RuntimeError("NO_COMMON_OUTWARD_FACE_CONE")
        direction = optimum.x / np.linalg.norm(optimum.x)
        result.append(direction)
    return np.array(result)
