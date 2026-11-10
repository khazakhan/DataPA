"""EP / ROOT direct-op rules (user 2026-11-11: 'sometimes direct EP operations give the result, sometimes ROOT
operations, and their transformations - cut, no change, inc, dec, flip xy/yx').  Every rule makes ONE number:
  base   = EP or ROOT                       (the number the op is put on)
  source = EP op (prev->EP) or ROOT op (EP->ROOT, the same step as earlier-EP -> ROOT)
  cross  = no / yes (x op on y and y op on x: xy <-> yx)
  change per side = same, cut switched (+5), sign flipped (-s), +1, -1   -> 5 x 5
200 rules, counted on every chart's full history from number 300 (each rule is fixed, nothing learned), with
both halves, so a lucky rule shows up as unstable.  Chance per rule 1% (1.1% with the EP tens left out)."""
import os, sys, collections
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, 'tools')
from oc_deep_study import charts
NAME = {0: 'nc', 1: '+1', 2: '+2', 3: 'c-2', 4: 'c-1', 5: 'cut', 6: 'c+1', 7: 'c+2', 8: '-2', 9: '-1'}
CH = {'same': lambda s: s, 'cut sw': lambda s: (s + 5) % 10, 'sign': lambda s: (-s) % 10,
      '+1': lambda s: (s + 1) % 10, '-1': lambda s: (s - 1) % 10}
T, U = (lambda v: v // 10), (lambda v: v % 10)
step = lambda a, b: ((T(b) - T(a)) % 10, (U(b) - U(a)) % 10)
rules = [(b, src, cr, cx, cy) for b in ('EP', 'ROOT') for src in ('EP op', 'ROOT op') for cr in (0, 1) for cx in CH for cy in CH]
cnt = collections.defaultdict(lambda: [0, 0, 0, 0])   # n, hits, hits half1, n half1
for grp_want in ('low', 'normal'):
    pass
for name, fl in charts():
    low = sum(a // 10 == b // 10 for a, b in zip(fl, fl[1:])) / (len(fl) - 1) < 0.06
    last = {}; mid = (300 + len(fl)) // 2
    for i in range(1, len(fl) - 1):
        ep, nx = fl[i], fl[i + 1]
        j = last.get(ep); last[ep] = i
        if i < 300 or j is None or j + 1 >= i:
            continue
        root = fl[j + 1]
        so = {'EP op': step(fl[i - 1], ep), 'ROOT op': step(ep, root)}
        for r in rules:
            b, src, cr, cx, cy = r
            s = so[src]; s = (s[1], s[0]) if cr else s
            base = ep if b == 'EP' else root
            n = ((T(base) + CH[cx](s[0])) % 10) * 10 + (U(base) + CH[cy](s[1])) % 10
            if low and T(n) == T(ep):
                continue_hit = False
            for g in (('low' if low else 'normal'), 'all'):
                c = cnt[(g, r)]; c[0] += 1; c[1] += n == nx
                if i < mid:
                    c[3] += 1; c[2] += n == nx
for g in ('low', 'normal'):
    rows = sorted(((r, c) for (gg, r), c in cnt.items() if gg == g), key=lambda t: -t[1][1] / t[1][0])
    n = rows[0][1][0]
    print(f"\n{g} tens-repeat charts: {n} rounds per rule, chance 1.0% = {n/100:.0f} hits; best of 200 rules by luck alone is about {n/100 + 2.6*(n/100)**.5:.0f}")
    print("   rule                                              hits    %     half1   half2")
    for r, c in rows[:12]:
        b, src, cr, cx, cy = r
        print(f"   {b:4s} + {src:7s} {'crossed' if cr else 'as is  '} x {cx:6s} y {cy:6s}   {c[1]:5d} {100*c[1]/c[0]:5.2f}%  {100*c[2]/max(1,c[3]):5.2f}%  {100*(c[1]-c[2])/max(1,c[0]-c[3]):5.2f}%")
    print("   ... worst:", ', '.join(f"{100*c[1]/c[0]:.2f}%" for r, c in rows[-3:]))
