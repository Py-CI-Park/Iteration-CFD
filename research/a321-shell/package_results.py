#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: uv run package_results.py (exact fixed study paths only).
"""Package generated derivatives for the user's public fork and retain custody receipts."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    """Stream exact SHA256."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    """Publish only the new derivative model and code, never the original reference native."""
    native = Path(
        "D:/Chanil_Park/Project/Programming/Aircraft-Workbench/.workstation/models/a321/source-native/A321_NATIVE_G1B_LOCAL_NORMAL_ENCODING_RESEARCH.blend"
    )
    expected = "1fd3cfd08b1dbf5e5f2fb288caf9846ad149ff8839a37cc2e4c2c8074bc1073c"
    if digest(native) != expected:
        raise RuntimeError("SOURCE_CHANGED")
    delivery = ROOT / "models"
    delivery.mkdir(exist_ok=True)
    for name in ("A321_AIRFRAME_SHELL_R2.blend", "A321_AIRFRAME_SHELL_R2.stl"):
        source = ROOT / "artifacts/shell-r2" / name
        target = delivery / name
        if target.exists() and digest(target) != digest(source):
            raise RuntimeError("DELIVERY_ALREADY_EXISTS_WITH_DIFFERENT_BYTES")
        if not target.exists():
            shutil.copyfile(source, target)
    for name in ("overview.png", "sections-r2.png"):
        target = ROOT / "evidence" / name
        if not target.exists():
            shutil.copyfile(ROOT / "artifacts" / name, target)
    logs = []
    for name in ("cpu-mesh.log", "cpu-mesh-r2.log", "meshpy.log"):
        source = ROOT / "artifacts" / name
        text = source.read_text(encoding="utf8", errors="replace")
        logs.append(
            {
                "name": name,
                "bytes": source.stat().st_size,
                "sha256": digest(source),
                "tail": text.splitlines()[-15:],
            }
        )
    (ROOT / "evidence/meshing-attempts.json").write_text(
        json.dumps(logs, indent=2), encoding="utf8"
    )
    files = []
    for folder in ("artifacts", "models"):
        for file in sorted((ROOT / folder).rglob("*")):
            if file.is_file():
                files.append(
                    {
                        "path": file.relative_to(ROOT).as_posix(),
                        "bytes": file.stat().st_size,
                        "sha256": digest(file),
                        "publish_intended": folder == "models",
                    }
                )
    report = {
        "study": "A321_AERO_SHELL_20261105",
        "source_sha256": expected,
        "source_unchanged": True,
        "source_uploaded": False,
        "files": files,
        "blender_reexport_byte_identical": digest(
            ROOT / "artifacts/shell-r2/blender-export.stl"
        )
        == digest(ROOT / "artifacts/shell-r2/reopened.stl"),
        "gpu_compute_executed": False,
        "solver_executed": False,
        "volume_mesh_executed": "CPU MeshPy/TetGen",
        "public_fork": "https://github.com/Py-CI-Park/Iteration-CFD",
        "branch": "codex/a321-aero-shell-20261105",
    }
    (ROOT / "evidence/artifact-manifest.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "files"}))


if __name__ == "__main__":
    main()
