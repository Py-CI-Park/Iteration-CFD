#!/usr/bin/env bash
set -euo pipefail
main() {
export FOAM_ETC=/usr/share/openfoam/etc
export WM_PROJECT_DIR=/usr/share/openfoam
export WM_PROJECT_VERSION=v1912
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
case "${1:-}" in snappy-04|snappy-05) ;; *) echo 'INVALID_TRIAL' >&2; exit 2;; esac
target="$root/artifacts/$1"
if [[ "$(realpath -e -- "$target")" != "$target" ]]; then
    echo 'TRIAL_PATH_ESCAPE' >&2
    exit 2
fi
cd -- "$target"
source "$root/guard_snappy.sh"
blockMesh > log.blockMesh 2>&1
surfaceFeatureExtract > log.features 2>&1
decomposePar > log.decompose 2>&1
mpirun --allow-run-as-root --oversubscribe -np 8 snappyHexMesh -parallel -overwrite > log.snappy 2>&1
reconstructParMesh -constant > log.reconstruct 2>&1
checkMesh -constant > log.checkMesh-standard 2>&1
checkMesh -constant -allTopology -allGeometry > log.checkMesh-extended 2>&1
tail -12 log.checkMesh-extended
echo GENERATION_AND_DIAGNOSTICS_COMPLETE_NOT_ACCEPTANCE
}
main "$@"; exit $?
