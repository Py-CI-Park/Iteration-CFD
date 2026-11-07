#!/usr/bin/env bash
set -euo pipefail
main() {
    export FOAM_ETC=/usr/share/openfoam/etc
    export WM_PROJECT_DIR=/usr/share/openfoam
    export WM_PROJECT_VERSION=v1912
    local root target runner
    runner="$(realpath -e -- "${BASH_SOURCE[0]}")"
    root="$(dirname -- "$runner")"
    case "${1:-}" in snappy-06|snappy-07) ;; *) echo INVALID_TRIAL >&2; return 2;; esac
    target="$root/artifacts/$1"
    [[ "$(realpath -e -- "$target")" == "$target" ]] || return 2
    if [[ "${2:-}" == "--inspect" ]]; then
        printf 'runner=%s\ntarget=%s\nmode=READ_ONLY_INSPECTION\n' "$runner" "$target"
        return 0
    fi
    [[ "$#" == 1 ]] || return 2
    cd -- "$target"
    source "$root/guard_snappy.sh"
    cp -- "$runner" .execution.lock/runner.sh
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
