#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Usage (inside WSL): run_surfacecheck_r7.sh <name> <abs-stl-path> [outputThreshold]
# OpenFOAM v1912 surfaceCheck on a COPY of the STL in a fresh mktemp -d directory under r7/openvsp/sc/attempts
# (same procedure as r6/checks/run_surfacecheck_r6.sh; only the attempt directory differs so that nothing is
# written outside r7/openvsp). The original STL is never a target; its SHA-256 is compared before and after.
set -eo pipefail
name="$1"; stl="$2"; threshold="${3:-0}"
root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/r7/openvsp/sc/attempts
mkdir -p "$root"
attempt=$(mktemp -d "$root/sc-${name}-XXXXXX")
set +e; source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1; set -e
cd "$attempt"; set -C
sha256sum "$stl" > before.sha256
cp --update=none "$stl" input.stl
sha256sum input.stl > copy.sha256
start=$(date +%s.%N)
/usr/bin/time -p surfaceCheck -checkSelfIntersection -outputThreshold "$threshold" input.stl > result.log 2>&1 || echo "SURFACECHECK_EXIT_NONZERO" >> result.log
end=$(date +%s.%N)
sha256sum "$stl" > after.sha256; cmp before.sha256 after.sha256
echo "wrapper_wall_seconds $(echo "$end - $start" | bc)" > wall.txt
rm -f input.stl
echo "$attempt"
