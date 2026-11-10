"""OPEN / CLOSE deep dive, part 2 (2026-11-10): mixes of the page's own lists with the chart's digit
statistics, on every logged round (rrr_records/history_all.json 1,293 + live.jsonl).  Each round
uses only what the page showed before the result + the chart before the result.
Usage: python3 tools/oc_mix_study.py"""
import os, sys, re, json, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, 'tools')
from oc_deep_study import State, D

R = []
for h in json.load(open('rrr_records/history_all.json')):
    R.append(dict(ds=h['ds'], res=int(h['res']), rk=h['src']['rk'], strong=h['src']['strong'], rec=h['src'].get('rec', []), grp=None, src='hist', ser=h['series']))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append(dict(ds=r['dataset'], res=r['result'], rk=r['ranked'], strong=r['lists']['strong'], rec=r['lists'].get('rec', []), src='live', ser=re.match(r'[A-Z]+', r['round']).group(0).lower()))
seen = set(); RR = []
CACHE = {}
for r in R:
    if r['ds'] not in seen:
        seen.add(r['ds']); RR.append(r)
R = RR

def norm(x):
    s = sum(x) or 1
    return [v / s for v in x]

def rankw(rk, k, N=10):
    c = [0] * 10
    for i, v in enumerate(rk[:N]):
        c[D(v, k)] += N - i
    return c

res = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0]))
CACHE = {}
for r in R:
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(r['ds']).read())]
    if len(fl) < 100 or not r['rk']:
        continue
    rep = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1)
    low = len(fl) > 300 and rep < 0.06
    grp = 'low-repeat' if low else 'normal'
    for k, lab in (('t', 'OPEN'), ('u', 'CLOSE')):
        st = State(k)
        for v in fl:
            st.add(v)
        sc = st.scores()
        av = D(fl[-1], 't') if (k == 't' and low) else None
        ocjp = norm(rankw(r['rk'], k)); ocjp20 = norm(rankw(r['rk'], k, 20))
        strong = norm([sum(D(v, k) == d for v in r['strong']) for d in range(10)])
        rec = norm([sum(D(v, k) == d for v in r['rec']) for d in range(10)])
        chart = norm(sc['step x freq']); stepn = norm(sc['step'])
        M = {'OCJP top10 (CLOSE now)': ocjp, 'OCJP top20': ocjp20, 'STRONG 20 digits': strong, 'RECOMMENDED digits': rec,
             'chart step (OPEN now, low)': stepn, 'chart step x freq': chart,
             'OCJP + STRONG': [a + b for a, b in zip(ocjp, strong)],
             'OCJP + chart': [a + b for a, b in zip(ocjp, chart)],
             'STRONG + chart': [a + b for a, b in zip(strong, chart)],
             'OCJP + STRONG + chart': [a + b + c for a, b, c in zip(ocjp, strong, chart)],
             'OCJP + STRONG + REC + chart': [a + b + c + e for a, b, c, e in zip(ocjp, strong, chart, rec)],
             'OCJP20 + STRONG + chart': [a + b + c for a, b, c in zip(ocjp20, strong, chart)]}
        t = D(r['res'], k)
        for m, s in M.items():
            o = sorted(range(10), key=lambda d: (d == av, -s[d], d))
            for g in (grp, 'all', f"{grp}/{r['src']}"):
                a = res[(lab, g)][m]; a[0] += 1; a[1] += t == o[0]; a[2] += t in o[:3]
for (lab, g), d in sorted(res.items()):
    n = next(iter(d.values()))[0]
    print(f"\n{lab} — {g} ({n} rounds)  chance 10% / 30%")
    for m, (n_, h1, h3) in sorted(d.items(), key=lambda t: -(t[1][1] + t[1][2] / 3)):
        print(f"   {m:30s} top1 {h1:4d} = {100*h1/n_:5.1f}%   top3 {h3:4d} = {100*h3/n_:5.1f}%")
