#!/usr/bin/env bash
# Sourced after cd to a fresh prepared trial. Atomic lock survives failures intentionally.
if [ -e constant/polyMesh ] || compgen -G 'processor[0-9]*' >/dev/null || compgen -G 'log.*' >/dev/null; then
    echo 'EXISTING_TRIAL_REFUSED'; exit 2
fi
if ! mkdir .execution.lock; then echo 'CONCURRENT_TRIAL_REFUSED'; exit 2; fi
sha256sum --check input-manifest.sha256 > .execution.lock/manifest-verification.txt
expected=2c0111c3bafd34b49b506325e52d13045f997aeaced11236f45b744f08abe745
actual=$(sha256sum constant/triSurface/aircraft.stl | cut -d ' ' -f 1)
if [ "$actual" != "$expected" ]; then echo 'R3_INPUT_CHANGED'; exit 2; fi
sha256sum constant/triSurface/aircraft.stl system/* > .execution.lock/inputs.sha256
printf '%s\n' 'CPU external mesh generation only; not a project quality acceptance or solver authorization.' > .execution.lock/scope.txt
