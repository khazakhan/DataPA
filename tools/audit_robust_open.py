import sys, re, itertools, math
sys.path.insert(0, 'tools'); import open_robust_study as O
from slot4_study import load
from openclose_study import rank_all_of, seq_of
# 1) take the LIVE code block out of DataProcessing.py and run it exactly as written
src = open('DataProcessing.py').read()
a = src.index("            _fl2 = [v for v in (_RRR3_PREV.get('flat') or []) if v is not None]")
b = src.index("            _RRR3_PREV['oc_final2'] = _oc2")
block = '\n'.join(l[12:] for l in src[a:b].splitlines())
def live_open(h, ra):
    g = {'_RRR3_PREV': {'flat': h}, '_vote_all': ra}
    exec(block, g); return g['_oc2']['open'][:2]
mism = n = 0; new = old = ls = 0; disc = [0, 0]; per = {}
for k in range(1, 25):
    R = load(f'set{k:02d}'); rank_all_of(k, R); S = seq_of(k)
    for r in R:
        h = [v for v in S[:r['pos']] if v is not None]
        if len(h) < 50 or not r.get('rank_all'): continue
        sc = O.scores(S, r['pos'], r); B = {x: O.borda(s) for x, s in sc.items()}
        st = O.top2([B['step after step'][d] + B['step all (now)'][d] + B['vote bottom 30 avoided'][d] + 0.01 * B['step all (now)'][d] for d in range(10)])
        lv = live_open(h, r['rank_all'])
        n += 1; mism += st != lv
        if k >= 13:
            t = r['result'] // 10; hn = t in lv; ho = t in O.top2(sc['step all (now)'])
            hs = t in O.top2([B['step after step'][d] + B['step all (now)'][d] + 0.01 * B['step all (now)'][d] for d in range(10)])
            new += hn; old += ho; ls += hs
            if hn != ho: disc[hn] += 1
            p = per.setdefault(k, [0, 0, 0]); p[0] += hn; p[1] += ho; p[2] += 1
print(f'code check: live code vs tested rule differ on {mism} of {n} rounds (with vote list)')
m = sum(p[2] for p in per.values())
print(f'proof sets 13-24, rounds with vote list: {m}: NEW {new} ({100*new/m:.2f}%), OLD {old} ({100*old/m:.2f}%), learn-top-only rule {ls} ({100*ls/m:.2f}%), chance {m/5:.0f}')
w, l = disc[1], disc[0]; z = (w - l) / math.sqrt(w + l)
print(f'paired: NEW hit & OLD missed {w}, OLD hit & NEW missed {l}, z = {z:.2f}')
zc = (new - m * 0.2) / math.sqrt(m * 0.2 * 0.8); print(f'NEW vs chance z = {zc:.2f}')
print('per proof set NEW vs OLD:', ' '.join(f'S{k}:{p[0]}/{p[1]}' for k, p in sorted(per.items())), ' new>=old in', sum(p[0] >= p[1] for p in per.values()), 'of 12')
