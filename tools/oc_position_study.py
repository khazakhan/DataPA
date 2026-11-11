"""Where does the result's digit sit in the OPEN / CLOSE full order? (user 2026-11-11: 'close strong always
showing last digits').  Full order = the 10 digits strong -> weak exactly as the page shows.  Chance: 10% per place."""
import os, sys, re, json, collections, io, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['rk'], h['src']['strong'], 'hist'))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['ranked'], r['lists']['strong'], 'live'))
P = collections.defaultdict(lambda: [0] * 10); N = collections.Counter()
for ds, res, rk, st, src in R:
    if ds in seen or not rk:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    D._RRR3_PREV['flat'] = fl; D._RRR3_PREV['strong20'] = list(st)
    D._open_close(rk)
    o, c = D._RRR3_PREV['oc_full']
    low = D._tens_avoid() is not None
    for g in (('low' if low else 'normal'), f"{'low' if low else 'normal'}/{src}", 'all'):
        N[g] += 1
        P[(g, 'OPEN')][o.index(res // 10)] += 1
        P[(g, 'CLOSE')][c.index(res % 10)] += 1
for g in ('all', 'low', 'low/live', 'low/hist', 'normal'):
    for side in ('OPEN', 'CLOSE'):
        p = P[(g, side)]; n = N[g]
        print(f"{g:9s} {side:5s} n={n:4d}  place 1..10 %: " + ' '.join(f"{100*x/n:4.1f}" for x in p)
              + f"   top3 {100*sum(p[:3])/n:4.1f}  last3 {100*sum(p[7:])/n:4.1f}")
