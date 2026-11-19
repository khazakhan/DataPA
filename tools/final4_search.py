"""FINAL 4 search engine (user AE81: 'keep on search ... until best logic found').
Learns a per-number score from many features and picks the top 4, tested ONLY on rounds it never trained on.
Part A - logged rounds (rrr_records/live.jsonl): features = every table's membership, plain-vote rank,
  OPEN/CLOSE vote digit scores, SHADOW chart-step score, EP/ROOT repeat, chart frequencies, EP followers.
  Walk-forward: train on all earlier rounds, predict the next block of 50, retrain; several models.
Part B - charts only (all series, ~62k positions): same chart features, leave-one-chart-out.
Compared with the plain vote top 4 (Part A) and chance 4%.
  python3 tools/final4_search.py [A|B|AB]"""
import json, os, re, sys, glob, warnings
import numpy as np
warnings.filterwarnings('ignore')
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
_cache = {}
def chart(p):
    if p not in _cache:
        try: _cache[p] = [int(x) for x in re.findall(r'(?<!\*)\b\d\d\b', open(p).read())]
        except Exception: _cache[p] = []
    return _cache[p]
def nums(l):
    out = []
    for x in l if isinstance(l, list) else []:
        v = x[0] if isinstance(x, (list, tuple)) else x
        if isinstance(v, int) and 0 <= v <= 99: out.append(v)
    return out
