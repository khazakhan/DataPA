"""Slot-4 study (user 2026-11-25: 'implement the hit logic for various data sets').

FINAL 4 today = top 3 of the vote + EP repeat (KING) in slot 4.  Rule tested:
keep the EP repeat only when the chart's own PAST repeat rate (next == previous
number, counted only on numbers before the round) is >= T; otherwise put the
next-ranked vote number (rank12, first one not already in the top 3) there.

Reads holdout_sets/<set>_r12.jsonl (from tools/allrounds.py --out ..._r12.jsonl).
Usage: python3 tools/slot4_study.py set01 set02 set03 [--t 0.010]
"""
import json
import sys


def load(name):
    toks = open(f'holdout_sets/{name}.txt').read().split()
    vals = [int(t) if t.isdigit() else None for t in toks]
    rows = []
    for l in open(f'holdout_sets/{name}_r12.jsonl'):
        r = json.loads(l)
        if r['result'] is None or not r['final4'] or not r.get('rank12'):
            continue
        h = [v for v in vals[:r['pos']] if v is not None]
        rep = sum(a == b for a, b in zip(h, h[1:]))
        r['rate'] = rep / max(len(h) - 1, 1)
        rows.append(r)
    rows.sort(key=lambda r: r['pos'])
    return rows


def picks(r, t):
    top3 = r['final4'][:3]
    if r['rate'] >= t:
        return top3 + [r['king']]
    alt = next((v for v in r['rank12'] if v not in top3), None)
    return top3 + [alt]


def main():
    argv = sys.argv[1:]
    ts = [0.0, 0.006, 0.008, 0.010, 0.012, 0.015, 1.0]
    if '--t' in argv:
        i = argv.index('--t'); ts = [float(argv[i + 1])]; argv = argv[:i] + argv[i + 2:]
    sets = {n: load(n) for n in argv}
    print('| Set | Rounds | Live FINAL 4 | ' + ' | '.join(f'T={t:g}' for t in ts) + ' |')
    print('|---' * (3 + len(ts)) + '|')
    tot = [0] * (len(ts) + 1); n_all = 0
    for name, rows in sets.items():
        live = sum(r['result'] in r['final4'] for r in rows)
        res = [sum(r['result'] in picks(r, t) for r in rows) for t in ts]
        n_all += len(rows); tot[0] += live
        for i, x in enumerate(res):
            tot[i + 1] += x
        print(f'| {name} | {len(rows)} | {live} | ' + ' | '.join(map(str, res)) + ' |')
    print(f'| **all** | {n_all} | **{tot[0]}** ({100 * tot[0] / max(n_all, 1):.2f}%) | '
          + ' | '.join(f'{x} ({100 * x / max(n_all, 1):.2f}%)' for x in tot[1:]) + ' |')
    print('T=0 = always EP repeat (should equal live); T=1 = never EP repeat (always next-ranked).')


if __name__ == '__main__':
    main()
