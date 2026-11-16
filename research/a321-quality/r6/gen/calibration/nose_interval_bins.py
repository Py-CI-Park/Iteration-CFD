# meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
# Source-available, not Open Source. Teaching and academic research are
# free; commercial and non-academic research require a licence.
# Enquiries: simul@msimul.com
# See LICENSE at the repository root.
# Provenance: see PROVENANCE.md. No GPL-licensed source was consulted.
"""Exact deviation of the R6-c fuselage nose binned by ledger interval, plus vertex x-row counts (orchestrator diagnostic 2026-11-16).

How to run: uv run --no-project --with numpy --with scipy --with trimesh --with rtree python nose_interval_bins.py <gen dir> <attempt dir>
"""
import sys
from pathlib import Path
import numpy as np
import trimesh
gen = Path(sys.argv[1]); att = Path(sys.argv[2])
sys.path.insert(0, str(gen))
import r6_io, r6_ledger
cand = r6_io.read_stl(att / "fuselage.stl").astype(np.float64)
ref = r6_io.read_stl(r6_ledger.R3_DIR / "fuselage.stl").astype(np.float64)
B = np.array([[1/3,1/3,1/3],[.5,.5,0],[0,.5,.5],[.5,0,.5],[2/3,1/6,1/6],[1/6,2/3,1/6],[1/6,1/6,2/3]])
def mesh(t): return trimesh.Trimesh(vertices=t.reshape(-1,3), faces=np.arange(len(t)*3).reshape(-1,3), process=False)
vx = np.unique(np.round(cand.reshape(-1,3)[:,0], 6))
print("candidate vertex x-rows in (0.001,0.25):", int(((vx>0.0011)&(vx<0.2499)).sum()), "in (0.25,0.498):", int(((vx>0.2501)&(vx<0.4979)).sum()))
rx = np.unique(np.round(ref.reshape(-1,3)[:,0], 6))
print("R3 vertex x-rows <0.6:", rx[rx<0.6].tolist())
for lab,(a,b) in (("cand->R3",(cand,ref)),("R3->cand",(ref,cand))):
    sel = a[a[:,:,0].mean(axis=1) < 1.0]
    pts = np.einsum("bk,nkd->nbd", B, sel).reshape(-1,3)
    _, d, _ = trimesh.proximity.closest_point(mesh(b), pts)
    for lo,hi in ((0,0.001),(0.001,0.25),(0.25,0.498),(0.498,1.0)):
        m = (pts[:,0]>=lo)&(pts[:,0]<hi)
        if m.any(): print(lab, f"x[{lo},{hi})", "n", int(m.sum()), "max mm", round(float(d[m].max())*1000,2), "over25", int((d[m]>0.025).sum()))
