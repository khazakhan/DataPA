"""Back-test of FINAL 4 and every list on series L data (2026-10-16).

Builds rounds from l0.txt: the last 20 grid rows (120 numbers) plus the real
L results are replayed one at a time (base grid + earlier numbers as result
lines).  Each round is run with RRR3_DUMP2 and its FINAL 4 box is saved:

  for f in DIR/r*.txt; do RRR3_DUMP2=${f%.txt}.json python3 DataProcessing.py $f \
    | sed 's/\x1b\[[0-9;]*m//g' | grep -A6 "OCJP FINAL 4  —" | tail -6 > ${f%.txt}.f4; done

Then: python3 rrr_final4/l_backtest.py DIR
"""
import glob, json, re, sys
S = sys.argv[1]
rows = []
for a in sorted(glob.glob(S + '/r*.ans')):
    ans = open(a).read().strip()
    if not ans.isdigit():
        continue
    b = a[:-4]
    d = json.load(open(b + '.json'))
    f4 = [int(m) for m in re.findall(r'^\D*\d\. (\d\d) ', open(b + '.f4').read(), re.M)]
    rows.append((int(ans), d, f4))
n = len(rows)


def stat(name, get):
    hit = sum(r in get(d, f) for r, d, f in rows)
    sz = sum(len(set(get(d, f))) for r, d, f in rows) / n
    print('%-12s size %5.1f  hit %3d/%d = %5.1f%%  chance %5.1f%%  x%.2f'
          % (name, sz, hit, n, 100 * hit / n, sz, (hit / n) / (sz / 100)))


stat('FINAL 4', lambda d, f: f)
stat('STRONG 20', lambda d, f: d['strong'])
stat('cell', lambda d, f: {x[0] if isinstance(x, list) else x for x in d['fam_seats']} | set(d['strong']))
stat('OCJP', lambda d, f: {x[0] for x in d['ocjp_full']})
stat('RECOMMENDED', lambda d, f: d['rec'])
stat('RRR table', lambda d, f: {x[0] for x in d['table']})
stat('yx', lambda d, f: d['yx'])
stat('WIDE', lambda d, f: d['wide'])
stat('3RRR', lambda d, f: d['found'])
stat('same op', lambda d, f: d['again'])
