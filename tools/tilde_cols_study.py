"""Study for the user's ~xy / ~yx columns (2026-11-04, S32 screenshot:
'add two more columns ~xy and ~yx reverse with strong best suitable
prediction').  Per row, a ~ op takes x from one source and y from another
(row old/new x/y, outer x/y), each as is / flipped / cut sw / step sw /
cut sw + flip / cut sw + step sw / flip + step sw; the columns show both the
xy and the yx reading, so a form is scored on the union of both.  The * form
is excluded.  Ranked on all live rounds and checked leave-one-series-out.
python3 tools/tilde_cols_study.py"""
import sys, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
__file__ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'star_cols_study.py')
exec(open(__file__).read().split("combos = [")[0])
TR2 = ['', 'F', 'C', 'S', 'FC', 'CS', 'FS']
_tr = tr
def tr(name, t):
    if t in ('CS', 'FS'):
        return AB[STEP[D.OP_ABBREV[_tr(name, t[0])]]]
    return _tr(name, t)
SRC2 = ['ox', 'oy', 'nx', 'ny', 'Ox', 'Oy']
forms = {}
for sx in SRC2:
    for tx in TR2:
        for sy in SRC2:
            for ty in TR2:
                key = frozenset([((sx, tx), (sy, ty)), ((sy, ty), (sx, tx))])
                forms[key] = ((sx, tx), (sy, ty))
STAR = (('oy', ''), ('ox', 'FC'))
forms = [f for f in forms.values() if frozenset([f, (f[1], f[0])]) != frozenset([STAR, (STAR[1], STAR[0])])]
def sets(f):
    return [numset(r, (f[0], f[1], 'all rows')) | numset(r, (f[1], f[0], 'all rows')) for r in R]
S = {f: sets(f) for f in forms}
def score(f, idx):
    h = sum(R[i]['result'] in S[f][i] for i in idx); e = sum(len(S[f][i]) for i in idx) / 100
    return ((h - e) / math.sqrt(e) if e else -9), h, e
allidx = list(range(len(R)))
rank = sorted(forms, key=lambda f: -score(f, allidx)[0])
print(f'{len(forms)} forms on {len(R)} rounds (luck alone gives a best z near +3.5 among this many)')
for f in rank[:8]:
    z, h, e = score(f, allidx); print(f'  x={f[0]} y={f[1]}: {h} vs chance {e:.1f}  z {z:+.1f}')
H = E = 0
for s in sorted({r['round'][0] for r in R}):
    tr_i = [i for i in allidx if R[i]['round'][0] != s]; te = [i for i in allidx if R[i]['round'][0] == s]
    f = max(forms, key=lambda f: score(f, tr_i)[0]); z, h, e = score(f, te); H += h; E += e
    print(f'  held-out {s}: pick x={f[0]} y={f[1]} -> {h} vs chance {e:.1f}')
print(f'  held-out total {H} vs chance {E:.1f}')
for nm, f in [('* sign flipped', (('oy', 'F'), ('ox', 'C'))), ('* cut switched', (('oy', 'C'), ('ox', 'F'))), ('* as is reversed (x = old x, y = old y FC)', (('ox', ''), ('oy', 'FC')))]:
    if f in S: z, h, e = score(f, allidx); print(f'  {nm}: {h} vs chance {e:.1f}  z {z:+.1f}')
