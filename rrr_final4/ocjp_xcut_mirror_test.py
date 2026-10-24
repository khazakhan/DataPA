"""Replay test on ALL series (N225 = 92 after 89 on EP 77, +2/cut): the OCJP %
form (x cut switched, both x steps) now runs on places 15-20; places 27-30
are the same shape as 15-18 (an operation with y fixed at cut or nc), so the
% form is tried there too.  New hits against numbers added, per series."""
import json, sys
R = [r for r in json.load(open(sys.argv[1])) if r.get('res') is not None and r.get('ocjp_full')]
SW = {1: 2, 2: 1, -1: -2, -2: -1}
def parse(s):
    c = s.startswith('c'); s = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if s in ('', 'nc') else int(s))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
by = {}; gain = size = 0
for r in R:
    ep, have = r['ep'], set(r['ocjp']); add = set()
    for n, op, p, k in r['ocjp_full']:
        if k != 'base' or not 27 <= p <= 30: continue
        (cx, kx), (cy, ky) = map(parse, op.split('/'))
        if kx == 0: continue
        for x in (kx, SW[kx]):
            add.add(ap(ep // 10, not cx, x) * 10 + ap(ep % 10, cy, ky))
    add -= have; g = r['res'] in add
    s = by.setdefault(r['series'], [0, 0, 0]); s[0] += 1; s[1] += g; s[2] += len(add)
    gain += g; size += len(add)
N = len(R)
print(f'all series {N} rounds: OCJP +{gain} hits, size +{size / N:.2f} per round = {size / 100:.1f} expected by chance')
for k, (n, g, z) in sorted(by.items(), key=lambda x: -x[1][0]):
    print(f'   {k:<3} {n:4d} rounds  +{g}  (chance {z / 100:.1f})')
