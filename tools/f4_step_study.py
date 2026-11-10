"""FINAL 4 STEP ±1 study (2026-11-11: five Z results were a FINAL 4 number with one digit ±1).
±1 neighbours (tens ±1 or units ±1) of MASTER / MASTER+#2 / all 4, on every logged round;
low tens-repeat charts drop EP-tens numbers, as on the page."""
import os, sys, re, json, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
T, U = (lambda v: v // 10), (lambda v: v % 10)
nb = lambda n: {((T(n) + d) % 10) * 10 + U(n) for d in (1, -1)} | {T(n) * 10 + (U(n) + d) % 10 for d in (1, -1)}
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['rk'], 'hist'))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['ranked'], 'live'))
A = collections.defaultdict(lambda: [0, 0, 0])
for ds, res, rk, src in R:
    if ds in seen or len(rk) < 4:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    low = len(fl) > 300 and sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1) < 0.06
    av = fl[-1] // 10 if low else None
    f4 = rk[:4]
    for k, base in (('MASTER ±1 (4)', f4[:1]), ('MASTER+#2 ±1 (8)', f4[:2]), ('all FINAL 4 ±1 (16)', f4)):
        s = set().union(*[nb(n) for n in base]) - set(f4)
        if av is not None:
            s = {v for v in s if T(v) != av}
        for g in (('low' if low else 'normal'), 'all', f"{'low' if low else 'normal'}/{src}"):
            a = A[(g, k)]; a[0] += 1; a[1] += res in s; a[2] += len(s)
for g in ('all', 'low', 'low/live', 'low/hist', 'normal'):
    for k in ('MASTER ±1 (4)', 'MASTER+#2 ±1 (8)', 'all FINAL 4 ±1 (16)'):
        n, h, s = A[(g, k)]
        if n: print(f"{g:10s} {k:22s} {h:4d} of {n:4d} = {100*h/n:5.1f}%   chance {s/100:6.1f}  x{h/(s/100):.2f}")
