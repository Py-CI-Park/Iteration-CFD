# R7 fuselage phase A (measurements for contract 03a) provenance (scoped integration note)

Authored for the 2026-11-16 worker brief `sonnet-r7-fuselage` (phase A only). No GPL/LGPL source was read or copied.
No fuselage surface, mesh, STL or OBJ was generated; no mesher, solver, VSPAERO or GPU was run.

- Source drawing: Airbus "A321 Aircraft Characteristics - Airport and Maintenance Planning" (PDF pages 73 and 74, 1-based),
  SHA-256 `50ae7a11b9834cbb1b0f8b862fcb6e85aa7817e77596cd12903033e81456d40d`, read from the local copy under
  `Aircraft-Workbench/.migration/bridge/blobs/` (the path in the brief lacked the `Programming/` level). The raw traced
  polylines and page rasters are Airbus copyright and stay in the git-excluded `.worktmp/r7-trace/`; this folder holds only
  fitted parameters, residual statistics, drawing indices and the SHA-256 of the raw trace file.
- **`trace_drawing.py` imports PyMuPDF (AGPL-3.0 or commercial licence).** It is a separate trace program; no other R7 script
  imports PyMuPDF (`r7_trace_io.py` reads only its JSON output). No PyMuPDF source was read or copied. Keep it out of any
  distributed product, or replace it with a permissively licensed PDF reader before integration.
- `shapely` (BSD) is used inside the trace program only. `numpy`, `scipy`, `trimesh`, `rtree`, `matplotlib` (permissive) are used
  through public APIs. Interpolation reuses the repository modules `research/a321-quality/r6/gen/r6_splines.py`,
  `r6_io.py`, `r6_ledger.py` read-only (Fritsch-Carlson C1 monotone fallback, STL reader, R3 ledger).
- Methods are textbook: cubic B-spline least squares (De Boor), curve-length/curvature equidistribution of knots, first-order
  distance to an implicit surface F/|grad F|, local Nelder-Mead minimisation for exact point-to-surface distance, marching
  triangles on a vertex field for the junction loops.
- Local data used read-only: reused component STLs (`r6-c/attempt01`, SHA-256 checked equal to contract 03), R3 ledger and
  R3 `fuselage.stl`.

| Source | Basis |
|---|---|
| trace_drawing.py | Original stroke-path trace of the fuselage outline from the vector paths (imports PyMuPDF, AGPL) |
| r7_trace_io.py | Original loader of the raw trace JSON; splits the four outline branches |
| r7_profiles.py | Original M2 normalisation (length 44.51, width 3.95, height 4.14, R3 z frame) |
| r7_r3.py | Original read-only measurement of the R3 ledger constant section and rho |
| r7_consistency.py | Original drawing self-consistency measurements (symmetry, scale, line, length) |
| r7_compare.py | Original normalised outline vs R3 comparison by x region |
| r7_fit.py, r7_fitrun.py | Original LSQ cubic B-spline fits, knot rule, residual, overshoot and Fritsch-Carlson fallback statistics |
| r7_model.py | Original analytic two-half-ellipse fuselage model (implicit function, ring points); no mesh |
| r7_rings.py | Original ring spacing rule, 02a paper check from ring-point coordinates, deviation estimate (nothing written to disk) |
| r7_embed.py | Original A5 root embedment and junction-loop analysis against the analytic fuselage |
| run_measure.py | Original driver; writes `r7-measure.json` |
| make_figures.py | Original SVG figures (fitted curves and residual statistics only) |
| test_r7_measure.py | Original invariant checks |

No solver equation, criterion, tolerance contract or published validation result changed.
