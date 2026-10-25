"""User idea after N315/N316 (2026-10-26): the 8-number family of a FINAL 4 number:
both digits as is or cut, and reversed (10 -> 10 15 60 65 01 51 06 56).
Test: family of MASTER, family of all FINAL 4, hit rate against the share of numbers they cover.
usage: python3 family8_test.py all4.json DUMP_DIR"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rank_now import rank
R = json.load(open(sys.argv[1])); D = sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
live = []
for k in range(235, 1000):
    f, nx = f'{D}/d2_{k}.json', f'{here}/../rrr_datasets/n{k + 1}.txt'
    if os.path.exists(f) and os.path.exists(nx):
        r = json.load(open(f)); r['res'] = int(open(nx).read().split()[-1]); live.append(r)
cut = lambda d: (d + 5) % 10
def fam(n):
    a, b = n // 10, n % 10
    return {x * 10 + y for x in (a, cut(a)) for y in (b, cut(b))} | {y * 10 + x for x in (a, cut(a)) for y in (b, cut(b))}
for name, rows in (('old replay', R), ('old series N', [r for r in R if r['series'] == 'n']), ('live N235+', live)):
    out = []
    for lab, pick in (('MASTER family', lambda f4: fam(f4[0])), ('FINAL 4 families', lambda f4: set().union(*map(fam, f4))),
                      ('FINAL 4 families minus FINAL 4', lambda f4: set().union(*map(fam, f4)) - set(f4))):
        h = sz = 0
        for r in rows:
            f4 = rank(r)[0][:4]; s = pick(f4); sz += len(s); h += r['res'] in s
        out.append(f'{lab}: {h}/{len(rows)} = {100 * h / len(rows):.1f}% (chance {sz / len(rows):.1f}%)')
    print(name + '\n  ' + '\n  '.join(out))
