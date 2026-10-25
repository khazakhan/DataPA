"""Replay test on ALL series (N235 = 04 after 62 on EP 97, +1/c+2): LAST row
09 (+1/+2), 18 (+2/+1); place 19 held 09 (+1/+2) and the % forms (x cut
switched) but never the y cut switched alone.  Candidate forms on places
19-20 (the LAST row's own xy and yx), new hits against numbers added:
  A  y cut switched, x kept                       (+1/+2 -> +1/c+2)
  B  A + y step switched too                      (-> +1/c+2, +1/c+1)
  C  B + x step switched (the # form of 1-8)      (-> +1/c+2 ... +2/c+1)"""
import json, sys
R = [r for r in json.load(open(sys.argv[1])) if r.get('res') is not None and r.get('ocjp_full')]
SW = {1: 2, 2: 1, -1: -2, -2: -1}
def parse(s):
    c = s.startswith('c'); s = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if s in ('', 'nc') else int(s))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
for name in 'ABC':
    by = {}; gain = size = 0
    for r in R:
        ep, have = r['ep'], set(r['ocjp']); add = set()
        for n, op, p, k in r['ocjp_full']:
            if k != 'base' or not 19 <= p <= 20: continue
            (cx, kx), (cy, ky) = map(parse, op.split('/'))
            if ky == 0: continue
            xs = [kx] + ([SW[kx]] if name == 'C' and kx else [])
            ys = [ky] + ([SW[ky]] if name in 'BC' else [])
            for x in xs:
                for y in ys:
                    add.add(ap(ep // 10, cx, x) * 10 + ap(ep % 10, not cy, y))
        add -= have; g = r['res'] in add
        s = by.setdefault(r['series'], [0, 0, 0]); s[0] += 1; s[1] += g; s[2] += len(add)
        gain += g; size += len(add)
    N = len(R)
    print(f'{name}: all series {N} rounds: OCJP +{gain} hits, size +{size / N:.2f} per round = {size / 100:.1f} expected by chance')
    print('   ' + '  '.join(f'{k} {n}r +{g} ({z / 100:.1f})' for k, (n, g, z) in sorted(by.items(), key=lambda x: -x[1][0])))
