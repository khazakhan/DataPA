#!/usr/bin/env python3
"""
Tests whether TYPE A (reachable via TABLE 1/2) vs TYPE B NEW (not reachable)
can be predicted in advance from structural features known BEFORE the result
is revealed: Trans (chain length), 10-C-T table size, EP==Root flag, EP x==y
flag. If table size strongly predicts TYPE B probability, the RECOMMENDED
pick strategy could lean toward TypeBNEW-style candidates when the table is
small, instead of table-based signals (AllChainBase etc.) that can only ever
be right when the round is structurally TYPE A.
"""
from DataProcessing import load_data, find_op, get_next_number, compute_variants, SIGN_FLIP

WINDOWS = [
    ('D341-D446', 'temp_data_d341_d446_backup.txt', 174, 341),
    ('D447-D592', 'temp_data_d447_d592_backup.txt', 169, 447),
    ('D593-current', 'temp_data.txt', 151, 593),
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
        ops_list.append((find_op(a // 10, b // 10), find_op(a % 10, b % 10)))
    return endpoint, root, ops_list, group_index


def table_set(root, ops_list):
    ct = set()
    for xo, yo in ops_list:
        for v in compute_variants(root, xo, yo):
            ct.add(v)
        fxo, fyo = SIGN_FLIP[xo], SIGN_FLIP[yo]
        for v in compute_variants(root, fxo, fyo):
            ct.add(v)
    return ct


rows_out = []  # (window, d_num, trans, table_size, ep_eq_root, ep_xy_coin, actual, is_type_b)

for name, fname, grid_rows, d_start in WINDOWS:
    with open(fname) as f:
        all_lines = [l for l in f if l.strip()]
    n_rounds = len(all_lines) - grid_rows
    for k in range(n_rounds):
        d_num = d_start + k
        split = grid_rows + k
        hist_lines = all_lines[:split]
        next_line = all_lines[split]
        rows = load_data(hist_lines)
        actual = load_data([next_line])[0][0]
        state = compute_state(rows)
        if state is None or len(state[2]) < 1:
            continue
        endpoint, root, ops_list, group_index = state
        trans = len(ops_list)
        ct = table_set(root, ops_list)
        table_size = len(ct)
        ep_eq_root = (endpoint == root)
        ep_xy_coin = (endpoint // 10 == endpoint % 10)
        is_type_b = actual not in ct
        rows_out.append((name, d_num, trans, table_size, ep_eq_root, ep_xy_coin, actual, is_type_b))

total = len(rows_out)
type_b_total = sum(1 for r in rows_out if r[7])
print(f"Overall: {type_b_total}/{total} = {type_b_total/total*100:.1f}% TYPE B NEW\n")

# Bucket by Trans
print("=== P(TYPE B) by Trans (chain length) bucket ===")
buckets = {}
for r in rows_out:
    trans = r[2]
    b = trans if trans <= 20 else '20+'
    buckets.setdefault(b, [0, 0])
    buckets[b][1] += 1
    if r[7]:
        buckets[b][0] += 1
for b in sorted(buckets, key=lambda x: (isinstance(x, str), x)):
    hits, tot = buckets[b]
    print(f"  Trans={b:<5} N={tot:<5} P(TYPE B)={hits/tot*100:.1f}%")

# Bucket by table size (10-value bins)
print("\n=== P(TYPE B) by table-size bucket ===")
buckets2 = {}
for r in rows_out:
    ts = r[3]
    b = ts // 10 * 10
    buckets2.setdefault(b, [0, 0])
    buckets2[b][1] += 1
    if r[7]:
        buckets2[b][0] += 1
for b in sorted(buckets2):
    hits, tot = buckets2[b]
    print(f"  table_size={b:>3}-{b+9:<3} N={tot:<5} P(TYPE B)={hits/tot*100:.1f}%")

# EP==Root flag
print("\n=== P(TYPE B) by EP==Root flag ===")
for flag in (True, False):
    subset = [r for r in rows_out if r[4] == flag]
    if not subset:
        continue
    hits = sum(1 for r in subset if r[7])
    print(f"  EP==Root={flag}  N={len(subset):<5} P(TYPE B)={hits/len(subset)*100:.1f}%")

# EP x==y coin-flip flag
print("\n=== P(TYPE B) by EP x==y flag ===")
for flag in (True, False):
    subset = [r for r in rows_out if r[5] == flag]
    if not subset:
        continue
    hits = sum(1 for r in subset if r[7])
    print(f"  EP_x==y={flag}  N={len(subset):<5} P(TYPE B)={hits/len(subset)*100:.1f}%")

# Per-window baseline for reference
print("\n=== Per-window overall TYPE B rate (sanity/consistency check) ===")
for name, *_ in WINDOWS:
    subset = [r for r in rows_out if r[0] == name]
    if not subset:
        continue
    hits = sum(1 for r in subset if r[7])
    print(f"  {name:<15} N={len(subset):<5} P(TYPE B)={hits/len(subset)*100:.1f}%")

# Correlation strength: table_size vs is_type_b (point-biserial-ish via simple bucketed monotonicity)
print("\n=== Table-size vs TYPE-B: is it a strong/monotonic predictor? ===")
import statistics
sizes = [r[3] for r in rows_out]
flags = [1 if r[7] else 0 for r in rows_out]
mean_size_typeb = statistics.mean(s for s, f in zip(sizes, flags) if f == 1)
mean_size_typea = statistics.mean(s for s, f in zip(sizes, flags) if f == 0)
print(f"  Mean table size when TYPE B: {mean_size_typeb:.1f}")
print(f"  Mean table size when TYPE A (hit table): {mean_size_typea:.1f}")
