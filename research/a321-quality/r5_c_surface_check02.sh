#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
# See LICENSE at repository root. Public external CLI only.
set -eo pipefail
root="$(dirname -- "$(realpath -e -- "${BASH_SOURCE[0]}")")"
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1
set -uC
input="$root/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_B.stl"
[[ -f "$input" ]] || exit 2
sha256sum "$input" > "$root/evidence/r5-c-check02-before.sha256"
surfaceCheck -checkSelfIntersection -outputThreshold 0 "$input" > "$root/evidence/r5-c-check02.log" 2>&1
sha256sum "$input" > "$root/evidence/r5-c-check02-after.sha256"
cmp "$root/evidence/r5-c-check02-before.sha256" "$root/evidence/r5-c-check02-after.sha256"
tail -25 "$root/evidence/r5-c-check02.log"
