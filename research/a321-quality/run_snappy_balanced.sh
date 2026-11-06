#!/usr/bin/env bash
set -eo pipefail
export FOAM_ETC=/usr/share/openfoam/etc
export WM_PROJECT_DIR=/usr/share/openfoam
export WM_PROJECT_VERSION=v1912
case_dir=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/artifacts/snappy-03
cd "$case_dir"
source /mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/guard_snappy.sh
blockMesh > log.blockMesh 2>&1
surfaceFeatureExtract > log.features 2>&1
decomposePar > log.decompose 2>&1
mpirun --allow-run-as-root --oversubscribe -np 8 snappyHexMesh -parallel -overwrite > log.snappy 2>&1
reconstructParMesh -constant > log.reconstruct 2>&1
checkMesh -constant > log.checkMesh-standard 2>&1
checkMesh -constant -allTopology -allGeometry > log.checkMesh-extended 2>&1
tail -35 log.checkMesh-standard
echo 'GENERATION_AND_DIAGNOSTICS_COMPLETE_NOT_ACCEPTANCE'
