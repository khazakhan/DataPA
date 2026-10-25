"""Does the number of OCJP entries (places and forms) a number gets predict the result?
usage: python3 ocjp_count_test.py all4.json"""
import json, sys
from collections import Counter
R = json.load(open(sys.argv[1]))
for name, rows in (('all', R), ('N', [r for r in R if r['series'] == 'n'])):
    hit = Counter(); tot = Counter()
    for r in rows:
        c = Counter(n for n, o, p, k in r['ocjp_full'])
        for n in range(100):
            m = min(c.get(n, 0), 5); tot[m] += 1; hit[m] += (n == r['res'])
    print(name, ' '.join(f'{m}:{hit[m]}/{tot[m]}={hit[m] / tot[m] * 100:.2f}%' for m in sorted(tot)))
    h = sum(r['res'] in sorted(range(100), key=lambda n: (-sum(1 for x in r['ocjp_full'] if x[0] == n), n))[:4] for r in rows)
    print(f'  top 4 by OCJP count: {h} / {len(rows)} = {h / len(rows):.1%}')
