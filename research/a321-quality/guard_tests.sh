#!/usr/bin/env bash
# Test execution custody using fresh isolated fixtures, no meshing or solver.
set -eo pipefail
study=/mnt/d/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality
root="$study/artifacts/guard-tests-01"
mkdir "$root"
guard="$study/guard_snappy.sh"
prepare() {
    mkdir -p "$1/constant/triSurface" "$1/system"
    cp "$study/artifacts/snappy-01/constant/triSurface/aircraft.stl" "$1/constant/triSurface/aircraft.stl"
    printf 'test only\n' > "$1/system/controlDict"
    (cd "$1"; sha256sum constant/triSurface/aircraft.stl system/* > input-manifest.sha256)
}
prepare "$root/race"
bash -ec 'cd "$1"; source "$2"; echo ACQUIRED; sleep 1' bash "$root/race" "$guard" > "$root/race-a.log" 2>&1 &
first=$!
bash -ec 'cd "$1"; source "$2"; echo ACQUIRED; sleep 1' bash "$root/race" "$guard" > "$root/race-b.log" 2>&1 &
second=$!
if wait "$first"; then a=0; else a=$?; fi
if wait "$second"; then b=0; else b=$?; fi
if ! { [ "$a" = 0 ] && [ "$b" = 2 ]; } && ! { [ "$a" = 2 ] && [ "$b" = 0 ]; }; then exit 3; fi
prepare "$root/existing"
mkdir "$root/existing/constant/polyMesh"
printf 'PRESERVE\n' > "$root/existing/constant/polyMesh/points"
if bash -ec 'cd "$1"; source "$2"' bash "$root/existing" "$guard" > "$root/existing.log" 2>&1; then exit 4; else existing=$?; fi
test "$existing" = 2
grep -q PRESERVE "$root/existing/constant/polyMesh/points"
prepare "$root/changed"
printf 'changed\n' >> "$root/changed/system/controlDict"
if bash -ec 'cd "$1"; source "$2"' bash "$root/changed" "$guard" > "$root/changed.log" 2>&1; then exit 5; else changed=$?; fi
test "$changed" != 0
printf '{"concurrent_exit_codes":[%s,%s],"existing_trial_exit":%s,"altered_input_exit":%s,"existing_bytes_preserved":true,"mesher_or_solver_run":false}\n' "$a" "$b" "$existing" "$changed" > "$study/evidence/guard-tests.json"
cat "$study/evidence/guard-tests.json"
