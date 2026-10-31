"""Does the LAST operation (new + old ops) and the row before it help FINAL 4?
cost(v) = fewest changes (sign flip, cut switch, step switch each 1) for a
row's ops, read xy or yx, to turn the EP into v."""
import json, sys
sys.path.insert(0, '/home/khazakhan/DataScinceAnal')
D = json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/replay/lastprev.json'))
def side(lab):
    c = lab.startswith('c') and lab != 'cut' or lab == 'cut'
    t = lab[1:] if lab.startswith('c') and lab != 'cut' else ('0' if lab in ('cut', 'nc') else lab)
    return c, int(t)
def app(d, c, k): return ((d + 5) % 10 + k) % 10 if c else (d + k) % 10
def kcost(k, k2):
    if k == k2: return 0
    if k2 == -k or (k * k2 > 0): return 1
    return 2
def cost_digit(d, t, lab):
    c, k = side(lab); best = 9
    for c2 in (c, not c):
        for k2 in (-2, -1, 0, 1, 2):
            if app(d, c2, k2) == t: best = min(best, (c2 != c) + kcost(k, k2))
    return best
def cost(ep, v, ops):
    x, y = ep // 10, ep % 10; tx, ty = v // 10, v % 10; best = 9
    for a, b in ops:
        best = min(best, cost_digit(x, tx, a) + cost_digit(y, ty, b), cost_digit(x, tx, b) + cost_digit(y, ty, a))
    return best
def opsets(o):
    rows = o['rows']; li = [i for i, r in enumerate(rows) if r[7] == 'LAST']
    if not li: return None
    i = li[-1]; L = rows[i]
    last = [(L[5], L[6]), (L[3], L[4])]          # new ops, old (previous) ops
    prev = [(rows[i-1][5], rows[i-1][6]), (rows[i-1][3], rows[i-1][4])] if i > 0 else []
    return last, prev
res = {}
def tally(name, ok, ser):
    res.setdefault(name, {}).setdefault(ser, 0); res[name][ser] += ok
N = {}
for o in D:
    s = opsets(o)
    if s is None or len(o['rk']) < 20: continue
    last, prev = s; ep, r, rk, ser = o['ep'], o['res'], o['rk'], o['series']
    N[ser] = N.get(ser, 0) + 1
    tally('FINAL 4 now', r in rk[:4], ser)
    for nm, ops in (('LAST', last), ('LAST+prev row', last + prev), ('LAST new only', last[:1])):
        for top in (8, 10, 20, 40):
            rr = sorted(rk[:top], key=lambda v: (cost(ep, v, ops), rk.index(v)))[:4]
            tally(f'{nm}: top{top} re-ranked', r in rr, ser)
        c = cost(ep, r, ops)
        for k in (0, 1, 2): tally(f'{nm}: result cost<={k}', c <= k, ser)
        # size of cost<=k sets (average)
        for k in (0, 1, 2):
            sz = sum(1 for v in range(100) if cost(ep, v, ops) <= k)
            res.setdefault(f'{nm}: size cost<={k}', {}).setdefault(ser, 0); res[f'{nm}: size cost<={k}'][ser] += sz
tot = sum(N.values()); print('rounds', N, tot)
for k, d in res.items():
    t = sum(d.values())
    print(f"{k:38s} {t:6d}  {t/tot*100:5.1f}%   " + ' '.join(f"{s}:{d.get(s,0)}" for s in N))
