"""Replay test (N218 = 31 after 52 on EP 58, -2/c-2; LAST row +2/-1, -1/+2):
two candidate OCJP additions, counted as new hits against numbers added.
A: on places 31-38 the # forms (y cut switched, both y steps) also with
   the x sign flipped (as the ! form does on places 1-8).
B: places 31-38 family completed: each of the two operations on both
   sides with the cut on one side only (+2/c+2, c+2/+2, -2/c-2, c-2/-2)."""
import json, sys
R = [r for r in json.load(open(sys.argv[1])) if r.get('res') is not None and r['ocjp_full']]
SW = {1: 2, 2: 1, -1: -2, -2: -1}
def parse(s):
    c = s.startswith('c'); s = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if s in ('', 'nc') else int(s))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
def num(ep, x, y): return ap(ep // 10, *x) * 10 + ap(ep % 10, *y)
N = len(R); res = {}
for name in 'AB':
    gain = size = 0
    for r in R:
        ep, have = r['ep'], set(r['ocjp']); add = set()
        base = {p: op for n, op, p, k in r['ocjp_full'] if k == 'base'}
        if name == 'A':
            for p in range(31, 39):
                if p not in base: continue
                (cx, kx), (cy, ky) = map(parse, base[p].split('/'))
                if kx == 0 or ky == 0: continue
                for y in (ky, SW[ky]):
                    add.add(num(ep, (cx, -kx), (not cy, y)))
        else:
            for p in (31, 35):           # (o, s[o]) of X and of Y
                if p not in base: continue
                (cx, kx), _ = map(parse, base[p].split('/'))
                if kx == 0: continue
                for k in (kx, -kx):
                    add |= {num(ep, (False, k), (True, k)), num(ep, (True, k), (False, k))}
        add -= have; size += len(add); gain += r['res'] in add
    print(f'{name}: OCJP +{gain} hits; size +{size / N:.2f} per round = {size / 100:.1f} expected by chance ({N} rounds)')
