"""FROZEN candidate rule (2026-11-25, learned on Sets 1-5, W=400 fixed before Set 6).
Each round: compare on THIS chart's last 400 tested rounds how often 'recent 4'
(4 most recently seen numbers other than the EP) held the result vs OCJP FINAL 4;
use recent 4 only if it has been ahead, else keep FINAL 4.  Needs 100 past rounds.
Usage: python3 tools/adapt_recent.py set06 [set07 ...]   (needs <set>_r12.jsonl)"""
import sys
sys.path.insert(0, 'tools')
from slot4_study import load
from simple_rules import rules
W = 400
for n in sys.argv[1:]:
    rows = load(n); toks = open(f'holdout_sets/{n}.txt').read().split()
    hist = []; live = [0, 0]; ad = [0, 0]; h2 = len(rows) // 2
    for i, r in enumerate(rows):
        rec = rules([int(t) for t in toks[:r['pos']] if t.isdigit()])['recent']
        past = hist[-W:]
        use = len(past) >= 100 and sum(a for a, _ in past) > sum(b for _, b in past)
        pk = rec if use else r['final4']
        k = i >= h2
        live[k] += r['result'] in r['final4']; ad[k] += r['result'] in pk
        hist.append((r['result'] in rec, r['result'] in r['final4']))
    print(f'{n} {len(rows)} rounds | live FINAL 4 {sum(live)} (halves {live[0]}|{live[1]}) '
          f'| adaptive {sum(ad)} (halves {ad[0]}|{ad[1]})')
