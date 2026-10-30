import json, sys
from math import comb
def p_at_least(k, n, p):
    return sum(comb(n, i) * p**i * (1-p)**(n-i) for i in range(k, n+1))
def evaluate(path, srcs, weights=None):
    data = json.load(open(path)); out = {}
    for K in (1, 4, 10, 20):
        hits = 0
        for r in data:
            s = r['src']; order = s.get('rk', [])
            rank = {v: i for i, v in enumerate(order)}
            score = {}
            for n in range(100):
                score[n] = sum((weights or {}).get(k, 1) for k in srcs if n in s.get(k, []))
            ranked = sorted(range(100), key=lambda n: (-score[n], rank.get(n, 99), n))
            hits += r['res'] in ranked[:K]
        out[K] = (hits, len(data), p_at_least(hits, len(data), K / 100))
    return out
for name, srcs in [('top40 order only', []), ('rule5', ['rule5']), ('rule5+rule2', ['rule5', 'rule2']),
                   ('rule5+rule2+rule18', ['rule5', 'rule2', 'rule18']),
                   ('rule5+rule2+rule18+top10', ['rule5', 'rule2', 'rule18', 'top10'])]:
    for path in sys.argv[1:]:
        e = evaluate(path, srcs)
        print(f"{name:28} {path.split('/')[-1]:10} " + '  '.join(f"top{K}: {h}/{n} (chance {n*K/100:.1f}, p={p:.3f})" for K, (h, n, p) in e.items()))
