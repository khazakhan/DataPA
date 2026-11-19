"""OPEN/CLOSE majority-vote study (user AE57: 'fetch big bull pick from various table data and vote
majority'). Logged rounds in rrr_records/live.jsonl: each table in 'lists' votes for digits.
  A  current: rank-weighted top 10 of the plain vote (ranked)
  B  every table 1 vote, split over its numbers' digits
  C  every table votes for its own most common digit
  D  A + B (sum of normalised scores)
Scores: OPEN/CLOSE digit #1 and top 3, and OPEN1 x CLOSE4 as FINAL 4, per half.
  python3 tools/oc_majority_study.py"""
import json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
R = [r for r in map(json.loads, open('rrr_records/live.jsonl'))
     if r.get('result') is not None and r.get('ranked') and isinstance(r.get('lists'), dict)]
def nums(l):
    out = []
    for x in l if isinstance(l, list) else []:
        v = x[0] if isinstance(x, (list, tuple)) else x
        if isinstance(v, int) and 0 <= v <= 99: out.append(v)
    return out
def norm(s):
    t = sum(s) or 1; return [x / t for x in s]
def order(s): return sorted(range(10), key=lambda d: (-s[d], d))
def scores(r, f):
    rk = nums(r['ranked'])[:10]
    A = [0] * 10
    for i, v in enumerate(rk): A[f(v)] += 10 - i
    B = [0] * 10; C = [0] * 10
    for k, l in r['lists'].items():
        l = list(dict.fromkeys(nums(l)))
        if not l or len(l) > 40: continue
        c = [0] * 10
        for v in l: c[f(v)] += 1
        for d in range(10): B[d] += c[d] / len(l)
        C[order(c)[0]] += 1
    D = [a + b for a, b in zip(norm(A), norm(B))]
    return {'A': A, 'B': B, 'C': C, 'D': D}
half = len(R) // 2
res = {}
for i, r in enumerate(R):
    h = 0 if i < half else 1; y = r['result']
    so, sc = scores(r, lambda v: v // 10), scores(r, lambda v: v % 10)
    for m in 'ABCD':
        oo, cc = order(so[m]), order(sc[m])
        e = res.setdefault(m, [[0] * 5 for _ in range(2)])
        e[h][0] += oo[0] == y // 10; e[h][1] += y // 10 in oo[:3]
        e[h][2] += cc[0] == y % 10; e[h][3] += y % 10 in cc[:3]
        e[h][4] += oo[0] == y // 10 and y % 10 in cc[:4]
n = [half, len(R) - half]
print(f"{len(R)} logged rounds, halves {n}; chance digit 10% / top3 30% / OC14 4%")
for m, e in res.items():
    print(m, ' | '.join(f"OPEN1 {e[h][0]} top3 {e[h][1]}  CLOSE1 {e[h][2]} top3 {e[h][3]}  OC14 {e[h][4]}" for h in range(2)))
