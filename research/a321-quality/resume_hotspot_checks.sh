#!/usr/bin/env bash
# Postprocess already completed CPU mesh generation; no decompose, remeshing, or flow solve.
set -euo pipefail
main() {
    export FOAM_ETC=/usr/share/openfoam/etc
    export WM_PROJECT_DIR=/usr/share/openfoam
    export WM_PROJECT_VERSION=v1912
    local root target
    root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
    case "${1:-}" in snappy-04|snappy-05) ;; *) echo INVALID_TRIAL >&2; return 2;; esac
    target="$root/artifacts/$1"
    [[ "$(realpath -e -- "$target")" == "$target" ]] || return 2
    cd -- "$target"
    grep -q '^Finished meshing' log.snappy
    if [[ -e log.reconstruct || -e log.checkMesh-standard || -e log.checkMesh-extended ]]; then
        echo EXISTING_POSTPROCESS_REFUSED >&2; return 2
    fi
    mkdir .postprocess.lock
    cp -- "${BASH_SOURCE[0]}" .postprocess.lock/runner.sh
    reconstructParMesh -constant > log.reconstruct 2>&1
    checkMesh -constant > log.checkMesh-standard 2>&1
    checkMesh -constant -allTopology -allGeometry > log.checkMesh-extended 2>&1
    tail -12 log.checkMesh-extended
    echo POSTPROCESS_COMPLETED_NOT_ACCEPTANCE
}
main "$@"
