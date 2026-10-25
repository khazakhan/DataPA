# shipped FINAL 4 order since 2026-10-26: votes from rec, table, again, found; tie strong+ncspec+fam_seats, then lower number
import json
def side(s):
    c = s.startswith('c'); t = s[3:] if s.startswith('cut') else s[1:] if c else s
    return c, (0 if t in ('', 'nc') else int(t))
def rank(d):
    L = {'rec': d['rec'], 'table': [a for a, _ in d['table']], 'again': [a for a in d['again'] if a is not None], 'found': d['found']}
    st = {x[0] if isinstance(x, list) else x for x in d['strong']}; nc = set(d['ncspec']); fs = set(d['fam_seats'])
    v = lambda m: sum(m in set(L[u]) for u in L); t = lambda m: (m in st) + (m in nc) + (m in fs)
    rk = sorted(set(d['ocjp']), key=lambda m: (-v(m), -t(m), m))
    op = {}
    for n, o, p, k in d['ocjp_full']: op.setdefault(n, o)
    return rk, op, v
def ap(dg, c, k): return (((dg + 5) % 10 if c else dg) + k) % 10
def rules(d, last):
    rk, op, v = rank(d); dg = [d['ep'] // 10, d['ep'] % 10]
    LL = [side(s) for s in last.split('/')]; r1 = []
    for m in rk[:4]:
        o = [side(s) for s in op[m].split('/')]; out = []
        for i in range(2):
            c, k = o[i]; tt = LL[i][1]; k = k + (tt > k) - (tt < k); out.append(ap(dg[i], c, k))
        r1.append(out[0] * 10 + out[1])
    fam = set(); r2 = []
    for m in rk:
        f = tuple(side(s)[1] for s in op[m].split('/'))
        if f in fam: continue
        fam.add(f); r2.append(m)
        if len(r2) == 4: break
    r3 = []
    for m in rk[:4]:
        x, y = map(side, op[m].split('/')); nx, ny = y, (x[0], -x[1])
        r3.append(ap(dg[0], *nx) * 10 + ap(dg[1], *ny))
    return rk[:4], r1, r2, r3, int(f'{rk[0] % 10}{rk[0] // 10}')
