# Focused M3 locator and map QA

Verdict: focused locator checks PASS; engineering M3 FAIL and diagnostic discrepancy remain retained. Final stable JSON, SVG, and PNG checks PASS.

## Executed checks

| Check | Actual result | Evidence |
|---|---|---|
| Supplied pytest suite, including crossing, shared-edge exclusion, disjoint, rational overlap beyond shared edge, normal shared diagonal | 5 passed in 18.24 s; exit 0; wrapper wall 60.6685054 s | `qa-review-tests.log` contains exact command/start/duration |
| Bounded independent vertex-order permutations | 216 assertions passed: 3 cases x 36 vertex permutation pairs x 2 algorithms; exit 0; wrapper wall 27.3970712 s | `qa-permutations.log` contains complete one-shot command |
| Initial JSON/local inspection/OBJ/SVG parse | 15 IDs in order, 14 unique coordinates, 15 OBJ vertex rows, coordinate rows match, 15 local-inspection records, before/after hashes equal, SVG root parsed | `qa-initial-artifact-parse.log`; explicitly initial snapshot |
| Initial PNG manual visual inspection | Top and side views readable; all IDs 1-15 appear, duplicate 1/2 combined visibly; title preserves unresolved discrepancy and M3 FAIL | `assembly-initial/c15-map.png`, viewed with image tool |

The independent permutation cases were an interior noncoplanar crossing, coplanar containment overlap without shared vertices, and separated parallel triangles. Each checked locator intersection presence and the exact rational auditor's beyond-contact classification. These are focused synthetic checks, not a global scan or proof of completeness.

## Findings and limits

No reproducible defect found by the executed focused tests. The locator intentionally excludes any pair sharing an exact vertex. Its zero count therefore establishes only its specified non-adjacent search result; the rational audit supplies a distinct local adjacent-contact check. The unresolved surfaceCheck count discrepancy cannot be closed by these green tests.

Final stable JSON/SVG parsed successfully: 15 ordered IDs, 15 OBJ rows, 14 unique coordinates, no coordinate mismatches, 15 local records, equal before/after hashes. Actual STL SHA was rehashed and matches the map. Both independent pair and cluster counts remain zero. Neutral radius_ratio_quality and rational audit fields are present; openfoam_shape_quality is absent. The final PNG was manually viewed again: readable top/side panels, IDs 1-15 with duplicate 1/2, unresolved discrepancy/M3 FAIL title. Evidence: qa-final-artifact-parse.log and qa-final-contract.log. Transient missing outputs during regeneration were not treated as final defects. No full 305k-facet scan, geometry modification, mesher, Blender, CFD, or GPU operation was run by this QA task. Only new `review-qa.md` and `qa-*` logs were written.

