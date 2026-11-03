import sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from stl_bbox import load_stl

def holes_on_face(v, axis, side):
    t = v.reshape(-1,3,3)
    ext = v.max(0)-v.min(0)
    coord = v.max(0)[axis] if side=='max' else v.min(0)[axis]
    # triangles whose 3 vertices lie on that plane
    on = np.all(np.abs(t[:,:,axis]-coord)<1e-3, axis=1)
    tt = t[on]
    other = [a for a in range(3) if a!=axis]
    def key(p): return (round(p[other[0]],3), round(p[other[1]],3))
    edges = collections.Counter()
    for tri in tt:
        ks=[key(p) for p in tri]
        for i in range(3):
            e = tuple(sorted((ks[i],ks[(i+1)%3])))
            edges[e]+=1
    b=[e for e,c in edges.items() if c==1]
    # connected loops
    adj=collections.defaultdict(list)
    for a,c in b:
        adj[a].append(c); adj[c].append(a)
    seen=set(); loops=[]
    for s in adj:
        if s in seen: continue
        st=[s]; comp=[]
        seen.add(s)
        while st:
            x=st.pop(); comp.append(x)
            for y in adj[x]:
                if y not in seen: seen.add(y); st.append(y)
        loops.append(np.array(comp))
    return loops, other, tt.shape[0]

def summarize(name, v):
    ext=v.max(0)-v.min(0)
    axis=int(np.argmin(ext))
    for side in ('max',):
        loops, other, ntri = holes_on_face(v, axis, side)
        print(f"== {name}: thin axis={'XYZ'[axis]} ({ext[axis]:.2f} mm), face {side}: {ntri} tris, {len(loops)} boundary loops, axes {['XYZ'[o] for o in other]}")
        rows=[]
        for L in loops:
            mn=L.min(0); mx=L.max(0); c=(mn+mx)/2; w=mx-mn
            rows.append((c[0],c[1],w[0],w[1],len(L)))
        # outer = biggest
        rows.sort(key=lambda r:-(r[2]*r[3]))
        print("   outer loop bbox: %.2f x %.2f mm"%(rows[0][2],rows[0][3]))
        inner=[r for r in rows[1:]]
        # group by diameter
        by=collections.defaultdict(list)
        for r in inner:
            by[(round(r[2],1),round(r[3],1))].append(r)
        for k,lst in sorted(by.items(), key=lambda kv:-len(kv[1])):
            print(f"   hole size {k[0]} x {k[1]} mm ({k[0]/25.4:.3f} x {k[1]/25.4:.3f} in): count {len(lst)}")
        return inner, other

if __name__=='__main__':
    d=sys.argv[1]
    for fn in sys.argv[2:]:
        v,n,k=load_stl(os.path.join(d,fn))
        inner,other=summarize(fn,v)
        # print hole centers for small files
        if len(inner)<=40:
            pts=sorted([(round(r[0],2),round(r[1],2)) for r in inner])
            print("   centers:",pts)
        else:
            xs=sorted(set(round(r[0],1) for r in inner)); ys=sorted(set(round(r[1],1) for r in inner))
            print("   unique x centers:",xs[:40]); print("   unique y centers:",ys[:40])
