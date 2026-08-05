#!/usr/bin/env python3
"""
Live A/B integration test for the one candidate that survived cross-window
screening in mine_grid_positions.py (2026-08-08 re-run): RootRow-c0, "+1"
relation, y-axis -- D341-D446=18.5%(10/54), D447-D592=18.0%(11/61) on "all
rounds". This does NOT just report the correlational rate (which is subject
to a large multiple-comparisons search space, ~8 positions x 8 relations x
2 axes x 5 windows) -- it actually injects the candidate as a real signal
into a COPY of the live scores dict and re-checks whether it changes the
top-40 hit rate, the same live-backtest discipline used for every signal
ever added to this project (see the "ChainFirst +1 x" precedent, 2026-07-05
Extended forensic mining -- cleared cross-window screening but showed ZERO
net effect once actually integrated).
"""
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

WINDOWS = [
    ("temp_data_d341_d446_backup.txt", 174),
    ("temp_data_d447_d592_backup.txt", 169),
    ("temp_data_d593_d818_backup.txt", 151),
    ("temp_data_d819_d1038_backup.txt", 151),
    ("temp_data.txt", 546),
]

def compute_state_positions(rows):
    endpoint = rows[-1][-1]
    endpoint_pos = (len(rows) - 1, len(rows[-1]) - 1)
    group_index = []
    positions = []
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if val != endpoint:
                continue
            if (r, c) == endpoint_pos:
                continue
            nxt = get_next_number(rows, r, c)
            if nxt is not None:
                group_index.append(nxt)
                if c + 1 < len(row):
                    positions.append((r, c + 1))
                else:
                    positions.append((r + 1, 0))
    if not group_index:
        return None
    root = group_index[-1]
    root_pos = positions[-1]
    ops_list = []
    for i in range(len(group_index) - 1):
        a, b = group_index[i], group_index[i + 1]
        ops_list.append((find_op(a // 10, b // 10), find_op(a % 10, b % 10)))
    return endpoint, root, root_pos, ops_list, group_index

baseline_hits = 0
boosted_hits = 0
flips_gained = 0   # was miss, now hit
flips_lost = 0     # was hit, now miss (boost pushed something else in)
total = 0

for fname, grid_rows in WINDOWS:
    with open(fname) as f:
        all_lines = [l for l in f if l.strip()]
    n_rounds = len(all_lines) - grid_rows
    for k in range(n_rounds):
        split = grid_rows + k
        hist_lines = all_lines[:split]
        next_line = all_lines[split]
        rows = load_data(hist_lines)
        actual = load_data([next_line])[0][0]

        state = compute_state_positions(rows)
        if state is None or len(state[3]) < 1:
            continue
        endpoint, root, root_pos, ops_list, group_index = state
        top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
        if not top4:
            continue
        total += 1

        # baseline top-40 hit
        baseline_top40 = {v for v, _, _ in top4}
        base_hit = actual in baseline_top40

        # candidate: RootRow-c0 value, y-digit +1 relation
        rr, rc = root_pos
        if not (0 <= rr < len(rows)) or len(rows[rr]) < 1:
            # can't compute candidate this round -- count baseline only
            baseline_hits += base_hit
            boosted_hits += base_hit
            continue
        cand_val = rows[rr][0]
        cand_y = cand_val % 10
        target_y = (cand_y + 1) % 10

        # inject a synthetic vote into a COPY of the scores dict for every
        # value whose y-digit matches target_y (mirrors how a real signal
        # would add one reason-string per matching value)
        boosted_scores = {v: list(reasons) for v, reasons in scores.items()}
        for v in range(100):
            if v % 10 == target_y:
                boosted_scores.setdefault(v, []).append('RootRow-c0+1y-TEST')

        ranked = sorted(range(100), key=lambda v: len(boosted_scores.get(v, [])), reverse=True)
        boosted_top40 = set(ranked[:40])
        boost_hit = actual in boosted_top40

        baseline_hits += base_hit
        boosted_hits += boost_hit
        if not base_hit and boost_hit:
            flips_gained += 1
        elif base_hit and not boost_hit:
            flips_lost += 1

print(f"Total rounds: {total}")
print(f"Baseline top-40 hit rate: {baseline_hits}/{total} = {baseline_hits/total*100:.1f}%")
print(f"Boosted  top-40 hit rate: {boosted_hits}/{total} = {boosted_hits/total*100:.1f}%")
print(f"Net change: {boosted_hits - baseline_hits:+d} rounds")
print(f"Flips gained (miss->hit): {flips_gained}")
print(f"Flips lost   (hit->miss): {flips_lost}")
