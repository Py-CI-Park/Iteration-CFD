"""Dev helper: quick quality stats of an attempt directory (numpy; imports r6_metrics from ../checks)."""
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "checks"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r6_metrics as M, build_r6 as B
for n in ('fuselage','wing','horizontal','vertical'):
    d=np.load(f'{sys.argv[1]}/{n}.npz'); v=d['vertices']; f=d['faces']
    t=M.triangle_quality(v,f); q=t['q_of']; a=t['min_angle_deg']; ar=t['aspect']; val=B.valence(f,len(v))
    print(n,len(f),'Qmin %.2e p1 %.3f'%(q.min(),np.percentile(q,1)),'angmin %.2f p5 %.1f'%(a.min(),np.percentile(a,5)),'aspect max %.0f p99 %.1f'%(ar.max(),np.percentile(ar,99)),'maxval',val.max(),'n>8',(val>8).sum())
import r6_mesh
print('--- adjacent area ratio / dihedral')
for n in ('fuselage','wing','horizontal','vertical'):
    d=np.load(f'{sys.argv[1]}/{n}.npz'); v=d['vertices']; f=d['faces']
    topo,edges=r6_mesh.closure_and_orientation(v,f)
    area,_,_=r6_mesh.face_geometry(v,f)
    ids,fa,fb=M.pair_arrays(edges)
    ra=np.maximum(area[fa],area[fb])/np.minimum(area[fa],area[fb])
    print(n,'area ratio max %.1f p99 %.1f'%(ra.max(),np.percentile(ra,99)),'pairs>30',(ra>30).sum())
