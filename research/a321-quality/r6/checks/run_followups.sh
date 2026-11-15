#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Usage: bash run_followups.sh name [name ...]   (names from baseline_inputs.txt; needs logs/<name>-full-report.json)
set -u
cd "$(dirname "$0")"
root=../../../..
for name in "$@"; do
  path=$(grep "^$name=" baseline_inputs.txt | cut -d= -f2-)
  ( uv run --no-project followup_obj_coverage.py "$name" "$root/$path" logs "logs/followup-$name.json" > "logs/followup-$name.log" 2>&1 ) &
done
wait
