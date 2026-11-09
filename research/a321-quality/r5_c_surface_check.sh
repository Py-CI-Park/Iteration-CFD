#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 Iterations Co., Ltd.
# Source-available, not Open Source; see LICENSE at repository root.
# Teaching and academic research are free; commercial/non-academic research require a licence.
# Enquiries: simul@msimul.com
# Provenance: public external CLI only; no GPL implementation source consulted.
set -eo pipefail
root="$(dirname -- "$(realpath -e -- "${BASH_SOURCE[0]}")")"
source /usr/share/openfoam/etc/bashrc >/dev/null 2>&1
set -uC
input="$root/rebuild/artifacts/rebuild-r5-c/A321_AIRFRAME_REBUILD_R5_A.stl"
# The fixed export basename is retained by the copied trial; receipt/candidate path identify C.
[[ -f "$input" ]] || exit 2
sha256sum "$input" > "$root/evidence/r5-c-selfcheck-before.sha256"
surfaceCheck -checkSelfIntersection -outputThreshold 0 "$input" > "$root/evidence/r5-c-surfaceCheck.log" 2>&1
sha256sum "$input" > "$root/evidence/r5-c-selfcheck-after.sha256"
cmp "$root/evidence/r5-c-selfcheck-before.sha256" "$root/evidence/r5-c-selfcheck-after.sha256"
tail -25 "$root/evidence/r5-c-surfaceCheck.log"
