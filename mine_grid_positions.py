#!/usr/bin/env python3
"""
Extended forensic mining — tests whether the actual result relates to grid
positions OTHER than just Root/Endpoint (which the 2026-07-04 study already
covered and found nothing for). Two independent tests, run across all THREE
available dataset windows (D341-D446, D447-D592, D593-current) for
cross-window validation:

PART A — Exact-match-at-fixed-lag: does the actual result already appear
verbatim in the grid at some fixed distance back from the end of the visible
data? (Reading-order flatten, tested at every lag 1..300.) This is a much
cheaper/stronger test than digit-relations: since results are 2-digit values,
chance of an exact match at any single position is roughly 1% (adjusted for
the real value-frequency distribution), so even a 5-10x lift is meaningful.

PART B — Digit-relations against curated OTHER positions: Root's row/column
neighbors, Endpoint's row neighbors, Endpoint's vertical neighbor (cell
directly above), first cell of the grid, first row of the grid, and the
first element of the chain (as opposed to just the last=Root, already
tested). Same ~9 relation types as the 2026-07-04 study, run over zero-signal
misses (primary, matches prior methodology) and over all rounds (secondary,
more power).

Caveat carried over from the prior study: many hypotheses x many positions
means some combination WILL look inflated by chance. Only combinations that
clear a high bar (order of magnitude above baseline) AND replicate across
at least 2 of the 3 independent windows are worth treating as real.
"""
import sys
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

WINDOWS = [
    ('D341-D446', 'temp_data_d341_d446_backup.txt', 174, 341),
    ('D447-D592', 'temp_data_d447_d592_backup.txt', 169, 447),
    ('D593-current', 'temp_data.txt', 151, 593),
]

def compute_state_positions(rows):
    """Like compute_state in backtest.py/ablation.py, but also tracks the
    (r,c) grid position of Root and of every chain element."""
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
    return endpoint, endpoint_pos, root, root_pos, ops_list, group_index, positions


def load_window(fname, grid_rows):
    with open(fname) as f:
        all_lines = [l for l in f if l.strip()]
    n_rounds = len(all_lines) - grid_rows
    return all_lines, n_rounds


# ── PART A: exact-match-at-fixed-lag ───────────────────────────────────────

MAX_LAG = 300

def part_a(window_name, all_lines, grid_rows, n_rounds):
    lag_hits = {lag: 0 for lag in range(1, MAX_LAG + 1)}
    total = 0
    value_freq = {}
    for k in range(n_rounds):
        split = grid_rows + k
        hist_lines = all_lines[:split]
        next_line = all_lines[split]
        rows = load_data(hist_lines)
        actual = load_data([next_line])[0][0]
        flat = [v for row in rows for v in row]
        value_freq[actual] = value_freq.get(actual, 0) + 1
        total += 1
        max_lag = min(len(flat), MAX_LAG)
        for lag in range(1, max_lag + 1):
            if flat[-lag] == actual:
                lag_hits[lag] += 1
    mode_val, mode_count = max(value_freq.items(), key=lambda kv: kv[1])
    mode_rate = mode_count / total * 100
    top = sorted(lag_hits.items(), key=lambda kv: -kv[1])[:10]
    print(f"\n[Part A] {window_name}  ({total} rounds)")
    print(f"  Mode-value baseline (always guessing {mode_val:02d}): {mode_rate:.1f}%")
    print(f"  Top 10 lags by exact-match rate:")
    for lag, hits in top:
        rate = hits / total * 100
        print(f"    lag={lag:<4} hits={hits:<4} rate={rate:.1f}%")
    return lag_hits, total


# ── PART B: digit-relations against curated other positions ───────────────

def dig(n):
    return n // 10, n % 10

def cut(d):
    return (d + 5) % 10

RELATIONS = {
    'same':     lambda a, b: a == b,
    'reverse':  lambda a, b: a == cut(cut(b)) or True and False,  # placeholder unused
}

def relation_matches(src_digit, dst_digit):
    """Return set of relation names that hold between src and dst digit."""
    hits = []
    if src_digit == dst_digit:
        hits.append('same')
    if cut(src_digit) == dst_digit:
        hits.append('cut')
    if (src_digit + 1) % 10 == dst_digit:
        hits.append('+1')
    if (src_digit - 1) % 10 == dst_digit:
        hits.append('-1')
    if (src_digit + 2) % 10 == dst_digit:
        hits.append('+2')
    if (src_digit - 2) % 10 == dst_digit:
        hits.append('-2')
    if (9 - src_digit) == dst_digit:
        hits.append('9-comp')
    if (src_digit + dst_digit) % 10 == 0:
        hits.append('sum10')
    return hits


