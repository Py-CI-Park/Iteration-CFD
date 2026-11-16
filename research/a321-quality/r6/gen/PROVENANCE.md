# R6 generator provenance (scoped integration note)

Authored for the 2026-11-16 worker brief `sonnet-r6-gen` plus one orchestrator diagnostic. No GPL/LGPL/AGPL
source was read or copied.

- **Blender 5.2.2** (GPL) is driven only by the separate adapter `blender_r6.py`, which runs inside Blender's
  own Python (`blender --background --python`) and carries `SPDX-License-Identifier: GPL-2.0-or-later` because
  it imports `bpy`. It exchanges files (NPZ/STL/JSON) with the rest of the pipeline. No other file imports it.
  Keep it a separate program when integrating; do not vendor it into the Rust crate.
- **OpenFOAM v1912** (`surfaceCheck`, `surfaceBooleanFeatures`) is used only as a separate CLI in WSL on copies.
- **PyMeshLab** (GPL-3.0) is reached only through `../checks/r6_meshlab_worker.py` as a separate process.
- `numpy`, `scipy`, `trimesh`, `rtree` (permissive) are used through public APIs.
- Interpolation: textbook C2 cubic splines and the Fritsch-Carlson monotone C1 method
  (Fritsch & Carlson, SIAM J. Numer. Anal. 17(2), 1980), implemented from the published description.

| Source | Basis |
|---|---|
| r6_ledger.py, r6_io.py | Original R3 ledger loader and binary STL reader/writer |
| r6_splines.py, r6_lines.py, r6_sections.py, r6_grid.py | Original C2 / Fritsch-Carlson interpolation, grid lines, sections, ring columns |
| r6_kinks.py, r6_tess.py, r6_flip.py | Original 2-degree kink rule, leaning-strip tessellation, axis-parallel edge flip |
| r6_dev.py, dev_stats.py, locate_deviation.py | Original deviation helpers (k-nearest-centroid search, over-estimates only) |
| build_r6.py, run_pipeline.py, check_r6.py, make_refs.py, a3_reference.py, display_union.py, junction_analysis.py | Original orchestration, gate table, full-span references, drawing band, junction analysis |
| blender_r6.py | Original GPL-2.0-or-later Blender adapter (bpy), separate program |
| test_build_r6.py | Original synthetic tests |
| calibration/*.py | Original diagnostics; `dense_component_deviation.py` added by the orchestrator 2026-11-16 (exact trimesh closest_point) |

CONTRIBUTING asks for rows in `rust/PROVENANCE.md`; this local ledger records them for later integration.
No solver equation, criterion, tolerance contract or published validation result changed.
