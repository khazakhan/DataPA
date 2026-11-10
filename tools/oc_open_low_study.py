"""OPEN on low tens-repeat charts (2026-11-10): STRONG 20 tens digits vs chart steps and mixes,
on every logged round of a low-repeat chart (history_all + live).  Halves for stability."""
import os, sys, re, json, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, 'tools')
from oc_deep_study import State, D
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['strong'], 'hist'))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['lists']['strong'], 'live'))
norm = lambda x: [v / (sum(x) or 1) for v in x]
out = collections.defaultdict(lambda: [0, 0, 0]); rows = []
for ds, res, strong, src in R:
    if ds in seen:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    rep = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1)
    if not (len(fl) > 300 and rep < 0.06):
        continue
    st = State('t')
    for v in fl:
        st.add(v)
    sc = st.scores(); av = fl[-1] // 10
    S = norm([sum(v // 10 == d for v in set(strong)) for d in range(10)])
    P, X = norm(sc['step']), norm(sc['step x freq'])
    M = {'step (now)': P, 'step x freq': X, 'STRONG 20 tens': S, 'STRONG + step': [a + b for a, b in zip(S, P)],
         'STRONG + step x freq': [a + b for a, b in zip(S, X)], 'STRONG + step + step x freq': [a + b + c for a, b, c in zip(S, P, X)],
         '2 STRONG + step': [2 * a + b for a, b in zip(S, P)]}
    rows.append((src, res // 10, {m: sorted(range(10), key=lambda d: (d == av, -s[d], d)) for m, s in M.items()}))
h = len(rows) // 2
for nm, part in (('all', rows), ('first half', rows[:h]), ('second half', rows[h:]), ('live only', [r for r in rows if r[0] == 'live'])):
    print(f"\n{nm} ({len(part)} rounds)  chance 10%/30% (EP tens left out: ~11%/33%)")
    for m in rows[0][2]:
        a = sum(t == o[m][0] for _, t, o in part); b = sum(t in o[m][:3] for _, t, o in part)
        print(f"   {m:28s} top1 {a:3d} = {100*a/len(part):5.1f}%   top3 {b:3d} = {100*b/len(part):5.1f}%")
