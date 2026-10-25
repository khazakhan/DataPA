"""Tie-break by RECOMMENDED position instead of the lower number (after N282=55 REC #1 and N285=57 REC #3 both lost 2-vote tie-breaks).
usage: python3 rec_tiebreak_test.py all4.json"""
import json, sys
R = json.load(open(sys.argv[1]))
def parts(r):
    tb = [n for n, _ in r['table']]; st = {x[0] if isinstance(x, list) else x for x in r['strong']}
    L = [set(r['rec']), set(tb), set(r['again']), set(r['wide']), set(r['yx']), set(r['found'])]
    v = lambda n: sum(n in l for l in L); t = lambda n: (n in st) + (n in set(r['ncspec']))
    rp = lambda n: r['rec'].index(n) if n in r['rec'] else 99
    return v, t, rp
KEYS = {
    'shipped: votes, STRONG, lower number': lambda v, t, rp: lambda n: (-v(n), -t(n), n),
    'votes, STRONG, REC position': lambda v, t, rp: lambda n: (-v(n), -t(n), rp(n), n),
    'votes, REC position': lambda v, t, rp: lambda n: (-v(n), rp(n), n),
    'votes, REC position, STRONG': lambda v, t, rp: lambda n: (-v(n), rp(n), -t(n), n),
}
for name, rows in (('all series', R), ('series N', [r for r in R if r['series'] == 'n']),
                   ('first half', R[:len(R) // 2]), ('second half', R[len(R) // 2:])):
    out = []
    for k, f in KEYS.items():
        h = 0
        for r in rows:
            key = f(*parts(r)); h += r['res'] in sorted(set(r['ocjp']), key=key)[:4]
        out.append(f'{k}: {h} ({h / len(rows):.1%})')
    print(f'{name} ({len(rows)} rounds):\n  ' + '\n  '.join(out))