def chart_feats(fl):
    """10 chart-only features for each of the 100 numbers, from results fl (before the round)."""
    e = fl[-1]; S = list(zip(fl, fl[1:]))
    t = np.zeros(10); u = np.zeros(10)
    for a, b in S: t[(b // 10 - a // 10) % 10] += 1; u[(b % 10 - a % 10) % 10] += 1
    t /= max(len(S), 1); u /= max(len(S), 1)
    T1 = np.zeros((10, 10)); U1 = np.zeros((10, 10))
    for a, b in S: T1[a // 10, b // 10] += 1; U1[a % 10, b % 10] += 1
    T1 = (T1[e // 10] + 1) / (T1[e // 10].sum() + 10); U1 = (U1[e % 10] + 1) / (U1[e % 10].sum() + 10)
    tf = np.bincount([v // 10 for v in fl[-200:]], minlength=10) / 200
    uf = np.bincount([v % 10 for v in fl[-200:]], minlength=10) / 200
    nf = np.bincount(fl[-300:], minlength=100) / 300
    fo = np.zeros(100)
    for a, b in S:
        if a == e: fo[b] += 1
    fo /= max(fo.sum(), 1)
    gap = np.full(100, len(fl), float)
    for i, v in enumerate(fl): gap[v] = len(fl) - i
    gap = np.minimum(gap, 300) / 300
    n = np.arange(100); ts = (n // 10 - e // 10) % 10; us = (n % 10 - e % 10) % 10
    F = np.stack([t[ts] * u[us], t[ts], u[us], T1[n // 10] * U1[n % 10], tf[n // 10] * uf[n % 10],
                  nf, fo, gap, (n == e).astype(float), ((n // 10 == e // 10) | (n % 10 == e % 10)).astype(float)], 1)
    return F
CH_NAMES = ['shadow step', 'tens step', 'units step', 'markov', 'digit freq', 'num freq', 'EP followers', 'gap', 'EP repeat', 'shares digit']

def part_a():
    R = [r for r in map(json.loads, open('rrr_records/live.jsonl'))
         if r.get('result') is not None and r.get('ranked') and isinstance(r.get('lists'), dict)]
    keys = [k for k in sorted({k for r in R for k in r['lists']}) if sum(k in r['lists'] for r in R) > 0.8 * len(R)]
    X, Y, base = [], [], []
    for r in R:
        fl = [v for v in chart(r['dataset']) if v is not None]
        if len(fl) < 100: continue
        rk = nums(r['ranked']); n = np.arange(100)
        M = np.zeros((100, len(keys)))
        for j, k in enumerate(keys):
            for v in set(nums(r['lists'].get(k, []))): M[v, j] = 1
        rkf = np.zeros(100); 
        for i, v in enumerate(rk[:40]): rkf[v] = 1 / (1 + i)
        o = np.zeros(10); c = np.zeros(10)
        for i, v in enumerate(rk[:10]): o[v // 10] += 10 - i; c[v % 10] += 10 - i
        o /= max(o.sum(), 1); c /= max(c.sum(), 1)
        extra = np.stack([rkf, o[n // 10], c[n % 10], o[n // 10] * c[n % 10], (n == r['ep']).astype(float), M.sum(1) / len(keys)], 1)
        X.append(np.hstack([M, extra, chart_feats(fl)])); Y.append((n == r['result']).astype(int)); base.append(rk[:4])
    X = np.array(X); Y = np.array(Y); N = len(X)
    names = keys + ['plain rank', 'OPEN score', 'CLOSE score', 'OPENxCLOSE', 'ROOT repeat', 'list count'] + CH_NAMES
    print(f"Part A: {N} logged rounds, {X.shape[2]} features per number")
    models = {'logistic C=0.1': lambda: LogisticRegression(C=0.1, max_iter=2000),
              'logistic C=1': lambda: LogisticRegression(C=1, max_iter=2000),
              'grad boost': lambda: HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_leaf_nodes=15, l2_regularization=1.0)}
    start, step = 300, 50
    res = {m: [] for m in models}; plain = []; coef = None
    for s in range(start, N, step):
        tr = slice(0, s); te = range(s, min(s + step, N))
        Xt = X[tr].reshape(-1, X.shape[2]); Yt = Y[tr].reshape(-1)
        for m, mk in models.items():
            clf = mk().fit(Xt, Yt)
            if m == 'logistic C=0.1': coef = clf.coef_[0]
            for i in te:
                p = clf.predict_proba(X[i])[:, 1]; top = np.argsort(-p)[:4]
                res[m].append(int(Y[i][top].sum()))
        for i in te: plain.append(int(Y[i][base[i]].sum()) if len(base[i]) == 4 else 0)
    T = len(plain); h = T // 2
    print(f"walk-forward test rounds: {T} (rounds {start}-{N}); chance 4% = {T*0.04:.1f}")
    print(f"  {'plain vote top 4':18s} {sum(plain[:h]):3d} | {sum(plain[h:]):3d}  total {sum(plain)} ({sum(plain)/T*100:.1f}%)")
    for m, v in res.items():
        print(f"  {m:18s} {sum(v[:h]):3d} | {sum(v[h:]):3d}  total {sum(v)} ({sum(v)/T*100:.1f}%)")
    if coef is not None:
        top = np.argsort(-np.abs(coef))[:10]
        print("  strongest logistic weights:", ', '.join(f"{names[j]} {coef[j]:+.2f}" for j in top))

def load_seq(p):
    seq = []
    for line in open(p):
        for t in line.split():
            if re.fullmatch(r'\d\d', t): seq.append(int(t))
    return seq
def part_b():
    files = {}
    for p in glob.glob('rrr_datasets/*.txt'):
        m = re.fullmatch(r'rrr_datasets/([a-z]+)(\d+)\.txt', p)
        if m and (m.group(1) not in files or int(m.group(2)) > files[m.group(1)][0]): files[m.group(1)] = (int(m.group(2)), p)
    data = {}
    for s, (_, p) in sorted(files.items()):
        fl = load_seq(p)
        if len(fl) < 1200: continue
        key = tuple(fl[:50])                      # skip duplicate charts (same history under another letter)
        if any(k == key for k, _ in data.values()): continue
        Xs, Ys = [], []
        for i in range(400, len(fl), 3):           # every 3rd position keeps it fast
            Xs.append(chart_feats(fl[:i])); Ys.append((np.arange(100) == fl[i]).astype(int))
        data[s] = (key, (np.array(Xs), np.array(Ys)))
    print(f"\nPart B: {len(data)} distinct charts, {sum(len(v[1][1]) for v in data.values())} test positions")
    tot = {'logistic': 0, 'shadow only': 0, 'n': 0}
    for s in data:
        Xtr = np.concatenate([data[k][1][0].reshape(-1, 10) for k in data if k != s]); Ytr = np.concatenate([data[k][1][1].reshape(-1) for k in data if k != s])
        clf = LogisticRegression(C=1, max_iter=2000).fit(Xtr, Ytr)
        Xs, Ys = data[s][1]
        for x, y in zip(Xs, Ys):
            tot['logistic'] += y[np.argsort(-clf.predict_proba(x)[:, 1])[:4]].sum()
            tot['shadow only'] += y[np.argsort(-x[:, 0], kind='stable')[:4]].sum(); tot['n'] += 1
    n = tot['n']
    print(f"  leave-one-chart-out top 4: logistic {tot['logistic']} ({tot['logistic']/n*100:.2f}%), SHADOW score {tot['shadow only']} ({tot['shadow only']/n*100:.2f}%), chance 4.00%")
if __name__ == '__main__':
    w = sys.argv[1] if len(sys.argv) > 1 else 'AB'
    if 'A' in w: part_a()
    if 'B' in w: part_b()
