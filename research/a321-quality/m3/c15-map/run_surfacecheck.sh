#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
set -eo pipefail
task_root=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight
attempt_dir=$(mktemp -d "$task_root/research/a321-quality/m3/c15-map/surfacecheck-XXXXXX")
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1
cd "$attempt_dir"
candidate="$task_root/research/a321-quality/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl"
set -C
sha256sum "$candidate" > before.sha256
cp --no-clobber "$candidate" input.stl
/usr/bin/time -p surfaceCheck -checkSelfIntersection -outputThreshold 100 -writeSets vtk input.stl > result.log 2>&1
sha256sum "$candidate" > after.sha256
cmp before.sha256 after.sha256
sha256sum input.stl > local-copy.sha256
pwd
ls -lh
tail -35 result.log
