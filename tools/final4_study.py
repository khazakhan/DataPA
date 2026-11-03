import json, sys, io, contextlib, itertools
import numpy as np
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
R = [json.loads(l) for l in open('/home/khazakhan/DataScinceAnal/rrr_records/live.jsonl')]
def t(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o
LISTS = ['strong','rec','yx','wide','table','charrow','hot','finder','rule1','rule2','rule3','rule5','rule18','rule22','rule28']
def feats(r):
    ex, ey = r['ep']//10, r['ep']%10
    F = np.zeros((100, 0)).tolist()
    mk = np.zeros((100, 5))       # makers by change count 0..4
    mkl = np.zeros((100, 3))      # LAST row makers 0..2
    for row in r['rows']:
        for nm in ('new', 'old'):
            for rd in ('xy', 'yx'):
                p, q = row[nm] if rd == 'xy' else row[nm][::-1]
                seen = {}
                for fx in ('', 'F', 'C', 'FC'):
                    for fy in ('', 'F', 'C', 'FC'):
                        v = D.apply_op(ex, t(AB[p], fx))*10 + D.apply_op(ey, t(AB[q], fy))
                        c = len(fx)+len(fy)
                        seen[v] = min(seen.get(v, 9), c)
                for v, c in seen.items():
                    mk[v, c] += 1
                    if row['last'] and c <= 2: mkl[v, c] += 1
    L = np.array([[v in set(r['lists'].get(k, []) or r.get(k, []) ) for k in LISTS] for v in range(100)], float)
    extra = np.array([[v in r.get('prime4fam',[]), v in r.get('prime4rev',[]), v in r.get('lastop',[])[:8], v in r.get('prime10',[])] for v in range(100)], float)
    rk = np.zeros((100, 1)); 
    for i, v in enumerate(r['ranked']): rk[v, 0] = (40 - i)/40
    return np.hstack([L, extra, mk, mkl, rk])
X = [feats(r) for r in R]; Y = [r['result'] for r in R]; S = [r['round'][0] for r in R]
names = LISTS + ['p4fam','p4rev','lastop8','prime10'] + [f'mk{c}' for c in range(5)] + [f'last{c}' for c in range(3)] + ['rank']
np.save('/home/khazakhan/DataScinceAnal/rrr_records/f4_X.npy', np.array(X))
json.dump(dict(Y=Y, S=S, names=names), open('/home/khazakhan/DataScinceAnal/rrr_records/f4_meta.json','w'))
# single-feature lift: P(result | feature on) vs base 1%
Xa = np.array(X); 
for j, n in enumerate(names):
    on = Xa[:, :, j] > 0
    hit = sum(on[i, Y[i]] for i in range(len(Y))); size = on.sum()
    print(f'{n:9s} held {hit:3d}/{len(Y)}  avg size {size/len(Y):5.1f}  lift {hit/ max(size,1)*100:4.2f}x')
cur = sum(Y[i] in R[i]['ranked'][:4] for i in range(len(R)))
print('current FINAL 4 hits', cur, 'of', len(R), 'chance 5.7')
