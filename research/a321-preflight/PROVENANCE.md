# Research source provenance

All scripts in this directory were written for the CPU-only A321 preflight on 2026-11-04. No solver numerics were changed. No GPL-licensed implementation was consulted or copied. Blender is invoked as a separate installed program and its public bpy API is used. numpy/scipy/matplotlib/stdlib APIs implement the measurements and plots.

| Files | Classification and purpose |
|---|---|
| inventory.py | Original scene metadata adapter |
| prepare_surface.py | Original selection/evaluated mesh/voxel trial orchestration; calls Blender modifier |
| surface_metrics.py | Original edge incidence, area, signed-volume measurements |
| test_surface_metrics.py | Original analytic tetrahedron/hole/reversal/duplicate/nonfinite tests |
| verify_stl.py | Original independent binary STL reader and connected-component measurement |
| reopen_candidate.py | Original fresh-process native readback and STL re-export |
| extract_wing.py | Original exact native subsystem extraction |
| plot_sections.py | Original triangle-plane intersection visualization |
| make_manifest.py | Original file SHA and custody ledger |
| custody.py, test_custody.py | Original no-overwrite output boundary and regression tests |
| build_report.py | Original fixed-target Markdown-to-HTML report builder |
| browser-*.mjs | Original Ego Lite browser actions and evidence receipts |

Geometry custody: Aircraft-Workbench's authored G1B native is an external, read-only research input. Its ownership/licensing and research HOLD are not replaced by this repository's source licence. No model is published or uploaded. Binary artifacts remain local under artifacts/; evidence references exact SHA256. NASA source text is retained as research evidence with URLs and access timestamps, not presented as original prose or approval of this study.

Known limits: edge incidence is not an intersection proof; nearest-distance samples are not Hausdorff bounds; signed volume of open meshes is not a physical enclosed volume; a closed wing box is not the full aircraft.
