"""MASTER OP AUDIT (user AF300, 2026-11-24): take the op on ROOT that makes MASTER (x op / y op),
change it (as is, cut switched, sign changed, cut + sign, no change, step +1/-1/+2/-2) and put
it on ROOT and on EP.  Scores every logged round (rrr_records/live.jsonl, MASTER = ranked[0]).
  python3 tools/master_op_audit.py"""
import json, os, sys, collections
sys.path.insert(0, '.')
R = []
for l in open('rrr_records/live.jsonl'):
    r = json.loads(l)
    try:
        res, root, ep, m = int(r['result']), int(r['ep']), int(r['after']), int(r['ranked'][0])
    except Exception:
        continue
    R.append((r['round'], res, root, ep, m))
def side(src, dst):                  # op as (cut flag, step), step -2..2
    for c in (0, 1):
        for s in (0, 1, -1, 2, -2):
            if ((src + 5 * c) + s) % 10 == dst: return c, s
def ap(d, c, s): return (d + 5 * c + s) % 10
V = {'as is': lambda c, s: (c, s), 'cut switched': lambda c, s: (1 - c, s), 'sign changed': lambda c, s: (c, -s),
     'cut + sign': lambda c, s: (1 - c, -s), 'no change (nc/nc)': lambda c, s: (0, 0),
     'step +1': lambda c, s: (c, s + 1), 'step -1': lambda c, s: (c, s - 1), 'step +2': lambda c, s: (c, s + 2), 'step -2': lambda c, s: (c, s - 2)}
def forms(root, ep, m):
    xo, yo = side(root // 10, m // 10), side(root % 10, m % 10)
    out = {}
    for tgt, base in (('ROOT', root), ('EP', ep)):
        for k, f in V.items():
            x, y = f(*xo), f(*yo)
            out[f'{k} on {tgt}'] = ap(base // 10, *x) * 10 + ap(base % 10, *y)
    return out
if __name__ == '__main__':
    n = len(R); H = n // 2
    hit = collections.defaultdict(lambda: [0, 0]); setsz = [0, 0]; seth = [0, 0]; rs = [0, 0]; rsh = [0, 0]
    for i, (rd, res, root, ep, m) in enumerate(R):
        f = forms(root, ep, m); h = i >= H
        for k, v in f.items(): hit[k][h] += v == res
        s = set(f.values()); setsz[h] += len(s); seth[h] += res in s
        se = {v for k, v in f.items() if k.endswith('EP')}; rs[h] += len(se); rsh[h] += res in se
    print(f'MASTER OP AUDIT: {n} logged rounds (halves {H} / {n - H}); one number: chance 1% = {H * .01:.1f} per half')
    for k, (a, b) in sorted(hit.items(), key=lambda t: -sum(t[1])):
        print(f'  {k:28s} {a:3d} | {b:3d}  = {100 * (a + b) / n:4.2f}%  x{(a + b) / (n * .01):.2f}')
    print(f'  ALL 18 forms (avg {sum(setsz) / n:.1f} numbers): held {seth[0]} | {seth[1]} = {100 * sum(seth) / n:.1f}%  vs chance {100 * sum(setsz) / n / 100:.1f}%')
    print(f'  EP 9 forms   (avg {sum(rs) / n:.1f} numbers): held {rsh[0]} | {rsh[1]} = {100 * sum(rsh) / n:.1f}%  vs chance {sum(rs) / n:.1f}%')
