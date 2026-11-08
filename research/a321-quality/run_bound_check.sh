#!/usr/bin/env bash
# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: public CLI, native output and Python stdlib; no GPL source consulted.
# Usage: bash research/a321-quality/run_bound_check.sh snappy-11
set -euo pipefail
case "${1:-}" in snappy-08|snappy-09|snappy-10|snappy-11) ;; *) exit 2;; esac
[[ "$#" == 1 ]] || exit 2
export FOAM_ETC=/usr/share/openfoam/etc
export WM_PROJECT_DIR=/usr/share/openfoam
export WM_PROJECT_VERSION=v1912
root="$(dirname -- "$(realpath -e -- "${BASH_SOURCE[0]}")")"
python3 - "$root" "$1" <<'PY'
from __future__ import annotations
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from collections.abc import Mapping

NAMES = ("points", "faces", "owner", "neighbour", "boundary")
COMMAND = ("checkMesh", "-constant", "-allTopology", "-allGeometry")


def sha(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def mesh(case: Path) -> Mapping[str, str]:
    return {name: sha(case / "constant/polyMesh" / name) for name in NAMES}


def sets(case: Path) -> Mapping[str, str]:
    folder = case / "constant/polyMesh/sets"
    if not folder.exists():
        return {}
    paths = sorted(folder.rglob("*"))
    if folder.resolve() != folder or any(p.is_symlink() for p in paths):
        raise RuntimeError("ALIASED_DIAGNOSTIC_SET")
    return {p.relative_to(folder).as_posix(): sha(p) for p in paths if p.is_file()}


def check_log(text: str, case: Path) -> None:
    commands = re.findall(r"^Exec\s*:\s*(.*)$", text, re.M)
    cases = re.findall(r"^Case\s*:\s*(.*)$", text, re.M)
    times = re.findall(r"^Time\s*=\s*(.*)$", text, re.M)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summaries = [i for i, line in enumerate(lines)
                 if re.fullmatch(r"Mesh OK\.|Failed [1-9][0-9]* mesh checks\.", line)]
    if (commands != [" ".join(COMMAND)] or cases != [case.as_posix()]
        or any(t.strip() != "constant" for t in times)
        or not lines or lines[-1] != "End" or lines.count("End") != 1
        or len(summaries) != 1 or summaries[0] != len(lines) - 2
        or re.search(r"FOAM FATAL|FOAM exiting|Segmentation fault|MPI_ABORT", text)):
        raise RuntimeError("WRONG_OR_INCOMPLETE_CONSTANT_CHECK")


def main() -> None:
    root = Path(sys.argv[1]).resolve()
    candidate = sys.argv[2]
    if candidate not in {"snappy-08", "snappy-09", "snappy-10", "snappy-11"}:
        raise RuntimeError("INVALID_CANDIDATE")
    source = root / "artifacts" / candidate
    clone = root / "artifacts" / (candidate + "-bound-check")
    evidence = root / "evidence"
    if source.resolve() != source or evidence.resolve() != evidence:
        raise RuntimeError("ALIASED_STUDY_PATH")
    old_log = source / "log.checkMesh-extended"
    old_raw = old_log.read_bytes()
    check_log(old_raw.decode("utf8"), source)
    before = mesh(source)
    source_sets = sets(source)
    destination = evidence / (candidate + "-bound-check.json")
    if destination.exists() or destination.is_symlink():
        raise RuntimeError("BOUND_RECEIPT_ALREADY_EXISTS")
    clone.mkdir(exist_ok=False)
    (clone / "constant/polyMesh").mkdir(parents=True)
    for name in NAMES:
        shutil.copyfile(source / "constant/polyMesh" / name,
                        clone / "constant/polyMesh" / name)
    shutil.copytree(source / "system", clone / "system")
    if (source / "constant/polyMesh/sets").exists():
        shutil.copytree(source / "constant/polyMesh/sets", clone / "constant/polyMesh/sets")
        shutil.copytree(source / "constant/polyMesh/sets", clone / "diagnostics-before")
    clone_before = mesh(clone)
    clone_sets_before = sets(clone)
    if clone_before != before or clone_sets_before != source_sets:
        raise RuntimeError("CLONE_COPY_MISMATCH")
    new_log = clone / "log.bound-check-extended"
    with new_log.open("xb") as handle:
        result = subprocess.run(COMMAND, cwd=clone, stdout=handle,
                                stderr=subprocess.STDOUT, check=False)
    after, clone_after = mesh(source), mesh(clone)
    source_sets_after, clone_sets_after = sets(source), sets(clone)
    complete = True
    try:
        check_log(new_log.read_text(encoding="utf8"), clone)
    except RuntimeError:
        complete = False
    unchanged = (before == after == clone_before == clone_after
                 and source_sets == source_sets_after == clone_sets_before == clone_sets_after
                 and old_log.read_bytes() == old_raw)
    status = "BOUND_REPLAY_COMPLETE" if complete and unchanged and result.returncode == 0 else "BOUND_REPLAY_INVALID"
    record = dict(schema_version=1, candidate=candidate, source_case=source.as_posix(),
                  clone_case=clone.as_posix(), command=list(COMMAND),
                  old_log_sha256=hashlib.sha256(old_raw).hexdigest(),
                  new_log_sha256=sha(new_log), source_mesh_before=before,
                  source_mesh_after=after, clone_mesh_before=clone_before,
                  clone_mesh_after=clone_after, source_sets_before=source_sets,
                  source_sets_after=source_sets_after, clone_sets_before=clone_sets_before,
                  clone_sets_after=clone_sets_after, returncode=result.returncode, status=status)
    with destination.open("x", encoding="utf8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": status, "receipt": str(destination), "clone": str(clone)}))
    if status != "BOUND_REPLAY_COMPLETE":
        raise SystemExit("Originals untouched; clone and diagnostics-before retained; no restoration attempted.")


if __name__ == "__main__":
    main()
PY
