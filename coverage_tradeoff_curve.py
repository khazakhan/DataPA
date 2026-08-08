#!/usr/bin/env python3
"""
Coverage-vs-size tradeoff curve (2026-08-08, follow-up to
recommended_coverage_backtest.py). User asked for a "no miss" fix to the
RECOMMENDED set; that's not achievable (49.1% coverage at ~47 values,
barely above the size-driven chance baseline). This shows the actual
tradeoff at fixed set sizes so the user can pick a size matching their
risk tolerance, instead of an unqualified "fix it."
"""
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

WINDOWS = [
    ("temp_data_d341_d446_backup.txt", 174),
    ("temp_data_d447_d592_backup.txt", 169),
    ("temp_data_d593_d818_backup.txt", 151),
    ("temp_data_d819_d1038_backup.txt", 151),
    ("temp_data.txt", 548),
]

SIZES = [30, 40, 50, 60, 70, 80, 90, 95, 99]

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
    hits = {s: 0 for s in SIZES}
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
            state = compute_state(rows)
            if state is None or len(state[2]) < 1:
                continue
            endpoint, root, ops_list, group_index = state
            top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
            ranked = sorted(range(100), key=lambda v: len(scores.get(v, [])), reverse=True)
            total += 1
            for s in SIZES:
                if actual in ranked[:s]:
                    hits[s] += 1

    print(f"Total rounds: {total}\n")
    print(f"{'Set size':<10}{'Coverage':<12}{'Chance baseline':<18}{'Edge'}")
    for s in SIZES:
        cov = hits[s] / total * 100
        chance = s
        print(f"{s:<10}{cov:<11.1f}%{chance:<17}%{cov - chance:+.1f}pp")

if __name__ == "__main__":
    main()