def candidate_positions(rows, root_pos, endpoint_pos, group_index):
    """Return dict of {label: value} for curated OTHER grid positions."""
    cands = {}
    rr, rc = root_pos
    er, ec = endpoint_pos
    # Root's row neighbors (other columns, same row)
    if 0 <= rr < len(rows):
        for c, v in enumerate(rows[rr]):
            if c != rc:
                cands[f'RootRow-c{c}'] = v
    # Root's vertical neighbors (same column, row above/below)
    if rr - 1 >= 0 and rc < len(rows[rr - 1]):
        cands['RootColUp'] = rows[rr - 1][rc]
    if rr + 1 < len(rows) and rc < len(rows[rr + 1]):
        cands['RootColDown'] = rows[rr + 1][rc]
    # Endpoint's row neighbors (other columns, same row)
    if 0 <= er < len(rows):
        for c, v in enumerate(rows[er]):
            if c != ec:
                cands[f'EPRow-c{c}'] = v
    # Endpoint's vertical neighbor (row above, same column)
    if er - 1 >= 0 and ec < len(rows[er - 1]):
        cands['EPColUp'] = rows[er - 1][ec]
    # First element of the chain (as opposed to last=Root) — varies per round
    # (unlike GridFirst/GridFirstRow, which are constant within a window and
    # were dropped: testing a constant against varying actuals just remeasures
    # digit frequency, already covered by DataFreq/ColFreq, not a real
    # positional relationship)
    if group_index:
        cands['ChainFirst'] = group_index[0]
    return cands


def part_b(window_name, all_lines, grid_rows, n_rounds, only_zero_signal=True):
    tally = {}  # (label, relation, digit) -> [hits, total]
    n_tested = 0
    n_zero_signal = 0
    for k in range(n_rounds):
        d_num = grid_rows  # unused
        split = grid_rows + k
        hist_lines = all_lines[:split]
        next_line = all_lines[split]
        rows = load_data(hist_lines)
        actual = load_data([next_line])[0][0]

        state = compute_state_positions(rows)
        if state is None or len(state[4]) < 1:
            continue
        endpoint, endpoint_pos, root, root_pos, ops_list, group_index, positions = state

        if only_zero_signal:
            _, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
            score = len(scores.get(actual, []))
            if score != 0:
                continue
            n_zero_signal += 1

        n_tested += 1
        ax, ay = dig(actual)
        cands = candidate_positions(rows, root_pos, endpoint_pos, group_index)
        for label, val in cands.items():
            vx, vy = dig(val)
            for rel in relation_matches(vx, ax):
                key = (label, rel, 'x')
                tally.setdefault(key, [0, 0])
                tally[key][0] += 1
            for rel in relation_matches(vy, ay):
                key = (label, rel, 'y')
                tally.setdefault(key, [0, 0])
                tally[key][0] += 1
            # denom: count this candidate as "tested" once per round regardless
            for axis in ('x', 'y'):
                pass
        for label in cands:
            for axis in ('x', 'y'):
                for rel in ['same', 'cut', '+1', '-1', '+2', '-2', '9-comp', 'sum10']:
                    key = (label, rel, axis)
                    tally.setdefault(key, [0, 0])
                    tally[key][1] += 1

    tag = "zero-signal misses" if only_zero_signal else "all rounds"
    print(f"\n[Part B] {window_name} — {tag}  (N={n_tested})")
    ranked = sorted(tally.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))
    shown = 0
    for (label, rel, axis), (hits, total) in ranked:
        if total < 15 or hits < 4:
            continue
        rate = hits / total * 100
        print(f"    {label:<20} {rel:<8} {axis}   hits={hits:<4}/{total:<4}  rate={rate:.1f}%")
        shown += 1
        if shown >= 15:
            break
    if shown == 0:
        print("    (nothing cleared N>=15, hits>=4 threshold)")
    return tally, n_tested


