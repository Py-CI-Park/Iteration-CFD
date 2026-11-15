#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# Runs r6_gate.py once per baseline surface, all in parallel, one log + one JSON per surface.
# Usage: bash run_baselines.sh   (from this directory, Git Bash on Windows)
set -u
cd "$(dirname "$0")"
root=../../../..
mkdir -p logs
while IFS== read -r name path; do
  extra=""
  case "$name" in r4|r5_c|r5_a) extra="--deviation $name=$root/research/a321-integration/models/A321_AIRFRAME_SHELL_R3.stl";; esac
  (
    echo "START_UTC $(date -u +%FT%TZ)" > "logs/run-$name.log"
    s=$(date +%s.%N)
    uv run --no-project r6_gate.py --surface "$name=$root/$path" \
      --stations $root/research/a321-integration/evidence/reconstruction-r3.json $extra \
      --log-dir logs --out "logs/report-$name.json" >> "logs/run-$name.log" 2>&1
    echo "EXIT_CODE $?" >> "logs/run-$name.log"
    echo "WALL_SECONDS $(echo "$(date +%s.%N) - $s" | bc)" >> "logs/run-$name.log"
    echo "END_UTC $(date -u +%FT%TZ)" >> "logs/run-$name.log"
  ) &
done < baseline_inputs.txt
wait
