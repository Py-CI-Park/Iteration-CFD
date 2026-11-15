# R6 gate suite provenance (scoped integration note)

All scripts here were authored for the 2026-11-16 worker brief `sonnet-r6-checks`. No GPL/LGPL/AGPL
source was read or copied.

- **OpenFOAM v1912** was used only as a separate CLI (`surfaceCheck`, in WSL, on a copy of each STL). Its
  help text, run logs and its per-triangle `quality` array were inspected. No OpenFOAM source was consulted.
  The triangle-quality formula `Q_OF = 4A / (3 sqrt(3) R^2)` was **fitted empirically** against the
  surfaceCheck `quality` array of the R3 fuselage (ratio 1 +/- 6e-8 over 46,592 triangles;
  `calibrate_quality_vs_surfacecheck.py`, `attempts/calibration-r3fuselage-writeSets/`).
- **PyMeshLab** (GPL-3.0) is called only from the separate process `r6_meshlab_worker.py`, which exchanges JSON
  with the gate. It is not imported by, and no code of it is copied into, any other file. Treat that worker as
  a GPL-adjacent tool when integrating: keep it a separate program, do not vendor it into the Rust crate.
- `trimesh`, `rtree`, `scipy`, `numpy` (permissive licences) are called through their public APIs.
- `locate_intersections.py` (existing, `research/a321-quality/m3/c15-map/`) is reused by import, unmodified.

| Source | Basis |
|---|---|
| r6_mesh.py | Original binary STL reader/writer, exact-value weld, edge table, component/Euler/winding/signed-volume code |
| r6_metrics.py | Original quality (fitted formula), size grading, dihedral, feature/station metrics, sampled deviation (trimesh closest_point) |
| r6_selfint.py | Original wrappers: locator import, PyMeshLab subprocess call, surfaceCheck WSL runner and log parser, OBJ point coverage |
| r6_meshlab_worker.py | Original thin driver around the public PyMeshLab filter `compute_selection_by_self_intersections_per_face` |
| r6_gate.py | Original CLI and orchestration |
| test_r6_gate.py | Original synthetic fixtures (tetra, icosphere, crossing/adjacent triangles, sliver, cube, lofted cylinders) |
| run_surfacecheck_r6.sh | Adapted procedure of `m3/c15-map/run_surfacecheck.sh` (fresh `mktemp -d` attempt, copy of the STL, SHA check) |
| run_baselines.sh, make_features_r3.py, calibrate_quality_vs_surfacecheck.py | Original helper scripts |

CONTRIBUTING asks for rows in `rust/PROVENANCE.md`. The worker brief forbids modifying existing files, so this
local ledger records the rows for the orchestrator to integrate; `rust/PROVENANCE.md` was not modified.
No solver equation, criterion, tolerance contract or published validation result changed.
