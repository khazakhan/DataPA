"""User 2026-11-07 (U7 = 28): 'Rule 28 87 -> reverse 78 -> cut tens 28'. Rebuild Rule 28 (crossed, LAST row)
on all 1,293 history rounds and test: pick 1 / all 4 picks, as is, reversed, reversed + cut tens, and
other single digit moves of the reversed number. Chance = numbers / 100."""
import sys, io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
sw = {1: 2, 2: 1, -1: -2, -2: -1, 0: 0}
def r28(r):
    ex, ey = r['root'] // 10, r['root'] % 10
    _, a, b, ox, oy, nx, ny, _t = r['last']
    cy0, ky0 = D._op_side(ny); cx0, kx0 = D._op_side(nx)
    xc, xk = (not cy0), ky0; out = []
    for yc, yk in ((cx0, sw[kx0]), (not cx0, sw[kx0]), (cx0, -sw[kx0]), (not cx0, -sw[kx0])):
        out.append(D._op_apply(ex, xc, xk) * 10 + D._op_apply(ey, yc, yk))
    return out
rev = lambda v: (v % 10) * 10 + v // 10
ct = lambda v: ((v // 10 + 5) % 10) * 10 + v % 10      # cut tens
cu = lambda v: (v // 10) * 10 + (v % 10 + 5) % 10      # cut units
cb = lambda v: ct(cu(v))
n = len(R)
T = {'as is': lambda v: v, 'reversed': rev, 'reversed + cut tens (user U7)': lambda v: ct(rev(v)),
     'reversed + cut units': lambda v: cu(rev(v)), 'reversed + cut both': lambda v: cb(rev(v)),
     'cut tens (no reverse)': ct}
print(f"rounds {n}")
for k, f in T.items():
    for lab, sl in (('pick 1', slice(0, 1)), ('all 4 picks', slice(0, 4))):
        hits = cov = 0
        for r in R:
            s = {f(v) for v in r28(r)[sl]}; cov += len(s); hits += r['res'] in s
        print(f"  {k:30s} {lab:12s} covers {cov/n:4.1f}   held {hits:3d} = {100*hits/n:4.1f}%   chance {cov/n:4.1f}%")
