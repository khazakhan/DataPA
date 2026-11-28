"""CLOSE 2 / CLOSE 4 of the LIVE code (DataProcessing.py FINAL 2 block run as written) on every round of the 24 sets:
proof sets 13-24 per half, sets above chance, and the last 10 rounds of each set.  Usage: python3 tools/audit_close4.py"""
import sys, os, math
sys.path.insert(0, 'tools')
from slot4_study import load
from openclose_study import rank_all_of, seq_of
src = open('DataProcessing.py').read()
a = src.index("            _fl2 = [v for v in (_RRR3_PREV.get('flat') or []) if v is not None]")
b = src.index("            _RRR3_PREV['oc_final2'] = _oc2")
block = '\n'.join(l[12:] for l in src[a:b].splitlines())
res = {2: {}, 4: {}}; last = {2: [0, 0], 4: [0, 0]}
for k in range(1, 25):
    R = [r for r in load(f'set{k:02d}') if True]; rank_all_of(k, R); S = seq_of(k)
    R = [r for r in R if r.get('rank_all')]; h_ = len(R) // 2
    for i, r in enumerate(R):
        h = [v for v in S[:r['pos']] if v is not None]
        if len(h) < 50: continue
        g = {'_RRR3_PREV': {'flat': h}, '_vote_all': r['rank_all']}; exec(block, g)
        c = g['_oc2']['close']; t = r['result'] % 10
        for N in (2, 4):
            x = res[N].setdefault(k, [0, 0, 0, 0]); j = 0 if i < h_ else 2
            x[j] += t in c[:N]; x[j + 1] += 1
            if i >= len(R) - 10: last[N][0] += t in c[:N]; last[N][1] += 1
for N in (2, 4):
    ag = lambda ks: [sum(res[N][k][j] for k in ks if k in res[N]) for j in range(4)]
    L, P = ag(range(1, 13)), ag(range(13, 25))
    above = sum(1 for k in range(13, 25) if (res[N][k][0] + res[N][k][2]) / (res[N][k][1] + res[N][k][3]) > N / 10)
    n = P[1] + P[3]; hit = P[0] + P[2]; z = (hit - n * N / 10) / math.sqrt(n * N / 10 * (1 - N / 10))
    print(f'CLOSE {N}: learn {100*(L[0]+L[2])/(L[1]+L[3]):.2f}%  prove {100*hit/n:.2f}% ({100*P[0]/P[1]:.2f} / {100*P[2]/P[3]:.2f})  '
          f'{above} of 12 proof sets above {N*10}%  z vs chance {z:.2f}  last 10 rounds x 24 sets: {last[N][0]} of {last[N][1]} (chance {last[N][1]*N/10:.0f})')
