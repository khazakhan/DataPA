"""Collect EP-family rows + every change for replay rounds.
python3 tools/finder_study.py pairs.json out.json"""
import sys, io, os, json, contextlib
from multiprocessing import Pool
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT); sys.path.insert(0, ROOT)
import DataProcessing as D
def t(o, f):
    if 'C' in f: o = D.KK_CUT_TOGGLE[o]
    if 'F' in f: o = D.SIGN_FLIP[o]
    return o
def one(p):
    ds, res = p
    with contextlib.redirect_stdout(io.StringIO()):
        try: D.run(open(ds), None, None)
        except Exception: return None
    ep = D._RRR_ASK.get('ep'); rows = D._RRR_ASK.get('rows', [])
    if ep is None: return None
    ex, ey = ep // 10, ep % 10
    forms = [(ep, 'EP'), (D.cut(ex) * 10 + D.cut(ey), 'full'), (ex * 10 + D.cut(ey), 'units'), (D.cut(ex) * 10 + ey, 'tens')]
    rel = {}
    for n, lab in forms: rel.setdefault(n, lab)
    for n, lab in forms:
        for d in (-1, 1):
            rel.setdefault((n // 10) * 10 + (n % 10 + d) % 10, lab + ('-1' if d < 0 else '+1'))
    out = []
    for pos, a, b, ox, oy, nx, ny, mark in rows:
        r = rel.get(a, 'none')
        if mark == 'LAST': r += '|LAST'
        ch = {}
        for nm, (xo, yo) in {'new': (nx, ny), 'old': (ox, oy)}.items():
            for lab, (p_, q_) in {'xy': (xo, yo), 'yx': (yo, xo)}.items():
                for fx in ('', 'F', 'C', 'FC'):
                    for fy in ('', 'F', 'C', 'FC'):
                        ch[f"{nm}.{lab}.x{fx or '-'}.y{fy or '-'}"] = D.apply_op(ex, t(p_, fx)) * 10 + D.apply_op(ey, t(q_, fy))
        out.append({'pos': pos, 'rel': r, 'ch': ch})
    return {'ds': ds, 'res': res, 'ep': ep, 'rows': out}
if __name__ == '__main__':
    pairs = json.load(open(sys.argv[1]))
    with Pool(6) as pool:
        res = [r for r in pool.map(one, pairs) if r]
    json.dump(res, open(sys.argv[2], 'w')); print(len(res), 'rounds')
