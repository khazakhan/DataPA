"""FINAL 4 voting-list variants (2026-10-26 live diagnosis: WIDE and yx below chance in both
the old replay and the live N235+ rounds, STRONG 20 the steadiest list at lift 1.4).
usage: python3 vote_lists_test.py DUMP_DIR FIRST LAST all4.json"""
import json, os, sys
D, A, B, ALL = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
here = os.path.dirname(os.path.abspath(__file__))
live = []
for k in range(A, B + 1):
    f, nxt = f'{D}/d2_{k}.json', f'{here}/../rrr_datasets/n{k + 1}.txt'
    if os.path.exists(f) and os.path.exists(nxt):
        r = json.load(open(f)); r['res'] = int(open(nxt).read().split()[-1]); live.append(r)
old = json.load(open(ALL))
def pick(r, use, strong_vote):
    L = {'rec': r['rec'], 'table': [n for n, _ in r['table']], 'again': [a for a in r['again'] if a is not None],
         'wide': r['wide'], 'yx': r['yx'], 'found': r['found']}
    st = {x[0] if isinstance(x, list) else x for x in r['strong']}; nc = set(r['ncspec']); fs = set(r['fam_seats'])
    v = lambda n: sum(n in set(L[k]) for k in use) + (strong_vote and n in st)
    t = lambda n: (n in st) + (n in nc) + (n in fs)
    return sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n))[:4]
ALL6 = ['rec', 'table', 'again', 'wide', 'yx', 'found']
V = {'V0 shipped (6 lists)': (ALL6, False),
     'V1 without WIDE and yx': (['rec', 'table', 'again', 'found'], False),
     'V2 without WIDE and yx, STRONG votes': (['rec', 'table', 'again', 'found'], True),
     'V3 6 lists + STRONG votes': (ALL6, True)}
n_ = [r for r in old if r['series'] == 'n']
sets = [('old all 13 series', old), ('old 1st half', old[:len(old) // 2]), ('old 2nd half', old[len(old) // 2:]),
        ('old series N', n_), ('LIVE N235+ (untuned)', live)]
print(f"{'variant':<40}" + ''.join(f'{s:>24}' for s, _ in sets))
for name, (use, sv) in V.items():
    row = ''
    for _, R in sets:
        h = sum(r['res'] in pick(r, use, sv) for r in R); m = sum(r['res'] == pick(r, use, sv)[0] for r in R)
        row += f'{f"{h}/{len(R)} {100 * h / len(R):.1f}% M{m}":>24}'
    print(f'{name:<40}' + row)
