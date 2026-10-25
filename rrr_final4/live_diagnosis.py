"""Diagnosis on live rounds never used for tuning (2026-10-26, user: "diagnose as a bull worker").
usage: python3 live_diagnosis.py DUMP_DIR FIRST LAST all4.json
DUMP_DIR holds d2_NNN.json (the round declared as NNN); the result of round NNN is the
last number of rrr_datasets/n(NNN+1).txt."""
import json, os, re, sys
from collections import Counter
D, A, B, ALL = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
here = os.path.dirname(os.path.abspath(__file__))
live = []
for k in range(A, B + 1):
    f, nxt = f'{D}/d2_{k}.json', f'{here}/../rrr_datasets/n{k + 1}.txt'
    if os.path.exists(f) and os.path.exists(nxt):
        r = json.load(open(f)); r['res'] = int(open(nxt).read().split()[-1]); r['series'] = 'live'
        live.append(r)
old = json.load(open(ALL))
def lists(r):
    tb = [n for n, _ in r['table']]
    return {'RECOMMENDED': r['rec'], 'RRR table': tb, 'same op again': [a for a in r['again'] if a is not None],
            'WIDE': r['wide'], 'yx': r['yx'], '3RRR RESULT': r['found'],
            'STRONG 20': [x[0] if isinstance(x, list) else x for x in r['strong']], 'NC/CUT': r['ncspec'],
            'OCJP': r['ocjp']}
VOTE = ['RECOMMENDED', 'RRR table', 'same op again', 'WIDE', 'yx', '3RRR RESULT']
def votes(r):
    L = lists(r); return lambda n: sum(n in set(L[k]) for k in VOTE)
def shipped(r):
    L = lists(r); v = votes(r); t = lambda n: (n in set(L['STRONG 20'])) + (n in set(L['NC/CUT']))
    return sorted(set(r['ocjp']), key=lambda n: (-v(n), -t(n), n))[:4]
def star4(r):
    return [s[0] for s in r['star'][:4]]
for name, R in (('LIVE N235+ (never tuned on)', live), ('old replay, all 13 series (tuned on)', old)):
    n = len(R)
    print(f'\n=== {name}: {n} rounds ===')
    print(f"{'list':<16}{'hits':>6}{'avg size':>10}{'hit %':>8}{'chance %':>10}{'lift':>7}")
    for k in lists(R[0]):
        h = sum(r['res'] in set(lists(r)[k]) for r in R); sz = sum(len(set(lists(r)[k])) for r in R) / n
        print(f"{k:<16}{h:>6}{sz:>10.1f}{100 * h / n:>8.1f}{sz:>10.1f}{(100 * h / n) / sz if sz else 0:>7.2f}")
    # result votes vs the share of numbers holding that many votes
    rv, nv = Counter(), Counter()
    for r in R:
        v = votes(r); rv[min(v(r['res']), 3)] += 1
        for m in range(100):
            nv[min(v(m), 3)] += 1
    print('votes: ' + '  '.join(f"{k}v results {rv[k]} ({100 * rv[k] / n:.0f}%) vs numbers {100 * nv[k] / (100 * n):.0f}% lift {(rv[k] / n) / (nv[k] / (100 * n)) if nv[k] else 0:.2f}" for k in range(4)))
    for lab, f in (('shipped FINAL 4', shipped), ('star top 4', star4)):
        h = sum(r['res'] in f(r) for r in R); print(f'{lab}: {h} of {n} = {100 * h / n:.1f}% (chance 4%)')
    m = sum(r['res'] == shipped(r)[0] for r in R if shipped(r)); print(f'MASTER: {m} of {n} = {100 * m / n:.1f}% (chance 1%)')
