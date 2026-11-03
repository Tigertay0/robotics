import sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from stl_bbox import load_stl
from stl_holes import holes_on_face

d=sys.argv[1]
for fn in sys.argv[2:]:
    v,n,k=load_stl(os.path.join(d,fn))
    ext=v.max(0)-v.min(0)
    print("=====",fn, "bbox", np.round(ext,2))
    for axis in range(3):
        for side in ('min','max'):
            try:
                loops, other, ntri = holes_on_face(v, axis, side)
            except Exception as e:
                print("  err",e); continue
            if ntri==0: continue
            rows=[]
            for L in loops:
                mn=L.min(0); mx=L.max(0); c=(mn+mx)/2; w=mx-mn
                rows.append((c[0],c[1],w[0],w[1]))
            rows.sort(key=lambda r:-(r[2]*r[3]))
            inner=rows[1:]
            circ=[r for r in inner if abs(r[2]-r[3])<0.15 and r[2]>1.0]
            by=collections.Counter((round(r[2],1)) for r in circ)
            print(f"  face {'XYZ'[axis]}{side}: tris={ntri}, loops={len(loops)}, outer={rows[0][2]:.1f}x{rows[0][3]:.1f}, circ holes by dia(mm): {dict(sorted(by.items()))}")
            # pitch
            if len(circ)>1 and len(circ)<400:
                xs=sorted(set(round(r[0],2) for r in circ)); ys=sorted(set(round(r[1],2) for r in circ))
                dx=np.diff(xs); dy=np.diff(ys)
                def mode(a):
                    if len(a)==0: return None
                    c=collections.Counter(np.round(a,2)); return c.most_common(3)
                print("     x-spacing mode:",mode(dx),"| y-spacing mode:",mode(dy))
