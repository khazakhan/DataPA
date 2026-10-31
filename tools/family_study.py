"""Family picker study: PRIME numbers spread to their digit-cut families
(as is, tens cut, units cut, both cut).  Leave-one-series-out.
python3 tools/family_study.py"""
import json, math
from collections import defaultdict, Counter
S = 'FNMKO'
src = {s: json.load(open(f'rrr_records/replay/src{s}.json')) for s in S}
cut = lambda d: (d + 5) % 10
REL = {'as': lambda n: n, 'T': lambda n: cut(n // 10) * 10 + n % 10,
       'U': lambda n: (n // 10) * 10 + cut(n % 10), 'TU': lambda n: cut(n // 10) * 10 + cut(n % 10)}
def prime(r):
    s = r['src']; rk = s.get('rk', [])
    v = {n: (n in s.get('rule5', [])) + (n in s.get('rule2', [])) + (n in s.get('rule18', [])) for n in range(100)}
    rp = {x: i for i, x in enumerate(rk)}
    return sorted(range(100), key=lambda n: (-v[n], rp.get(n, 999), n))[:10]
def rel_of(res, p):
    return [k for k, f in REL.items() if f(p) == res]
# 1) plain coverage of family lists
N = sum(len(src[s]) for s in S)
for k in (4, 10):
    hit = sz = 0
    for s in S:
        for r in src[s]:
            fam = {f(p) for p in prime(r)[:k] for f in REL.values()}
            hit += r['res'] in fam; sz += len(fam)
    print(f"family of PRIME {k}: held {hit} of {N}, avg size {sz/N:.1f}, chance {sz/100:.1f}, lift {hit/(sz/100):.2f}")
# 2) when the result is in a PRIME family, which member and which PRIME rank
mem, rank = Counter(), Counter()
for s in S:
    for r in src[s]:
        for i, p in enumerate(prime(r)):
            for k in rel_of(r['res'], p): mem[k] += 1; rank[i + 1] += 1
print("member that came:", dict(mem)); print("PRIME rank whose family it was:", dict(sorted(rank.items())))
# 3) learned family picker: score(n) = sum over PRIME p with n in fam(p) of w_rank[p] * w_rel[rel]
def train(rounds):
    wr, wm = Counter(), Counter()
    for r in rounds:
        for i, p in enumerate(prime(r)):
            for k in rel_of(r['res'], p): wr[i] += 1; wm[k] += 1
    return {i: (wr[i] + 1) for i in range(10)}, {k: (wm[k] + 1) for k in REL}
tot = Counter(); base = Counter()
for s in S:
    wr, wm = train([r for t in S if t != s for r in src[t]])
    for r in src[s]:
        sc = defaultdict(float); pr = prime(r)
        for i, p in enumerate(pr):
            for k, f in REL.items(): sc[f(p)] += wr[i] * wm[k]
        rk = sorted(range(100), key=lambda n: (-sc[n], pr.index(n) if n in pr else 99))
        for kk in (4, 8, 10, 16): tot[kk] += r['res'] in rk[:kk]
        for kk in (4, 8, 10): base[kk] += r['res'] in pr[:kk]
print(f"learned FAMILY picker (out of sample): top4 {tot[4]} top8 {tot[8]} top10 {tot[10]} top16 {tot[16]}"
      f" | PRIME {base[4]} {base[8]} {base[10]} | chance {N*.04:.1f} {N*.08:.1f} {N*.1:.1f} {N*.16:.1f}")
