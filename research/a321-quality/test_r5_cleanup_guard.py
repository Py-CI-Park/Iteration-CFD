# /// script
# requires-python = ">=3.12"
# dependencies = ["pytest","numpy","scipy","trimesh","manifold3d","rtree"]
# ///
# How to run: uv run --with pytest --with numpy --with scipy --with trimesh --with manifold3d --with rtree -m pytest test_r5_cleanup_guard.py
"""A library's effective tolerance cannot silently exceed the declared experiment."""
import pytest
from r5_cleanup_trial import CleanupRejected, check_tolerance

def test_effective_tolerance_excess_rejected() -> None:
    # Given library raises effective tolerance; When checked; Then refuse.
    with pytest.raises(CleanupRejected, match="EFFECTIVE_TOLERANCE"):
        check_tolerance(1e-6, 1e-5)

def test_declared_tolerance_accepted() -> None:
    # Given actual at declared ceiling; When checked; Then proceed.
    check_tolerance(1e-6,1e-6)

def test_nonfinite_tolerance_rejected() -> None:
    # Given invalid library value; When checked; Then refuse.
    with pytest.raises(CleanupRejected, match="EFFECTIVE_TOLERANCE"):
        check_tolerance(1e-6,float("nan"))
