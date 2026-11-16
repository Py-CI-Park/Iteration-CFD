#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Usage (inside WSL): run_junction_r7.sh <tag> <abs-fuselage-stl> <abs-other-stl>
# OpenFOAM v1912 surfaceBooleanFeatures intersection on COPIES in a fresh mktemp -d dir under .worktmp/r7-gen/sbf (no -perturb).
# Derived from r6/gen/run_junction_gen.sh; only the scratch root differs. Prints the attempt directory as the last line.
set -eo pipefail
tag="$1"; a="$2"; b="$3"
root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/.worktmp/r7-gen/sbf
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
ulimit -f 20480
start=$(date +%s)
set +e
surfaceBooleanFeatures intersection fuselage.stl other.stl > result.log 2>&1
rc=$?
set -e
if [ "$rc" != "0" ]; then echo "SBF_EXIT_NONZERO rc=$rc" >> result.log; fi
end=$(date +%s)
sha256sum "$a" "$b" > after.sha256; cmp before.sha256 after.sha256
echo "wall_seconds $((end - start))" > wall.txt
rm -f constant/triSurface/fuselage.stl constant/triSurface/other.stl
echo "$attempt"
