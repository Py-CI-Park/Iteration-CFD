#!/usr/bin/env bash
# External executables and public dictionaries only; no solver/GPU execution.
set -eo pipefail
# Ubuntu's split binary package has /usr/bin tools; upstream bashrc expects a missing bin/ tree.
export FOAM_ETC=/usr/share/openfoam/etc
export WM_PROJECT_DIR=/usr/share/openfoam
export WM_PROJECT_VERSION=v1912
case_dir=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/artifacts/snappy-01
cd "$case_dir"
source /mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/guard_snappy.sh
blockMesh > log.blockMesh 2>&1
surfaceCheck constant/triSurface/aircraft.stl > log.surfaceCheck 2>&1
surfaceFeatureExtract > log.features 2>&1
decomposePar > log.decompose 2>&1
mpirun --allow-run-as-root --oversubscribe -np 8 snappyHexMesh -parallel -overwrite > log.snappy 2>&1
reconstructParMesh -constant > log.reconstruct 2>&1
checkMesh -constant -allTopology -allGeometry > log.checkMesh 2>&1
tail -45 log.checkMesh
echo 'GENERATION_AND_DIAGNOSTICS_COMPLETE_NOT_ACCEPTANCE'
