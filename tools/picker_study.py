"""Trained picker study: learn which (row relation x change) holds the result,
score every number, test leave-one-series-out.  python3 tools/picker_study.py"""
import json, math
from collections import defaultdict
S = 'FNMKO'
data = {s: json.load(open(f'rrr_records/replay/fs{s}.json')) for s in S}
src = {s: {r['ds']: r['src'] for r in json.load(open(f'rrr_records/replay/src{s}.json'))} for s in S}
def feats(row, lab):
    rel = row['rel'].split('|')[0]; last = 'L' if 'LAST' in row['rel'] else ''
    yield (rel + last, lab)
    yield ('*', lab)
def train(rounds, a=1.0):
    seen, hit = defaultdict(int), defaultdict(int)
    for r in rounds:
        for row in r['rows']:
            for lab, n in row['ch'].items():
                for f in feats(row, lab):
                    seen[f] += 1; hit[f] += (n == r['res'])
    # log-lift with smoothing toward chance (1/100)
    return {f: math.log((hit[f] + a * 0.01 * 100) / (seen[f] + a * 100) / 0.01) for f in seen}
def score(r, w):
    sc = defaultdict(float)
    for row in r['rows']:
        for lab, n in row['ch'].items():
            for f in feats(row, lab):
                sc[n] += max(0.0, w.get(f, 0.0))
    return sorted(range(100), key=lambda n: -sc[n])
tot = defaultdict(int); base = defaultdict(int); N = 0
for s in S:
    w = train([r for t in S if t != s for r in data[t]])
    for r in data[s]:
        rk = score(r, w); N += 1
        for k in (4, 10, 20): tot[k] += r['res'] in rk[:k]
        sr = src[s].get(r['ds'], {})
        base['final4'] += r['res'] in sr.get('top4', [])
        base['top10'] += r['res'] in sr.get('top10', [])
        base['top20'] += r['res'] in sr.get('top20', [])
print(f"rounds {N}; trained picker (leave-one-series-out): top4 {tot[4]} top10 {tot[10]} top20 {tot[20]}"
      f"  | chance {N*.04:.1f} {N*.1:.1f} {N*.2:.1f}")
print(f"current script same rounds: FINAL 4 {base['final4']}, top10 {base['top10']}, top20 {base['top20']}")
w = train([r for s in S for r in data[s]])
print("strongest features (all data):", sorted(w.items(), key=lambda kv: -kv[1])[:12])
