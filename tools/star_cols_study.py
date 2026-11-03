"""Study for the user's *xy / *yx columns (2026-11-04).

Outer op = op from the number before the after number to the after number
(e.g. 18->64 = cut/c+1).  For every RRR row, a star op takes its x from one
source and its y from another, each source being outer x/y, row old x/y or
row new x/y, used as is / sign flipped / cut switched / step switched /
cut switched + flipped.  Read xy (= *xy column); *yx is the same combo with
x and y sources swapped, so it is in the grid too.  Each combo is scored on
all live rounds (rrr_records/live.jsonl): hits vs chance (= set size / 100),
and leave-one-series-out: pick the best combo on three series, test on the
fourth.  python3 tools/star_cols_study.py"""
import json, sys, os, io, contextlib, itertools, math
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
DIFF = {0: 'nc', 1: '+1', 2: '+2', 9: '-1', 8: '-2', 5: 'cut', 6: 'c+1', 7: 'c+2', 4: 'c-1', 3: 'c-2'}
STEP = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1', 'c+1': 'c+2', 'c+2': 'c+1', 'c-1': 'c-2', 'c-2': 'c-1', 'nc': 'nc', 'cut': 'cut'}
def op_of(a, b): return DIFF[(b - a) % 10]
def tr(name, t):
    o = AB[name]
    if t == 'F': o = D.SIGN_FLIP[o]
    elif t == 'C': o = D.KK_CUT_TOGGLE[o]
    elif t == 'FC': o = D.SIGN_FLIP[D.KK_CUT_TOGGLE[o]]
    elif t == 'S': return AB[STEP[name]]
    return o
R = [json.loads(l) for l in open('rrr_records/live.jsonl')]
for r in R:
    tok = [x for x in open(r['dataset']).read().split() if x.isdigit()]
    a, b = int(tok[-2]), int(tok[-1]); assert b == r['after']
    r['outer'] = (op_of(a // 10, b // 10), op_of(a % 10, b % 10))
SRC = ['Ox', 'Oy', 'ox', 'oy', 'nx', 'ny']; TR = ['', 'F', 'C', 'S', 'FC']
def src(row, r, s):
    return {'Ox': r['outer'][0], 'Oy': r['outer'][1], 'ox': row['old'][0], 'oy': row['old'][1], 'nx': row['new'][0], 'ny': row['new'][1]}[s]
FILT = {'all rows': lambda row, r: True,
        'rows sharing an outer op': lambda row, r: bool(set(row['old'] + row['new']) & set(r['outer'])),
        'LAST row': lambda row, r: row['last']}
def numset(r, combo):
    (sx, tx), (sy, ty), filt = combo
    ex, ey = r['ep'] // 10, r['ep'] % 10
    out = set()
    for row in r['rows']:
        if not FILT[filt](row, r): continue
        out.add(D.apply_op(ex, tr(src(row, r, sx), tx)) * 10 + D.apply_op(ey, tr(src(row, r, sy), ty)))
    return out
combos = [((sx, tx), (sy, ty), f) for sx in SRC for tx in TR for sy in SRC for ty in TR for f in FILT]
res = {}
for c in combos:
    sets = [numset(r, c) for r in R]
    res[c] = ([r['result'] in s for r, s in zip(R, sets)], [len(s) for s in sets])
def score(c, idx):
    h = sum(res[c][0][i] for i in idx); e = sum(res[c][1][i] for i in idx) / 100
    return (h - e) / math.sqrt(e) if e else -9, h, e
allidx = range(len(R))
best = sorted(combos, key=lambda c: -score(c, allidx)[0])[:12]
print(f'{len(combos)} combos on {len(R)} rounds. Best in-sample (expect ~+3 z by luck alone among this many):')
for c in best:
    z, h, e = score(c, allidx); print(f'  x={c[0][0]}{"/"+c[0][1] if c[0][1] else ""} y={c[1][0]}{"/"+c[1][1] if c[1][1] else ""} [{c[2]}]: {h} hits vs chance {e:.1f}  z={z:+.1f}')
ser = sorted({r['round'][0] for r in R}); tot_h = tot_e = 0
print('Leave-one-series-out:')
for s in ser:
    tr_i = [i for i in allidx if R[i]['round'][0] != s]; te = [i for i in allidx if R[i]['round'][0] == s]
    c = max(combos, key=lambda c: score(c, tr_i)[0]); z, h, e = score(c, te); tot_h += h; tot_e += e
    print(f'  test {s}: picked x={c[0]} y={c[1]} [{c[2]}] -> {h} hits vs chance {e:.1f}')
print(f'  total held-out {tot_h} vs chance {tot_e:.1f}')
user = ((('Ox', ''), ('Oy', 'FC'), 'LAST row'))
z, h, e = score(user, allidx); print(f"User's S26 move (outer x as is, outer y cut sw + flip): {h} hits vs chance {e:.1f}")
