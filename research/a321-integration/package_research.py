#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: uv run package_research.py; hashes study artifacts, never uploads reference native.
"""Record exact model/polyMesh evidence and clean derivative publication boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    """Stream exact file SHA256."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    """Track source identity and derived model/mesh artifacts, retaining failures locally."""
    source = Path(
        "D:/Chanil_Park/Project/Programming/Aircraft-Workbench/.workstation/models/a321/source-native/A321_NATIVE_G1B_LOCAL_NORMAL_ENCODING_RESEARCH.blend"
    )
    expected = "1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c"
    if digest(source) != expected:
        raise RuntimeError("ORIGINAL_CHANGED")
    records = []
    for folder in ("models", "artifacts"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file():
                records.append(
                    {
                        "path": path.relative_to(ROOT).as_posix(),
                        "bytes": path.stat().st_size,
                        "sha256": digest(path),
                        "publish_intended": folder == "models",
                    }
                )
    attempts = []
    for path in sorted((ROOT / "artifacts").glob("*.log")):
        if path.name.startswith("studio."):
            continue
        raw = path.read_text(encoding="utf8", errors="replace")
        attempts.append(
            {"path": path.name, "sha256": digest(path), "tail": raw.splitlines()[-18:]}
        )
    (ROOT / "evidence/attempt-ledger.json").write_text(
        json.dumps(attempts, indent=2), encoding="utf8"
    )
    report = {
        "study": "A321_STUDIO_LAYERS_20261106",
        "branch": "codex/a321-aero-shell-20261105",
        "base": "6d4bfed29618a5755898dbb9cd8fcd4d4e62656a",
        "source_sha256": expected,
        "source_unchanged": True,
        "source_uploaded": False,
        "files": records,
        "r3_native_reexport_byte_identical": digest(
            ROOT / "models/A321_AIRFRAME_SHELL_R3.stl"
        )
        == digest(ROOT / "artifacts/r3-reopened.stl"),
        "gpu_memory_diagnostic_executed": True,
        "gpu_arithmetic_kernel_executed": False,
        "aircraft_solver_executed": False,
        "mesh_status": "FIX_FIRST",
        "overall_status": "PARTIAL",
    }
    (ROOT / "evidence/artifact-manifest.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "files"}))


if __name__ == "__main__":
    main()
