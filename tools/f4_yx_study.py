"""FINAL 4 yx column study (2026-11-11, Z32 = yx of MASTER 11): yx = the FINAL 4 number's two ops crossed on
the ROOT.  Logged rounds (history_all + live): FINAL 4 vs its yx column vs both, low-repeat vs normal."""
import os, sys, re, json, collections, io, contextlib
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
T, U = (lambda v: v // 10), (lambda v: v % 10)
yx = lambda r, n: ((T(r) + (U(n) - U(r))) % 10) * 10 + (U(r) + (T(n) - T(r))) % 10
R, seen = [], set()
for h in json.load(open('rrr_records/history_all.json')):
    R.append((h['ds'], int(h['res']), h['src']['rk'], int(h['ep']), 'hist'))
for r in map(json.loads, open('rrr_records/live.jsonl')):
    if r.get('result') is not None:
        R.append((r['dataset'], r['result'], r['ranked'], r['ep'], 'live'))
A = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
for ds, res, rk, root, src in R:
    if ds in seen or len(rk) < 4:
        continue
    seen.add(ds)
    fl = [int(x) for x in re.findall(r'(?<![\d*])\d\d(?![\d*])', open(ds).read())]
    low = len(fl) > 300 and sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1) < 0.06
    f4 = rk[:4]; y4 = [yx(root, n) for n in f4]; y_only = [v for v in y4 if v not in f4]
    for g in (('low' if low else 'normal'), 'all', f"{'low' if low else 'normal'}/{src}"):
        a = A[g]; a[0] += 1; a[1] += res in f4; a[2] += res in y4; a[3] += res in set(f4) | set(y4)
        a[4] += len(set(y4)); a[5] += len(set(f4) | set(y4))
for g, (n, h4, hy, hb, sy, sb) in sorted(A.items()):
    print(f"{g:12s} {n:5d} rounds  FINAL 4 {h4:4d} ({100*h4/n:4.1f}%, chance {4*n/100:.0f})   yx column {hy:4d} ({100*hy/n:4.1f}%, chance {sy/100:.0f})"
          f"   both {hb:4d} ({100*hb/n:4.1f}%, chance {sb/100:.0f})")
