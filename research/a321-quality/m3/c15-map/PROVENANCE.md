# M3-a source provenance (scoped integration note)

All scripts here were authored for the 2026-11-09 worker brief. No GPL/LGPL/AGPL
source was read or copied. OpenFOAM v1912 was used only as a separate CLI; its
help, run log and point output were inspected. No OpenFOAM source was consulted.

| Source | Basis |
|---|---|
| locate_intersections.py | Original binary STL parser, Rtree broad phase, analytic plane cuts, line-interval intersection and convex polygon clipping |
| exact_contacts.py | Original exact Fraction arithmetic: plane orientation, edge intersection, convex half-plane clipping and shared-topology audit |
| inspect_locations.py | Original local AABB/closest-point diagnostic; analytic triangle edge/area/shape metrics; trimesh public API |
| assemble_map.py | Original source-ledger bounds/station mapping, candidate normal-angle calculation, rational contact audit and Matplotlib projection |
| test_locate_intersections.py | Original synthetic crossing, adjacency, separation and rational-overlap fixtures |
| run_logged.ps1 | Original bounded command capture with duration/exit status |
| run_surfacecheck.sh | Worker brief fresh-attempt procedure, installed CLI help flags, safe local STL copy |
| write_report.ps1 | Original Korean report assembly from diagnostic JSON, command logs and observed evidence |

CONTRIBUTING asks for rows in `rust/PROVENANCE.md`. The worker brief forbids
modifying any existing file. This new local ledger records the rows for the
orchestrator to integrate later; `rust/PROVENANCE.md` was not modified. No solver
equation, criterion, tolerance contract or published validation result changed.