if __name__ == '__main__':
    all_a = {}
    all_b_zero = {}
    all_b_all = {}
    per_window_zero = {}  # window_name -> {key: rate}
    per_window_all = {}
    for name, fname, grid_rows, d_start in WINDOWS:
        try:
            all_lines, n_rounds = load_window(fname, grid_rows)
        except FileNotFoundError:
            print(f"skip {name}: {fname} not found")
            continue
        lag_hits, total = part_a(name, all_lines, grid_rows, n_rounds)
        for lag, hits in lag_hits.items():
            e = all_a.setdefault(lag, [0, 0])
            e[0] += hits
            e[1] += total

        tally_zero, n_zero = part_b(name, all_lines, grid_rows, n_rounds, only_zero_signal=True)
        per_window_zero[name] = {k: (h / t * 100 if t else 0, h, t) for k, (h, t) in tally_zero.items()}
        for key, (hits, total_) in tally_zero.items():
            e = all_b_zero.setdefault(key, [0, 0])
            e[0] += hits
            e[1] += total_

        tally_all, n_all = part_b(name, all_lines, grid_rows, n_rounds, only_zero_signal=False)
        per_window_all[name] = {k: (h / t * 100 if t else 0, h, t) for k, (h, t) in tally_all.items()}
        for key, (hits, total_) in tally_all.items():
            e = all_b_all.setdefault(key, [0, 0])
            e[0] += hits
            e[1] += total_

    print("\n" + "=" * 70)
    print("COMBINED ACROSS ALL WINDOWS")
    print("=" * 70)

    print("\n[Part A combined] Top 10 lags by exact-match rate:")
    top = sorted(all_a.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))[:10]
    for lag, (hits, total) in top:
        rate = hits / total * 100 if total else 0
        print(f"    lag={lag:<4} hits={hits:<4}/{total:<4}  rate={rate:.1f}%")

    print("\n[Part B combined, zero-signal misses]:")
    ranked = sorted(all_b_zero.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))
    shown = 0
    for (label, rel, axis), (hits, total) in ranked:
        if total < 30 or hits < 6:
            continue
        rate = hits / total * 100
        print(f"    {label:<20} {rel:<8} {axis}   hits={hits:<4}/{total:<4}  rate={rate:.1f}%")
        shown += 1
        if shown >= 15:
            break
    if shown == 0:
        print("    (nothing cleared N>=30, hits>=6 threshold)")

    print("\n[Part B combined, ALL rounds]:")
    ranked = sorted(all_b_all.items(), key=lambda kv: -(kv[1][0] / kv[1][1] if kv[1][1] else 0))
    shown = 0
    for (label, rel, axis), (hits, total) in ranked:
        if total < 30 or hits < 6:
            continue
        rate = hits / total * 100
        print(f"    {label:<20} {rel:<8} {axis}   hits={hits:<4}/{total:<4}  rate={rate:.1f}%")
        shown += 1
        if shown >= 15:
            break
    if shown == 0:
        print("    (nothing cleared N>=30, hits>=6 threshold)")

    # ── Cross-window consistency check ──────────────────────────────────
    # A combo only counts as a real candidate if it clears a bar (rate >=18%,
    # N>=15) INDEPENDENTLY in at least 2 of the 3 windows — this is the same
    # bar the earlier signal-family ablation studies used ("helps on both
    # windows" not just combined-noise).
    print("\n" + "=" * 70)
    print("CROSS-WINDOW CONSISTENCY CHECK (bar: rate>=18%, N>=15, in >=2/3 windows)")
    print("=" * 70)
    for tag, per_window in [("zero-signal misses", per_window_zero), ("all rounds", per_window_all)]:
        print(f"\n[{tag}]")
        all_keys = set()
        for w in per_window.values():
            all_keys |= set(w.keys())
        survivors = []
        for key in all_keys:
            clears = []
            for wname, w in per_window.items():
                rate, hits, total = w.get(key, (0, 0, 0))
                if total >= 15 and rate >= 18:
                    clears.append((wname, rate, hits, total))
            if len(clears) >= 2:
                survivors.append((key, clears))
        if not survivors:
            print("    NONE — no combo clears the bar in 2+ independent windows.")
        else:
            for key, clears in survivors:
                label, rel, axis = key
                detail = ", ".join(f"{w}={r:.1f}%({h}/{t})" for w, r, h, t in clears)
                print(f"    {label:<20} {rel:<8} {axis}   {detail}")
