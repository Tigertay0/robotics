import sys, struct, re, os
import numpy as np

def load_stl(path):
    data = open(path, 'rb').read()
    # binary check: 80 header + uint32 count + 50*count
    if len(data) >= 84:
        n = struct.unpack('<I', data[80:84])[0]
        if 84 + 50 * n == len(data):
            dt = np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
            arr = np.frombuffer(data, dtype=dt, count=n, offset=84)
            return arr['v'].reshape(-1, 3).astype(np.float64), n, 'binary'
    txt = data.decode('utf-8', errors='replace')
    vs = re.findall(r'vertex\s+(\S+)\s+(\S+)\s+(\S+)', txt)
    v = np.array(vs, dtype=np.float64)
    return v, len(v) // 3, 'ascii'

def volume(v):
    t = v.reshape(-1, 3, 3)
    return np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6.0

if __name__ == '__main__':
    d = sys.argv[1]
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith('.stl'):
            continue
        v, n, kind = load_stl(os.path.join(d, fn))
        mn, mx = v.min(0), v.max(0)
        ext = mx - mn
        print(f"{fn} | {kind} | tris={n} | min=({mn[0]:.2f},{mn[1]:.2f},{mn[2]:.2f}) max=({mx[0]:.2f},{mx[1]:.2f},{mx[2]:.2f}) | bbox mm = {ext[0]:.2f} x {ext[1]:.2f} x {ext[2]:.2f} | in = {ext[0]/25.4:.2f} x {ext[1]/25.4:.2f} x {ext[2]/25.4:.2f} | vol(cm3)={abs(volume(v))/1000:.2f}")
