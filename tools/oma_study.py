"""ONE-MEN-ARMY study (user 2026-11-06: 'pick very strong and fired results from
all tables ... only 20').  Each history list gets a weight = log((held+1)/(chance+1))
learnt on the OTHER series (leave one series out); a number's score = sum of the
weights of the lists holding it; ONE-MEN-ARMY = top 20 by score (ties: ranking).
Compared on the held-out series with top 20 of the ranking and STRONG 20."""
import json, math, collections
H = [h for h in json.load(open('/home/khazakhan/DataScinceAnal/rrr_records/history_all.json')) if len(h['src'].get('rk', [])) >= 20]
L = sorted({k for h in H for k in h['src'] if k not in ('rk', 'top4', 'top10', 'top20', 'top40')})
ser = sorted({h['series'] for h in H})
def weights(tr, only_pos):
    w = {}
    for k in L:
        held = sum(h['res'] in h['src'].get(k, []) for h in tr); ch = sum(len(set(h['src'].get(k, []))) for h in tr) / 100
        w[k] = math.log((held + 1) / (ch + 1)) if ch else 0
        if only_pos: w[k] = max(w[k], 0)
    return w
def oma(h, w, n=20):
    pos = {v: i for i, v in enumerate(h['src']['rk'])}
    sc = collections.Counter()
    for k in L:
        for v in set(h['src'].get(k, [])): sc[v] += w[k]
    return sorted(range(100), key=lambda v: (-sc[v], pos.get(v, 999), v))[:n]
R = collections.Counter(); per = collections.defaultdict(collections.Counter)
for s in ser:
    tr = [h for h in H if h['series'] != s]; te = [h for h in H if h['series'] == s]
    for nm, op in (('ONE-MEN-ARMY (all lists weighted)', False), ('ONE-MEN-ARMY (only lists above chance)', True)):
        w = weights(tr, op)
        for h in te:
            x = h['res'] in oma(h, w); R[nm] += x; per[s][nm] += x
    for h in te:
        R['top 20 of ranking'] += h['res'] in h['src']['rk'][:20]; per[s]['top 20 of ranking'] += h['res'] in h['src']['rk'][:20]
        st = h['src'].get('strong', [])
        if len(st) >= 20:
            R['STRONG 20'] += h['res'] in st[:20]; R['strong rounds'] += 1
n = len(H)
print(f"rounds {n}, series {len(ser)}, chance for 20 numbers {n*0.2:.0f}")
for k, v in R.items(): print(f"   {k:42s} {v}")
print("newest 6 series (OMA all / OMA pos / top 20):")
for s in ser[-6:]: print('  ', s, per[s]['ONE-MEN-ARMY (all lists weighted)'], per[s]['ONE-MEN-ARMY (only lists above chance)'], per[s]['top 20 of ranking'], 'of', sum(h['series'] == s for h in H))
print("variants (held-out):")
V = collections.Counter()
for s in ser:
    tr = [h for h in H if h['series'] != s]; te = [h for h in H if h['series'] == s]
    w = weights(tr, True)
    for thr in (0.1, 0.2, 0.3):
        w2 = {k: (x if x >= thr else 0) for k, x in w.items()}
        for h in te: V[f'only lists with log-lift >= {thr}'] += h['res'] in oma(h, w2)
    for h in te:
        st = h['src'].get('strong', [])[:20]
        # STRONG 20 re-ordered: keep STRONG numbers, fill/replace by OMA score
        o = oma(h, w, 40); keep = [v for v in o if v in st]
        V['STRONG 20 ∩ OMA first, then OMA'] += h['res'] in (keep + [v for v in o if v not in keep])[:20]
for k, v in V.items(): print(f"   {k:42s} {v}")
print("weights learnt on all series (log lift, >0 only):")
w = weights(H, True)
for k, x in sorted(w.items(), key=lambda t: -t[1]): print(f"   {k:10s} {x:.2f}")
