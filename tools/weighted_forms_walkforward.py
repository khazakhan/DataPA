"""Weighted-forms picker, walk-forward (user after AD110: 'check the weightage, balance the
open/close cut and 1-2 variant gaps in OCJP FINAL 4').
Every number gets a score = sum over FORMS of w_form * (best vote-rank weight of a number that
turns into it by that form).  Forms: exact, yx, tens cut, units cut, full cut, turned, turned+units
cut, turned+tens cut, units ±1, tens ±1.  Weights are learned by coordinate search on one half of
the live records and scored (top 4) on the other half, both directions.
python3 tools/weighted_forms_walkforward.py"""
import json, itertools
L = [json.loads(l) for l in open('rrr_records/live.jsonl')]
L = [r for r in L if r.get('result') is not None and len(r['ranked']) >= 10 and r.get('ep') is not None]
op = lambda a, b: ((b // 10 - a // 10) % 10, (b % 10 - a % 10) % 10)
ap = lambda n, o: ((n // 10 + o[0]) % 10) * 10 + (n % 10 + o[1]) % 10
T = lambda n: (n % 10) * 10 + n // 10
tc = lambda n: ((n // 10 + 5) % 10) * 10 + n % 10
uc = lambda n: (n // 10) * 10 + (n % 10 + 5) % 10
FORMS = {
 'exact': lambda v, R: [v], 'yx': lambda v, R: [ap(R, op(R, v)[::-1])],
 'tens cut': lambda v, R: [tc(v)], 'units cut': lambda v, R: [uc(v)], 'full cut': lambda v, R: [tc(uc(v))],
 'turned': lambda v, R: [T(v)], 'turned+units cut': lambda v, R: [uc(T(v))], 'turned+tens cut': lambda v, R: [tc(T(v))],
 'units ±1': lambda v, R: [(v // 10) * 10 + (v % 10 + d) % 10 for d in (1, -1)],
 'tens ±1': lambda v, R: [((v // 10 + d) % 10) * 10 + v % 10 for d in (1, -1)],
}
K = 10
def feats(r):
    R = r['ep']; F = {f: {} for f in FORMS}
    for i, v in enumerate(r['ranked'][:K]):
        s = 1 / (i + 1)
        for f, g in FORMS.items():
            for n in g(v, R):
                if s > F[f].get(n, 0): F[f][n] = s
    return F
FE = [feats(r) for r in L]
def top4(F, w):
    sc = {}
    for f, d in F.items():
        if w[f]:
            for n, s in d.items(): sc[n] = sc.get(n, 0) + w[f] * s
    return sorted(sc, key=lambda n: (-sc[n], n))[:4]
def hits(idx, w): return sum(L[i]['result'] in top4(FE[i], w) for i in idx)
def learn(idx):
    w = {f: (1.0 if f == 'exact' else 0.0) for f in FORMS}; best = hits(idx, w)
    for _ in range(3):
        for f in FORMS:
            for val in (0, .1, .2, .35, .5, .75, 1, 1.5):
                w2 = dict(w); w2[f] = val; h = hits(idx, w2)
                if h > best: best, w = h, w2
    return w, best
h = len(L) // 2; A, B = list(range(h)), list(range(h, len(L)))
base = {f: (1.0 if f == 'exact' else 0.0) for f in FORMS}
print(f'{len(L)} live rounds; plain vote top 4: first {hits(A, base)} | second {hits(B, base)} (chance {h*.04:.1f})')
for nm, tr, te in (('learn first -> test second', A, B), ('learn second -> test first', B, A)):
    w, b = learn(tr)
    print(f'{nm}: train {b} (plain {hits(tr, base)}), TEST {hits(te, w)} (plain {hits(te, base)})')
    print('   weights', {f: v for f, v in w.items() if v})
