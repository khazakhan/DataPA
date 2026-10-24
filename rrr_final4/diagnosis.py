"""Deep diagnosis of OCJP FINAL 4 / MASTER (2026-10-25, after N222 = 83).
Run on the full replay dump (all.json, every series b..n, 1018 rounds).
Every rate is set against what its own size gives by chance."""
import json, sys, math
from collections import Counter

R = [r for r in json.load(open(sys.argv[1])) if r.get('res') is not None and r['ocjp']]
N = len(R)
VOTE = ('rec', 'table', 'again', 'wide', 'yx', 'found')

def lists(r):
    out = {k: set(r[k]) for k in VOTE if k != 'table'}
    out['table'] = {x for x, _ in r['table']}
    return out

def order(r):
    L = lists(r); oc = sorted(set(r['ocjp']))
    return sorted(oc, key=lambda m: (-sum(m in v for v in L.values()),
                                     -((m in r['strong']) + 1 + (m in r['ncspec'])), m))

def binom_p(k, n, p):                     # one-sided P(X >= k)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))

print(f'rounds {N}\n')

# 1. where does the result sit in the FINAL 4 ordering?
ranks = []; outside = 0
for r in R:
    o = order(r)
    if r['res'] in o: ranks.append((o.index(r['res']) + 1, len(o)))
    else: outside += 1
print('1. result rank in the FINAL 4 ordering (rank 1 = MASTER)')
for lo, hi in ((1, 1), (1, 4), (5, 10), (11, 20), (21, 40), (41, 60), (61, 80), (81, 100)):
    k = sum(lo <= a <= hi for a, _ in ranks)
    exp = sum(max(0, min(hi, n) - lo + 1) / n for _, n in ranks)
    print(f'   ranks {lo:>2}-{hi:<3} {k:4d} hits   chance {exp:6.1f}   ratio {k / exp:4.2f}')
print(f'   result outside OCJP: {outside}')
k4 = sum(a <= 4 for a, _ in ranks); k1 = sum(a == 1 for a, _ in ranks)
print(f'   FINAL 4 {k4}/{N} = {k4/N:.1%} (p = {binom_p(k4, N, .04):.1e});  MASTER {k1}/{N} = {k1/N:.1%} (p = {binom_p(k1, N, .01):.2f})')

# 2. hit rate per number by vote count
print('\n2. chance a number is the result, by how many voting lists hold it (chance 1.0%)')
vc = Counter(); vh = Counter()
for r in R:
    L = lists(r)
    for m in set(r['ocjp']):
        v = sum(m in s for s in L.values()); vc[v] += 1; vh[v] += m == r['res']
for v in sorted(vc):
    print(f'   {v} votes: {vh[v]:4d} of {vc[v]:6d} numbers = {vh[v] / vc[v]:.2%}')

# 3. each list: hit rate against its own size
print('\n3. each list: hits vs what its size gives by chance')
for k in VOTE + ('strong', 'ncspec'):
    h = s = 0
    for r in R:
        v = {x for x, _ in r['table']} if k == 'table' else set(r[k])
        s += len(v); h += r['res'] in v
    print(f'   {k:<7} {h:4d} hits, chance {s / 100:6.1f}  ratio {h / max(s / 100, 1e-9):4.2f}')

# 4. the raw question: is the result's digit change from the EP uniform?
dx = Counter((r['res'] // 10 - r['ep'] // 10) % 10 for r in R)
dy = Counter((r['res'] % 10 - r['ep'] % 10) % 10 for r in R)
chi = lambda c: sum((c[i] - N / 10) ** 2 / (N / 10) for i in range(10))
print('\n4. digit change result - EP (mod 10); uniform = every op equally likely')
print('   tens  ', ' '.join(f'{dx[i]:3d}' for i in range(10)), f'  chi2 {chi(dx):5.1f} (9 df, 5% cut 16.9)')
print('   units ', ' '.join(f'{dy[i]:3d}' for i in range(10)), f'  chi2 {chi(dy):5.1f}')
res = Counter(r['res'] for r in R)
c100 = sum((res[i] - N / 100) ** 2 / (N / 100) for i in range(100))
print(f'   results 00-99 chi2 {c100:.1f} (99 df, 5% cut 123.2)')
pt = Counter((a['res'] // 10, b['res'] // 10) for a, b in zip(R, R[1:]))
cpt = sum((pt[(i, j)] - (N - 1) / 100) ** 2 / ((N - 1) / 100) for i in range(10) for j in range(10))
print(f'   tens digit after tens digit (10x10) chi2 {cpt:.1f} (81 df for independence, 5% cut 103.0)')

# 5. per series: is FINAL 4 steady or did one stretch carry it?
print('\n5. FINAL 4 by series')
by = {}
for r in R:
    s = r.get('series', '?'); by.setdefault(s, [0, 0]); by[s][1] += 1; by[s][0] += r['res'] in order(r)[:4]
for s, (h, n) in sorted(by.items(), key=lambda x: -x[1][1]):
    print(f'   {s:<3} {h:3d}/{n:<4} = {h / n:5.1%}')

# 6. the one non-uniform sign (tens digit after tens digit): does it predict
#    walk-forward?  Each round uses only the rounds before it.
print('\n6. walk-forward: next tens digit from the previous result\'s tens digit')
T = [[0] * 10 for _ in range(10)]; hit = Counter(); n6 = 0
for a, b in zip(R, R[1:]):
    row = T[a['res'] // 10]
    if sum(row) >= 20:
        rank = sorted(range(10), key=lambda d: (-row[d], d))
        for k in (1, 3): hit[k] += b['res'] // 10 in rank[:k]
        n6 += 1
    T[a['res'] // 10][b['res'] // 10] += 1
for k in (1, 3):
    print(f'   top {k} tens digit(s): {hit[k]}/{n6} = {hit[k] / n6:.1%}  (chance {k * 10}%, p = {binom_p(hit[k], n6, k / 10):.2f})')
