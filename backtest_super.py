"""Backtest SUPER SPECIAL 10 vs STRONG top-10 vs ★R3 vs chance.
Cuts the grid at each of the last N positions, runs run() silently, checks
whether the actual next number is in each list. Usage: python3 backtest_super.py 1000"""
import sys, io, time, contextlib
sys.path.insert(0, ".")
import DataProcessing as D
rows = D.load_data(open('temp_data.txt'))
# keep only full grid rows (drop trailing single-value pending rows)
flat = [(r, c) for r in range(len(rows)) for c in range(len(rows[r]))]
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
hits_super = hits_top10 = hits_r3 = n = 0
t0 = time.time()
for p in range(len(flat) - N, len(flat)):
    r, c = flat[p]
    actual = rows[r][c]
    if actual < 0:
        continue
    trunc = [list(x) for x in rows[:r]] + ([rows[r][:c]] if c > 0 else [])
    if not trunc or trunc[-1][-1] < 0:
        continue
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            res = D.run(trunc)
        except Exception as e:
            continue
    if not res:
        continue
    _, _, top4, scores = res
    if not top4:
        continue
    top10, _ = D.super_special_top10(top4, scores)
    sup = {v for v, *_ in top10}
    n += 1
    hits_super += actual in sup
    hits_top10 += actual in {v for v, *_ in top4[:10]}
    hits_r3 += actual in {v for v, *_ in top4[:3]}
print(f"rounds={n}  SUPER10 hits={hits_super} ({100*hits_super/n:.1f}%)  "
      f"STRONG top10 hits={hits_top10} ({100*hits_top10/n:.1f}%)  "
      f"R3 hits={hits_r3} ({100*hits_r3/n:.1f}%)  chance10=10.0%  "
      f"time={time.time()-t0:.0f}s")
