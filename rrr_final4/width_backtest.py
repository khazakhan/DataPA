"""How wide must a list be to never miss? (2026-10-17)

Every number 00-99 gets one vote per list that holds it (cell, OCJP,
RECOMMENDED, RRR table, yx, WIDE, 3RRR, same op again, STRONG 20; STRONG
seat as tie-break).  The rank of the real result is recorded each round; the
worst rank is the list size needed for zero misses.

  python3 rrr_final4/width_backtest.py DIR   (DIR from l_backtest.py: r*.json + r*.ans)
"""
import glob, json, sys


def order(d):
    cell = {x[0] if isinstance(x, list) else x for x in d['fam_seats']} | set(d['strong'])
    oc = {x[0] for x in d['ocjp_full']}
    tab = {x[0] for x in d['table']}
    sc = {}
    for n in range(100):
        sc[n] = ((n in cell) + (n in oc) + (n in d['rec']) + (n in tab) + (n in d['yx'])
                 + (n in d['wide']) + (n in d['found']) + (n in d['again']) + (n in d['strong']))
        if n in d['strong']:
            sc[n] += (20 - d['strong'].index(n)) / 1000
    return sorted(range(100), key=lambda n: -sc[n])


rk = []
for a in sorted(glob.glob(sys.argv[1] + '/r*.ans')):
    s = open(a).read().strip()
    if s.isdigit():
        rk.append(order(json.load(open(a[:-4] + '.json'))).index(int(s)) + 1)
n = len(rk)
print(n, 'rounds; list size needed for zero misses:', max(rk))
for k in (4, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100):
    print('  top %3d: %5.1f%%  (random %d%%)' % (k, 100 * sum(x <= k for x in rk) / n, k))
