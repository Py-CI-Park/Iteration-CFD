#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cuda-python", "numpy"]
# ///
# How to run: set CUDA_VISIBLE_DEVICES to the pinned SUPER UUID, then uv run gpu_diagnostic.py
"""Bounded CUDA driver memory roundtrip on the specifically authorized GPU."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from cuda.bindings import driver as cu

ROOT = Path(__file__).resolve().parent
UUID = "GPU-2147afeb-b9fc-c7f5-398b-d5d00a3a5a90"


def checked(result: tuple):
    """Reject every CUDA error instead of continuing with unknown device state."""
    if result[0] != cu.CUresult.CUDA_SUCCESS:
        raise RuntimeError(f"CUDA_ERROR:{result[0]}")
    return result[1:]


def main() -> None:
    """Allocate 1GiB maximum, copy/verify a deterministic buffer, release context."""
    if os.environ.get("CUDA_VISIBLE_DEVICES") != UUID:
        raise RuntimeError("SUPER_UUID_NOT_PINNED")
    checked(cu.cuInit(0))
    (device,) = checked(cu.cuDeviceGet(0))
    (name,) = checked(cu.cuDeviceGetName(128, device))
    name = name.decode().split("\0")[0].strip()
    if "4080 SUPER" not in name:
        raise RuntimeError("WRONG_GPU")
    (context,) = checked(cu.cuDevicePrimaryCtxRetain(device))
    checked(cu.cuCtxSetCurrent(context))
    pointer = None
    try:
        free, total = checked(cu.cuMemGetInfo())
        count = 1024**3
        if free < count + 2 * 1024**3:
            raise RuntimeError("INSUFFICIENT_FREE_MEMORY_FOR_BOUNDED_TEST")
        (pointer,) = checked(cu.cuMemAlloc(count))
        pattern = np.arange(16 * 1024**2, dtype=np.uint32)
        returned = np.zeros_like(pattern)
        checked(cu.cuMemcpyHtoD(pointer, pattern.ctypes.data, pattern.nbytes))
        checked(cu.cuMemcpyDtoH(returned.ctypes.data, pointer, returned.nbytes))
        equal = bool(np.array_equal(pattern, returned))
        if not equal:
            raise RuntimeError("MEMORY_ROUNDTRIP_MISMATCH")
        checked(cu.cuMemFree(pointer))
        pointer = None
        free_after, _total_after = checked(cu.cuMemGetInfo())
        result = {
            "gpu": name,
            "requested_uuid": UUID,
            "device_logical_index": 0,
            "total_bytes": total,
            "free_before_bytes": free,
            "scratch_allocation_bytes": count,
            "verified_roundtrip_bytes": pattern.nbytes,
            "roundtrip_equal": equal,
            "free_after_release_bytes": free_after,
            "context_release_attempted": True,
            "scope": "driver allocation +64MiB HtoD/DtoH, no arithmetic kernel or aircraft solver",
            "solver_executed": False,
            "cuda_kernel_executed": False,
        }
    finally:
        if pointer is not None:
            checked(cu.cuMemFree(pointer))
        checked(cu.cuDevicePrimaryCtxRelease(device))
    (ROOT / "evidence/gpu-diagnostic.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
