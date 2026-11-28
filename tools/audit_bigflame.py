import sys, re, pickle, math, os
sys.path.insert(0, 'tools'); import builder60 as B
recs = pickle.load(open(sys.argv[1], 'rb')); n = len(recs); h = n // 2
rule = lambda f: not f['star'] and f['rows'] >= 2 and f['rk'] < 20
# 1) code check: table code (count_table) vs tested rule, on every page
P = B.pages(); ST = {}; mism = cnt = 0; i = 0
for p, L, r in P:
    if len(ST) >= 5:
        rk = B.rank(L, ST)[0]; bands = [rk[:20], rk[20:40], rk[40:B.K]]; stars = [b[:5] for b in bands]
        t = B.count_table(stars, bands, B.supports(L), '', None, f4=[], test=[], cnt={})
        shown = set(int(x) for x in re.findall(r'🔥🔥\*\*(\d\d)', t))
        tested = {v for v, f in recs[i][2].items() if rule(f)}
        mism += shown != tested; cnt += 1; i += 1
    B.learn(ST, L, r)
print(f'code check: table marks vs tested rule differ on {mism} of {cnt} pages')
# 2) per half / per series / significance
def ev(part):
    hit = size = 0
    for p, r, F in part:
        s = [v for v, f in F.items() if rule(f)]; size += len(s); hit += r in s
    return hit, size / 100
for nm, part in (('half A', recs[:h]), ('half B', recs[h:]), ('all', recs)):
    a, e = ev(part); print(f'{nm}: {a} held vs {e:.1f} by chance, z = {(a - e) / math.sqrt(e):.2f}')
ser = {}
for p, r, F in recs:
    ser.setdefault(re.match(r'rrr_outputs/([a-z]+)', p).group(1), []).append((p, r, F))
print('per series (held / chance):', ' '.join(f'{s.upper()} {ev(v)[0]}/{ev(v)[1]:.1f}' for s, v in sorted(ser.items()) if len(v) >= 30))
# 3) honest selection: choose the best of the same ~40 rules on half A only, then look at half B
import itertools
rules = {}
for R in (1, 2, 3):
    rules[f'rows>={R}'] = (lambda R: lambda f: f['rows'] >= R)(R)
    for K in (20, 40, 60):
        rules[f'rows>={R}&rank<{K}'] = (lambda R, K: lambda f: f['rows'] >= R and f['rk'] < K)(R, K)
        rules[f'rows>={R}&rank>={K}'] = (lambda R, K: lambda f: f['rows'] >= R and f['rk'] >= K)(R, K)
    for N in (2, 3, 4, 5):
        rules[f'rows>={R}&lists>={N}'] = (lambda R, N: lambda f: f['rows'] >= R and f['nl'] >= N)(R, N)
def ev2(rl, part):
    hit = size = 0
    for p, r, F in part:
        s = [v for v, f in F.items() if not f['star'] and f['rows'] > 0 and rl(f)]; size += len(s); hit += r in s
    return hit, size / 100
best = max(rules, key=lambda k: (lambda a, e: (a - e) / math.sqrt(max(e, 1)))(*ev2(rules[k], recs[:h])))
a, e = ev2(rules[best], recs[:h]); b, eb = ev2(rules[best], recs[h:])
print(f'honest pick on half A only: {best} -> half A {a}/{e:.1f}, half B {b}/{eb:.1f}')
