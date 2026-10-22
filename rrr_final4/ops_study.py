"""Walk-forward test (2026-10-22): can the operation pick FINAL 4 better than list votes?
Usage: python3 ops_study.py all.json   (all.json from rrr_datasets/dump_all.py)
Every score for round i is learned only from rounds before i."""
import json, sys, collections, math
import numpy as np

R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and 'res' in r]
order = {s: i for i, s in enumerate('b c d ds e f h i j k l m n'.split())}
R.sort(key=lambda r: (order.get(r['series'], 99), r['k']))
fl = lambda v: [x[0] if isinstance(x, list) else x for x in v]
NEVER = ['rec', 'table', 'again', 'wide', 'yx', 'found']

def cands(r):
    c = {}
    for v, op, place, form in r['ocjp_full']:
        e = c.setdefault(v, {'ops': set(), 'places': set(), 'forms': set()})
        e['ops'].add(op); e['places'].add(place); e['forms'].add(form)
    return c

def votes(r, v):
    return sum(v in set(fl(r.get(k, []))) for k in NEVER)

WARM = 100
stats = collections.defaultdict(lambda: [0, 0])  # key -> [hits, seen]
recent = collections.deque(maxlen=30)            # recent result ops
def rate(key, prior=0.04, w=20):
    h, n = stats[key]; return (h + prior * w) / (n + w)

methods = collections.Counter(); rounds = 0
rows_X, rows_y = [], []   # for walk-forward logistic model
def feats(r, v, e):
    xs = [o.split('/')[0] for o in e['ops']]; ys = [o.split('/')[1] for o in e['ops']]
    f = [votes(r, v),
         int(v in fl(r.get('strong', []))),
         math.log(max(rate(('op', o)) for o in e['ops'])),
         math.log(max(rate(('x', x)) for x in xs)),
         math.log(max(rate(('y', y)) for y in ys)),
         math.log(max(rate(('place', p)) for p in e['places'])),
         math.log(max(rate(('form', f_)) for f_ in e['forms'])),
         len(e['places']),
         sum(o in recent for o in e['ops'])]
    return f
w = None
for i, r in enumerate(R):
    c = cands(r); res = r['res']
    if i >= WARM and res in c:
        rounds += 1
        F = {v: feats(r, v, e) for v, e in c.items()}
        tie = lambda v: -v * 1e-6
        def top(score): return sorted(c, key=lambda v: -(score(v) + tie(v)))[:4]
        picks = {
            'current (list votes)': top(lambda v: F[v][0] * 100 + F[v][1]),
            'op seen most': top(lambda v: F[v][2]),
            'x op + y op seen most': top(lambda v: F[v][3] + F[v][4]),
            'OCJP place hit rate': top(lambda v: F[v][5]),
            'OCJP form hit rate': top(lambda v: F[v][6]),
            'recent 30 ops': top(lambda v: F[v][8] * 10 + F[v][0]),
            'votes then op rate': top(lambda v: F[v][0] * 100 + F[v][2]),
            'votes then place rate': top(lambda v: F[v][0] * 100 + F[v][5]),
            'most OCJP places': top(lambda v: F[v][7] * 100 + F[v][0]),
        }
        if w is not None:
            Xn = {v: (np.array(F[v]) - mu) / sd for v in c}
            picks['logistic (all features)'] = top(lambda v: float(Xn[v] @ w))
        for k, p in picks.items(): methods[k] += res in p
        methods['random 4 of OCJP'] += 4 / len(c)
        for v in c:
            rows_X.append(F[v]); rows_y.append(int(v == res))
        if rounds % 50 == 0:   # refit on everything seen so far
            X = np.array(rows_X, float); y = np.array(rows_y, float)
            mu, sd = X.mean(0), X.std(0) + 1e-9; Xs = (X - mu) / sd
            w = np.zeros(X.shape[1]); b = -3.0
            for _ in range(300):
                p = 1 / (1 + np.exp(-(Xs @ w + b)))
                w -= 0.5 * (Xs.T @ (p - y)) / len(y); b -= 0.5 * (p - y).mean()
    # learn from this round's result (after scoring it)
    if res in c:
        e = c[res]
        for v, ee in c.items():
            hit = v == res
            for o in ee['ops']: stats[('op', o)][1] += 1; stats[('op', o)][0] += hit
            for x in {o.split('/')[0] for o in ee['ops']}: stats[('x', x)][1] += 1; stats[('x', x)][0] += hit
            for y_ in {o.split('/')[1] for o in ee['ops']}: stats[('y', y_)][1] += 1; stats[('y', y_)][0] += hit
            for p_ in ee['places']: stats[('place', p_)][1] += 1; stats[('place', p_)][0] += hit
            for f_ in ee['forms']: stats[('form', f_)][1] += 1; stats[('form', f_)][0] += hit
        for o in e['ops']: recent.append(o)

print(f'{len(R)} rounds, {rounds} scored after {WARM} warm-up (4 of 100 by chance = {rounds*0.04:.1f})')
for k, v in sorted(methods.items(), key=lambda t: -t[1]):
    print(f'  {k:28s} {v:6.1f}  {v/rounds:.1%}')
