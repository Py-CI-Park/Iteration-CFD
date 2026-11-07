#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pydantic>=2", "typer", "pytest"]
# ///
# How to run: uv run --with numpy --with pydantic --with typer --with pytest pytest research/a321-quality/test_owner_diagnostic.py -q
"""Check the exact reduction meaning used by the visualization-only case."""

import numpy as np
import pytest
from diagnostic_owner_view import owner_minimum


def test_shared_owner_uses_minimum_and_leaves_nonwall_unknown():
    # Given two conflicting faces at owner 0 and one face at owner 1.
    owners = np.array([0, 1, 0], dtype=np.int64)
    counts = np.array([8.0, 4.0, 0.0])
    # When deriving the explicitly named conservative volume diagnostic.
    values, ambiguous = owner_minimum(owners, counts, 3)
    # Then no maximum is misrepresented as an exact face value.
    assert values.tolist() == [0, 4, -1]
    assert ambiguous.tolist() == [True, False, True]


@pytest.mark.parametrize("counts", [[float("nan")], [-1.0], [9.0], [1.5]])
def test_invalid_layer_values_are_rejected(counts):
    with pytest.raises(RuntimeError, match="INVALID_OWNER"):
        owner_minimum(np.array([0]), np.array(counts), 1)
