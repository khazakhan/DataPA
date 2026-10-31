"""Research pass 2 (user, 2026-11-01: 'research on missed results').
Every idea is scored on all rounds and, where it is picked from data, on a
held-out series (leave one series out)."""
import json, sys, itertools, collections, re
sys.argv = ['x']
src = open('/home/khazakhan/DataScinceAnal/tools/booster_study.py').read().split("R = [o for o")[0]
exec(src)
R = [o for o in D if o['rows'] and len(o['rk']) >= 4]
G = [gens(o) for o in R]; ser = sorted({o['series'] for o in R}); N = len(R)
def rep(name, hits, size):
    print(f"{name:62s} {hits:4d} of {N}   chance {size:6.1f}   {'ABOVE' if hits > size * 1.25 else 'at/below'}")
# 1. previous row (the row before LAST): old / new ops, xy / yx, 0 or 1 change
for on in ('old', 'new', 'both'):
    for lim in (0, 1):
        mods = ['as'] if lim == 0 else ['as', 'F', 'C', 'S']
        h = s = 0
        for g, o in zip(G, R):
            nums = {g[k] for k in g if k[0] == 'prev' and (on == 'both' or k[1] == on)
                    and k[3] in mods and k[4] in mods and (k[3] != 'as') + (k[4] != 'as') <= lim}
            s += len(nums); h += o['res'] in nums
        rep(f"1. prev row {on} ops xy/yx, changes<={lim}", h, s / 100)
# 2. result = an earlier number in the data (repeat of the last 1..20 results)
def hist(o):
    t = open('/home/khazakhan/DataScinceAnal/' + o['ds']).read().split()
    return [int(x) for x in t if x.isdigit() and len(x) == 2]
for n in (1, 5, 10, 20):
    h = s = 0
    for o in R:
        hs = set(hist(o)[-n:]); s += len(hs); h += o['res'] in hs
    rep(f"2. repeat of one of the last {n} numbers", h, s / 100)
# 3. digit-level: most common x op / y op (picked on other series), the one number it gives
OPS = {}
def opof(d, t):
    out = []
    for c in (False, True):
        for k in (-2, -1, 0, 1, 2):
            if app(d, c, k) == t: out.append((c, k))
    return out
for o in R: o['xo'] = opof(o['ep'] // 10, o['res'] // 10); o['yo'] = opof(o['ep'] % 10, o['res'] % 10)
for top in (1, 2, 4):
    h = s = 0
    for sv in ser:
        tr = [o for o in R if o['series'] != sv]
        cx = collections.Counter(op for o in tr for op in o['xo']); cy = collections.Counter(op for o in tr for op in o['yo'])
        bx = [k for k, _ in cx.most_common(top)]; by = [k for k, _ in cy.most_common(top)]
        for o in R:
            if o['series'] != sv: continue
            nums = {app(o['ep'] // 10, *a) * 10 + app(o['ep'] % 10, *b) for a in bx for b in by}
            s += len(nums); h += o['res'] in nums
    rep(f"3. top {top} x op x top {top} y op (held-out)", h, s / 100)
# 4. op pair repeat: last round's actual op used again (same op again)
h = s = 0
prev = {}
for o in R:
    key = o['ds'].rsplit('/', 1)[1].rstrip('0123456789.txt') if False else o['series']
    p = prev.get(key)
    if p:
        nums = {app(o['ep'] // 10, *a) * 10 + app(o['ep'] % 10, *b) for a in p['xo'] for b in p['yo']}
        s += len(nums); h += o['res'] in nums
    prev[key] = o
rep("4. previous round's op pair used again", h, s / 100)
# 5. digit distribution: hottest result digits (tens, units) in the last 30 numbers of the grid
for k in (3, 5):
    h = s = 0
    for o in R:
        hs = hist(o)[-30:]
        tx = [d for d, _ in collections.Counter(v // 10 for v in hs).most_common(k)]
        ty = [d for d, _ in collections.Counter(v % 10 for v in hs).most_common(k)]
        s += k * k; h += (o['res'] // 10 in tx and o['res'] % 10 in ty)
    rep(f"5. hot {k} tens x hot {k} units digits (last 30 numbers)", h, s / 100)
# 6. where the script's current ranking holds it
for n in (4, 8, 10, 20, 40):
    rep(f"6. script top {n}", sum(o['res'] in o['rk'][:n] for o in R), N * n / 100)
