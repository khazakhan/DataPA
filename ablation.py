#!/usr/bin/env python3
"""
Signal-ablation study — tests whether specific signal groups in
build_strong_predictions() help, hurt, or are neutral to the top-30 hit rate.

Method: run the REAL (fixed, deterministic) build_strong_predictions() once per
round to get the full scores dict with per-contribution labels attached. Then,
for each ablation config, filter out score contributions whose label matches a
suspect group, re-rank with the SAME deterministic tie-break used in
production (score desc, then value desc), and check whether the actual result
lands in the filtered top-30.

Caveat (documented, not hidden): this does NOT re-run the two-pass compound
signals against a scores dict that never had the ablated group in it — it
only strips that group's OWN contributions post-hoc. It also does not
replicate the "guarantee 10 missing-set slots" forced-override, applied
uniformly to every config here (natural top-30 only), so this script's
"baseline" hit rate will differ slightly from the live backtest.py numbers.
Relative differences BETWEEN configs are what this measures, not exact
production replication.

Covers D447-D497 (51 rounds) — every round with a known result in the
current continuous dataset (uploaded fresh at D447, replacing D341-D446).
The digit-transform family (CutBoth/CbRev/Reverse/CutUnits/CutTens/
PredNeighbor), TableProx, CompOp, and Obs1/Obs1B are already permanently
filtered inside build_strong_predictions() (see the _ablated_prefixes
block) so they never appear in `scores` here and are not re-tested.
"""
from DataProcessing import load_data, find_op, get_next_number, build_strong_predictions

with open('temp_data.txt') as f:
    all_lines = [l for l in f if l.strip()]

GRID_ROWS = 458
D_START = 1629
N_ROUNDS = len(all_lines) - GRID_ROWS  # D447..current

FAMILIES = {
    'AllChainBase': ['AllChainBase-sxy', 'AllChainBase-syx', 'AllChainBase-xy', 'AllChainBase-yx'],
    'Arriving': ['Arriving', 'Arriving-T1-SWAP', 'Arriving-T1-SWAP-yx', 'Arriving-T2-STEP-FWD',
                 'Arriving-T2-STEP-FWD-yx', 'Arriving-T3-STRIP+FLIP', 'Arriving-T3-STRIP+FLIP-yx',
                 'Arriving-T4-ADD+STEP', 'Arriving-T4-ADD+STEP-yx'],
    'ChainMiss': ['ChainMiss-x1D', 'ChainMiss-x1D-yx', 'ChainMiss-y1D', 'ChainMiss-y1D-yx'],
    'ColFreq': ['ColFreq-top10', 'ColFreq-top20', 'ColFreq-top30'],
    'CompOp': ['CompOp-sxy', 'CompOp-syx', 'CompOp-xy', 'CompOp-yx'],
    'DataFreq': ['DataFreq-top10', 'DataFreq-top20', 'DataFreq-top30'],
    'DigRes': [f'DigRes-Op{i}' for i in range(1, 21)],
    'DoubleObs3': [f'DoubleObs3-ry-Op{i}' for i in range(1, 21)],
    'EP-as-result': ['EP-as-result'],
    'GroupIndex-A1': ['GroupIndex-A1'],
    'Last-op': ['Last-op'],
    'NearMiss-1D': ['NearMiss-1D'],
    'Obs1': ['Obs1', 'Obs1B'],
    'Obs2': ['Obs2'],
    'Obs3': [f'Obs3-Op{i}' for i in range(1, 22)] + [f'Obs3Next-Op{i}' for i in range(1, 22)],
    'Op1': ['Op1', 'Op1-sign+xy-extra'],
    'Pre-arriving': ['Pre-arriving-1', 'Pre-arriving-2'],
    'Root-as-result': ['Root-as-result'],
    'Root-internal': ['Root-internal'],
    'RootOpClose': ['RootOpClose-1D-inchain'],
    'RootOpRepeat': ['RootOpRepeat-next'],
    'ArrOp-elsewhere-next': ['ArrOp-elsewhere-next'],
    'Rule9': [f'Rule9-node{s:02d}' for s in range(100)],
    'Rule10': [f'Rule10-node{s:02d}' for s in range(100)],
    'Rule11': [f'Rule11-node{s:02d}' for s in range(100)],
    'repeat-pair': ['repeat-pair'],
}

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
        ops_list.append((find_op(a // 10, b // 10), find_op(a % 10, b % 10)))
    return endpoint, root, ops_list, group_index

def filtered_rank(scores, exclude_labels, actual):
    """Re-rank using scores with any label exactly matching an excluded set removed."""
    excl = set(exclude_labels)
    filt = {}
    for v, reasons in scores.items():
        if excl:
            kept = [r for r in reasons if r.split()[0] not in excl]
        else:
            kept = reasons
        if kept:
            filt[v] = kept
    ranked = sorted(filt.items(), key=lambda kv: (len(kv[1]), -kv[0]), reverse=True)
    top30 = [v for v, _ in ranked[:30]]
    hit = actual in top30
    ascore = len(filt.get(actual, []))
    return hit, ascore

configs = {'baseline_all_signals': []}
for name, labels in FAMILIES.items():
    configs[f'minus_{name}'] = labels

tallies = {name: 0 for name in configs}
per_round = []

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
    _, scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)

    row_result = {'D': d_num, 'actual': actual}
    for cfg_name, labels in configs.items():
        hit, ascore = filtered_rank(scores, labels, actual)
        tallies[cfg_name] += 1 if hit else 0
        row_result[cfg_name] = (hit, ascore)
    per_round.append(row_result)

total = len(per_round)
print(f"Rounds tested: {total} (D{D_START}-D{D_START+N_ROUNDS-1})\n")
print(f"{'Config':<28}{'Hits':<6}{'Hit Rate':<10}{'Delta vs baseline'}")
baseline_hits = tallies['baseline_all_signals']
for name in sorted(configs, key=lambda n: -tallies[n]):
    hits = tallies[name]
    rate = hits / total * 100
    delta = hits - baseline_hits
    sign = '+' if delta > 0 else ''
    print(f"{name:<28}{hits:<6}{rate:<10.1f}{sign}{delta}")
