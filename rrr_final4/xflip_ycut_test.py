"""User idea after N298 = 17 (2026-10-26): FINAL 4 #2 52 (c+2/nc) with x sign flipped and y cut
switched gives c-2/cut = 17. Test: that turn applied to every FINAL 4 op (shipped 4-list ranking).
usage: python3 xflip_ycut_test.py all4.json DUMP_DIR"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_now import rank, side, ap
R = json.load(open(sys.argv[1])); D = sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
live = []
for k in range(235, 1000):
    f, nx = f'{D}/d2_{k}.json', f'{here}/../rrr_datasets/n{k + 1}.txt'
    if os.path.exists(f) and os.path.exists(nx):
        r = json.load(open(f)); r['res'] = int(open(nx).read().split()[-1]); live.append(r)
def turn(r):
    rk, op, _ = rank(r); out = []
    for m in rk[:4]:
        (cx, kx), (cy, ky) = [side(s) for s in op[m].split('/')]
        out.append(ap(r['ep'] // 10, cx, -kx) * 10 + ap(r['ep'] % 10, not cy, ky))
    return set(out) - set(rk[:4])
for name, rows in (('old replay', R), ('old series N', [r for r in R if r['series'] == 'n']), ('live N235+', live)):
    sz = sum(len(turn(r)) for r in rows) / len(rows); h = sum(r['res'] in turn(r) for r in rows)
    print(f'{name}: {len(rows)} rounds, {sz:.1f} new numbers a round, hits {h} = {100 * h / len(rows):.1f}% (chance {sz:.1f}%)')
