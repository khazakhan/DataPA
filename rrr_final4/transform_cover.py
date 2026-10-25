"""After N272 = 79: the user found 35 (c+2/-1) -> +1/c-2 = 79 (sides swapped,
both signs flipped).  Over N264-N272 three different transforms of a FINAL 4
op have each matched one result.  This measures how many numbers the whole
family of such transforms reaches each round, and how often the result is
among them: if the share of hits equals the share of the board covered,
finding a matching transform after the result is expected by chance."""
import json, sys, glob, os, re, itertools
R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and r.get('res') is not None]
S = os.path.dirname(sys.argv[1]); seen = {(r['series'], r['k']) for r in R}
for f in glob.glob(os.path.join(S, 'd2_*.json')):
    m = re.search(r'd2_(\d+)\.json$', f)
    if not m: continue
    k = int(m.group(1)); nxt = f'rrr_datasets/n{k + 1}.txt'
    if ('n', k) in seen or not os.path.exists(nxt): continue
    d = json.load(open(f)); d.update(series='n', k=k, res=int(open(nxt).read().split()[-1])); R.append(d)
def side(s):
    c = s.startswith('c'); t = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if t in ('', 'nc') else int(t))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
def ranked(r):
    tb = [n for n, _ in r['table']]; st = [x[0] if isinstance(x, list) else x for x in r['strong']]
    L = [r['rec'], tb, r['again'], r['wide'], r['yx'], r['found']]
    v = lambda n: sum(n in set(l) for l in L); t = lambda n: (n in st) + (n in set(r['ncspec']))
    op = {}
    for n, o, p, k in r['ocjp_full']: op.setdefault(n, o)
    return sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n)), op
SETS = {'swap / sign flips (8 forms)': (False, False),
        '+ cut moved or toggled (32 forms)': (True, False),
        '+ one step up/down (all)': (True, True)}
for name, rows in (('all series', R), ('series N', [r for r in R if r['series'] == 'n'])):
    n = len(rows); print(f'{name}: {n} rounds')
    for sn, (cuts, steps) in SETS.items():
        h = cov = 0
        for r in rows:
            rk, op = ranked(r); s = set()
            for m in rk[:4]:
                x, y = map(side, op[m].split('/'))
                for sw, fx, fy in itertools.product((0, 1), (1, -1), (1, -1)):
                    a, b = (y, x) if sw else (x, y)
                    for tx, ty in (itertools.product((0, 1), repeat=2) if cuts else [(0, 0)]):
                        for dx, dy in (itertools.product((-1, 0, 1), repeat=2) if steps else [(0, 0)]):
                            ka, kb = a[1] * fx + dx, b[1] * fy + dy
                            if abs(ka) > 2 or abs(kb) > 2: continue
                            s.add(ap(r['ep'] // 10, a[0] != bool(tx), ka) * 10 + ap(r['ep'] % 10, b[0] != bool(ty), kb))
            h += r['res'] in s; cov += len(s)
        print(f'   {sn:<36} covers {cov / n:5.1f} of 100 numbers a round; holds the result {h / n:5.1%}')
