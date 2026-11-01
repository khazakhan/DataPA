"""Series R review (2026-11-02): test the ideas series R suggested on all
412 replay/live rounds, per series."""
import json, collections, sys
sys.argv = ['x']
exec(open('/home/khazakhan/DataScinceAnal/tools/booster_study.py').read().split("R = [o for o")[0])
R = [o for o in D if o['rows'] and len(o['rk']) >= 4]
ser = sorted({o['series'] for o in R}); N = len(R)
def show(name, fn):
    h = collections.Counter(); s = 0.0
    for o in R:
        nums = fn(o)
        s += len(nums); h[o['series']] += o['res'] in nums
    t = sum(h.values())
    print(f"{name:58s} {t:4d} of {N}  chance {s/100:5.1f}   " + ' '.join(f"{k}:{h[k]}" for k in ser))
def last(o):
    li = [i for i, r in enumerate(o['rows']) if r[7] == 'LAST']
    return o['rows'][li[-1]] if li else None
def mk(ep, a, b): ca, cb = side(a), side(b); return app(ep // 10, *ca) * 10 + app(ep % 10, *cb)
def flip(l):
    c, k = side(l); return ('c' if c and k else '') + (('+' if -k > 0 else '') + str(-k) if k else ('cut' if c else 'nc')) if k else l
def cutsw(l):
    c, k = side(l)
    if k == 0: return 'nc' if c else 'cut'
    return (f"{k:+d}" if c else f"c{k:+d}")
SW = {1: 2, 2: 1, -1: -2, -2: -1, 0: 0}
def stepsw(l):
    c, k = side(l); k = SW[k]
    if k == 0: return l
    return (f"c{k:+d}" if c else f"{k:+d}")
# 1 LAST-OP ★1 cell: new xy, x cut switched, y sign flipped
def star1(o):
    L = last(o); return {mk(o['ep'], cutsw(L[5]), flip(L[6]))} if L else set()
show("1. LAST-OP ★1 cell (new xy, x cut sw, y flip)", star1)
# 2 rule 28 first pick: x = new y cut sw, y = new x step sw
def r28(o):
    L = last(o); return {mk(o['ep'], cutsw(L[6]), stepsw(L[5]))} if L else set()
show("2. rule 28 first pick (x new y cut sw, y new x step sw)", r28)
# 3 crossed grid (16)
def grid(o):
    L = last(o)
    if not L: return set()
    xs = {L[6], flip(L[6]), cutsw(L[6]), stepsw(L[6])}; ys = {L[5], flip(L[5]), cutsw(L[5]), stepsw(L[5])}
    return {mk(o['ep'], a, b) for a in xs for b in ys}
show("3. crossed grid (4 x 4)", grid)
# 4 EP-row follower
show("4. row starting at EP -> its 2nd number", lambda o: {r[2] for r in o['rows'] if r[1] == o['ep']})
# 5 script FINAL 4 / top 8
show("5. script FINAL 4", lambda o: set(o['rk'][:4]))
show("6. script top 8", lambda o: set(o['rk'][:8]))
show("7. FINAL 4 + LAST-OP ★1 (5 numbers)", lambda o: set(o['rk'][:4]) | star1(o))
show("8. top 4 + rule 28 first pick (5 numbers)", lambda o: set(o['rk'][:4]) | r28(o))
