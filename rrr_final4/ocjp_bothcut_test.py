"""Replay test (N209 = 16 after 22 on EP 83, c-2/c-2): on the OCJP places
19-20, the % companions (x cut switched, both x steps) also with the y cut
switched.  Counts new hits against the numbers added (chance = size/100)."""
import json, sys
R = [r for r in json.load(open(sys.argv[1])) if r.get('res') is not None and r['ocjp_full']]
SW = {1: 2, 2: 1, -1: -2, -2: -1}
def parse(s):
    c = s.startswith('c'); s = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if s in ('', 'nc') else int(s))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
gain = size = 0; base = 0
for r in R:
    ep, have = r['ep'], set(r['ocjp'])
    base += r['res'] in have
    add = set()
    for n, op, p, kind in r['ocjp_full']:
        if kind != 'base' or p not in (19, 20): continue
        (cx, kx), (cy, ky) = map(parse, op.split('/'))
        if kx == 0 or ky == 0: continue          # x must step (as %), y must step
        for x in (kx, SW[kx]):
            add.add(ap(ep // 10, not cx, x) * 10 + ap(ep % 10, not cy, ky))
    add -= have
    size += len(add); gain += r['res'] in add
N = len(R)
print(f'rounds {N}: OCJP hits {base} -> {base + gain} (+{gain}); size +{size / N:.2f} per round, '
      f'{size / 100:.1f} hits expected by chance')
