# CPU meshing investigation

R1 raw simplified discrete STL + box: Gmsh 4.15.2 PLC segment/facet intersection.
R2 surface classify/reparametrize: pathological partition recursion, many four-triangle patches. User-owned processes untouched; own run interrupted and command line inventory showed no descendant cpu_mesh.py.

Hypotheses: (1) simplified surface has very small/inexact intersections; (2) Gmsh discrete surface parameterization creates poor triangles; (3) PLC topology/orientation around the cavity is incompatible. Need independent PLC backend to distinguish. No quality threshold relaxed. Each attempt output folder/log is retained as research evidence, no scratch source instrumentation remains.
