#!/usr/bin/env python3
"""
Weight-optimization backtest.

Every signal's contribution to a candidate's score is currently a hand-picked
constant (e.g. AllChainBase-xy adds a fixed amount, ColFreq-top10 adds
another). Those constants were set by intuition when each signal was added,
never re-derived from data. This script measures, from real history, how
often each signal category actually fires on the true result vs. how often
it fires on wrong candidates (its "lift" over the 1/100 baseline), then
tests whether re-weighting scores by that measured lift beats the current
hand-tuned weights on held-out rounds.

Train/test split: first 80% of backtestable rounds train the lift weights,
last 20% are held out to check whether the re-weighting generalizes (guards
against fitting noise in a dataset already confirmed statistically random
at the single-number level).
"""
import re
from collections import defaultdict
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

with open('temp_data.txt') as f:
    all_lines = [l for l in f if l.strip()]

GRID_ROWS = 186
D_START = 1697


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


def normalize(label):
    """Collapse per-call variants (Op7, node05, ±3, ...) into one category."""
    label = re.sub(r'\d+', '#', label)
    label = re.sub(r'[★]', '', label)
    return label.strip()


N_ROUNDS = len(all_lines) - GRID_ROWS

rounds = []  # (d_num, actual, {value: set(categories)})
for k in range(N_ROUNDS):
    d_num = D_START + k
    split = GRID_ROWS + k
    hist_lines = all_lines[:split]
    next_line = all_lines[split]
    rows = load_data(hist_lines)
    actual = load_data([next_line])[0][0]

    state = compute_state(rows)
    if state is None or len(state[2]) < 1:
        continue
    endpoint, root, ops_list, group_index = state
    top4, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)

    cand_cats = {}
    for v in range(100):
        raw = scores.get(v, [])
        cand_cats[v] = set(normalize(r) for r in raw)
    rounds.append((d_num, actual, cand_cats))

print(f"Backtestable rounds: {len(rounds)}")

split_idx = int(len(rounds) * 0.8)
train, test = rounds[:split_idx], rounds[split_idx:]
print(f"Train: {len(train)} rounds ({train[0][0]}-{train[-1][0]})  |  "
      f"Test: {len(test)} rounds ({test[0][0]}-{test[-1][0]})")

# ---- 1. measure lift per category on TRAIN ----
fires = defaultdict(int)   # category -> total (round,candidate) fires
hits = defaultdict(int)    # category -> fires where candidate == actual
for d_num, actual, cand_cats in train:
    for v, cats in cand_cats.items():
        for c in cats:
            fires[c] += 1
            if v == actual:
                hits[c] += 1

BASE = 1 / 100
lift = {}
for c in fires:
    if fires[c] < 20:       # too rare in train to trust
        continue
    precision = hits[c] / fires[c]
    lift[c] = precision / BASE

print(f"\nCategories measured (>=20 fires in train): {len(lift)}")
print("\nTop 15 by lift (fires >= 20):")
for c, l in sorted(lift.items(), key=lambda x: -x[1])[:15]:
    print(f"  {c:<40} lift={l:5.2f}  fires={fires[c]:<5} hits={hits[c]}")
print("\nBottom 10 by lift (fires >= 20) — candidates for down-weighting or removal:")
for c, l in sorted(lift.items(), key=lambda x: x[1])[:10]:
    print(f"  {c:<40} lift={l:5.2f}  fires={fires[c]:<5} hits={hits[c]}")


def score_with(weight_fn, cand_cats):
    return sum(weight_fn(c) for c in cand_cats)


def eval_topN(rounds_set, weight_fn, n=40):
    hit_count = 0
    for d_num, actual, cand_cats in rounds_set:
        scored = sorted(range(100), key=lambda v: score_with(weight_fn, cand_cats[v]), reverse=True)
        if actual in scored[:n]:
            hit_count += 1
    return hit_count / len(rounds_set) * 100


# current (hand-tuned) weight == raw count of that category's original appends;
# recover it by re-running with the *original* scores (len of raw list per cat
# occurrence) -- approximate baseline via category presence count of 1 (since
# categories were deduped to sets above, baseline weight = 1 per unique
# category, matching how many DISTINCT signals fired instead of the literal
# hard-coded per-append constants). This still lets us do an apples-to-apples
# comparison: "count of distinct signals firing" vs "lift-weighted signals".
def baseline_weight(c):
    return 1.0


def lift_weight(c):
    return lift.get(c, 1.0)


base_train = eval_topN(train, baseline_weight)
base_test = eval_topN(test, baseline_weight)
lift_train = eval_topN(train, lift_weight)
lift_test = eval_topN(test, lift_weight)

print(f"\n=== Top-40 hit rate: unweighted (1 pt/signal) vs lift-weighted ===")
print(f"  TRAIN  unweighted={base_train:.1f}%   lift-weighted={lift_train:.1f}%")
print(f"  TEST   unweighted={base_test:.1f}%   lift-weighted={lift_test:.1f}%   <-- the number that matters")
