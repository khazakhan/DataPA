#!/usr/bin/env python3
"""
Coverage backtest for the RECOMMENDED BY DECADE / RECOMMENDED BY FAMILY set
(score >= #40-cutoff score, "no fixed range", currently ~44 values/round).

User's question (2026-08-08): can this set be made to NEVER miss the actual
result? This replays every historical round across all independently-
preserved dataset windows through the CURRENT build_strong_predictions()
scoring engine and checks membership in that exact set (same _rec_set logic
as the live script, DataProcessing.py ~line 2441-2442 pre-reorder / see
RECOMMENDED BY DECADE/FAMILY block).

Result as of 2026-08-08 (700 rounds, 5 windows): 49.1% coverage (344/700),
barely above the 46.7% a same-sized random subset would get by chance.
"No miss" is not achievable short of ~90+ values. See
project_datascinceanal_august10_deadline.md for the full write-up.
"""
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

WINDOWS = [
    ("temp_data_d341_d446_backup.txt", 174),
    ("temp_data_d447_d592_backup.txt", 169),
    ("temp_data_d593_d818_backup.txt", 151),
    ("temp_data_d819_d1038_backup.txt", 151),
    ("temp_data.txt", 387),
]

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

def main():
    total = 0
    hits = 0
    sizes = []
    misses_detail = []

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
            state = compute_state(rows)
            if state is None or len(state[2]) < 1:
                continue
            endpoint, root, ops_list, group_index = state
            top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
            if not top4:
                continue
            cutoff = top4[-1][1]
            rec_set = {v for v in range(100) if len(scores.get(v, [])) >= cutoff}
            total += 1
            sizes.append(len(rec_set))
            if actual in rec_set:
                hits += 1
            else:
                misses_detail.append((fname, split, actual, len(rec_set)))

    print(f"Total rounds: {total}")
    print(f"Hits (actual inside RECOMMENDED set): {hits}")
    print(f"Coverage rate: {hits/total*100:.1f}%")
    print(f"Miss rate: {(total-hits)/total*100:.1f}%")
    print(f"RECOMMENDED set size: min={min(sizes)} max={max(sizes)} avg={sum(sizes)/len(sizes):.1f}")
    print(f"Chance baseline (size/100 avg): {sum(sizes)/len(sizes):.1f}%")
    print(f"\nFirst 15 misses (file, split-line, actual, set-size):")
    for m in misses_detail[:15]:
        print(" ", m)

if __name__ == "__main__":
    main()
