"""Walk-forward check of simple chart-only pick rules (4 numbers) vs chance 4%.
Usage: python3 tools/simple_rules.py set01 set02 ...  (reads holdout_sets/<set>.txt)"""
import sys
from collections import Counter

def rules(h):
    last = h[-1]
    out = {}
    out['hot100'] = [v for v, _ in Counter(h[-100:]).most_common(4)]
    fol = Counter(b for a, b in zip(h, h[1:]) if a == last)
    out['EPfollow'] = [v for v, _ in fol.most_common(4)]
    seen = {}
    for i, v in enumerate(h): seen[v] = i
    out['overdue'] = sorted(range(100), key=lambda v: seen.get(v, -1))[:4]
    rec = []
    for v in reversed(h[:-1]):
        if v not in rec and v != last: rec.append(v)
        if len(rec) == 4: break
    out['recent'] = rec
    out['cold100'] = sorted(range(100), key=lambda v: (Counter(h[-100:])[v], v))[:4]
    return out

if __name__ == '__main__':
    tot = Counter(); N = 0
    for n in sys.argv[1:]:
        vals = [int(t) for t in open(f'holdout_sets/{n}.txt').read().split() if t.isdigit()]
        hit = Counter(); cnt = 0
        for p in range(100, len(vals)):
            for k, pk in rules(vals[:p]).items():
                hit[k] += vals[p] in pk
            cnt += 1
        N += cnt; tot.update(hit)
        print(n, cnt, ' '.join(f'{k}={hit[k]} ({100*hit[k]/cnt:.1f}%)' for k in sorted(hit)))
    print('ALL', N, ' '.join(f'{k}={tot[k]} ({100*tot[k]/N:.2f}%)' for k in sorted(tot)))
