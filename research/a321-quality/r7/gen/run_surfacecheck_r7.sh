#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Usage (inside WSL): run_surfacecheck_r7.sh <name> <abs-stl-path> <outputThreshold>
# Runs OpenFOAM v1912 surfaceCheck -checkSelfIntersection on a COPY of the STL inside a fresh mktemp -d directory under
# .worktmp/r7-gen/sc (surfaceCheck writes side files next to its input; the original is never a target).
# Prints the attempt directory as the last line. Wall time is measured with date.
set -eo pipefail
name="$1"; stl="$2"; threshold="${3:-100000}"
root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/.worktmp/r7-gen/sc
mkdir -p "$root"
attempt=$(mktemp -d "$root/sc-${name}-XXXXXX")
set +e; source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1; set -e
cd "$attempt"
set -C
sha256sum "$stl" > before.sha256
cp --update=none "$stl" input.stl
sha256sum input.stl > copy.sha256
ulimit -f 20480
start=$(date +%s.%N)
set +e
/usr/bin/time -p surfaceCheck -checkSelfIntersection -outputThreshold "$threshold" input.stl > result.log 2>&1
rc=$?
set -e
if [ "$rc" != "0" ]; then echo "SURFACECHECK_EXIT_NONZERO rc=$rc" >> result.log; fi
end=$(date +%s.%N)
sha256sum "$stl" > after.sha256
cmp before.sha256 after.sha256
echo "wrapper_wall_seconds $(echo "$end - $start" | bc)" > wall.txt
echo "$attempt"
