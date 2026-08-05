#!/usr/bin/env python3
"""
Rolling backtest — replays D341..D446 (the current continuous, fully-preserved
dataset) through the CURRENT build_strong_predictions() scoring engine.

Why only D341 onward: temp_data.txt = 174 fixed grid rows (uploaded fresh at
D341, replacing the earlier D273-D340 dataset) + trailing single-value lines
(one appended per round since). That means the exact historical state at
every one of those rounds is still on disk. D1-D340 used datasets that were
overwritten by later resets and cannot be reconstructed.

For each split point, this rebuilds EXACTLY what run() computes (endpoint,
group_index, root, ops_list) using only the data available at that point in
time, scores it with today's build_strong_predictions(), and checks the
actual next value against that score set — not against whatever partial
signal-set happened to be live when the round was originally run live.
"""
import sys
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

with open('temp_data.txt') as f:
    all_lines = [l for l in f if l.strip()]

GRID_ROWS = 188
D_START = 1715

def compute_state(rows):
    """Replicate run() steps 1-4: endpoint, group_index, root, ops_list."""
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
            if nxt is not None:
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

N_ROUNDS = len(all_lines) - GRID_ROWS  # all appended rounds with known results

results = []
for k in range(N_ROUNDS):  # D341 .. current
    d_num = D_START + k
    split = GRID_ROWS + k          # lines[:split] = data available at this round
    hist_lines = all_lines[:split]
    next_line = all_lines[split]
    rows = load_data(hist_lines)
    actual = load_data([next_line])[0][0]

    state = compute_state(rows)
    if state is None or len(state[2]) < 1:
        results.append((d_num, None, None, None, actual, None, None))
        continue
    endpoint, root, ops_list, group_index = state
    top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)

    rscore = len(scores.get(actual, []))
    rank = next((i + 1 for i, (v, _, _) in enumerate(top4) if v == actual), None)
    if rank is None:
        all_vals = sorted(range(100), key=lambda v: len(scores.get(v, [])), reverse=True)
        full_rank = all_vals.index(actual) + 1
    else:
        full_rank = rank
    hit = rank is not None
    results.append((d_num, endpoint, root, len(ops_list), actual, hit, rank, full_rank, rscore))

print(f"{'D#':<6}{'EP':<5}{'Root':<6}{'Trans':<7}{'Result':<8}{'HIT?':<6}{'Rank(40)':<10}{'Rank(100)':<10}{'Score':<6}")
hits = 0
for row in results:
    if row[1] is None:
        d_num, *_ = row
        print(f"{d_num:<6}{'--':<5}{'--':<6}{'--':<7}{row[4]:<8}{'SKIP':<6}")
        continue
    d_num, endpoint, root, trans, actual, hit, rank, full_rank, rscore = row
    if hit:
        hits += 1
    print(f"{d_num:<6}{endpoint:02d}   {root:02d}    {trans:<7}{actual:02d}      {'HIT' if hit else 'MISS':<6}"
          f"{(str(rank) if rank else '-'):<10}{full_rank:<10}{rscore:<6}")

valid = sum(1 for r in results if r[1] is not None)
print(f"\nTotal rounds backtested: {valid}  |  HITs (in current top-40): {hits}  |  Hit rate: {hits/valid*100:.1f}%")
