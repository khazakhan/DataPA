"""OPEN/CLOSE swap check (user 2026-11-11, Z45/Z46: 'Close coming as Open and Open coming as Close').
On every logged round, rebuild OPEN-3 / CLOSE-3 exactly as the script does now (_open_close with the
chart and STRONG 20), then compare normal (tens in OPEN, units in CLOSE) with swapped (tens in CLOSE,
units in OPEN).  Chance: 1 digit 10%, 3 digits 30% (OPEN on low-repeat ~11/33% with EP tens out)."""
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
A = collections.defaultdict(collections.Counter)
for ds, res, rk, st, src in R:
    if ds in seen or not rk:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    D._RRR3_PREV['flat'] = fl; D._RRR3_PREV['strong20'] = list(st)
    o, c = D._open_close(rk)
    low = D._tens_avoid() is not None
    t, u = res // 10, res % 10
    for g in (('low' if low else 'normal'), 'all', f"{'low' if low else 'normal'}/{src}"):
        a = A[g]; a['n'] += 1
        a['normal OPEN digit (tens)'] += t == o[0]; a['normal CLOSE digit (units)'] += u == c[0]
        a['swap CLOSE digit as tens'] += t == c[0]; a['swap OPEN digit as units'] += u == o[0]
        a['normal OPEN set'] += t in o; a['normal CLOSE set'] += u in c
        a['swap CLOSE set as tens'] += t in c; a['swap OPEN set as units'] += u in o
        a['normal both sets (grid 9)'] += t in o and u in c
        a['swap both sets (grid 9)'] += t in c and u in o
for g in ('all', 'low', 'low/live', 'low/hist', 'normal'):
    a = A[g]; n = a.pop('n')
    print(f"\n{g} ({n} rounds)  chance: digit 10%, set 30%, grid 9%")
    for k, v in a.items():
        print(f"   {k:30s} {v:4d} = {100*v/n:5.1f}%")
