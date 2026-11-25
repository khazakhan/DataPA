"""FINAL 40 evaluation (FROZEN 2026-11-25 before Sets 7/8; user: 4 of 7 with 40 numbers).
Three candidate 40-number lists per round, all walk-forward:
  VOTE 40   = the script's own vote ranking, top 40 (rank_all from RRR3_F4DUMP)
  RECENT 40 = 40 most recently seen distinct numbers, EP excluded
  ADAPT 40  = whichever of the two passed more 7-round blocks on THIS chart so far
              (ties / fewer than 15 past blocks -> VOTE 40)
Chance: 40% per round, 29.0% of 7-round blocks reach 4+.
Usage: python3 tools/final40_eval.py set07 set08   (needs <set>_r12.jsonl with rank_all)"""
import json
import sys
sys.path.insert(0, 'tools')
from list40_study import lists


def evaluate(name):
    toks = open(f'holdout_sets/{name}.txt').read().split()
    rows = sorted((json.loads(l) for l in open(f'holdout_sets/{name}_r12.jsonl')), key=lambda r: r['pos'])
    rows = [r for r in rows if r['result'] is not None and r.get('rank_all')]
    hits = {'VOTE 40': [], 'RECENT 40': [], 'ADAPT 40': []}
    for r in rows:
        vote = set(r['rank_all'][:40])
        rec = lists([int(t) for t in toks[:r['pos']] if t.isdigit()])['recent40']
        nb = len(hits['VOTE 40']) // 7
        pv = sum(sum(hits['VOTE 40'][i * 7:i * 7 + 7]) >= 4 for i in range(nb))
        pr = sum(sum(hits['RECENT 40'][i * 7:i * 7 + 7]) >= 4 for i in range(nb))
        adapt = rec if nb >= 15 and pr > pv else vote
        hits['VOTE 40'].append(r['result'] in vote)
        hits['RECENT 40'].append(r['result'] in rec)
        hits['ADAPT 40'].append(r['result'] in adapt)
    n = len(rows); h = n // 2
    print(f'**{name}: {n} rounds** — chance 40% per round, 29.0% of blocks pass 4 of 7')
    print('| List | Hit rate | 1st half | 2nd half | Blocks 4+ of 7 | Pass % |')
    print('|---|---|---|---|---|---|')
    for k, hs in hits.items():
        bl = [sum(hs[i:i + 7]) for i in range(0, n - 6, 7)]
        ps = sum(b >= 4 for b in bl)
        print(f'| {k} | {100 * sum(hs) / max(n, 1):.1f}% | {100 * sum(hs[:h]) / max(h, 1):.1f}% | '
              f'{100 * sum(hs[h:]) / max(n - h, 1):.1f}% | {ps} of {len(bl)} | {100 * ps / max(len(bl), 1):.1f}% |')


if __name__ == '__main__':
    for a in sys.argv[1:]:
        evaluate(a)
