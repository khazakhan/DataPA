#!/usr/bin/env python3
"""
2026-07-09 deep-dive requested by user: re-examine the family-coverage claim
with the full 214-round dataset now on disk (D819-D1032), AND properly test
the narrower "single-sibling digit-transform" alternative that was left
pending in feedback_output_format.md, instead of re-litigating the already-
rejected "expand top-30 to full family membership" idea.

Three things measured per round, over D819-D1032 (214 known-result rounds):
  1. Family-covered: does actual result's family match ANY top-30 member's family?
     (re-confirms the 2026-07-07/08 finding using the now-larger live sample)
  2. Random-30-family-covered: same check but for a RANDOM 30-number sample
     instead of the real top-30 (the pigeonhole control group)
  3. Transform-covered: is actual result reachable by applying reverse/cut-both/
     cb+rev/cut-units/cut-tens to ANY top-30 member?
  4. Random-30-transform-covered: same control group for transforms
"""
import random
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions, build_family_map, cut

with open('temp_data.txt') as f:
    all_lines = [l for l in f if l.strip()]

GRID_ROWS = 151
D_START = 819

FAMILY_MAP, FAMILY_ORDER = build_family_map()

def compute_state(rows):
    endpoint = rows[-1][-1]
    endpoint_pos = (len(rows) - 1, len(rows[-1]) - 1)
    group_index = []
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if val != endpoint:
                continue
            if (r, c) == endpoint_pos:
                continue
            nxt = get_next_number(rows, r, c)
            if nxt is not None and nxt != -1:
                group_index.append(nxt)
    if not group_index:
        return None
    root = group_index[-1]
    ops_list = []
    for i in range(len(group_index) - 1):
        a, b = group_index[i], group_index[i + 1]
        ax, ay = a // 10, a % 10
        bx, by = b // 10, b % 10
        ops_list.append((find_op(ax, bx), find_op(ay, by)))
    return endpoint, root, ops_list, group_index

def transforms_of(v):
    x, y = v // 10, v % 10
    out = set()
    out.add(cut(x) * 10 + cut(y))          # cut-both
    out.add(y * 10 + x)                     # reverse
    out.add(cut(y) * 10 + cut(x))           # cb+rev
    out.add(x * 10 + cut(y))                # cut-units
    out.add(cut(x) * 10 + y)                # cut-tens
    return out

N_ROUNDS = len(all_lines) - GRID_ROWS

random.seed(42)

fam_hits = 0
fam_rand_hits = 0
tr_hits = 0
tr_rand_hits = 0
total = 0

for k in range(N_ROUNDS):
    d_num = D_START + k
    split = GRID_ROWS + k
    hist_lines = all_lines[:split]
    next_line = all_lines[split]
    try:
        actual = int(next_line.strip())
    except ValueError:
        continue
    rows = load_data(hist_lines)
    state = compute_state(rows)
    if state is None:
        continue
    endpoint, root, ops_list, group_index = state
    if len(ops_list) < 1:
        continue
    top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
    top30_vals = [v for v, _, _ in top4]
    if len(top30_vals) < 30:
        continue
    total += 1

    rand30 = random.sample(range(100), 30)

    # 1. family coverage (real top-30)
    actual_fam = FAMILY_MAP.get(actual)
    if actual_fam is not None and any(FAMILY_MAP.get(v) == actual_fam for v in top30_vals):
        fam_hits += 1
    # 2. family coverage (random 30)
    if actual_fam is not None and any(FAMILY_MAP.get(v) == actual_fam for v in rand30):
        fam_rand_hits += 1

    # 3. transform coverage (real top-30)
    tr_candidates = set()
    for v in top30_vals:
        tr_candidates |= transforms_of(v)
    if actual in tr_candidates:
        tr_hits += 1
    # 4. transform coverage (random 30)
    tr_rand_candidates = set()
    for v in rand30:
        tr_rand_candidates |= transforms_of(v)
    if actual in tr_rand_candidates:
        tr_rand_hits += 1

print(f"Rounds tested: {total} (D{D_START}-D{D_START+total-1})\n")
print(f"Family-covered  (REAL top-30):   {fam_hits}/{total} = {fam_hits/total*100:.1f}%")
print(f"Family-covered  (RANDOM 30):     {fam_rand_hits}/{total} = {fam_rand_hits/total*100:.1f}%")
print()
print(f"Transform-covered (REAL top-30): {tr_hits}/{total} = {tr_hits/total*100:.1f}%")
print(f"Transform-covered (RANDOM 30):   {tr_rand_hits}/{total} = {tr_rand_hits/total*100:.1f}%")
