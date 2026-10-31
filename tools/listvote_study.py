"""Learned list-vote picker: weight each list by its out-of-sample lift,
leave-one-series-out.  python3 tools/listvote_study.py"""
import json, math
from collections import defaultdict
S = 'FNMKO'
src = {s: json.load(open(f'rrr_records/replay/src{s}.json')) for s in S}
def lists(r):
    L = {k: set(v) for k, v in r['src'].items() if k not in ('rk',) and v}
    rk = r['src'].get('rk', [])
    for k in (1, 2, 4, 10, 20, 40): L[f'rk{k}'] = set(rk[:k])
    return L
def train(rounds):
    seen, hit = defaultdict(float), defaultdict(int)
    for r in rounds:
        for k, v in lists(r).items():
            seen[k] += len(v) / 100; hit[k] += r['res'] in v
    return {k: math.log((hit[k] + 1) / (seen[k] + 1)) for k in seen}
def rank(r, w):
    sc = defaultdict(float)
    for k, v in lists(r).items():
        for n in v: sc[n] += max(0, w.get(k, 0))
    rk = r['src'].get('rk', [])
    return sorted(range(100), key=lambda n: (-sc[n], rk.index(n) if n in rk else 99))
tot = defaultdict(int); f4 = 0; N = 0
for s in S:
    w = train([r for t in S if t != s for r in src[t]])
    for r in src[s]:
        N += 1; rk = rank(r, w)
        for k in (4, 8, 10): tot[k] += r['res'] in rk[:k]
        f4 += r['res'] in r['src'].get('top4', [])
print(f"rounds {N}: learned vote top4 {tot[4]} top8 {tot[8]} top10 {tot[10]} | chance {N*.04:.1f} {N*.08:.1f} {N*.1:.1f} | FINAL 4 {f4} | PRIME (earlier) top4 23 top8 43 top10 48")
