#!/usr/bin/env bash
# Usage (inside WSL): run_junction_gen.sh <tag> <abs-fuselage-stl> <abs-other-stl>
# OpenFOAM v1912 surfaceBooleanFeatures intersection on COPIES in a fresh mktemp -d dir under gen/attempts (no -perturb).
set -eo pipefail
tag="$1"; a="$2"; b="$3"
root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/r6/gen/attempts
mkdir -p "$root"
attempt=$(mktemp -d "$root/sbf-${tag}-XXXXXX")
set +e; source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1; set -e
cd "$attempt"; set -C
mkdir system
cat > system/controlDict <<CD
FoamFile { version 2.0; format ascii; class dictionary; object controlDict; }
application surfaceBooleanFeatures; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1; writeControl timeStep; writeInterval 1;
CD
sha256sum "$a" "$b" > before.sha256
mkdir -p constant/triSurface; cp --update=none "$a" constant/triSurface/fuselage.stl; cp --update=none "$b" constant/triSurface/other.stl
start=$(date +%s)
surfaceBooleanFeatures intersection fuselage.stl other.stl > result.log 2>&1 || echo "SBF_EXIT_NONZERO" >> result.log
end=$(date +%s)
sha256sum "$a" "$b" > after.sha256; cmp before.sha256 after.sha256
echo "wall_seconds $((end - start))" > wall.txt
rm -f constant/triSurface/fuselage.stl constant/triSurface/other.stl
echo "$attempt"
