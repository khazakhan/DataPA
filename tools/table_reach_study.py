"""How much of 00-99 can table 4 make, and how often does it hold the result,
by number of changes.  python3 tools/table_reach_study.py"""
import json
from collections import Counter
nch = lambda lab: sum(len(p) - 1 if p[1:] != '-' else 0 for p in lab.split('.')[2:])
N = 0; size = Counter(); hit = Counter(); rowpick = Counter(); rows_n = 0
for s in 'FNMKO':
    for r in json.load(open(f'rrr_records/replay/fs{s}.json')):
        N += 1; rows_n += len(r['rows'])
        for k in (0, 1, 2, 4):
            nums = {n for row in r['rows'] for lab, n in row['ch'].items() if nch(lab) <= k}
            size[k] += len(nums); hit[k] += r['res'] in nums
        # how many rows can make the result within 1 change
        rowpick[sum(any(n == r['res'] and nch(l) <= 1 for l, n in row['ch'].items()) for row in r['rows'])] += 1
print(f"{N} replay rounds, {rows_n/N:.1f} rows per table on average")
for k in (0, 1, 2, 4):
    print(f"  within {k} changes: table makes {size[k]/N:.1f} numbers, held the result {hit[k]} times ({hit[k]/N:.0%}), chance {size[k]/100:.1f}")
print("  rows that make the result within 1 change:", dict(sorted(rowpick.items())))
