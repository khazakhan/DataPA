import sys, os, collections
sys.path.insert(0, 'tools'); os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import builder60 as B
P = B.pages(); ST = {}; recs = []
for p, L, r in P:
    if len(ST) >= 5:
        rk = B.rank(L, ST)[0]
        bands = [rk[:20], rk[20:40], rk[40:B.K]]; stars = [b[:5] for b in bands]
        allstar = {x for s in stars for x in s}; sup = B.supports(L)
        fams = [B.FAMILY[x] for s in stars for x in s]
        rows = collections.Counter(); inb = collections.Counter(); inp = collections.Counter()
        for s, bd in zip(stars, bands):
            for x in s:
                for v in range(100):
                    if v == x or B.FAMILY[v] != B.FAMILY[x]: continue
                    a, b = v in bd, v in sup
                    if a or b: rows[v] += 1
                    if a: inb[v] += 1
                    if b: inp[v] += 1
        nl = {v: sum(v in ns for k, ns in L.items() if k not in B.BIG) for v in range(100)}
        feats = {v: dict(rows=rows[v], inb=inb[v], inp=inp[v], fam=fams.count(B.FAMILY[v]), rk=rk.index(v), nl=nl[v], star=v in allstar) for v in range(100)}
        recs.append((p, r, feats))
    B.learn(ST, L, r)
import pickle; pickle.dump(recs, open(sys.argv[1], 'wb')); print(len(recs))
