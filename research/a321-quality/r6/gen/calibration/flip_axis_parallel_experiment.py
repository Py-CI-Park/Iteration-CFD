# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy"]
# ///
"""Diagnostic experiment on a COPY: flip every exactly axis-parallel edge and re-run surfaceCheck (not a candidate).

Question: do the surfaceCheck self-intersection records that remain after the leaning strip (R6-b) disappear when the
exactly y-parallel ring edges of flat clips are flipped to the other quad diagonal? No ledger point moves; only the
connectivity of the copy changes. The candidate files are never modified. Result is appended to the output JSON.

How to run: python flip_axis_parallel_experiment.py --stl f.stl --tag name --out report.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import os
from pathlib import Path

import numpy as np

GEN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEN))
import r6_io

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MSYS_NO_PATHCONV="1")


def wsl(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def parallel_edges(v32: np.ndarray, faces: np.ndarray) -> set[tuple[int, int]]:
    e = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    d = v32[e[:, 1]] - v32[e[:, 0]]
    zero = (d == 0).sum(axis=1)
    return {(int(a), int(b)) for (a, b), z in zip(e, zero, strict=True) if z >= 2}


def flip_all(v: np.ndarray, faces: np.ndarray, targets: set[tuple[int, int]]) -> tuple[np.ndarray, int, int]:
    faces = faces.copy()
    directed = {}
    for fi, (a, b, c) in enumerate(faces):
        for u, w, o in ((a, b, c), (b, c, a), (c, a, b)):
            directed[(int(u), int(w))] = (fi, int(o))
    existing = {tuple(sorted(k)) for k in directed}
    flipped = skipped = 0
    for a, b in sorted(targets):
        if (a, b) in directed and (b, a) in directed:
            u, w = a, b
        else:
            skipped += 1
            continue
        f1, c = directed[(u, w)]
        f2, d = directed[(w, u)]
        if tuple(sorted((c, d))) in existing or c == d:
            skipped += 1
            continue
        n_old = [np.cross(v[faces[f][1]] - v[faces[f][0]], v[faces[f][2]] - v[faces[f][0]]) for f in (f1, f2)]
        t1, t2 = (u, d, c), (d, w, c)
        n_new = [np.cross(v[t[1]] - v[t[0]], v[t[2]] - v[t[0]]) for t in (t1, t2)]
        ref = n_old[0] / max(np.linalg.norm(n_old[0]), 1e-300) + n_old[1] / max(np.linalg.norm(n_old[1]), 1e-300)
        ok = all(np.linalg.norm(n) > 0 and float(np.dot(n, ref)) > 0 for n in n_new)
        if not ok:
            skipped += 1
            continue
        faces[f1], faces[f2] = t1, t2
        for key in ((u, w), (w, c), (c, u)):
            directed.pop(key, None)
        for key in ((w, u), (u, d), (d, w)):
            directed.pop(key, None)
        for fi, t in ((f1, t1), (f2, t2)):
            for p, q, o in ((t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1])):
                directed[(int(p), int(q))] = (fi, int(o))
        existing.discard(tuple(sorted((u, w))))
        existing.add(tuple(sorted((c, d))))
        flipped += 1
    return faces, flipped, skipped


def surface_check(tag: str, tri: np.ndarray) -> int:
    path = GEN / "calibration" / "stl" / f"{tag}.stl"
    path.parent.mkdir(parents=True, exist_ok=True)
    r6_io.write_stl(path, tri, tag)
    out = subprocess.run(["wsl", "bash", wsl(GEN / "run_surfacecheck_gen.sh"), f"flipexp-{tag}", wsl(path), "100"], env=ENV, capture_output=True, text=True).stdout.strip().splitlines()[-1]
    log = GEN / "attempts" / Path(out).name / "result.log"
    match = re.search(r"self-intersecting at (\d+) locations", log.read_text(errors="replace"))
    path.unlink()
    return int(match.group(1)) if match else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stl", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    v, f = r6_io.weld(r6_io.read_stl(args.stl))
    v32 = v.astype(np.float32)
    targets = parallel_edges(v32, f)
    before = len(targets)
    f2, flipped, skipped = flip_all(v, f, targets)
    after = len(parallel_edges(v32, f2))
    result = {"source": str(args.stl), "axis_parallel_edges_before": before, "flipped": flipped, "skipped": skipped, "axis_parallel_edges_after": after,
              "surfaceCheck_locations_after_flip": surface_check(args.tag, v[f2]), "note": "diagnostic copy only; candidate unchanged; no vertex moved"}
    args.out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
