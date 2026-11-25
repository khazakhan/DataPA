"""40-number list study (user 2026-11-25: 4 of 7 with a 40-number list, chance 40%).
Walk-forward on raw chart numbers.  Lists:
  recent40 : 40 most recently seen distinct numbers (EP excluded)
  hot40    : 40 most frequent in last 200
  cold40   : 40 least recently seen (overdue)
Reports per-round hit rate and share of 7-round blocks with 4+ hits (chance 29.0%).
Usage: python3 tools/list40_study.py set01 set02 ..."""
import sys
from collections import Counter
N = 40
def lists(h):
    last = h[-1]; rec = []
    for v in reversed(h):
        if v != last and v not in rec: rec.append(v)
        if len(rec) == N: break
    rec += [v for v in range(100) if v not in rec and v != last][:N - len(rec)]
    c = Counter(h[-200:])
    hot = sorted(range(100), key=lambda v: (-c[v], v))[:N]
    seen = {v: i for i, v in enumerate(h)}
    cold = sorted(range(100), key=lambda v: seen.get(v, -1))[:N]
    return {'recent40': set(rec), 'hot40': set(hot), 'cold40': set(cold)}
if __name__ == '__main__':
    tot = {}
    for n in sys.argv[1:]:
        vals = [int(t) for t in open(f'holdout_sets/{n}.txt').read().split() if t.isdigit()]
        hits = {}
        for p in range(100, len(vals)):
            for k, s in lists(vals[:p]).items():
                hits.setdefault(k, []).append(vals[p] in s)
        row = []
        for k, hs in hits.items():
            bl = [sum(hs[i:i + 7]) for i in range(0, len(hs) - 6, 7)]
            ps = sum(b >= 4 for b in bl)
            t = tot.setdefault(k, [0, 0, 0, 0]); t[0] += sum(hs); t[1] += len(hs); t[2] += ps; t[3] += len(bl)
            row.append(f'{k} {100*sum(hs)/len(hs):.1f}% pass {ps}/{len(bl)} ({100*ps/len(bl):.0f}%)')
        print(n, ' | '.join(row))
    print('ALL', ' | '.join(f'{k} {100*a/b:.2f}% pass {c}/{d} ({100*c/d:.1f}%)' for k, (a, b, c, d) in tot.items()))
