# R6 drawing reference provenance (scoped integration note)

Authored for the 2026-11-16 worker brief `sonnet-r6-ref`. No GPL/LGPL/AGPL source was read or copied.

- Source drawing: Airbus "A321 Aircraft Characteristics – Airport and Maintenance Planning" (general dimensions
  pages), read from the locally stored PDF. Only printed dimension values and the page scale (7.9494 pt/m) were
  extracted. Page rasters and Blender overlays are kept outside the repository (copyright) and are not committed.
- `build_reference_scene.py` imports `bpy` and carries `SPDX-License-Identifier: GPL-2.0-or-later`; it runs only
  inside Blender as a separate program.
- **PyMuPDF (AGPL-3.0 or commercial licence) is imported directly by `extract_drawing_dims.py`.** No PyMuPDF
  source was read or copied, but the script links it at run time, so treat it as an AGPL-adjacent research tool:
  run it as a separate program, keep it out of the Rust crate and of any distributed product, or replace it with a
  permissively licensed PDF reader before integration. Flagged by the orchestrator 2026-11-16.
- `numpy`, `shapely`, `pillow`, `trimesh` (permissive) are used through public APIs.

| Source | Basis |
|---|---|
| extract_drawing_dims.py | Original extraction of printed dimension values and scale (imports PyMuPDF, AGPL) |
| measure_models.py | Original measurement of R3/R5-C/R6 models against the extracted dimensions |
| make_figures.py | Original SVG comparison figures |
| build_reference_scene.py | Original GPL-2.0-or-later Blender reference-scene adapter, separate program |

No solver equation, criterion, tolerance contract or published validation result changed.
