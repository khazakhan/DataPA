"""Which RRR rows can make the result: python3 tools/why.py <dataset before result> <result>"""
import sys, io, contextlib, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
import DataProcessing as D
ds, res = sys.argv[1], int(sys.argv[2])
with contextlib.redirect_stdout(io.StringIO()):
    D.run(open(ds), None, None)
ep = D._RRR_ASK['ep']; ex, ey = ep // 10, ep % 10
def t(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o
found = 0
for pos, a, b, ox, oy, nx, ny, _ in D._RRR_ASK['rows']:
    for nm, (xo, yo) in {'new': (nx, ny), 'old': (ox, oy)}.items():
        for lab, (p, q) in {'xy': (xo, yo), 'yx': (yo, xo)}.items():
            for fx in ('', 'F', 'C', 'FC'):
                for fy in ('', 'F', 'C', 'FC'):
                    x2, y2 = t(p, fx), t(q, fy)
                    if D.apply_op(ex, x2) * 10 + D.apply_op(ey, y2) == res:
                        found += 1
                        print(f"Op{pos} {a:02d}->{b:02d} {nm} {lab} x{fx or '-'} y{fy or '-'} -> {D.OP_ABBREV[x2]}/{D.OP_ABBREV[y2]}")
fd = D.ep_row_finder(ep, D._RRR_ASK['rows'])
print(f"EP {ep:02d}; rows that can make it: {found}; finder:",
      [(f"Op{p}", lab, k) for p, a, b, lab, v in fd for k in D.EP_FINDER_VARIANTS if v[k][0] == res] or 'no')
