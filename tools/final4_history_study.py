"""FINAL 4 study on the whole 6-month history (user 2026-11-05: 'use all the
data we played and adjust OCJP FINAL 4').

Input: rrr_records/history_all.json (every dataset file whose next file adds
one result: EP, result, RRR rows, every list the page shows, ranked top 40).
For each candidate number 00-99 of a round it builds features (which lists
hold it, its rank in the current ranking, how many RRR row forms make it with
0/1/2 changes, the */~/±/old columns) and tests FINAL 4 makers with
leave-one-series-out: fitted on every other series, scored on the held-out
one.  Prints hits vs the current FINAL 4 (ranked top 4) on the same rounds."""
import json, sys, io, contextlib, collections, math
import numpy as np
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
H = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json'))
H = [h for h in H if len(h['src'].get('rk', [])) >= 4]
ap = lambda e, x, y: D.apply_op(e // 10, x) * 10 + D.apply_op(e % 10, y)


def t(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o


LISTS = sorted({k for h in H for k in h['src'] if k not in ('rk',) and not k.startswith('top')})


def feats(h):
    e = h['ep']; F = np.zeros((100, 0))
    cols = []
    rk = h['src']['rk']
    r = np.zeros(100); r[:] = 0
    for i, v in enumerate(rk[:40]):
        r[v] = 1.0 / (1 + i)
    cols.append(r)
    for k in (4, 10, 20, 40):
        c = np.zeros(100); c[rk[:k]] = 1; cols.append(c)
    for k in LISTS:
        c = np.zeros(100); c[list(h['src'].get(k, []))] = 1; cols.append(c)
    mk = np.zeros((100, 3)); mkl = np.zeros((100, 3))
    extra = np.zeros((100, 5))
    for row in h['rows']:
        pos, a, b, ox, oy, nx, ny, tag = row
        ox, oy, nx, ny = AB[ox], AB[oy], AB[nx], AB[ny]
        for p, q in ((nx, ny), (ny, nx), (ox, oy), (oy, ox)):
            seen = {}
            for fx in ('', 'F', 'C', 'FC'):
                for fy in ('', 'F', 'C', 'FC'):
                    c = len(fx) + len(fy)
                    if c > 2: continue
                    v = ap(e, t(p, fx), t(q, fy)); seen[v] = min(seen.get(v, 9), c)
            for v, c in seen.items():
                mk[v, c] += 1
                if tag == 'LAST': mkl[v, c] += 1
        sx, sy = D._star_ops(ox, oy); tx, ty = D._tilde_ops(ox, oy)
        for j, (p, q) in enumerate(((sx, sy), (tx, ty), (nx, oy))):
            extra[ap(e, p, q), j] = 1; extra[ap(e, q, p), j] = 1
        extra[ap(e, oy, D.SIGN_FLIP[ny]), 3] = 1; extra[ap(e, ox, D.SIGN_FLIP[nx]), 3] = 1
        extra[ap(e, ox, oy), 4] = 1; extra[ap(e, oy, ox), 4] = 1
    X = np.column_stack(cols + [np.log1p(mk), np.log1p(mkl), extra])
    return X


names = ['rank', 'top4', 'top10', 'top20', 'top40'] + LISTS + ['mk0', 'mk1', 'mk2', 'mkl0', 'mkl1', 'mkl2',
                                                             'star', 'tilde', 'newold', 'sflip', 'oldops']
X = np.stack([feats(h) for h in H]); Y = np.array([h['res'] for h in H]); S = np.array([h['series'] for h in H])
n = len(H)
cur = np.array([Y[i] in H[i]['src']['rk'][:4] for i in range(n)])
print(f"rounds {n}, series {len(set(S))}, current FINAL 4 hits {cur.sum()} ({cur.mean()*100:.1f}%), chance 4.0%")
lift = []
for j, nm in enumerate(names):
    col = X[:, :, j] > 0
    held = sum(col[i, Y[i]] for i in range(n)); size = col.sum() / 100
    if size > 5: lift.append((held / size, nm, held, round(size, 1)))
print("lists by lift on all rounds (held / chance):")
for l, nm, h_, s_ in sorted(lift, reverse=True)[:12]:
    print(f"   {nm:10s} {h_:4d} vs {s_:7.1f}  lift {l:.2f}")


def top4(score):
    return np.argsort(-(score + np.random.default_rng(0).random(100) * 1e-9))[:4]


from sklearn.linear_model import LogisticRegression
res = collections.defaultdict(lambda: [0, 0, 0])
for s in sorted(set(S)):
    te = np.where(S == s)[0]; tr = np.where(S != s)[0]
    if len(te) < 5: continue
    Xt = X[tr].reshape(-1, X.shape[2]); yt = np.zeros(len(tr) * 100)
    for k_, i in enumerate(tr): yt[k_ * 100 + Y[i]] = 1
    mu, sd = Xt.mean(0), Xt.std(0) + 1e-9
    for C in (0.01, 0.1):
        m = LogisticRegression(C=C, max_iter=2000).fit((Xt - mu) / sd, yt)
        hit = sum(Y[i] in top4(m.decision_function((X[i] - mu) / sd)) for i in te)
        res[f'logit C={C}'][0] += hit
    # lift-weighted votes learned on the training series
    w = np.zeros(X.shape[2])
    for j in range(X.shape[2]):
        col = X[tr, :, j] > 0
        held = sum(col[k_, Y[i]] for k_, i in enumerate(tr)); size = col.sum() / 100
        w[j] = math.log((held + 1) / (size + 1)) if size > 0 else 0
    hit = sum(Y[i] in top4((X[i] > 0) @ w) for i in te); res['lift votes'][0] += hit
    for k in res: res[k][1] += len(te); res[k][2] += cur[te].sum()
print("leave-one-series-out (fitted on the other series):")
for k, (h_, nn, c_) in res.items():
    print(f"   {k:12s} {h_:4d} of {nn}  vs current FINAL 4 {c_}   (chance {nn*0.04:.0f})")

# per series: lift votes vs current (newest series are the honest test: FINAL 4 was built before them)
print("per series (lift votes / current / rounds):")
for s in sorted(set(S)):
    te = np.where(S == s)[0]; tr = np.where(S != s)[0]
    w = np.zeros(X.shape[2])
    for j in range(X.shape[2]):
        col = X[tr, :, j] > 0
        held = sum(col[k_, Y[i]] for k_, i in enumerate(tr)); size = col.sum() / 100
        w[j] = math.log((held + 1) / (size + 1)) if size > 0 else 0
    hv = sum(Y[i] in top4((X[i] > 0) @ w) for i in te)
    print(f"   {s}: {hv:3d} / {cur[te].sum():3d} / {len(te)}")
