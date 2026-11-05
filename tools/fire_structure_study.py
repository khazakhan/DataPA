"""FIRE STRUCTURE study (user 2026-11-05: 'find the structure how the result has
been firing from the Ops given ... check with EP and ROOT ... plan the structure').

All 1293 history rounds (rrr_records/history_all.json).  ROOT = h['ep'],
EP = last number of the dataset, result = h['res'].
A) generator recipes: base (ROOT/EP) x row role (LAST, prev, first) x old/new
   ops x xy/yx reading x a change on each side (as, flip, cut toggle, step
   swap and mixes, fixed nc / cut).  One recipe = one number per round.
B) op-transition table: result x-op / y-op on the base learnt from the LAST
   row op of the same side (and crossed side), top 2 x top 2 = 4 numbers.
Everything is chosen on the other series and scored on the held-out series."""
import json, sys, io, os, re, itertools, collections, contextlib
os.chdir('/home/khazakhan/DataScinceAnal'); sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
AB = {v: k for k, v in D.OP_ABBREV.items()}
H = [h for h in json.load(open('rrr_records/history_all.json')) if h['rows']]
for h in H:
    tk = [int(x) for x in open(h['ds']).read().split() if x.isdigit()]
    h['EP'] = tk[-1]
def side(o):
    c, k = D._op_side(o); return c, k
def app(d, c, k): return ((d + 5) % 10 + k) % 10 if c else (d + k) % 10
SW = {1: 2, 2: 1, -1: -2, -2: -1, 0: 0}
MODS = {'as': lambda c, k: (c, k), 'F': lambda c, k: (c, -k), 'C': lambda c, k: (not c, k),
        'S': lambda c, k: (c, SW[k]), 'FC': lambda c, k: (not c, -k), 'SC': lambda c, k: (not c, SW[k]),
        'FS': lambda c, k: (c, -SW[k]), 'nc': lambda c, k: (False, 0), 'cut': lambda c, k: (True, 0)}
def roles(rows):
    li = [i for i, r in enumerate(rows) if r[7] == 'LAST']; i = li[-1] if li else len(rows) - 1
    o = {'LAST': rows[i], 'first': rows[0]}
    if i > 0: o['prev'] = rows[i - 1]
    return o
def gens(h):
    g = {}
    for bn, b in (('ROOT', h['ep']), ('EP', h['EP'])):
        ex, ey = b // 10, b % 10
        for rn, r in roles(h['rows']).items():
            for on, (p0, q0) in (('new', (r[5], r[6])), ('old', (r[3], r[4]))):
                for rd, (p, q) in (('xy', (p0, q0)), ('yx', (q0, p0))):
                    cp, cq = side(p), side(q)
                    for mx, my in itertools.product(MODS, MODS):
                        g[(bn, rn, on, rd, mx, my)] = app(ex, *MODS[mx](*cp)) * 10 + app(ey, *MODS[my](*cq))
    return g
G = [gens(h) for h in H]; keys = set.intersection(*(set(g) for g in G))
hit = {k: [g[k] == h['res'] for g, h in zip(G, H)] for k in keys}
ser = sorted({h['series'] for h in H}); n = len(H)
print(f"rounds {n}, series {len(ser)}, recipes {len(keys)}")
tot = sorted(keys, key=lambda k: -sum(hit[k]))
print("best single recipes over all rounds (chance ~12.9 each; with this many recipes the best looks lucky):")
for k in tot[:10]: print(f"   {sum(hit[k]):3d}  {' '.join(k)}")
for bn in ('ROOT', 'EP'):
    ks = [k for k in keys if k[0] == bn]; avg = sum(sum(hit[k]) for k in ks) / len(ks)
    print(f"   average recipe on {bn}: {avg:.1f} (chance {n/100:.1f})")
cover = sum(any(g[k] == h['res'] for k in keys) for g, h in zip(G, H))
print(f"some recipe makes the result in {cover} of {n} rounds (recipes make {sum(len({g[k] for k in keys}) for g in G)/n:.0f} numbers a round)")
def greedy(idx, m):
    ch, cov = [], set()
    for _ in range(m):
        k = max(keys, key=lambda k: sum(1 for i in idx if i not in cov and hit[k][i])); ch.append(k)
        cov |= {i for i in idx if hit[k][i]}
    return ch
print("A) held-out (recipes picked on the other series):")
for m in (1, 4):
    th = sz = 0
    for s in ser:
        tr = [i for i, h in enumerate(H) if h['series'] != s]; te = [i for i, h in enumerate(H) if h['series'] == s]
        if not te: continue
        ch = greedy(tr, m)
        for i in te:
            nums = {G[i][k] for k in ch}; sz += len(nums); th += H[i]['res'] in nums
    print(f"   {m} recipe(s): {th} of {n}  (chance {sz/100:.1f})")
# B) op transition: result side-op on base given LAST row side-op
print("B) op-transition table, held-out, top 2 x-ops x top 2 y-ops = 4 numbers:")
def last(h): return roles(h['rows'])['LAST']
for bn in ('ROOT', 'EP'):
    for src in ('new same side', 'old same side', 'new crossed'):
        th = 0
        for s in ser:
            tr = [h for h in H if h['series'] != s]; te = [h for h in H if h['series'] == s]
            T = [collections.defaultdict(collections.Counter) for _ in (0, 1)]
            def feat(h, j):
                r = last(h)
                if src == 'new same side': return r[5 + j]
                if src == 'old same side': return r[3 + j]
                return r[6 - j]
            def base(h): return h['ep'] if bn == 'ROOT' else h['EP']
            for h in tr:
                b = base(h)
                for j in (0, 1):
                    d_b, d_r = (b // 10, h['res'] // 10) if j == 0 else (b % 10, h['res'] % 10)
                    T[j][feat(h, j)][D.find_op(d_b, d_r)] += 1
            for h in te:
                b = base(h); tops = []
                for j in (0, 1):
                    c = T[j][feat(h, j)]; tops.append([o for o, _ in c.most_common(2)])
                nums = {D.apply_op(b // 10, x) * 10 + D.apply_op(b % 10, y) for x in tops[0] for y in tops[1]}
                th += h['res'] in nums
        print(f"   base {bn:4s} from LAST {src:14s}: {th} of {n}  (chance {n*0.04:.0f})")
print(f"FINAL 4 now: {sum(h['res'] in h['src'].get('rk', [])[:4] for h in H)} of {n}")
