#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Pass 2: geometry-only metrics (no checkers) with the final station-exclusion code and the
# ring-derived demonstration features, one process per surface, in parallel.
set -u
cd "$(dirname "$0")"
root=../../../..
mkdir -p logs/pass2
while IFS== read -r name path; do
  [ "$name" = r3_union_artifact_copy ] && continue
  extra=""
  case "$name" in r4|r5_c|r5_a) extra="--deviation $name=$root/research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl";; esac
  (
    echo "START_UTC $(date -u +%FT%TZ)" > "logs/pass2/run-$name.log"
    uv run --no-project r6_gate.py --surface "$name=$root/$path" --checkers "" \
      --features features_r3_ring_derived.json \
      --stations $root/research/a321-integration/evidence/reconstruction-r3.json $extra \
      --log-dir logs/pass2 --out "logs/pass2/report-$name.json" >> "logs/pass2/run-$name.log" 2>&1
    echo "EXIT_CODE $?" >> "logs/pass2/run-$name.log"
    echo "END_UTC $(date -u +%FT%TZ)" >> "logs/pass2/run-$name.log"
  ) &
done < baseline_inputs.txt
wait
