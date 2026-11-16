#!/usr/bin/env bash
# Usage (inside WSL): run_surfacecheck_gen.sh <name> <abs-stl-path> <outputThreshold>
# Runs OpenFOAM v1912 surfaceCheck on a COPY of the STL in a fresh mktemp -d dir under gen/attempts (never on the original).
set -eo pipefail
name="$1"; stl="$2"; threshold="${3:-0}"
root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/r6/gen/attempts
mkdir -p "$root"
attempt=$(mktemp -d "$root/sc-${name}-XXXXXX")
set +e; source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1; set -e
cd "$attempt"; set -C
sha256sum "$stl" > before.sha256
cp --update=none "$stl" input.stl
sha256sum input.stl > copy.sha256
start=$(date +%s)
/usr/bin/time -p surfaceCheck -checkSelfIntersection -outputThreshold "$threshold" input.stl > result.log 2>&1 || echo "SURFACECHECK_EXIT_NONZERO" >> result.log
end=$(date +%s)
sha256sum "$stl" > after.sha256; cmp before.sha256 after.sha256
echo "wall_seconds $((end - start))" > wall.txt
rm -f input.stl
echo "$attempt"
