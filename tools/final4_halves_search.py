"""FINAL 4 two-half rule search (user AF278: 'please go ahead').
Logged rounds that carry the shown FINAL 4 (final8[:4], from Z19) are split in time order into
half 1 and half 2. Every candidate rule builds 4 numbers from the lists logged for that round
(top-k of one list, then top-k of another, filled from the plain ranking). The best rules are
picked on half 1 only, then checked unchanged on half 2 (and the reverse, as a second check).
A rule is a winner only if it beats today's FINAL 4 on BOTH halves.
  python3 tools/final4_halves_search.py"""
import json, os, itertools
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

def nums(l):
    out = []
    for x in l if isinstance(l, list) else []:
        v = x[0] if isinstance(x, (list, tuple)) else x
        if isinstance(v, int) and 0 <= v <= 99 and v not in out: out.append(v)
    return out
cut = lambda d: (d + 5) % 10
def sources(r):
    L = r.get('lists') or {}
    ep, root = r['after'], r['ep']                       # EP = last number, ROOT = follower of earlier EP
    S = {k: nums(L.get(k)) for k in ('rec', 'strong', 'yx', 'table', 'charrow', 'hot', 'rule1', 'rule2', 'rule3', 'rule5', 'wide')}
    S.update({'ranked': nums(r.get('ranked')), 'prime10': nums(r.get('prime10')), 'final8': nums(r.get('final8')),
              'lastop': nums(r.get('lastop')), 'r28': nums(r.get('r28')), 'net80': nums(r.get('net80')),
              'prime4fam': nums(r.get('prime4fam')), 'prime4rev': nums(r.get('prime4rev')),
              'final8 tail': nums(r.get('final8'))[4:]})
    t, u = ep // 10, ep % 10; rt, ru = root // 10, root % 10
    S['EP repeat'] = [ep]; S['ROOT repeat'] = [root]
    S['EP yx'] = [u * 10 + t]; S['ROOT yx'] = [ru * 10 + rt]
    S['EP cuts'] = nums([cut(t) * 10 + u, t * 10 + cut(u), cut(t) * 10 + cut(u)])
    S['ROOT cuts'] = nums([cut(rt) * 10 + ru, rt * 10 + cut(ru), cut(rt) * 10 + cut(ru)])
    S['EP step'] = nums([((t + a) % 10) * 10 + (u + b) % 10 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))])
    S['ROOT step'] = nums([((rt + a) % 10) * 10 + (ru + b) % 10 for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))])
    S['yx of final4'] = nums([(v % 10) * 10 + v // 10 for v in S['final8'][:4]])
    keys = [k for k in S if k not in ('ranked', 'net80', 'final8 tail')]
    cnt = {}
    for k in keys:
        for v in S[k]: cnt[v] = cnt.get(v, 0) + 1
    rk = {v: i for i, v in enumerate(S['ranked'])}
    S['list vote'] = sorted(cnt, key=lambda v: (-cnt[v], rk.get(v, 99), v))
    return S

def build(S, parts):
    out = []
    for src, k in parts:
        for v in S.get(src, [])[:k]:
            if len(out) < 4 and v not in out: out.append(v)
    for v in S['ranked']:
        if len(out) >= 4: break
        if v not in out: out.append(v)
    return out

R = [json.loads(l) for l in open('rrr_records/live.jsonl')]
R = [r for r in R if r.get('result') is not None and len(nums(r.get('final8'))) >= 4]
SS = [sources(r) for r in R]; Y = [r['result'] for r in R]
N = len(R); h = N // 2
names = sorted(SS[-1].keys())
rules = [((s, 4),) for s in names]
for a, b in itertools.permutations(names, 2):
    for k in (1, 2, 3): rules.append(((a, k), (b, 4)))
for a, b, c in itertools.permutations(['final8', 'ranked', 'prime10', 'rec', 'list vote', 'EP repeat', 'ROOT repeat',
                                       'EP yx', 'ROOT yx', 'yx of final4', 'strong', 'lastop', 'rule1', 'rule2', 'EP cuts', 'ROOT cuts'], 3):
    for k1, k2 in ((1, 1), (2, 1), (1, 2)): rules.append(((a, k1), (b, k2), (c, 4)))
def score(rule, idx):
    return sum(Y[i] in build(SS[i], rule) for i in idx)
H1, H2 = range(0, h), range(h, N)
base = ((('final8', 4),))
b1, b2 = score(base, H1), score(base, H2)
print(f"logged rounds with the shown FINAL 4: {N} ({R[0]['round']} .. {R[-1]['round']}); half 1 = {h}, half 2 = {N-h}")
print(f"{len(rules)} candidate rules; chance 4% = {h*0.04:.1f} per half")
print(f"today's FINAL 4: half 1 {b1} | half 2 {b2}  total {b1+b2} ({(b1+b2)/N*100:.1f}%)\n")
sc = [(score(r, H1), score(r, H2), r) for r in rules]
fmt = lambda r: ' + '.join(f"{s} top {k}" for s, k in r)
print("best 10 on half 1 (picked on half 1, then checked on half 2):")
for s1, s2, r in sorted(sc, key=lambda x: -x[0])[:10]:
    print(f"  {s1:3d} | {s2:3d}  {'WIN both' if s1 > b1 and s2 > b2 else '':8s} {fmt(r)}")
print("\nreverse check, best 10 on half 2 (then checked on half 1):")
for s1, s2, r in sorted(sc, key=lambda x: -x[1])[:10]:
    print(f"  {s1:3d} | {s2:3d}  {'WIN both' if s1 > b1 and s2 > b2 else '':8s} {fmt(r)}")
w = [x for x in sc if x[0] > b1 and x[1] > b2]
print(f"\nrules that beat today's FINAL 4 on both halves: {len(w)} of {len(rules)}")
import random
random.seed(1); fake = []
for _ in range(200):
    pick = lambda S: random.sample(range(100), 4)
    fake.append(sum(Y[i] in pick(None) for i in H2))
print(f"for scale: 200 random 4-number picks on half 2 average {sum(fake)/200:.1f}, best {max(fake)}")
for s1, s2, r in sorted(w, key=lambda x: -(x[0] + x[1]))[:10]:
    print(f"  {s1:3d} | {s2:3d}  total {s1+s2} ({(s1+s2)/N*100:.1f}%)  {fmt(r)}")

# rolling walk-forward: before each block of 50 rounds, pick the rule with the most hits on ALL earlier
# rounds, then use it unchanged on the next 50 (the fairest test: the rule never sees the rounds it is scored on)
import numpy as np
Hm = np.array([[Y[i] in build(SS[i], r) for i in range(N)] for r in rules], dtype=np.int32)
cs = np.cumsum(Hm, 1)
picked, basew, start = [], [], 200
for s in range(start, N, 50):
    j = int(np.argmax(cs[:, s - 1])); e = min(s + 50, N)
    picked.append(int(Hm[j, s:e].sum())); basew.append(sum(Y[i] in build(SS[i], base) for i in range(s, e)))
T = N - start
print(f"\nrolling walk-forward on rounds {start}-{N} ({T} rounds, chance {T*0.04:.1f}):")
print(f"  rule picked from the past each block: {sum(picked)} ({sum(picked)/T*100:.1f}%)  per block {picked}")
print(f"  today's FINAL 4 on the same rounds:   {sum(basew)} ({sum(basew)/T*100:.1f}%)  per block {basew}")
