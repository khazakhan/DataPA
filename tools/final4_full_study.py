"""Full study (user 2026-11-07): all 1,293 history rounds (+ live S/T rounds) - what was the result,
which operation it was on the EP and on the ROOT, how it relates to the RRR rows, and which FINAL 4
maker holds it most often on series it was NOT fitted on (leave-one-series-out)."""
import json, sys, io, re, contextlib, collections, itertools
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
OPS = list(D.OP_ABBREV.values())
ap = lambda e, x, y: D.apply_op(e // 10, AB[x]) * 10 + D.apply_op(e % 10, AB[y])
op_of = lambda e, r: (D.OP_ABBREV[D.find_op(e // 10, r // 10)], D.OP_ABBREV[D.find_op(e % 10, r % 10)])
H = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json'))
R = []
for h in H:
    if not h['rows'] or len(h['src'].get('rk', [])) < 4: continue
    try:
        tok = [int(t) for t in re.findall(r'(?<![\d*])\d{1,2}(?![\d*])', open('/home/khazakhan/DataScinceAnal/' + h['ds']).read())]
    except FileNotFoundError:
        continue
    last = [r for r in h['rows'] if r[7] == 'LAST'] or h['rows'][-1:]
    R.append(dict(series=h['series'], root=h['ep'], ep=tok[-1], res=h['res'], rows=h['rows'], last=last[0], rk=h['src']['rk']))
n = len(R)
print(f"rounds {n}, series {len(set(r['series'] for r in R))}")
# 1. result operation on ROOT and on EP
for base in ('root', 'ep'):
    cx = collections.Counter(); cy = collections.Counter(); cp = collections.Counter()
    for r in R:
        x, y = op_of(r[base], r['res']); cx[x] += 1; cy[y] += 1; cp[(x, y)] += 1
    print(f"\n1. result operation on {base.upper()} (each op = 10% by chance):")
    print("   x:", '  '.join(f"{o} {100*c/n:.1f}%" for o, c in cx.most_common()))
    print("   y:", '  '.join(f"{o} {100*c/n:.1f}%" for o, c in cy.most_common()))
    print("   top pairs:", '  '.join(f"{a}/{b} {c}" for (a, b), c in cp.most_common(6)), f"(chance {n/100:.1f} each)")
# 2. relation to the LAST row: same ops again / crossed / flipped
rel = collections.Counter()
for r in R:
    _, a, b, ox, oy, nx, ny, _t = r['last']
    x, y = op_of(r['root'], r['res'])
    rel['= LAST new ops'] += (x, y) == (nx, ny); rel['= LAST new ops crossed'] += (x, y) == (ny, nx)
    rel['= LAST old ops'] += (x, y) == (ox, oy); rel['= LAST old ops crossed'] += (x, y) == (oy, ox)
    rel['x = LAST new x'] += x == nx; rel['y = LAST new y'] += y == ny
    rel['x = LAST new y'] += x == ny; rel['y = LAST new x'] += y == nx
    ex, ey = op_of(r['root'], r['ep'])  # ROOT->EP move
    rel['= ROOT->EP op again'] += (x, y) == (ex, ey)
print("\n2. result op on ROOT vs the LAST row / ROOT->EP move (pair chance 1%, one side 10%):")
for k, v in rel.items(): print(f"   {k:26s} {v:4d} = {100*v/n:4.1f}%")
# 3. FINAL 4 makers, leave-one-series-out
def maker_freq(train, base):
    cx = collections.Counter(); cy = collections.Counter()
    for r in train:
        x, y = op_of(r[base], r['res']); cx[x] += 1; cy[y] += 1
    tx = [o for o, _ in cx.most_common(2)]; ty = [o for o, _ in cy.most_common(2)]
    return lambda r: [ap(r[base], a, b) for a in tx for b in ty]
def maker_trans(train, base, side):
    # result op given LAST new op (same side or crossed)
    T = collections.defaultdict(collections.Counter)
    for r in train:
        _, a, b, ox, oy, nx, ny, _t = r['last']; x, y = op_of(r[base], r['res'])
        kx, ky = (nx, ny) if side == 'same' else (ny, nx)
        T[('x', kx)][x] += 1; T[('y', ky)][y] += 1
    def f(r):
        _, a, b, ox, oy, nx, ny, _t = r['last']; kx, ky = (nx, ny) if side == 'same' else (ny, nx)
        tx = [o for o, _ in T[('x', kx)].most_common(2)] or OPS[:2]; ty = [o for o, _ in T[('y', ky)].most_common(2)] or OPS[:2]
        return [ap(r[base], a_, b_) for a_ in tx for b_ in ty]
    return f
def maker_pairfreq(train, base):
    c = collections.Counter(op_of(r[base], r['res']) for r in train); top = [p for p, _ in c.most_common(4)]
    return lambda r: [ap(r[base], a, b) for a, b in top]
def maker_resfreq(train):
    c = collections.Counter(r['res'] for r in train); top = [v for v, _ in c.most_common(4)]
    return lambda r: top
def maker_blend(train):
    # current ranking + op-pair frequency on ROOT and EP as tie-break weight
    cr = collections.Counter(op_of(r['root'], r['res']) for r in train); ce = collections.Counter(op_of(r['ep'], r['res']) for r in train)
    def f(r):
        sc = {v: (40 - i) / 40 for i, v in enumerate(r['rk'][:40])}
        for v in range(100):
            sc[v] = sc.get(v, 0) + 0.5 * (cr[op_of(r['root'], v)] + ce[op_of(r['ep'], v)]) / (2 * len(train) / 100)
        return sorted(range(100), key=lambda v: -sc[v])[:4]
    return f
MAKERS = {
    'current FINAL 4': lambda tr: (lambda r: r['rk'][:4]),
    'top-2 x op x top-2 y op on ROOT': lambda tr: maker_freq(tr, 'root'),
    'top-2 x op x top-2 y op on EP': lambda tr: maker_freq(tr, 'ep'),
    'top-4 op pairs on ROOT': lambda tr: maker_pairfreq(tr, 'root'),
    'top-4 op pairs on EP': lambda tr: maker_pairfreq(tr, 'ep'),
    'op after LAST new op, ROOT, same side': lambda tr: maker_trans(tr, 'root', 'same'),
    'op after LAST new op, ROOT, crossed': lambda tr: maker_trans(tr, 'root', 'cross'),
    'op after LAST new op, EP, same side': lambda tr: maker_trans(tr, 'ep', 'same'),
    'op after LAST new op, EP, crossed': lambda tr: maker_trans(tr, 'ep', 'cross'),
    'most frequent 4 results': maker_resfreq,
    'current ranking + EP/ROOT op frequency': maker_blend,
}
S = sorted(set(r['series'] for r in R))
print(f"\n3. FINAL 4 makers, fitted on the other series, scored on each held-out series ({n} rounds, chance 4% = {n*0.04:.0f}):")
out = {}
for name, mk in MAKERS.items():
    hit = 0
    for s in S:
        tr = [r for r in R if r['series'] != s]; f = mk(tr)
        hit += sum(r['res'] in f(r) for r in R if r['series'] == s)
    out[name] = hit
    print(f"   {name:42s} {hit:4d} = {100*hit/n:4.1f}%")
json.dump(out, open('/tmp/claude-1000/-home-khazakhan/891d18cb-db65-444d-a157-690398d88b6e/scratchpad/f4full.json', 'w'))
