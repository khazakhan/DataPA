"""Walk-forward vote-weight test (2026-11-17, after AC152).  Each candidate number gets
score = sum of w[list] for every fired list holding it (+ a small bonus for its place in
the ranked list as tie-break).  Weights are learned ONLY from earlier rounds (each list's
lift = hits / chance so far, log-scaled), then the top 4 are scored on the next round.
Compared with the logged FINAL 4.  python3 tools/vote_weight_walkforward.py"""
import json, math, collections
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and r.get('lists')]
K = ['strong', 'rec', 'yx', 'wide', 'ncspec', 'table', 'charrow', 'hot', 'rule2', 'rule5', 'rule28']
hit = collections.Counter(); exp = collections.Counter()
mine = base = n = 0; halves = [[0, 0], [0, 0]]
for i, r in enumerate(L):
    if i >= 100:
        w = {k: math.log((hit[k] + 1) / (exp[k] + 1)) for k in K}
        rk = r['ranked']
        def sc(v):
            s = sum(w[k] for k in K if v in r['lists'].get(k, []))
            return s + (0.3 * (40 - rk.index(v)) / 40 if v in rk else 0)
        top = sorted(range(100), key=lambda v: -sc(v))[:4]
        f4 = (r.get('final8') or [])[:4] or rk[:4]
        a = r['result'] in top; b = r['result'] in f4
        mine += a; base += b; n += 1; h = 0 if n <= (len(L) - 100) // 2 else 1
        halves[h][0] += a; halves[h][1] += b
    for k in K:
        s = set(r['lists'].get(k, []))
        if s: hit[k] += r['result'] in s; exp[k] += len(s) / 100
print(f'rounds scored {n}: learned-weight top 4 = {mine} ({100*mine/n:.2f}%), logged FINAL 4 = {base} ({100*base/n:.2f}%), chance 4%')
print('halves (learned / logged):', halves)
print('final weights:', {k: round(math.log((hit[k]+1)/(exp[k]+1)), 2) for k in K})
