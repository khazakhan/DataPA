"""FINAL 4 small-change study (user 2026-11-11: 'very close but failing with +1 -1 +2 -2, nc and cut on open or close').
For each logged round: which single change of ONE digit (tens or units: +1 -1 +2 -2 cut c+1 c-1 c+2 c-2) of MASTER / #2 /
any FINAL 4 number gives the result, and how big each set is - so coverage (how many numbers a rule names) is
separated from real skill.  Low tens-repeat charts drop EP-tens numbers."""
import os, re, json, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
T, U = (lambda v: v // 10), (lambda v: v % 10)
CH = {'+1': 1, '-1': 9, '+2': 2, '-2': 8, 'cut': 5, 'c+1': 6, 'c-1': 4, 'c+2': 7, 'c-2': 3}
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['rk']))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['ranked']))
per = collections.defaultdict(lambda: [0, 0, 0])
for ds, res, rk in R:
    if ds in seen or len(rk) < 4:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    low = len(fl) > 300 and sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1) < 0.06
    if not low:
        continue
    av = T(fl[-1])
    f4 = rk[:4]
    sets = collections.defaultdict(set)
    for rank, n in enumerate(f4):
        for c, d in CH.items():
            for side in ('tens', 'units'):
                v = ((T(n) + d) % 10) * 10 + U(n) if side == 'tens' else T(n) * 10 + (U(n) + d) % 10
                if T(v) == av or v in f4:
                    continue
                sets[f"{side} {c} of MASTER"].add(v) if rank == 0 else None
                if rank < 2: sets[f"{side} {c} of MASTER/#2"].add(v)
                sets[f"{side} {c} of FINAL 4"].add(v)
                sets['ANY one-digit change of FINAL 4'].add(v)
                if rank < 2: sets['ANY one-digit change of MASTER/#2'].add(v)
                if c in ('+1', '-1'): sets['±1 of MASTER/#2 (NEAR 8)'].add(v) if rank < 2 else None
    for k, s in sets.items():
        p = per[k]; p[0] += 1; p[1] += res in s; p[2] += len(s)
rows = sorted(per.items(), key=lambda t: -(t[1][1] / (t[1][2] / 100)) if t[1][2] else 0)
print(f"low tens-repeat logged rounds: {per['ANY one-digit change of FINAL 4'][0]}")
for k in ('ANY one-digit change of FINAL 4', 'ANY one-digit change of MASTER/#2', '±1 of MASTER/#2 (NEAR 8)'):
    n, h, s = per[k]; print(f"   {k:38s} {h:4d} of {n} = {100*h/n:5.1f}%  chance {s/100:6.1f}  x{h/(s/100):.2f}  (avg {s/n:.1f} numbers)")
print("\nsingle changes of FINAL 4 (best and worst by lift, need >= 8 chance-hits):")
ok = [(k, v) for k, v in rows if 'of FINAL 4' in k and not k.startswith('ANY') and v[2] / 100 >= 8]
for k, (n, h, s) in ok[:6] + [('...', (1, 0, 100))] + ok[-4:]:
    if k == '...': print('   ...'); continue
    print(f"   {k:28s} {h:4d}  chance {s/100:5.1f}  x{h/(s/100):.2f}")
