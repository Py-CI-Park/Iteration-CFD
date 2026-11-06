#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "scipy", "pytest"]
# ///
# How to run: uv run --with pytest -m pytest test_jacobian.py
"""Analytic inversion detector tests before any new prism candidate is accepted."""

import numpy as np
import pytest
from build_layers import jacobian_minimum, require_positive_jacobians


@pytest.mark.parametrize("values", [[0.0], [-1.0], [float("nan")], [float("inf")]])
def test_rejected_layer_cannot_be_consumed(values):
    with pytest.raises(RuntimeError, match="LAYER_JACOBIAN_REJECTED"):
        require_positive_jacobians(np.array(values))


def test_straight_prism_positive_every_sample():
    # Given
    v = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0.1], [1, 0, 0.1], [0, 1, 0.1]], float
    )
    # When
    minimum = jacobian_minimum(v, np.array([[0, 1, 2, 3, 4, 5]]))
    # Then
    assert np.allclose(minimum, [0.1])


def test_one_corner_inside_wall_is_rejected():
    # Given
    v = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, -0.01], [1, 0, 0.1], [0, 1, 0.1]],
        float,
    )
    # When
    minimum = jacobian_minimum(v, np.array([[0, 1, 2, 3, 4, 5]]))
    # Then
    assert minimum[0] < 0


@pytest.mark.parametrize(
    "top,expected", [([-4.0, -7 / 3], -1 / 24), ([-3.0, -3.0], 0.0)]
)
def test_interior_minimum_between_old_sample_planes(top, expected):
    # J is positive at t=0, .5, 1, but has a negative/zero minimum at t=.25.
    v = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [top[0], 0, 1], [0, top[1], 1]],
        float,
    )
    minimum = jacobian_minimum(v, np.array([[0, 1, 2, 3, 4, 5]]))
    assert minimum[0] == pytest.approx(expected, abs=1e-14)
    with pytest.raises(RuntimeError, match="LAYER_JACOBIAN_REJECTED"):
        require_positive_jacobians(minimum)
