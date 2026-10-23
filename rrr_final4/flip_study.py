"""User idea (2026-10-23, after N156): the result often comes from a FINAL 4
operation turned around on the EP - x and y ops swapped (yx), a sign flipped,
or the cut added / removed.  Test: build those forms from the FINAL 4 ops of
every replayed round and compare hits with their size (chance = size / 100).
Usage: python3 flip_study.py all.json   (all.json from rrr_datasets/dump_all.py)"""
import json, sys, itertools, collections

R = [r for r in json.load(open(sys.argv[1])) if r.get('ocjp_full') and 'res' in r]
fl = lambda v: [x[0] if isinstance(x, list) else x for x in v]
NEVER = ['rec', 'table', 'again', 'wide', 'yx', 'found']

def final4(r):
    """Shipped rule: votes in the never-repaired lists, then STRONG, then lower number."""
    ops = {}
    for v, op, *_ in r['ocjp_full']:
        ops.setdefault(v, op)
    lists = [set(fl(r.get(k, []))) for k in NEVER]
    strong = set(fl(r.get('strong', [])))
    score = lambda v: (-sum(v in s for s in lists), -(v in strong), v)
    return [(v, ops[v]) for v in sorted(ops, key=score)[:4]]

def side(tok):
    """'c-2' -> (cut, -2); 'nc' -> (False, 0); 'cut' -> (True, 0)."""
    if tok == 'nc': return (False, 0)
    if tok == 'cut': return (True, 0)
    if tok.startswith('c'): return (True, int(tok[1:]))
    return (False, int(tok))

def apply(d, s):
    c, k = s
    return (((d + 5) % 10 if c else d) + k) % 10

def last_side(a, b):
    """The op one digit went through: a -> b, as (cut, step)."""
    return {0: (False, 0), 1: (False, 1), 2: (False, 2), 9: (False, -1), 8: (False, -2),
            5: (True, 0), 6: (True, 1), 7: (True, 2), 4: (True, -1), 3: (True, -2)}[(b - a) % 10]

def nudge(s, last, mode):
    """mode 'toward': step moves 1 toward the last op's step (kept if equal);
    'free': both one up and one down (set grows)."""
    c, k = s
    if mode == 'toward':
        d = (last[1] > k) - (last[1] < k)
        return [(c, max(-2, min(2, k + d)))]
    return [(c, k)] + [(c, k + d) for d in (-1, 1) if -2 <= k + d <= 2]

def num(ep, sx, sy): return apply(ep // 10, sx) * 10 + apply(ep % 10, sy)

def forms(ep, op, swap, sign, cut, step=None, last=None):
    sx, sy = map(side, op.split('/'))
    out = set()
    for sw in ([False, True] if swap else [False]):
        a, b = (sy, sx) if sw else (sx, sy)
        for fx, fy in (itertools.product([1, -1], repeat=2) if sign else [(1, 1)]):
            for tx, ty in (itertools.product([0, 1], repeat=2) if cut else [(0, 0)]):
                ax = (a[0] != bool(tx), a[1] * fx)
                by = (b[0] != bool(ty), b[1] * fy)
                if step is None:
                    out.add(num(ep, ax, by))
                else:
                    for nx in nudge(ax, last[0], step):
                        for ny in nudge(by, last[1], step):
                            out.add(num(ep, nx, ny))
    return out

FAMILIES = {
    'FINAL 4, step 1 toward last op':  (False, False, False, 'toward'),
    'swap + signs, step toward last':  (True, True, False, 'toward'),
    'all moves, step toward last':     (True, True, True, 'toward'),
    'FINAL 4, step free +-1':          (False, False, False, 'free'),
    'swap + signs, step free +-1':     (True, True, False, 'free'),
    'FINAL 4 as given':              (False, False, False),
    'swap x/y only (yx)':            (True, False, False),
    'signs flipped only':            (False, True, False),
    'cut added/removed only':        (False, False, True),
    'swap + signs':                  (True, True, False),
    'swap + cut':                    (True, False, True),
    'signs + cut':                   (False, True, True),
    'swap + signs + cut (all)':      (True, True, True),
}
FAMILIES = {k: (v + (None,))[:4] for k, v in FAMILIES.items()}
PREV = {}
for r in R:
    PREV[(r['series'], r['k'])] = r

for label, sel in (('all series', lambda r: True), ('series N only', lambda r: r['series'] == 'n')):
    rows = [r for r in R if sel(r)]
    print(f'\n## {label}\n')
    print('| Forms built from FINAL 4 ops | Avg numbers | Hits | Hit rate | Chance (size/100) | Hits / chance |')
    print('|---|---|---|---|---|---|')
    for name, (sw, sg, ct, st) in FAMILIES.items():
        hits = size = n = 0
        for r in rows:
            ep = r['ep']
            p = PREV.get((r['series'], r['k'] - 1))
            if p is None or 'ep' not in p: continue   # need the last op
            last = (last_side(p['ep'] // 10, p['res'] // 10), last_side(p['ep'] % 10, p['res'] % 10))
            s = set()
            for v, op in final4(r):
                s |= forms(ep, op, sw, sg, ct, st, last)
            n += 1
            size += len(s); hits += r['res'] in s
        exp = size / 100
        print(f'| {name} | {size / n:.1f} | {hits} | {hits / n:.1%} | {exp / n:.1%} | {hits / exp:.2f} |')
