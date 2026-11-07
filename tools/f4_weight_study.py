"""User 2026-11-07: 'make FINAL 4 more powerful'. Re-weight what FINAL 4 already uses (4 voting lists,
3 tie lists, full-ranking position, OCJP place) with weights learned on the other series and scored on the
held-out series (leave-one-series-out, 1,293 rounds in rrr_records/f4_inputs.json)."""
import json, itertools, collections
import numpy as np
D = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/f4_inputs.json'))
LN = list(D[0]['lists'].keys())
def feats(d, v):
    f = [int(v in d['lists'][k]) for k in LN] + [int(v in t) for t in d['tie']]
    rk = d['tie'][1]; f.append(1 - (rk.index(v) / 100 if v in rk else 1))
    p = d['place'].get(str(v)); f.append(1 - (p / 100 if p is not None else 1))
    return f
grid = [0, 1, 2, 4]
W = np.array([w + t for w in itertools.product(grid, repeat=4)
              for t in itertools.product([0, .5], [0, .5], [0, .5], [0, 1, 3], [0, 1, 3])], float)
HIT = np.zeros((len(D), len(W)), bool)
for i, d in enumerate(D):
    c = sorted(set(d['cands']))
    F = np.array([feats(d, v) for v in c], float); sc = F @ W.T            # cands x weights
    if d['res'] not in c: continue
    j = c.index(d['res']); r = sc[j]
    better = (sc > r).sum(0) + ((sc == r) & (np.array(c)[:, None] < d['res'])).sum(0)  # ties: lower number first
    HIT[i] = better < 4
now = sum(d['res'] in d['final4'] for d in D)
print(f"rounds {len(D)}; FINAL 4 now {now}; weight sets {len(W)}; result among candidates {sum(d['res'] in d['cands'] for d in D)}")
ser = np.array([d['series'] for d in D]); held = 0
for s in sorted(set(ser)):
    tr, te = ser != s, ser == s
    b = HIT[tr].sum(0).argmax(); h = int(HIT[te, b].sum()); held += h
    print(f"  series {s:4s} {te.sum():4d} rds  held-out {h:3d}  (FINAL 4 now {sum(d['res'] in d['final4'] for d in D if d['series']==s):3d})  w={W[b].tolist()}")
print(f"HELD-OUT re-weighted FINAL 4: {held} of {len(D)}  vs FINAL 4 now {now}  (chance 52)")
b = HIT.sum(0).argmax(); print(f"best fitted on ALL rounds (optimistic, not a test): {HIT[:, b].sum()}  w={W[b].tolist()}")
