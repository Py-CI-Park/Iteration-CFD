#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# CPU mesh generation only. A failed lock is retained for investigation.
set -euo pipefail
main() {
    local runner root target
    runner="$(realpath -e -- "${BASH_SOURCE[0]}")"
    root="$(dirname -- "$runner")"
    case "${1:-}" in snappy-08|snappy-09|snappy-10) ;; *) echo INVALID_TRIAL >&2; return 2;; esac
    [[ "$#" == 1 || ( "$#" == 2 && "$2" == --inspect ) ]] || return 2
    target="$root/artifacts/$1"
    [[ "$(realpath -e -- "$target")" == "$target" ]] || return 2
    cd -- "$target"
    if [[ -e constant/polyMesh || -L constant/polyMesh ]] ||
        compgen -G 'processor*' >/dev/null || compgen -G 'log*' >/dev/null; then
        echo EXISTING_TRIAL_REFUSED >&2; return 2
    fi
    if [[ "${2:-}" == --inspect ]]; then
        printf 'runner=%s\ntarget=%s\nmode=READ_ONLY_INSPECTION_NOT_VALIDATION\n' "$runner" "$target"
        return 0
    fi
    mkdir .execution.lock || { echo CONCURRENT_TRIAL_REFUSED >&2; return 2; }
    cp -- "$runner" .execution.lock/runner.sh
    python3 - "$root" "$1" > .execution.lock/manifest-verification.txt <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root, name = Path(sys.argv[1]), sys.argv[2]
case = root / "artifacts" / name
r3 = "2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745"
baseline_sha = "a4bd8c95305eb5b71fd84c61400bac7c6c41e2e6d73be7cb19debdee8731c346"
systems = {"blockMeshDict", "controlDict", "decomposeParDict", "fvSchemes", "fvSolution", "snappyHexMeshDict", "surfaceFeatureExtractDict"}
surface = "constant/triSurface/aircraft.stl"
base = root / "artifacts/snappy-06"

def require(condition, reason):
    if not condition:
        raise SystemExit(reason)

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

require(digest(root.parent / "a321-integration/models/A321_AIRFRAME_SHELL_R3.stl") == r3, "CANONICAL_R3_CHANGED")
require(digest(base / "input-manifest.json") == baseline_sha, "BASELINE06_MANIFEST_CHANGED")
baseline = json.loads((base / "input-manifest.json").read_bytes())
expected = {surface, *("system/" + item for item in systems)}
require(baseline["legacy_post_run_snapshot"] is False and set(baseline["sha256"]) == expected, "INVALID_BASELINE")
require({p.name for p in (base / "system").iterdir()} == systems, "EXTRA_BASELINE_SYSTEM")
for relative, sha in baseline["sha256"].items():
    require(not (base / relative).is_symlink() and digest(base / relative) == sha, "BASELINE06_INPUT_CHANGED")
require(baseline["sha256"][surface] == r3, "BASELINE_NOT_R3")
baseline_lines = "".join(f"{sha}  {relative}\n" for relative, sha in baseline["sha256"].items())
require((base / "input-manifest.sha256").read_text() == baseline_lines, "BASELINE06_SIDECAR_CHANGED")
manifest_path = case / "input-manifest.json"
require(not manifest_path.is_symlink(), "MANIFEST_ALIAS")
data = json.loads(manifest_path.read_bytes())
require(set(data) == {"candidate", "plan", "source_path", "source_sha256", "baseline06_sha256", "canonical_r3_sha256", "geometry_receipt_sha256", "sha256"}, "INVALID_MANIFEST_FIELDS")
require(data["candidate"] == name and data["baseline06_sha256"] == baseline_sha and data["canonical_r3_sha256"] == r3, "TRIAL_IDENTITY_MISMATCH")
derivative = name in {"snappy-09", "snappy-10"}
inputs = expected | ({"geometry-receipt.json"} if derivative else set())
require(set(data["sha256"]) == inputs, "INCOMPLETE_OR_EXTRA_INPUTS")
require({p.name for p in (case / "system").iterdir()} == systems, "EXTRA_SYSTEM_INPUT")
lines = "".join(f"{sha}  {relative}\n" for relative, sha in data["sha256"].items())
lines += f"{digest(manifest_path)}  input-manifest.json\n"
require((case / "input-manifest.sha256").read_text() == lines, "MANIFEST_PIN_MISMATCH")
for relative, sha in data["sha256"].items():
    path = case / relative
    require(path.resolve().is_relative_to(case.resolve()) and not path.is_symlink(), "INPUT_ALIAS")
    require(digest(path) == sha, "TRIAL_INPUT_CHANGED: " + relative)
require(data["sha256"][surface] == data["source_sha256"], "SOURCE_SHA_MISMATCH")
if derivative:
    receipt = json.loads((case / "geometry-receipt.json").read_bytes())
    require(digest(case / "geometry-receipt.json") == data["geometry_receipt_sha256"], "RECEIPT_PIN_MISMATCH")
    require(receipt["source_sha256"] == r3 and receipt["stl_sha256"] == data["source_sha256"] != r3, "DERIVATIVE_RECEIPT_MISMATCH")
else:
    require(data["source_sha256"] == r3 and data["geometry_receipt_sha256"] is None, "R3_TRIAL_CHANGED")
for item in systems:
    content = (base / "system" / item).read_bytes()
    if item == "snappyHexMeshDict" and name in {"snappy-08", "snappy-10"}:
        require(content.count(b"minFaceWeight 0.02;") == 1, "BASELINE_FACE_WEIGHT_DRIFT")
        content = content.replace(b"minFaceWeight 0.02;", b"minFaceWeight 0.05;", 1)
    require((case / "system" / item).read_bytes() == content, "UNDECLARED_CONFIG_CHANGE: " + item)
for filename in ("input-manifest.json", "input-manifest.sha256"):
    with (case / ".execution.lock" / filename).open("xb") as stream:
        stream.write((case / filename).read_bytes())
print("INPUTS_VERIFIED_CPU_ONLY_NO_SOLVER_NO_GPU")
PY
    export FOAM_ETC=/usr/share/openfoam/etc
    export WM_PROJECT_DIR=/usr/share/openfoam
    export WM_PROJECT_VERSION=v1912
    blockMesh > log.blockMesh 2>&1
    surfaceFeatureExtract > log.features 2>&1
    decomposePar > log.decompose 2>&1
    mpirun --allow-run-as-root --oversubscribe -np 8 snappyHexMesh -parallel -overwrite > log.snappy 2>&1
    reconstructParMesh -constant > log.reconstruct 2>&1
    checkMesh -constant > log.checkMesh-standard 2>&1
    checkMesh -constant -allTopology -allGeometry > log.checkMesh-extended 2>&1
    tail -14 log.checkMesh-extended
    echo CPU_GENERATION_COMPLETE_NOT_ACCEPTANCE
}
main "$@"; exit $?
