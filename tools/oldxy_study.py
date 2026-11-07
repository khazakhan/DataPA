"""User 2026-11-07 (after U9 = 03): 'check old xy and old yx hit rate with total rounds'.
old xy = a row's OLD ops x/y applied to the ROOT; old yx = the same ops swapped (y op on tens, x op on units).
History: 1,293 rounds (rrr_records/history_all.json). Live: every recorded round in rrr_records/live.jsonl."""
import sys, io, contextlib, json
with contextlib.redirect_stdout(io.StringIO()):
    exec(open('tools/final4_full_study.py').read().split('n = len(R)')[0])
n = len(R)
def run(rows_of, label, Rs, get_old, root_of, res_of):
    out = {}
    for k in ('old xy', 'old yx', 'old xy + yx'):
        hits = cov = 0
        for r in Rs:
            s = set()
            for ox, oy in rows_of(r):
                if k != 'old yx': s.add(ap(root_of(r), ox, oy))
                if k != 'old xy': s.add(ap(root_of(r), oy, ox))
            cov += len(s); hits += res_of(r) in s
        m = len(Rs); out[k] = (hits, cov / m)
        print(f"  {label:22s} {k:12s} {hits:4d} of {m}  = {100*hits/m:5.1f}%   numbers {cov/m:4.1f}   chance {cov/m:4.1f}%   extra {hits - cov/100:+.0f}")
print(f"HISTORY ({n} rounds):")
run(lambda r: [(r['last'][3], r['last'][4])], 'LAST row only', R, None, lambda r: r['root'], lambda r: r['res'])
run(lambda r: [(x[3], x[4]) for x in r['rows']], 'all rows', R, None, lambda r: r['root'], lambda r: r['res'])
L = {}
for l in open('rrr_records/live.jsonl'):
    d = json.loads(l); L[d['round']] = d
L = [d for d in L.values() if d.get('rows') and 'result' in d]
print(f"\nLIVE ({len(L)} recorded rounds):")
run(lambda d: [tuple(x['old']) for x in d['rows'] if x['last']][-1:], 'LAST row only', L, None, lambda d: d['ep'], lambda d: d['result'])
run(lambda d: [tuple(x['old']) for x in d['rows']], 'all rows', L, None, lambda d: d['ep'], lambda d: d['result'])
TU = [d for d in L if d['round'][0] in 'TU']
print(f"\nSERIES T + U ({len(TU)} rounds):")
run(lambda d: [tuple(x['old']) for x in d['rows']], 'all rows', TU, None, lambda d: d['ep'], lambda d: d['result'])
