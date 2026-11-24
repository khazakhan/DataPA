"""FINAL 4 combo search (user AF325): build 4-number picks from single-pick slots
(tools/single_pick_study.slots), choose the best combos on the 1st half ONLY,
then score them on the unseen 2nd half against the live FINAL 4.
Usage: python3 tools/final4_combo_search.py"""
import json, itertools, sys
sys.path.insert(0, 'tools')
from single_pick_study import slots, load_side

rows = [json.loads(l) for l in open('rrr_records/live.jsonl')]
rows = [r for r in rows if r.get('result') is not None and r.get('final8')]
mops = load_side('rrr_records/master_ops10_live.jsonl', 'pick')
s1 = load_side('rrr_records/strong1_live.jsonl', 'pick')
S = [slots(r, mops, s1) for r in rows]
n = len(rows); h = n // 2
names = sorted({k for s in S for k in s if not k.startswith('MASTER op') and not k.startswith('ONE ROW') and k != 'STRONG 20 #1'})
names = [k for k in names if sum(k in s for s in S) > 0.9 * n]

def hits(combo, part):
    rng = range(0, h) if part == 0 else range(h, n)
    return sum(rows[i]['result'] in {S[i].get(k) for k in combo} for i in rng)

res = sorted(((hits(c, 0), c) for c in itertools.combinations(names, 4)), reverse=True)
live = ('FINAL8 #1', 'FINAL8 #2', 'FINAL8 #3', 'FINAL8 #4')
print(f'{n} rounds, halves {h}|{n-h}; {len(res)} combos of {len(names)} slots; chance ~{0.04*h:.1f} per half')
print(f"{'combo':78}{'1st (chosen on)':>16}{'2nd (unseen)':>14}")
print(f"{'LIVE FINAL 4':78}{hits(live,0):>16}{hits(live,1):>14}")
for a, c in res[:10]:
    print(f"{' + '.join(c):78}{a:>16}{hits(c,1):>14}")
