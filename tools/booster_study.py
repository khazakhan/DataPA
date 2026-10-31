"""SCRIPT BOOSTER study (user, 2026-11-01): for every one of the 374 rounds,
which simple general move would have made the result?  Each "generator" is
one fixed recipe that gives one number per round (row role x old/new ops x
xy/yx x change on each side).  Generators are chosen on some series and
tested on the held-out series (leave one series out), against FINAL 4."""
import json, sys, itertools, collections
D = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/replay/lastprev.json'))
def side(lab):
    if lab == 'cut': return True, 0
    if lab == 'nc': return False, 0
    if lab.startswith('c'): return True, int(lab[1:])
    return False, int(lab)
def app(d, c, k): return ((d + 5) % 10 + k) % 10 if c else (d + k) % 10
SW = {1: 2, 2: 1, -1: -2, -2: -1, 0: 0}
MODS = {'as': lambda c, k: (c, k), 'F': lambda c, k: (c, -k), 'C': lambda c, k: (not c, k),
        'S': lambda c, k: (c, SW[k]), 'FC': lambda c, k: (not c, -k), 'SC': lambda c, k: (not c, SW[k]),
        'FS': lambda c, k: (c, -SW[k]), 'nc': lambda c, k: (False, 0), 'cut': lambda c, k: (True, 0)}
def roles(rows):
    li = [i for i, r in enumerate(rows) if r[7] == 'LAST']
    i = li[-1] if li else len(rows) - 1
    out = {'LAST': rows[i]}
    if i > 0: out['prev'] = rows[i - 1]
    if i > 1: out['prev2'] = rows[i - 2]
    if rows: out['first'] = rows[0]
    if len(rows) > 1: out['second'] = rows[1]
    return out
def gens(o):
    ep = o['ep']; ex, ey = ep // 10, ep % 10; g = {}
    for rn, r in roles(o['rows']).items():
        for on, (a, b) in (('new', (r[5], r[6])), ('old', (r[3], r[4]))):
            for rd, (p, q) in (('xy', (a, b)), ('yx', (b, a)), ('crossed', (b, a))):
                if rd == 'crossed': continue
                cp, cq = side(p), side(q)
                for mx, my in itertools.product(MODS, MODS):
                    g[(rn, on, rd, mx, my)] = app(ex, *MODS[mx](*cp)) * 10 + app(ey, *MODS[my](*cq))
    g[('EP',)] = ep; g[('EP rev',)] = ey * 10 + ex
    return g
R = [o for o in D if o['rows'] and len(o['rk']) >= 4]
G = [gens(o) for o in R]
keys = set.intersection(*(set(g) for g in G))
ser = sorted({o['series'] for o in R})
print('rounds', len(R), 'generators', len(keys))
hit = {k: [g[k] == o['res'] for g, o in zip(G, R)] for k in keys}
tot = {k: sum(v) for k, v in hit.items()}
best = sorted(keys, key=lambda k: -tot[k])[:15]
print('best single generators over all rounds (chance ~3.7 of 374 each):')
for k in best: print('  ', tot[k], k)
# how many rounds can ANY generator explain, and how many distinct numbers they give
cover = sum(any(g[k] == o['res'] for k in keys) for g, o in zip(G, R))
dist = sum(len({g[k] for k in keys}) for g in G) / len(G)
print(f'any generator makes the result: {cover} of {len(R)}; distinct numbers per round {dist:.1f} (chance {dist:.1f}%)')
# leave-one-series-out: greedy pick 4 generators on train, test on held-out
def greedy(idx, n):
    chosen, covered = [], set()
    for _ in range(n):
        k = max(keys, key=lambda k: sum(1 for i in idx if i not in covered and hit[k][i]))
        chosen.append(k); covered |= {i for i in idx if hit[k][i]}
    return chosen
for n in (4, 8, 10):
    test_hits = f4 = tested = 0; sz = 0
    for s in ser:
        tr = [i for i, o in enumerate(R) if o['series'] != s]; te = [i for i, o in enumerate(R) if o['series'] == s]
        ch = greedy(tr, n)
        for i in te:
            nums = {G[i][k] for k in ch}; sz += len(nums)
            test_hits += R[i]['res'] in nums; tested += 1
    print(f'booster {n} generators, held-out: {test_hits} of {tested} (chance {sz/100:.1f}); in-sample fit would look better')
f4 = sum(o['res'] in o['rk'][:4] for o in R); print('FINAL 4 now:', f4, 'of', len(R), '(chance', len(R)*4/100, ')')
for n in (4, 8, 10, 20, 40):
    print(f'  top {n}: {sum(o["res"] in o["rk"][:n] for o in R)} (chance {len(R)*n/100:.1f})')
miss_out = sum(o['res'] not in o['rk'][:40] for o in R); print('result outside top 40:', miss_out)
