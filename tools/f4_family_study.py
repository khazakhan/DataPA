"""FINAL 4 family study (user 2026-11-11, Z30: 'same family 14 and 96'): how often the result is in the
cut-pair family (DataProcessing FAMILY_MAP) of MASTER / each FINAL 4 number, on every logged round
(history_all 1,293 + live).  Low tens-repeat charts: EP-tens members dropped, as on the page."""
import os, sys, re, json, collections, io, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
F = D.FAMILY_MAP; MEM = D.FAMILY_MEMBERS
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['rk'], 'hist'))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['ranked'], 'live'))
agg = collections.defaultdict(lambda: [0, 0, 0])
for ds, res, rk, src in R:
    if ds in seen or len(rk) < 4:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    rep = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / max(1, len(fl) - 1)
    av = fl[-1] // 10 if len(fl) > 300 and rep < 0.06 else None
    grp = 'low-repeat' if av is not None else 'normal'
    fam = lambda v: [m for m in MEM[F[v]] if av is None or m // 10 != av]
    sets = {'MASTER family': set(fam(rk[0])),
            'FINAL 4 #2 family': set(fam(rk[1])),
            'MASTER + #2 families': set(fam(rk[0])) | set(fam(rk[1])),
            'FINAL 4 families (all 4)': set().union(*[fam(v) for v in rk[:4]]),
            'family seen most in FINAL 4': set(fam(max(rk[:4], key=lambda v: (sum(F[w] == F[v] for w in rk[:4]), -rk.index(v)))))}
    for k, s in sets.items():
        for g in (grp, 'all', f'{grp}/{src}'):
            a = agg[(g, k)]; a[0] += 1; a[1] += res in s; a[2] += len(s)
for g in ('all', 'normal', 'low-repeat', 'low-repeat/live', 'low-repeat/hist'):
    print(f"\n{g}")
    for k in ('MASTER family', 'FINAL 4 #2 family', 'MASTER + #2 families', 'family seen most in FINAL 4', 'FINAL 4 families (all 4)'):
        n, h, s = agg[(g, k)]
        if n:
            print(f"   {k:30s} {h:4d} of {n:4d} = {100*h/n:5.1f}%   chance {s/100:6.1f} (x{h/(s/100):.2f}), avg {s/n:.1f} numbers")
