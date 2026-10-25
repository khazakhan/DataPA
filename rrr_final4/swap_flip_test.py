"""User idea after N264 = 74 (EP 37): FINAL 4 #2 61 (c-2/c-1) with the sides
swapped and the new y sign flipped gives c-1/c+2 = 74.  Test on every replayed
round: the 4 numbers made this way from FINAL 4 (and the other swap/sign
variants), hits against chance (4 numbers = 4%)."""
import json, sys, glob, os, re
R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and r.get('res') is not None]
S = os.path.dirname(sys.argv[1])
seen = {(r['series'], r['k']) for r in R}
for f in glob.glob(os.path.join(S, 'd2_[0-9]*.json')):
    m = re.search(r'd2_(\d+)\.json$', f)
    if not m: continue
    k = int(m.group(1))
    nxt = f'rrr_datasets/n{k + 1}.txt'
    if ('n', k) in seen or not os.path.exists(nxt): continue
    d = json.load(open(f)); d.update(series='n', k=k, res=int(open(nxt).read().split()[-1])); R.append(d)
def side(s):
    c = s.startswith('c'); t = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if t in ('', 'nc') else int(t))
def ap(d, c, k): return (((d + 5) % 10 if c else d) + k) % 10
def num(ep, x, y): return ap(ep // 10, *x) * 10 + ap(ep % 10, *y)
def final4(r):
    tb = [n for n, _ in r['table']]; st = [x[0] if isinstance(x, list) else x for x in r['strong']]
    L = {'rec': r['rec'], 'table': tb, 'again': r['again'], 'wide': r['wide'], 'yx': r['yx'], 'found': r['found']}
    v = lambda n: sum(n in set(L[k]) for k in L); t = lambda n: (n in st) + (n in set(r['ncspec']))
    top = sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n))[:4]
    op = {}
    for n, o, p, k in r['ocjp_full']: op.setdefault(n, o)
    return top, op
V = {'swap, flip new y (user)': lambda x, y: (y, (x[0], -x[1])),
     'swap, flip new x':        lambda x, y: ((y[0], -y[1]), x),
     'swap only':               lambda x, y: (y, x),
     'swap, flip both':         lambda x, y: ((y[0], -y[1]), (x[0], -x[1]))}
for name, rows in (('all series', R), ('series N', [r for r in R if r['series'] == 'n'])):
    n = len(rows); f4 = sum(r['res'] in final4(r)[0] for r in rows)
    print(f'{name}: {n} rounds, FINAL 4 {f4} = {f4 / n:.1%}')
    for vn, fn in V.items():
        h = sz = 0
        for r in rows:
            top, op = final4(r); s = set()
            for m in top:
                x, y = map(side, op[m].split('/')); s.add(num(r['ep'], *fn(x, y)))
            s -= set(top); h += r['res'] in s; sz += len(s)
        print(f'   {vn:<24} +{h} hits = {h / n:.1%}, {sz / n:.1f} new numbers a round (chance {sz / n:.1f}%)')
