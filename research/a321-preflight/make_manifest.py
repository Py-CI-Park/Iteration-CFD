#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# ─── How to run ───
# uv run make_manifest.py RESEARCH_ROOT
# Original file-custody ledger, CPU hashing only.
"""Record exact artifacts and fail if protected source identity has changed."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    """Stream a file digest without loading large models into RAM."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    """Write exact byte ledger and source/round-trip invariants."""
    root = Path(sys.argv[1]).resolve()
    if root != Path(__file__).resolve().parent:
        raise RuntimeError("MANIFEST_ROOT_MISMATCH")
    source = Path(
        "D:/Chanil_Park/Project/Programming/Aircraft-Workbench/.workstation/models/a321/source-native/A321_NATIVE_G1B_LOCAL_NORMAL_ENCODING_RESEARCH.blend"
    )
    expected = "1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c"
    frozen = root / "artifacts/input/A321_G1B_FROZEN.blend"
    if sha256(source) != expected or sha256(frozen) != expected:
        raise RuntimeError("PROTECTED_SOURCE_OR_FROZEN_HASH_MISMATCH")
    files = [p for p in (root / "artifacts").rglob("*") if p.is_file()]
    rows = [
        {
            "path": str(p.relative_to(root)).replace("\\", "/"),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        }
        for p in sorted(files)
    ]
    wing = root / "artifacts/wing-subsystem"
    trial = root / "artifacts/trial-v040"
    result = {
        "study_id": "A321-CPU-PREFLIGHT-20261104",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source),
        "source_bytes": source.stat().st_size,
        "source_sha256": sha256(source),
        "frozen_sha256": sha256(frozen),
        "source_unchanged": True,
        "frozen_matches_source": True,
        "wing_stl_reexport_byte_identical": sha256(wing / "wing-fixed-box.stl")
        == sha256(wing / "reopened.stl"),
        "trial040_stl_reexport_byte_identical": sha256(trial / "candidate.stl")
        == sha256(trial / "reopened.stl"),
        "gpu_compute_executed": False,
        "solver_executed": False,
        "volume_mesh_generated": False,
        "files": rows,
    }
    for folder, name in [
        (wing, "wing-reopened.json"),
        (trial, "trial040-reopened.json"),
    ]:
        (root / "evidence" / name).write_bytes((folder / "reopened.json").read_bytes())
    (root / "evidence/artifact-manifest.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "files"}))


if __name__ == "__main__":
    main()
