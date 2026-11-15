#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Usage (inside WSL): run_surfacecheck_r6.sh <name> <abs-stl-path> <outputThreshold> [writeSets-format]
# Runs OpenFOAM v1912 surfaceCheck on a COPY of the STL inside a fresh mktemp -d attempt
# directory (surfaceCheck writes side files next to its input; the original is never a target).
set -eo pipefail
name="$1"; stl="$2"; threshold="$3"; sets="${4:-}"
checks=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/r6/checks
mkdir -p "$checks/attempts"
attempt=$(mktemp -d "$checks/attempts/sc-${name}-XXXXXX")
set +e; source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1; set -e
cd "$attempt"
set -C
sha256sum "$stl" > before.sha256
cp --update=none "$stl" input.stl
sha256sum input.stl > copy.sha256
args=(-checkSelfIntersection -outputThreshold "$threshold")
if [ -n "$sets" ]; then args+=(-writeSets "$sets"); fi
start=$(date +%s.%N)
/usr/bin/time -p surfaceCheck "${args[@]}" input.stl > result.log 2>&1 || echo "SURFACECHECK_EXIT_NONZERO" >> result.log
end=$(date +%s.%N)
sha256sum "$stl" > after.sha256
cmp before.sha256 after.sha256
echo "wrapper_wall_seconds $(echo "$end - $start" | bc)" > wall.txt
echo "$attempt"
