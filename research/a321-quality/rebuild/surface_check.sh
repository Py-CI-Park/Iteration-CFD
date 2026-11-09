#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
set -eCo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
candidate="${1:-a}"
case "$candidate" in a|b) ;; *) exit 2 ;; esac
attempt="$(mktemp -d "$root/evidence/surface-check-r5-$candidate-XXXXXX")"
printf '%s\n' "$attempt"
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1
surfaceCheck -help > "$attempt/help.log" 2>&1
upper="$(printf '%s' "$candidate" | tr 'ab' 'AB')"
surfaceCheck -checkSelfIntersection -outputThreshold 0 "$root/artifacts/rebuild-r5-$candidate/A321_AIRFRAME_REBUILD_R5_$upper.stl" > "$attempt/result.log" 2>&1
