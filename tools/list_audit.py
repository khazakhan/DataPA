"""Audit every list in rrr_records/live.jsonl against chance, by halves (user AF323).

ratio = hits / chance hits for the list size (1.00 = chance).  A list is only
worth trusting if it beats chance in BOTH halves.  Also compares FINAL 4 with
its alternatives on the same rounds.  Usage: python3 tools/list_audit.py
"""
import json
from collections import defaultdict


def lists_of(r):
    d = {}
    for k, v in (r.get('lists') or {}).items():
        if isinstance(v, list):
            d['list ' + k] = v
    for k in ('ranked', 'prime10', 'prime4fam', 'lastop', 'r28', 'final8', 'net80', 'allbb'):
        if isinstance(r.get(k), list):
            d[k] = r[k]
    f = r.get('final8') or []
    if f:
        d['FINAL 4'] = f[:4]
        d['MASTER'] = f[:1]
    return d


def main():
    rs = [json.loads(l) for l in open('rrr_records/live.jsonl')]
    rs = [r for r in rs if r.get('result') is not None]
    n, half = len(rs), len(rs) // 2
    H = defaultdict(lambda: [0, 0, 0.0, 0.0, 0, 0])
    for i, r in enumerate(rs):
        h = 0 if i < half else 1
        for k, v in lists_of(r).items():
            s = {x for x in v if isinstance(x, int)}
            if s:
                H[k][h] += r['result'] in s
                H[k][2 + h] += len(s) / 100
                H[k][4 + h] += 1
    print(f'{n} rounds; ratio = hits / chance hits (1.00 = chance)')
    print(f"{'list':22}{'1st half':>16}{'2nd half':>16}{'ratio1':>8}{'ratio2':>8}")
    for k, (a, b, ea, eb, na, nb) in sorted(
            H.items(), key=lambda kv: -(kv[1][0] + kv[1][1]) / max(.01, kv[1][2] + kv[1][3])):
        if na + nb >= 200:
            print(f'{k:22}{a:>6} vs {ea:6.1f}{b:>6} vs {eb:6.1f}{a / max(ea, .01):8.2f}{b / max(eb, .01):8.2f}')

    same = [r for r in rs if r.get('final8') and (r.get('lists') or {}).get('top4')]
    m, h = len(same), len(same) // 2
    print(f'\nFINAL 4 alternatives on the same {m} rounds (halves {h}|{m - h}; chance 4%)')
    alts = {
        'FINAL 4 (live)': lambda r: set(r['final8'][:4]),
        'ranked top 4': lambda r: set(r['lists']['top4']),
        'ranked top 3 + EP': lambda r: set(r['lists']['top4'][:3]) | {r['after']},
    }
    for name, f in alts.items():
        a = sum(r['result'] in f(r) for r in same[:h])
        b = sum(r['result'] in f(r) for r in same[h:])
        print(f'{name:20}{a:4} |{b:4}  ({100 * (a + b) / m:.2f}%)')


if __name__ == '__main__':
    main()
