#!/usr/bin/env python3
"""
DataProcessing.py
-----------------
Analyzes number sequences using the cut rule and digit operations.

Cut Rule : cut(n) = (n + 5) % 10
Operations: no_change | +1 | -1 | +2 | -2 | cut | cut+1 | cut-1 | cut+2 | cut-2

Usage:
    python3 DataProcessing.py data.txt
    python3 DataProcessing.py data.txt --x-op cut+1 --y-op cut+1
    cat data.txt | python3 DataProcessing.py
"""

import sys
import argparse
from collections import defaultdict

# ── Constants ─────────────────────────────────────────────────────────────────

ALL_OPS = [
    'no_change', '+1', '-1', '+2', '-2',
    'cut', 'cut+1', 'cut-1', 'cut+2', 'cut-2'
]

SIGN_FLIP = {
    'no_change': 'no_change',
    '+1':        '-1',
    '-1':        '+1',
    '+2':        '-2',
    '-2':        '+2',
    'cut':       'cut',
    'cut+1':     'cut-1',
    'cut-1':     'cut+1',
    'cut+2':     'cut-2',
    'cut-2':     'cut+2',
}

# Rule 10 — y transform: reduce modifier magnitude by 1 then flip sign
# +2→-1, -2→+1, +1→nc, -1→nc, nc→nc, cut+2→cut-1, cut-2→cut+1, cut±1→cut, cut→cut
RULE10_Y_TRANSFORM = {
    'no_change': 'no_change',
    '+1':        'no_change',
    '-1':        'no_change',
    '+2':        '-1',
    '-2':        '+1',
    'cut':       'cut',
    'cut+1':     'cut',
    'cut-1':     'cut',
    'cut+2':     'cut-1',
    'cut-2':     'cut+1',
}

# Rule 6 helpers — remove "cut" prefix (inverse of ADD_CUT for cut-ops)
REMOVE_CUT = {
    'no_change': 'no_change', '+1': '+1', '-1': '-1', '+2': '+2', '-2': '-2',
    'cut': 'no_change', 'cut+1': '+1', 'cut-1': '-1', 'cut+2': '+2', 'cut-2': '-2',
}

# Strip ±n modifier, keeping only the cut/no-cut base
STRIP_MODIFIER = {
    'no_change': 'no_change', '+1': 'no_change', '-1': 'no_change',
    '+2': 'no_change', '-2': 'no_change',
    'cut': 'cut', 'cut+1': 'cut', 'cut-1': 'cut', 'cut+2': 'cut', 'cut-2': 'cut',
}

# Step ±1 on the modifier magnitude
STEP_UP = {
    'no_change': '+1', '+1': '+2', '+2': '+2', '-1': 'no_change', '-2': '-1',
    'cut': 'cut+1', 'cut+1': 'cut+2', 'cut+2': 'cut+2', 'cut-1': 'cut', 'cut-2': 'cut-1',
}
STEP_DOWN = {
    'no_change': '-1', '+1': 'no_change', '+2': '+1', '-1': '-2', '-2': '-2',
    'cut': 'cut-1', 'cut+1': 'cut', 'cut+2': 'cut+1', 'cut-1': 'cut-2', 'cut-2': 'cut-2',
}

# Pathan Obs 1 — x_op transform: add "cut" prefix
ADD_CUT = {
    'no_change': 'cut',
    '+1':        'cut+1',
    '-1':        'cut-1',
    '+2':        'cut+2',
    '-2':        'cut-2',
    'cut':       'cut',
    'cut+1':     'cut+1',
    'cut-1':     'cut-1',
    'cut+2':     'cut+2',
    'cut-2':     'cut-2',
}

# Pathan Obs 1 — y_op transform: remove "cut" prefix then flip sign
REMOVE_CUT_FLIP = {
    'cut+2':     '-2',
    'cut-2':     '+2',
    'cut+1':     '-1',
    'cut-1':     '+1',
    'cut':       'cut',
    '+2':        '-2',
    '-2':        '+2',
    '+1':        '-1',
    '-1':        '+1',
    'no_change': 'no_change',
}

OP_ALIASES = {
    'direct+1': '+1', 'direct +1': '+1', 'd+1': '+1',
    'direct-1': '-1', 'direct -1': '-1', 'd-1': '-1',
    'direct+2': '+2', 'direct +2': '+2', 'd+2': '+2',
    'direct-2': '-2', 'direct -2': '-2', 'd-2': '-2',
    'cut only': 'cut', 'cutonly': 'cut',
    'cut +1': 'cut+1', 'cut +2': 'cut+2',
    'cut -1': 'cut-1', 'cut -2': 'cut-2',
    'none': 'no_change', 'nc': 'no_change',
}


# ── Core Math ─────────────────────────────────────────────────────────────────

def cut(n):
    return (n + 5) % 10


def apply_op(digit, op):
    d = int(digit) % 10
    if   op == 'no_change': return d
    elif op == '+1':        return (d + 1) % 10
    elif op == '-1':        return (d - 1) % 10
    elif op == '+2':        return (d + 2) % 10
    elif op == '-2':        return (d - 2) % 10
    elif op == 'cut':       return cut(d)
    elif op == 'cut+1':     return (cut(d) + 1) % 10
    elif op == 'cut-1':     return (cut(d) - 1) % 10
    elif op == 'cut+2':     return (cut(d) + 2) % 10
    elif op == 'cut-2':     return (cut(d) - 2) % 10
    else:
        raise ValueError(f"Unknown operation: '{op}'")


def find_op(src, dst):
    """Return the operation that maps digit src → dst."""
    for op in ALL_OPS:
        if apply_op(src, op) == dst:
            return op
    return '?'


def compute_variants(root, x_op, y_op):
    """Return (xy, yx, sign_xy, sign_yx) for ROOT ELEMENT and given ops."""
    rx, ry   = root // 10, root % 10
    fx, fy   = SIGN_FLIP[x_op], SIGN_FLIP[y_op]

    xy       = apply_op(rx, x_op) * 10 + apply_op(ry, y_op)
    yx       = apply_op(rx, y_op) * 10 + apply_op(ry, x_op)
    sign_xy  = apply_op(rx, fx)   * 10 + apply_op(ry, fy)
    sign_yx  = apply_op(rx, fy)   * 10 + apply_op(ry, fx)

    return xy, yx, sign_xy, sign_yx


def classify_op(x_op, y_op, ops_list):
    """Return 'TABLE 1 (Op N)', 'TABLE 2 (NE N)', or 'NEW — not in either table'."""
    for i, (ox, oy) in enumerate(ops_list):
        if ox == x_op and oy == y_op:
            return f'TABLE 1  (Op {i+1})'
    for i, (ox, oy) in enumerate(ops_list):
        if SIGN_FLIP[ox] == x_op and SIGN_FLIP[oy] == y_op:
            return f'TABLE 2  (NE {i+1})'
    return 'NEW ── not in either table'


def find_result_ops(root, result, ops_list):
    rx, ry       = root   // 10, root   % 10
    result_x     = result // 10
    result_y     = result % 10

    findings = []

    xo = find_op(rx, result_x)
    yo = find_op(ry, result_y)
    xy, yx, sxy, syx = compute_variants(root, xo, yo)
    findings.append(dict(variant='xy',      x_op=xo, y_op=yo,
                         classification=classify_op(xo, yo, ops_list),
                         xy=xy, yx=yx, sign_xy=sxy, sign_yx=syx))

    xo = find_op(ry, result_y)
    yo = find_op(rx, result_x)
    xy, yx, sxy, syx = compute_variants(root, xo, yo)
    findings.append(dict(variant='yx',      x_op=xo, y_op=yo,
                         classification=classify_op(xo, yo, ops_list),
                         xy=xy, yx=yx, sign_xy=sxy, sign_yx=syx))

    xo = SIGN_FLIP[find_op(rx, result_x)]
    yo = SIGN_FLIP[find_op(ry, result_y)]
    xy, yx, sxy, syx = compute_variants(root, xo, yo)
    findings.append(dict(variant='sign+xy', x_op=xo, y_op=yo,
                         classification=classify_op(xo, yo, ops_list),
                         xy=xy, yx=yx, sign_xy=sxy, sign_yx=syx))

    xo = SIGN_FLIP[find_op(ry, result_y)]
    yo = SIGN_FLIP[find_op(rx, result_x)]
    xy, yx, sxy, syx = compute_variants(root, xo, yo)
    findings.append(dict(variant='sign+yx', x_op=xo, y_op=yo,
                         classification=classify_op(xo, yo, ops_list),
                         xy=xy, yx=yx, sign_xy=sxy, sign_yx=syx))

    return findings


def show_result_analysis(root, result, ops_list, scores=None, top4=None):
    """Print TABLE 1/TABLE 2 rows containing 'result', plus score/rank/signals."""
    rx, ry    = root // 10, root % 10
    col_names = ['xy', 'yx', 'sign+xy', 'sign+yx']

    def show_matching(table_label, row_label, table_ops):
        header_printed = False
        found_any      = False
        for i, (x_op, y_op) in enumerate(table_ops):
            xy, yx, sign_xy, sign_yx = compute_variants(root, x_op, y_op)
            hits = [col_names[j] for j, v in enumerate([xy, yx, sign_xy, sign_yx])
                    if v == result]
            if not hits:
                continue
            if not header_printed:
                print(f"  {table_label}:")
                print()
                print(f"  {row_label:>4}  {'Operation':<26}  {'xy':>4}  {'yx':>4}"
                      f"  {'sign+xy':>8}  {'sign+yx':>8}")
                sep()
                header_printed = True
                found_any      = True
            op_str  = f"x:{x_op:<10} y:{y_op}"
            hit_str = " / ".join(hits)
            print(f"  {i+1:>4}  {op_str:<26}  {xy:02d}    {yx:02d}"
                  f"    {sign_xy:02d}        {sign_yx:02d}   <-- {hit_str}")
        if header_printed:
            print()
        return found_any

    table2_ops = [(SIGN_FLIP[x], SIGN_FLIP[y]) for x, y in ops_list]

    sep('═')
    print(f"\n  RESULT = {result:02d}   ←   ROOT {root:02d}  (x={rx}, y={ry})\n")
    found1 = show_matching("TABLE 1", "Op#",  ops_list)
    found2 = show_matching("TABLE 2", "NE#",  table2_ops)
    if not found1 and not found2:
        print(f"  TYPE B NEW — {result:02d} not in TABLE 1 or TABLE 2\n")

    # Score + rank display
    if scores is not None:
        rscore = len(scores.get(result, []))
        rank   = next((i + 1 for i, (v, _, _) in enumerate(top4 or []) if v == result), None)
        if rank:
            rank_str = f"Rank #{rank} of {len(top4)}"
        else:
            all_vals = sorted(range(100), key=lambda v: len(scores.get(v, [])), reverse=True)
            full_rank = all_vals.index(result) + 1
            rank_str = f"Rank #{full_rank} of 100"
        print(f"  Score: {rscore}   {rank_str}")
        sig_labels = list(dict.fromkeys(sorted(scores.get(result, []))))
        if sig_labels:
            print(f"  Signals: {' | '.join(sig_labels[:8])}")
        else:
            print(f"  Signals: none — zero-signal result")
        # Digit-transform checks (display only — candidate patterns, not yet scored)
        rx_r, ry_r = result // 10, result % 10
        cut = lambda d: (d + 5) % 10
        transforms = {
            f"reverse":           (ry_r * 10 + rx_r),
            f"cut-tens":          (cut(rx_r) * 10 + ry_r),
            f"cut-units":         (rx_r * 10 + cut(ry_r)),
            f"cut-both":          (cut(rx_r) * 10 + cut(ry_r)),
            f"cb+rev":            (cut(ry_r) * 10 + cut(rx_r)),  # reverse then cut-both = cut(Y)*10+cut(X)
        }
        for label, variant in transforms.items():
            if variant != result:
                v_rank = next((i + 1 for i, (v, _, _) in enumerate(top4 or []) if v == variant), None)
                if v_rank:
                    print(f"  NOTE: {label}({result:02d}) = {variant:02d} was prediction #{v_rank}")
        # Pred-neighbor NOTE: result = prediction ± (1,1) on both digits
        for _dx, _dy in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
            _src = ((rx_r - _dx) % 10) * 10 + ((ry_r - _dy) % 10)
            _src_rank = next((i + 1 for i, (v, _, _) in enumerate(top4 or []) if v == _src), None)
            if _src_rank:
                print(f"  NOTE: pred-neighbor({result:02d}) ← #{_src_rank} pred={_src:02d} (variant: {_dx:+d},{_dy:+d})")
        print()

    sep('═')
    print()


def normalize_op(raw):
    """Normalize user-supplied operation string."""
    if raw is None:
        return None
    s = raw.strip().lower().replace(' ', '')
    if s in [o.replace(' ', '') for o in ALL_OPS]:
        for op in ALL_OPS:
            if s == op.replace(' ', '').lower():
                return op
    alias_key = raw.strip().lower()
    if alias_key in OP_ALIASES:
        return OP_ALIASES[alias_key]
    cleaned = raw.strip().lower().replace(' ', '')
    for op in ALL_OPS:
        if cleaned == op.lower():
            return op
    return None


# ── Prediction Helpers ────────────────────────────────────────────────────────

def pathan_obs1(root, x_op, y_op):
    """Pathan Obs 1 (confirmed D54): x→add_cut, y→rm_cut+flip; y_prime→rx, x_prime→ry."""
    rx, ry  = root // 10, root % 10
    x_prime = ADD_CUT.get(x_op, x_op)
    y_prime = REMOVE_CUT_FLIP.get(y_op, y_op)
    x_digit = apply_op(rx, y_prime)
    y_digit = apply_op(ry, x_prime)
    return x_digit * 10 + y_digit, x_prime, y_prime


def pathan_obs1b(root, x_op, y_op):
    """Pathan Obs 1B (confirmed D58): SWAPPED — y→add_cut, x→rm_cut+flip; y_prime→rx, x_prime→ry."""
    rx, ry  = root // 10, root % 10
    y_prime = ADD_CUT.get(y_op, y_op)
    x_prime = REMOVE_CUT_FLIP.get(x_op, x_op)
    x_digit = apply_op(rx, y_prime)
    y_digit = apply_op(ry, x_prime)
    return x_digit * 10 + y_digit, x_prime, y_prime


# ── Arriving-Op Transform Helpers (D59–D62 observations) ─────────────────────

_STRIP_CUT_MAP = {
    'cut': 'no_change', 'cut+1': '+1', 'cut-1': '-1',
    'cut+2': '+2',      'cut-2': '-2',
}

_PLAIN_STEP = {
    'no_change': '+1', '+1': '+2', '+2': '+2',
    '-1': '-2',        '-2': '-2',
}

_ADD_MODIFIER_STEP = {
    'no_change': 'cut',  'cut': 'cut+1',
    'cut+1': 'cut+2',   'cut+2': 'cut+2',
    'cut-1': 'cut',     'cut-2': 'cut-1',
    '+1': '+2',  '+2': '+2',  '-1': 'no_change',  '-2': '-1',
}


def arriving_transform_trigger(x_op, y_op):
    """Return 0-based index of triggered transform (0-3) or -1 if none match.
    Based on the STRUCTURAL type of each op, not specific strings.
    T1 (D59): y=plain-cut,  x=cut+modifier  → SWAP
    T2 (D60): x=no_change,  y=cut+modifier  → STEP-FWD
    T3 (D61): x=cut+modifier, y=no_change   → STRIP+FLIP
    T4 (D62): x=bare-signed, y=cut-any      → ADD-CUT+STEP"""
    nc_x      = x_op == 'no_change'
    nc_y      = y_op == 'no_change'
    cut_x_mod = 'cut' in x_op and x_op != 'cut'   # cut+1, cut-1, cut+2, cut-2
    cut_y_mod = 'cut' in y_op and y_op != 'cut'   # cut+1, cut-1, cut+2, cut-2
    bare_x    = x_op in ('+1', '-1', '+2', '-2')
    cut_y_any = 'cut' in y_op                     # cut, cut+1, cut-1, cut+2, cut-2

    if y_op == 'cut' and cut_x_mod:  return 0   # T1 SWAP
    if nc_x and cut_y_mod:           return 1   # T2 STEP-FWD (any cut+modifier on y)
    if cut_x_mod and nc_y:           return 2   # T3 STRIP+FLIP (any cut+modifier on x)
    if bare_x and cut_y_any:         return 3   # T4 ADD-CUT+STEP (any cut form on y)
    return -1


def arriving_transforms(root, x_op, y_op):
    """Four arriving-op transforms (D59–D62). Returns list of (name, new_x, new_y, pred_xy)."""
    def s(op):
        return _STRIP_CUT_MAP.get(op, op)

    results = []

    # T1 — SWAP (confirmed D59): y:cut→x:nc, x:cut+n→y:cut-base
    t1_x = 'no_change' if 'cut' in y_op else y_op
    t1_y = 'cut'       if 'cut' in x_op else x_op
    results.append(('T1-SWAP      (D59)', t1_x, t1_y, compute_variants(root, t1_x, t1_y)[0]))

    # T2 — STEP-FWD (confirmed D60): strip cut from both, step one further in same direction
    t2_x = _PLAIN_STEP.get(s(x_op), s(x_op))
    t2_y = _PLAIN_STEP.get(s(y_op), s(y_op))
    results.append(('T2-STEP-FWD  (D60)', t2_x, t2_y, compute_variants(root, t2_x, t2_y)[0]))

    # T3 — STRIP+FLIP (confirmed D61): strip cut, flip sign; y:nc→-1 special
    t3_x = SIGN_FLIP.get(s(x_op), s(x_op))
    t3_y = '-1' if y_op == 'no_change' else SIGN_FLIP.get(s(y_op), s(y_op))
    results.append(('T3-STRIP+FLIP (D61)', t3_x, t3_y, compute_variants(root, t3_x, t3_y)[0]))

    # T4 — ADD-CUT+STEP (confirmed D62): add cut to x, step modifier on y
    t4_x = ADD_CUT.get(x_op, x_op)
    t4_y = _ADD_MODIFIER_STEP.get(y_op, y_op)
    results.append(('T4-ADD+STEP  (D62)', t4_x, t4_y, compute_variants(root, t4_x, t4_y)[0]))

    return results


def find_root_positions(group_index, root):
    """Return (internal_pos_list, at_end). internal = all positions except last."""
    internal = [i + 1 for i, v in enumerate(group_index[:-1]) if v == root]
    at_end   = (group_index[-1] == root)
    return internal, at_end


def find_repeated_pairs(ops_list):
    """Return dict: (x_op,y_op) → list of 1-based occurrence indices (only pairs ≥2)."""
    seen = defaultdict(list)
    for i, pair in enumerate(ops_list):
        seen[pair].append(i + 1)
    return {k: v for k, v in seen.items() if len(v) > 1}


OP_ABBREV = {
    'no_change': 'nc',  'cut+1': 'c+1', 'cut-1': 'c-1',
    'cut+2':    'c+2',  'cut-2': 'c-2', 'cut':   'cut',
    '+1':       '+1',   '-1':    '-1',   '+2':    '+2',  '-2': '-2',
}


def show_chain_diagram(group_index, ops_list, root, internal_positions):
    """Print visual transition chain diagram with boxes and ==►► arrows."""
    PER_ROW = 5
    n       = len(ops_list)
    NODE    = 6   # ┌────┐ display width
    CONN    = 9   # connector width between boxes
    CELL    = NODE + CONN  # 15 chars per cell for label alignment

    internal_op_set = set(p - 1 for p in internal_positions)

    seen = defaultdict(list)
    for i, pair in enumerate(ops_list):
        seen[pair].append(i)
    repeat_op_set = set()
    for positions in seen.values():
        if len(positions) > 1:
            for p in positions[1:]:
                repeat_op_set.add(p)

    def ab(op):
        return OP_ABBREV.get(op, op)

    sep('═')
    print("\n  TRANSITION CHAIN DIAGRAM\n")

    for row_start in range(0, n, PER_ROW):
        row_end  = min(row_start + PER_ROW, n)
        top_line = '  '
        mid_line = '  '
        bot_line = '  '
        lbl_line = '  '

        for i in range(row_start, row_end):
            node_val          = group_index[i]
            x_op, y_op        = ops_list[i]
            xab, yab          = ab(x_op), ab(y_op)
            op_num            = i + 1

            top_line += '┌────┐'
            mid_line += f'│ {node_val:02d} │'
            bot_line += '└────┘'

            top_line += f'  x:{xab}'.ljust(CONN)
            mid_line += ' ==►► '.ljust(CONN)
            bot_line += f'  y:{yab}'.ljust(CONN)

            flags  = ''
            if i in internal_op_set:  flags += '◄KEY'
            if i in repeat_op_set:    flags += '★'
            if i == n - 1:            flags += 'LAST'
            lbl_line += f'[Op {op_num}]{flags}'.ljust(CELL)

        last_val  = group_index[row_end]
        top_line += '┌────┐'
        mid_line += f'│ {last_val:02d} │'
        bot_line += '└────┘'

        print(top_line)
        print(mid_line)
        print(bot_line)
        print(lbl_line)
        print()

    sep('═')
    print()


def show_last_rows_diagram(rows):
    """Print transition chain for the last 4 complete rows + trailing partial values."""
    # Separate trailing single-value rows (partial results) from complete rows
    split = len(rows)
    while split > 0 and len(rows[split - 1]) == 1:
        split -= 1
    last4_complete = rows[max(0, split - 4):split]
    trailing       = rows[split:]
    last3          = last4_complete + trailing   # combined display sequence

    sequence = []
    for row in last3:
        sequence.extend(row)

    if len(sequence) < 2:
        return

    trans_ops = []
    for i in range(len(sequence) - 1):
        a, b = sequence[i], sequence[i + 1]
        trans_ops.append((find_op(a // 10, b // 10), find_op(a % 10, b % 10)))

    # Mark transitions that cross row boundaries
    boundary_set = set()
    cumulative = 0
    for row in last3[:-1]:
        cumulative += len(row)
        boundary_set.add(cumulative - 1)

    PER_ROW = 5
    n       = len(trans_ops)
    CONN    = 9
    CELL    = 15

    base_idx = split - len(last4_complete)
    sep('═')
    print("\n  Last 4 rows of data grid:\n")
    for ri, row in enumerate(last3):
        rnum = base_idx + ri + 1
        print(f"  Row {rnum:>3}:  " + "   ".join(f"{v:02d}" for v in row))
    print()

    for row_start in range(0, n, PER_ROW):
        row_end  = min(row_start + PER_ROW, n)
        top_line = '  '
        mid_line = '  '
        bot_line = '  '
        lbl_line = '  '

        for i in range(row_start, row_end):
            node_val   = sequence[i]
            x_op, y_op = trans_ops[i]
            xab        = OP_ABBREV.get(x_op, x_op)
            yab        = OP_ABBREV.get(y_op, y_op)

            top_line += '┌────┐'
            mid_line += f'│ {node_val:02d} │'
            bot_line += '└────┘'

            top_line += f'  x:{xab}'.ljust(CONN)
            mid_line += ' ==►► '.ljust(CONN)
            bot_line += f'  y:{yab}'.ljust(CONN)

            marker    = '│' if i in boundary_set else ''
            lbl_line += f'[T{i+1}]{marker}'.ljust(CELL)

        last_val  = sequence[row_end]
        top_line += '┌────┐'
        mid_line += f'│ {last_val:02d} │'
        bot_line += '└────┘'

        print(top_line)
        print(mid_line)
        print(bot_line)
        print(lbl_line)
        print()

    sep('═')
    print()


def build_strong_predictions(root, ops_list, group_index, endpoint=None, rows=None):
    """Score every candidate value across all known signals; return top 8 unique."""
    scores = defaultdict(list)   # value → [reason_label, ...]

    arr_op = ops_list[-1]
    n      = len(ops_list)

    # Signal 1 — Pathan Obs 1: arrival-transform (confirmed D54, weight 3)
    pred_b,  _, _ = pathan_obs1 (root, arr_op[0], arr_op[1])
    pred_b2, _, _ = pathan_obs1b(root, arr_op[0], arr_op[1])
    for _ in range(3):
        scores[pred_b].append("Obs1 arrival-transform")
    for _ in range(3):
        scores[pred_b2].append("Obs1B arrival-transform-swapped")

    # Signal 2 — Root in array: depart xy (internal) or arrive yx (end-only, weight 2)
    internal_pos, _ = find_root_positions(group_index, root)
    if internal_pos:
        dep_op        = ops_list[internal_pos[0] - 1]
        xy, yx, s, t  = compute_variants(root, *dep_op)
        for _ in range(3): scores[xy].append("Root-internal depart xy")
        for _ in range(2): scores[yx].append("Root-internal depart yx")   # elevated 1→2
        scores[s].append("Root-internal depart sign+xy")
        scores[t].append("Root-internal depart sign+yx")
    else:
        xy, yx, s, t  = compute_variants(root, *arr_op)
        for _ in range(3): scores[yx].append("Root end-only arrive yx")
        for _ in range(4): scores[xy].append("Root end-only arrive xy")
        scores[s].append("Root end-only arrive sign+xy")
        scores[t].append("Root end-only arrive sign+yx")

    # Signal 3 — Arriving-op NE sign-flip (D56 confirmed); fxy=2, fyx=1
    flip_op      = (SIGN_FLIP[arr_op[0]], SIGN_FLIP[arr_op[1]])
    fxy, fyx, fs, ft = compute_variants(root, *flip_op)
    for _ in range(2): scores[fxy].append("Arriving NE-flip xy")
    scores[fyx].append("Arriving NE-flip yx")

    # Signal 4 — Repeated op pairs: 2nd occurrence; xy=2, yx=1, sign+xy=1, sign+yx=1
    repeats = find_repeated_pairs(ops_list)
    for (xop, yop), positions in repeats.items():
        xy2, yx2, s2, t2 = compute_variants(root, xop, yop)
        lbl = f"repeat-pair Ops{positions}"
        for _ in range(2): scores[xy2].append(lbl + " xy")
        scores[yx2].append(lbl + " yx")
        scores[s2].append(lbl + " sign+xy")
        scores[t2].append(lbl + " sign+yx")

    # Signal 5 — Op 1 xy: historically most frequent TABLE winner (weight 2)
    xy1, yx1, s1, t1 = compute_variants(root, *ops_list[0])
    for _ in range(2): scores[xy1].append("Op1 first-transition xy")
    scores[yx1].append("Op1 yx")
    scores[s1].append("Op1 sign+xy")
    scores[t1].append("Op1 sign+yx")

    # Signal 6 — Last transition all 4 variants (weight 1 each)
    xyl, yxl, sl, tl = compute_variants(root, *arr_op)
    scores[xyl].append("Last-op xy")
    scores[yxl].append("Last-op yx")
    scores[sl].append("Last-op sign+xy")
    scores[tl].append("Last-op sign+yx")

    # Signal 6b — Pre-arriving-1 (Op N-1): D95+D96 confirmed; xy=8, yx=3, sign+xy=1
    # xy boosted 3→8 (after D148): pre-arriving xy can't get NearMiss/ChainMiss (its NE op
    # IS the pre-arriving op, in-chain), while yx mirror gets NE-adjacent benefit. Same
    # structural fix as Signal 2 end-only xy boost after D147.
    if n >= 2:
        pre1_op = ops_list[-2]
        pxy, pyx, ps, pt = compute_variants(root, *pre1_op)
        for _ in range(5): scores[pxy].append("Pre-arriving-1 xy")
        for _ in range(3): scores[pyx].append("Pre-arriving-1 yx")
        scores[ps].append("Pre-arriving-1 sign+xy")
        scores[pt].append("Pre-arriving-1 sign+yx")

    # Signal 6c — Pre-arriving-2 (Op N-2): xy raised 1→4 after D259=48 confirmed blind spot
    # Same structural fix as pre-arr-1 raise (D148); pre-arr-2 can't get ChainMiss (op IS in chain)
    if n >= 3:
        pre2_op = ops_list[-3]
        p2xy, p2yx, p2s, p2t = compute_variants(root, *pre2_op)
        for _ in range(4): scores[p2xy].append("Pre-arriving-2 xy")
        scores[p2s].append("Pre-arriving-2 sign+xy")
        scores[p2t].append("Pre-arriving-2 sign+yx")

    # Signal 7 — Pathan Obs 2: arriving op appears elsewhere → prev-transition (weight 2/1/1/1)
    obs2_hits = [i + 1 for i, p in enumerate(ops_list[:-1]) if p == arr_op]
    for hit in obs2_hits:
        if hit > 1:
            prev_op = ops_list[hit - 2]
            px, py, ps, pt = compute_variants(root, *prev_op)
            for _ in range(2): scores[px].append(f"Obs2 prev-of-Op{hit} xy")
            scores[py].append(f"Obs2 prev-of-Op{hit} yx")
            scores[ps].append(f"Obs2 prev-of-Op{hit} sign+xy")
            scores[pt].append(f"Obs2 prev-of-Op{hit} sign+yx")

    # Signal 8 — Op 1 sign+yx (second historically strong variant, weight 1)
    scores[t1].append("Op1 sign+yx-extra")

    # Signal 9 — Obs3: ops where source x-digit = rx (scored xy=1 and yx=1 per match, excl root-depart)
    rx = root // 10
    ry = root % 10
    root_dep_idx = (internal_pos[0] - 1) if internal_pos else -1
    for i, val in enumerate(group_index[:-1]):
        if val // 10 == rx:
            o3op = ops_list[i]
            o3xy, o3yx, o3s, o3t = compute_variants(root, *o3op)
            scores[o3xy].append(f"Obs3-Op{i+1} xy")
            if i != root_dep_idx and i != n - 1:   # root-depart → Signal 2; arriving → Signal 1
                scores[o3yx].append(f"Obs3-Op{i+1} yx")

    # Signal 9C — DoubleObs3-ry: source BOTH digits = ry → DigRes already scores xy+2 and yx+2.
    #   D108: winner was sign+yx; D159: winner was xy. Boost BOTH symmetrically (+1 each).
    for i, val in enumerate(group_index[:-1]):
        if val // 10 == ry and val % 10 == ry:   # src = (ry, ry)
            if i == root_dep_idx or i == n - 1:
                continue
            dc_op = ops_list[i]
            dcxy, _, _, dcsyx = compute_variants(root, *dc_op)
            scores[dcxy].append(f"DoubleObs3-ry-Op{i+1} xy")
            scores[dcsyx].append(f"DoubleObs3-ry-Op{i+1} syx")

    # Signal 9B — Digit Resonance: src/dest digit alignment with rx, ry
    # When source or destination digits match root digits, specific variants are mathematically determined.
    # Full match (weight 2): dest=Root→sign+xy=SRC exactly; src=SwapRoot→yx=rev(dest); dest=SwapRoot→sign+yx=rev(src)
    # Partial match (weight 1): one digit of result is determined from the src/dest digit match
    for i, src_val in enumerate(group_index[:-1]):
        dst_val = group_index[i + 1]
        sx, sy  = src_val // 10, src_val % 10
        dx, dy  = dst_val // 10, dst_val % 10
        op_dr   = ops_list[i]
        is_arr  = (i == n - 1)               # arriving op — covered by Obs1 + pre-arriving
        is_rs   = (sx == rx and sy == ry)    # root src — covered by Root-Internal-Departure
        if is_rs or is_arr:
            continue
        drxy, dryx, drsxy, drsyx = compute_variants(root, *op_dr)
        is_rd   = (dx == rx and dy == ry)    # dest = root (internal arrival)
        is_ss   = (sx == ry and sy == rx)    # src = swapped root
        is_sd   = (dx == ry and dy == rx)    # dest = swapped root
        ldr     = f"DigRes-Op{i+1}"
        # Full matches (weight 2)
        if is_rd:
            for _ in range(2): scores[drsxy].append(f"{ldr} dest=Root→sxy={src_val:02d}")
        if is_ss:
            for _ in range(2): scores[dryx].append(f"{ldr} src=SwapRoot→yx={dryx:02d}")
        if is_sd:
            for _ in range(2): scores[drsyx].append(f"{ldr} dest=SwapRoot→syx={drsyx:02d}")
        # Partial source matches (weight 2 — training D106+D108: source digit→digit gives yx winner)
        if sy == ry:                          # src_y=ry → xy_y=dest_y
            for _ in range(2): scores[drxy].append(f"{ldr} src_y=ry→xy")
        if sx == ry and not is_ss:           # src_x=ry → yx_y=dest_x
            for _ in range(2): scores[dryx].append(f"{ldr} src_x=ry→yx")
        if sy == rx and not is_ss:           # src_y=rx → yx_x=dest_y
            for _ in range(2): scores[dryx].append(f"{ldr} src_y=rx→yx")
        # Partial dest matches (weight 1, skip when full match already scored same slot)
        if dx == rx and not is_rd:           # dest_x=rx → sign+xy_x=src_x
            scores[drsxy].append(f"{ldr} dest_x=rx→sxy")
        if dy == ry and not is_rd:           # dest_y=ry → sign+xy_y=src_y
            scores[drsxy].append(f"{ldr} dest_y=ry→sxy")
        if dx == ry and not is_sd:           # dest_x=ry → sign+yx_y=src_x
            scores[drsyx].append(f"{ldr} dest_x=ry→syx")
        if dy == rx and not is_sd:           # dest_y=rx → sign+yx_x=src_y
            scores[drsyx].append(f"{ldr} dest_y=rx→syx")

    # Signal 10 — Arriving-op transforms T1–T4 (D59–D62 confirmed)
    # Triggered: weight 3; others: weight 1; also score yx variant (weight 1)
    triggered_idx = arriving_transform_trigger(arr_op[0], arr_op[1])
    for idx, (t_name, t_x, t_y, t_val) in enumerate(arriving_transforms(root, arr_op[0], arr_op[1])):
        short  = t_name.split()[0]
        weight = 3 if idx == triggered_idx else 1
        for _ in range(weight):
            scores[t_val].append(f"Arriving-{short}")
        _, t_yx, _, _ = compute_variants(root, t_x, t_y)   # yx variant (weight 1)
        scores[t_yx].append(f"Arriving-{short}-yx")

    # ── New signals from observed rules (added additively, no existing signal changed) ──

    # Signal 11 — Rule 3 ext: score the NEXT transition op after each Obs3 match (weight 1)
    for i, val in enumerate(group_index[:-1]):
        if val // 10 == rx and i != root_dep_idx and i != n - 1:
            if i + 1 < n:
                nxt_op = ops_list[i + 1]
                nx_xy, nx_yx, _, _ = compute_variants(root, *nxt_op)
                scores[nx_xy].append(f"Obs3Next-Op{i+2} xy")
                scores[nx_yx].append(f"Obs3Next-Op{i+2} yx")

    # Signal 12 — Rule 4: root op appears 2+ times in chain → next op after last = candidate (weight 3 xy, 2 yx)
    root_nm_op = ops_list[root_dep_idx] if root_dep_idx >= 0 else ops_list[-1]
    root_repeat_pos = [i for i, op in enumerate(ops_list) if op == root_nm_op]
    if len(root_repeat_pos) >= 2:
        last_rp = root_repeat_pos[-1]
        if last_rp + 1 < n:
            rr_op = ops_list[last_rp + 1]
            rr_xy, rr_yx, _, _ = compute_variants(root, *rr_op)
            for _ in range(3): scores[rr_xy].append("RootOpRepeat-next xy")
            for _ in range(2): scores[rr_yx].append("RootOpRepeat-next yx")

    # Signal 13 — Rule 6: variants of root op NOT in chain = TYPE B NEW candidates
    # 1D: vary only x OR only y OR swap; weight 2 xy / 1 yx
    # 2D: cross-transform (strip-cut + step, etc.); weight 1 xy only
    ops_set = set(ops_list)
    rnx, rny = root_nm_op
    nm_1d = set()
    for xv in ALL_OPS:
        nm_1d.add((xv, rny))
    for yv in ALL_OPS:
        nm_1d.add((rnx, yv))
    nm_1d.add((rny, rnx))
    nm_1d.discard((rnx, rny))
    for (vx, vy) in nm_1d:
        if (vx, vy) not in ops_set:
            vxy, vyx, _, _ = compute_variants(root, vx, vy)
            for _ in range(2): scores[vxy].append("NearMiss-1D xy")
            scores[vyx].append("NearMiss-1D yx")
    # 2D cross-transforms: apply one semantic transform to each dim independently
    _tx = lambda op: {SIGN_FLIP[op], ADD_CUT[op], REMOVE_CUT[op],
                       STEP_UP[op], STEP_DOWN[op], STRIP_MODIFIER[op]}
    for xv in _tx(rnx):
        for yv in _tx(rny):
            if (xv, yv) == (rnx, rny): continue
            if (xv, rny) in nm_1d or (rnx, yv) in nm_1d: continue  # skip if already 1D
            if (xv, yv) not in ops_set:
                vxy, _, _, _ = compute_variants(root, xv, yv)
                scores[vxy].append("NearMiss-2D xy")

    # Signal 14 — Rule 8: EP itself sometimes comes as result (weight 1)
    if endpoint is not None:
        scores[endpoint].append("EP-as-result")

    # ── Additional signals from D1–D113 backtesting analysis ────────────────

    # Signal 15 — Root value itself sometimes = result (D67 confirmed: op nc,nc absent)
    scores[root].append("Root-as-result")

    # Signal 16 — First group_index element (A1) sometimes = result (D94 confirmed)
    if len(group_index) > 1:
        scores[group_index[0]].append("GroupIndex-A1")

    # Signal 17 — Op1 sign+xy extra (D55: Op1 sign+xy=33 matched result; mirrors Signal 8 sign+yx)
    first_op = ops_list[0]
    _, _, sxy1_extra, _ = compute_variants(root, *first_op)
    scores[sxy1_extra].append("Op1-sign+xy-extra")

    # Signal 18 — Root-op CLOSE VARIANTS in chain (complement to Signal 13 which targets NOT-in-chain)
    # 1D modifications of root op that ARE already in chain get scored — they're "close" to root op
    # This catches cases like D111 where winning op = STEP_DOWN of arrive op (exists in chain)
    for (vx, vy) in nm_1d:
        if (vx, vy) in ops_set:    # IN chain (opposite of Signal 13)
            cxy, cyx, _, _ = compute_variants(root, vx, vy)
            scores[cxy].append("RootOpClose-1D-inchain xy")
            scores[cyx].append("RootOpClose-1D-inchain yx")

    # Signal 19 — Arriving op appearing elsewhere in chain → NEXT op (Rule 4 arrive version)
    # Obs2 (Signal 7) scores PREVIOUS op; this scores the NEXT op after the match
    arr_match_elsewhere = [i for i, op in enumerate(ops_list[:-1]) if op == arr_op]
    if arr_match_elsewhere:
        last_ae = arr_match_elsewhere[-1]
        if last_ae + 1 < n:
            ae_next = ops_list[last_ae + 1]
            ae_xy, ae_yx, _, _ = compute_variants(root, *ae_next)
            for _ in range(2): scores[ae_xy].append("ArrOp-elsewhere-next xy")
            scores[ae_yx].append("ArrOp-elsewhere-next yx")

    # Signal 20 — Every chain-op 1D near-miss (D114: result 22 caught by 5 ops pointing here)
    # For each op in chain, apply each transform to x alone or y alone;
    # if the resulting op is NOT in the chain, score its xy result +2 per source (weight 2 like NearMiss-1D).
    # Multiple chain ops pointing to the same missing op accumulate score naturally (convergence).
    # Signal 30 — ChainMiss-yx: also score the yx of each missing op at weight=1 per source.
    # Fixes the yx blind spot identified from D246-D257 consecutive misses (yx/sign+yx cells get zero ChainMiss).
    chain_op_set_miss = set(ops_list)
    _all_transforms = (SIGN_FLIP, ADD_CUT, REMOVE_CUT, STEP_UP, STEP_DOWN, STRIP_MODIFIER)
    for (ox, oy) in ops_list:
        for tx in {t[ox] for t in _all_transforms}:
            if tx != ox and (tx, oy) not in chain_op_set_miss:
                vxy, vyx, _, _ = compute_variants(root, tx, oy)
                scores[vxy].append("ChainMiss-x1D")
                scores[vxy].append("ChainMiss-x1D")
                scores[vyx].append("ChainMiss-x1D-yx")   # Signal 30
        for ty in {t[oy] for t in _all_transforms}:
            if ty != oy and (ox, ty) not in chain_op_set_miss:
                vxy, vyx, _, _ = compute_variants(root, ox, ty)
                scores[vxy].append("ChainMiss-y1D")
                scores[vxy].append("ChainMiss-y1D")
                scores[vyx].append("ChainMiss-y1D-yx")   # Signal 30

    # Signal 21 — Rule 9: Direct-cut Root → find direct-cut nodes in chain, sign-flip BOTH x and y (xy=3, yx=2)
    if (rx + 5) % 10 == ry:
        r9_seen = set()
        for i, node in enumerate(group_index[:-1]):
            if node == root:
                continue
            nx, ny = node // 10, node % 10
            if (nx + 5) % 10 == ny:
                ox, oy = ops_list[i]
                r9_x, r9_y = SIGN_FLIP[ox], SIGN_FLIP[oy]
                if (r9_x, r9_y) not in r9_seen:
                    r9_seen.add((r9_x, r9_y))
                    r9xy, r9yx, _, _ = compute_variants(root, r9_x, r9_y)
                    for _ in range(5): scores[r9xy].append(f"Rule9-node{node:02d} xy")
                    for _ in range(4): scores[r9yx].append(f"Rule9-node{node:02d} yx")

    # Signal 22 — Rule 10: Double Root → find other double nodes in chain, sign-flip x + reduce-flip y (xy=8, yx=4)
    if rx == ry:
        r10_seen = set()
        for i, node in enumerate(group_index[:-1]):
            if node == root:
                continue
            nx, ny = node // 10, node % 10
            if nx == ny:
                ox, oy = ops_list[i]
                r10_x = SIGN_FLIP[ox]
                r10_y = RULE10_Y_TRANSFORM[oy]
                if (r10_x, r10_y) not in r10_seen:
                    r10_seen.add((r10_x, r10_y))
                    r10xy, r10yx, _, _ = compute_variants(root, r10_x, r10_y)
                    for _ in range(5): scores[r10xy].append(f"Rule10-node{node:02d} xy")
                    for _ in range(4): scores[r10yx].append(f"Rule10-node{node:02d} yx")

    # Signal 23 — Rule 11: Find cut(rx)*10+cut(ry) in chain, SIGN_FLIP x-op, keep y-op (xy=8, yx=4)
    rx_cut = (rx + 5) % 10
    ry_cut = (ry + 5) % 10
    cut_node = rx_cut * 10 + ry_cut
    r11_seen = set()
    for i, node in enumerate(group_index[:-1]):
        if node == cut_node:
            ox, oy = ops_list[i]
            r11_x = SIGN_FLIP[ox]
            r11_y = oy
            if (r11_x, r11_y) not in r11_seen:
                r11_seen.add((r11_x, r11_y))
                r11xy, r11yx, _, _ = compute_variants(root, r11_x, r11_y)
                for _ in range(5): scores[r11xy].append(f"Rule11-node{cut_node:02d} xy")
                for _ in range(4): scores[r11yx].append(f"Rule11-node{cut_node:02d} yx")

    # Signal 24 — Table-Proximity ±1/±2 (for TYPE B NEW / missing results)
    # Build unique TABLE 1 + TABLE 2 value set (= 10-C-T).
    # For each UNIQUE table value V, score neighbors V±1 and V±2 with weight 1
    # (only if the neighbor is NOT in the table — targeting missing-set values).
    # Per-unique-value (not per cell occurrence) keeps scores conservative.
    _tprox_vals_raw = []
    for (ox, oy) in ops_list:
        _tprox_vals_raw.extend(compute_variants(root, ox, oy))
        sfx, sfy = SIGN_FLIP[ox], SIGN_FLIP[oy]
        _tprox_vals_raw.extend(compute_variants(root, sfx, sfy))
    _tprox_set = set(_tprox_vals_raw)
    for v in _tprox_set:           # unique values only
        for delta in (-2, -1, 1, 2):
            nb = (v + delta) % 100
            if nb not in _tprox_set:
                scores[nb].append(f"TableProx±{abs(delta)}")

    # Signal 25 — Prediction-Neighbor (result ≈ prediction ± (1,1) on both digits)
    # Two-pass: preliminary rank → find top-16 → boost each digit-neighbor per source (accumulative, weight=3)
    # Accumulative: 3 separate predictions converging on same neighbor give +9 (stronger evidence).
    # D234: 00 ← #4=99, #8=19, #14=11 (3 sources → +9 → HIT); unique gave only +3.
    # Confirmed: D222(#11→14), D223(#12→22), D231(#14→61), D233(#6→86), D234(×3→00) — 4+, scored
    _pn_prelim = sorted(scores.items(), key=lambda kv: (len(kv[1]), -kv[0]), reverse=True)
    _pn_top16 = []
    _pn_seen = set()
    for _pnv, _ in _pn_prelim:
        if _pnv not in _pn_seen:
            _pn_top16.append(_pnv)
            _pn_seen.add(_pnv)
        if len(_pn_top16) == 30:
            break
    for _p in _pn_top16:
        _px, _py = _p // 10, _p % 10
        for _dx, _dy in ((1, -1), (1, 1), (-1, 1), (-1, -1)):
            _nb = ((_px + _dx) % 10) * 10 + ((_py + _dy) % 10)
            if _nb != _p:
                for _ in range(3): scores[_nb].append("PredNeighbor")

    # Signal 26 — Cut-Both (result = cut(X)*10+cut(Y) for a top-16 prediction XY)
    # Two-pass AFTER Signal 25: re-rank so PredNeighbor-boosted values (like 19) are included.
    # Accumulative weight=7 per source — matches Rule9/11; cut-both is single-source structural.
    # D236: 64 = cut-both(#1=19); 19 gets PredNeighbor boost → enters cb_top16 → 64 gets +7 → HIT.
    # Confirmed: D217(#15=39→84), D227(#9=17→62), D232(#10=42→97), D236(#1=19→64) — 4, now scored
    _cb_prelim = sorted(scores.items(), key=lambda kv: (len(kv[1]), -kv[0]), reverse=True)
    _cb_top16 = []
    _cb_seen = set()
    for _cbv, _ in _cb_prelim:
        if _cbv not in _cb_seen:
            _cb_top16.append(_cbv)
            _cb_seen.add(_cbv)
        if len(_cb_top16) == 30:
            break
    for _p in _cb_top16:
        _px2, _py2 = _p // 10, _p % 10
        _cbt = ((_px2 + 5) % 10) * 10 + ((_py2 + 5) % 10)
        if _cbt != _p:
            for _ in range(7): scores[_cbt].append("CutBoth")

    # Signal 27 — CbRev (result = cut(Y)*10+cut(X) for a top-16 prediction XY)
    # Two-pass, same _cb_top16 (post-Signal-25). Formula: swap digits then cut both.
    # Confirmed: D224(#2=80→53), D226(#8=93→84), D235(#1=91→64), D242(#1=20→57) — 4, now scored
    for _p in _cb_top16:
        _px2, _py2 = _p // 10, _p % 10
        _cbr = ((_py2 + 5) % 10) * 10 + ((_px2 + 5) % 10)
        if _cbr != _p:
            for _ in range(7): scores[_cbr].append("CbRev")

    # Signal 28 — Reverse (result = Y*10+X for a top-16 prediction XY)
    # Two-pass, same _cb_top16 (post-Signal-25). Simple digit swap.
    # Confirmed: D218(#?=60→06), D219(#?=95→59), D226(#?=48→84), D242(#7=75→57) — 4, now scored
    for _p in _cb_top16:
        _px2, _py2 = _p // 10, _p % 10
        _rev = _py2 * 10 + _px2
        if _rev != _p:
            for _ in range(5): scores[_rev].append("Reverse")

    # Signal 29 — CutUnits (result = X*10+cut(Y) for a top-16 prediction XY)
    # Two-pass, same _cb_top16 (post-Signal-25). Cuts only the units digit.
    # Confirmed: D229, D236, D237, D244(#16=86→81) — 4, now scored
    for _p in _cb_top16:
        _px2, _py2 = _p // 10, _p % 10
        _cut_u = _px2 * 10 + ((_py2 + 5) % 10)
        if _cut_u != _p:
            for _ in range(5): scores[_cut_u].append("CutUnits")

    # Signal 35 — CutTens (result = cut(X)*10+Y for a top-30 prediction XY)
    # Two-pass, same _cb_top16. Cuts only the TENS digit.
    # Confirmed: D219(#?=09→59), D220(#?=63→13), D237(#1=62→12) — 3+ cases
    for _p in _cb_top16:
        _px2, _py2 = _p // 10, _p % 10
        _cut_t = ((_px2 + 5) % 10) * 10 + _py2
        if _cut_t != _p:
            for _ in range(5): scores[_cut_t].append("CutTens")

    # Signal 31 — Column-Frequency: boost values that historically appear often in this column.
    # Universal signal: orthogonal to chain signals, covers TYPE-B-NEW cases (~50% of results).
    # Weight: 3 for top-10 by column frequency, 2 for 11-20, 1 for 21-30.
    if rows:
        _col_idx = len(rows[-1])  # 0-indexed position of the prediction in its row
        if _col_idx >= 7:
            _col_idx = 0
        _col_freq = {}
        for _row in rows[:-1]:
            if len(_row) == 7 and _col_idx < 7:
                v = _row[_col_idx]
                _col_freq[v] = _col_freq.get(v, 0) + 1
        _sorted_col = sorted(_col_freq.keys(), key=lambda v: -_col_freq[v])
        for _rank_i, _v in enumerate(_sorted_col):
            if _rank_i < 10:
                for _ in range(3): scores[_v].append("ColFreq-top10")
            elif _rank_i < 20:
                for _ in range(2): scores[_v].append("ColFreq-top20")
            elif _rank_i < 30:
                scores[_v].append("ColFreq-top30")
            else:
                break

    # Signal 34 — DataFreq: full-dataset value frequency as independent prior.
    # Orthogonal to chain structure — values that appear often in the dataset overall
    # are statistically more likely to appear again. Covers zero-signal TABLE and TYPE B NEW.
    # Weight: 4 for top-10, 3 for 11-20, 2 for 21-30 (higher than ColFreq — dataset-wide).
    if rows:
        _df_flat = [v for _row in rows for v in _row if v >= 0]
        _df_freq = {}
        for _v in _df_flat:
            _df_freq[_v] = _df_freq.get(_v, 0) + 1
        _df_sorted = sorted(_df_freq.keys(), key=lambda v: -_df_freq[v])
        for _ri, _dv in enumerate(_df_sorted):
            if _ri < 10:
                for _ in range(4): scores[_dv].append("DataFreq-top10")
            elif _ri < 20:
                for _ in range(3): scores[_dv].append("DataFreq-top20")
            elif _ri < 30:
                for _ in range(2): scores[_dv].append("DataFreq-top30")
            else:
                break

    # Signal 32 — AllChainBase: base weight for all mid-chain op variants not already scored.
    # Covers positions 1 to n-4 (excludes Op1/pre-arr-2/pre-arr-1/arriving already scored).
    # Weight: xy=yx=min(k+1,3), sign_xy=sign_yx=k (k = occurrences in mid-chain slice).
    # Addresses systematic zero-scoring of mid-chain TABLE 1/2 values.
    if n >= 5:
        _mid_ops = ops_list[1:-3]  # positions 1..n-4; pre-arr-2/-1/arriving excluded by slice
        _mid_counts = {}
        for _op in _mid_ops:
            _mid_counts[_op] = _mid_counts.get(_op, 0) + 1
        for _op, _k in _mid_counts.items():
            _w = min(_k + 1, 3)
            _cxy, _cyx, _csxy, _csyx = compute_variants(root, *_op)
            for _ in range(_w): scores[_cxy].append("AllChainBase-xy")
            for _ in range(_w): scores[_cyx].append("AllChainBase-yx")
            for _ in range(_k): scores[_csxy].append("AllChainBase-sxy")
            for _ in range(_k): scores[_csyx].append("AllChainBase-syx")

    # Signal 33 — CompOp: cross-component pairs where ox∈chain x-ops AND oy∈chain y-ops
    # but (ox,oy) absent from chain. Scores only missing-set values (not in 10-C-T).
    # Targets the TYPE B NEW blind spot: results from "component-mixed" ops where
    # 1D-adjacency (ChainMiss) never fires because there is no 1D bridge op in chain.
    # Weight: 4 per source for xy/yx, 3 for sign variants.
    _comp_x_ops = set(op[0] for op in ops_list)
    _comp_y_ops = set(op[1] for op in ops_list)
    _comp_chain_set = set(ops_list)
    for _cox in _comp_x_ops:
        for _coy in _comp_y_ops:
            if (_cox, _coy) not in _comp_chain_set:
                _cpxy, _cpyx, _cpsxy, _cpsyx = compute_variants(root, _cox, _coy)
                for _cv, _wt, _lbl in ((_cpxy, 4, "CompOp-xy"), (_cpyx, 4, "CompOp-yx"),
                                        (_cpsxy, 3, "CompOp-sxy"), (_cpsyx, 3, "CompOp-syx")):
                    if _cv not in _tprox_set:
                        for _ in range(_wt):
                            scores[_cv].append(_lbl)

    # Ablation study (2026-07-01, backtest over D273-D329, 57 rounds): the digit-transform
    # family (CutBoth/CbRev/Reverse/CutUnits/CutTens/PredNeighbor) and TableProx were each
    # added after only 3-4 anecdotal "confirmed" matches. Measured effect: baseline (all
    # signals) hit rate 21.1% (12/57); removing this group alone → 33.3% (19/57); removing
    # it together with TableProx → 36.8% (21/57), the best config tested and the first to
    # clear the 30% random-chance baseline for a top-30-of-100 pick. These signals were
    # inflating the score floor for coincidental digit-transform matches without adding real
    # predictive power, systematically crowding out lower-scored but correct candidates.
    # Filtered here (not deleted) so the effect is reversible — see feedback_script_changes.md.
    #
    # Second ablation study (2026-07-01, backtest over D341-D446, 106 rounds — the dataset
    # reset since the first study invalidated its D273-D330 sample): re-ran the same
    # methodology against the CURRENT continuous dataset. Baseline (all remaining signals)
    # hit rate had drifted to 25.5% (27/106), BELOW the 30% random-chance floor. Removing
    # CompOp (all 4 variants together — no single variant alone showed the effect) →
    # 33.0% (35/106); removing CompOp + Obs1/Obs1B together → 34.9% (37/106), the best
    # config tested. All other signal families tested individually were neutral (0 rounds
    # changed) or net-negative to remove (ChainMiss, NearMiss-1D, Rule11, repeat-pair,
    # DataFreq, ColFreq all hurt when removed) — left untouched. See ablation.py for the
    # full per-family breakdown and feedback_script_changes.md for the write-up.
    _ablated_prefixes = ('CutBoth', 'CbRev', 'Reverse', 'CutUnits', 'CutTens', 'PredNeighbor', 'TableProx',
                         'CompOp-xy', 'CompOp-yx', 'CompOp-sxy', 'CompOp-syx', 'Obs1', 'Obs1B')
    for _av in list(scores.keys()):
        _kept = [r for r in scores[_av] if not any(r.startswith(p) for p in _ablated_prefixes)]
        if _kept:
            scores[_av] = _kept
        else:
            del scores[_av]

    # Rank: sort by total weight — guarantee at least 5 TYPE B NEW (missing-set) slots in top-30.
    # TYPE B NEW values score below the natural floor; forced slots ensure consistent coverage.
    _missing_set_final = set(range(100)) - _tprox_set
    ranked = sorted(scores.items(), key=lambda kv: (len(kv[1]), -kv[0]), reverse=True)
    top4   = []
    seen   = set()
    for val, reasons in ranked:
        if val not in seen:
            unique_reasons = list(dict.fromkeys(r.split()[0] + ' ' + ' '.join(r.split()[1:])
                                                 for r in sorted(reasons)))
            top4.append((val, len(reasons), unique_reasons))
            seen.add(val)
        if len(top4) == 30:
            break
    # Force at least 10 missing-set (TYPE B NEW) candidates into top-30.
    # Split: top-7 by score (CompOp/ChainMiss/DataFreq) + up to 3 range-sampled zero-signal
    # values (one from each 33-value range). Covers component-absent TYPE B NEW blind spot.
    _miss_in_top = sum(1 for v, _, _ in top4 if v in _missing_set_final)
    _needed_miss = max(0, 10 - _miss_in_top)
    if _needed_miss > 0:
        _scored_miss = sorted(
            ((v, len(sc), list(dict.fromkeys(sc)))
             for v, sc in scores.items()
             if v in _missing_set_final and v not in seen),
            key=lambda x: (x[1], -x[0]), reverse=True
        )[:7]
        # Zero-signal range sampling: one unseen missing value from each 33-value range
        _ranges = [(0, 33), (33, 67), (67, 100)]
        _zero_picks = []
        for _lo, _hi in _ranges:
            for _zv in range(_lo, _hi):
                if _zv in _missing_set_final and _zv not in seen and _zv not in scores:
                    _zero_picks.append(_zv)
                    break
        _all_force = []
        _force_seen = set()
        for _mv, _ms, _mr in _scored_miss:
            if _mv not in _force_seen:
                _all_force.append((_mv, _ms, _mr + ["TypeBNEW"]))
                _force_seen.add(_mv)
        for _zv in _zero_picks:
            if _zv not in _force_seen and len(_all_force) < _needed_miss:
                _all_force.append((_zv, 0, ["TypeBNEW-RangeCover"]))
                _force_seen.add(_zv)
        _actual_force = _all_force[:_needed_miss]
        top4 = top4[:30 - len(_actual_force)]
        for _mv, _ms, _mr in _actual_force:
            top4.append((_mv, _ms, _mr))
            seen.add(_mv)
    return top4, scores


def show_prediction(endpoint, root, ops_list, group_index, rows=None):
    """Print full PREDICTION ANALYSIS before TABLE 1 and TABLE 2."""
    rx, ry   = root // 10, root % 10
    ep_x, ep_y = endpoint // 10, endpoint % 10
    n        = len(ops_list)

    sep('═')
    print(f"\n  PREDICTION ANALYSIS")
    print(f"  EP={endpoint:02d}  Root={root:02d}  (rx={rx}, ry={ry})  Transitions={n}\n")
    sep()

    # ── 1. Structural checks ─────────────────────────────────────────────────
    print("  [1] STRUCTURAL CHECKS")
    if root == endpoint:
        print(f"      Root=EP ({root:02d}=={endpoint:02d})  →  lean NEW  (usually NEW — broke D90: EP=62,Root=62→65 TABLE)")
    else:
        print(f"      Root=EP:  NO  ({root:02d} ≠ {endpoint:02d})")
    if ep_x == ep_y:
        print(f"      EP x=y:   YES (x=y={ep_x})  →  coin-flip only  (3/6 history, no predictive value)")
    else:
        print(f"      EP x=y:   NO  (x={ep_x}, y={ep_y})")
    print()

    # ── 2. Root element in array ─────────────────────────────────────────────
    internal_pos, at_end = find_root_positions(group_index, root)
    print("  [2] ROOT ELEMENT IN ARRAY  (My Obs — confirmed D47)")
    if internal_pos:
        pos       = internal_pos[0]
        dep_op    = ops_list[pos - 1]
        xy, yx, sxy, syx = compute_variants(root, *dep_op)
        nxt_el    = group_index[pos]
        pos_str   = ', '.join(str(p) for p in internal_pos)
        print(f"      Root {root:02d} INTERNAL at array pos [{pos_str}]  (also at end)")
        print(f"      Depart Op {pos}: x:{dep_op[0]}  y:{dep_op[1]}  →  next={nxt_el:02d}")
        print(f"      Pred A:  xy={xy:02d}  yx={yx:02d}  sign+xy={sxy:02d}  sign+yx={syx:02d}  (lean xy)")
    else:
        arr_op    = ops_list[-1]
        xy, yx, sxy, syx = compute_variants(root, *arr_op)
        print(f"      Root {root:02d} at END ONLY (no internal occurrence)")
        print(f"      Arrive Op {n}: x:{arr_op[0]}  y:{arr_op[1]}")
        print(f"      Pred A:  xy={xy:02d}  yx={yx:02d}  sign+xy={sxy:02d}  sign+yx={syx:02d}  (xy=7 yx=3)")
    print()

    # ── 3. Pathan Obs 1 & 1B — Root arrival transformation ──────────────────
    arr_op = ops_list[-1]
    pred_b,  x_prime,  y_prime  = pathan_obs1 (root, arr_op[0], arr_op[1])
    pred_b2, x_prime2, y_prime2 = pathan_obs1b(root, arr_op[0], arr_op[1])
    print("  [3] PATHAN OBS 1 & 1B — ROOT ARRIVAL TRANSFORM")
    print(f"      Arriving Op {n}: x:{arr_op[0]}  y:{arr_op[1]}")
    print(f"      Obs1  x→add_cut={x_prime}  y→rm+flip={y_prime}")
    print(f"            x-digit=apply(rx={rx},{y_prime})={apply_op(rx,y_prime)}"
          f"  y-digit=apply(ry={ry},{x_prime})={apply_op(ry,x_prime)}")
    print(f"            Pred B  (Obs1 ): {pred_b:02d}")
    print(f"      Obs1B y→add_cut={y_prime2}  x→rm+flip={x_prime2}")
    print(f"            x-digit=apply(rx={rx},{y_prime2})={apply_op(rx,y_prime2)}"
          f"  y-digit=apply(ry={ry},{x_prime2})={apply_op(ry,x_prime2)}")
    print(f"            Pred B2 (Obs1B): {pred_b2:02d}")
    print()

    # ── 3C. Arriving-op transforms (D59–D62 observations) ──────────────────────
    at_list      = arriving_transforms(root, arr_op[0], arr_op[1])
    trig_idx     = arriving_transform_trigger(arr_op[0], arr_op[1])
    print("  [3C] ARRIVING-OP TRANSFORMS  (D59–D62 confirmed)")
    print(f"      Arriving Op {n}: x:{arr_op[0]}  y:{arr_op[1]}")
    for idx, (t_name, t_x, t_y, t_val) in enumerate(at_list):
        marker = "  <<< TRIGGERED" if idx == trig_idx else ""
        print(f"      {t_name:<21} x:{t_x:<10} y:{t_y:<10} →  {t_val:02d}{marker}")
    print()

    # ── 3D. Pre-arriving-1 (Op N-1) — D95+D96 confirmed ─────────────────────────
    if n >= 2:
        pre1_op = ops_list[-2]
        pxy, pyx, ps, pt = compute_variants(root, *pre1_op)
        print(f"  [3D] PRE-ARRIVING-1 (Op {n-1} of {n})  — D95+D96 confirmed  [scored xy=8, yx=3]")
        print(f"      Op {n-1}: x:{pre1_op[0]}  y:{pre1_op[1]}")
        print(f"      xy={pxy:02d}  yx={pyx:02d}  sign+xy={ps:02d}  sign+yx={pt:02d}")
        print()

    # ── 3E. Pre-arriving-2 (Op N-2) ──────────────────────────────────────────────
    if n >= 3:
        pre2_op = ops_list[-3]
        p2xy, p2yx, p2s, p2t = compute_variants(root, *pre2_op)
        print(f"  [3E] PRE-ARRIVING-2 (Op {n-2} of {n})  — extended pattern  [scored xy=1, sign+xy=1, sign+yx=1]")
        print(f"      Op {n-2}: x:{pre2_op[0]}  y:{pre2_op[1]}")
        print(f"      xy={p2xy:02d}  yx={p2yx:02d}  sign+xy={p2s:02d}  sign+yx={p2t:02d}")
        print()

    # ── 4. Pathan Obs 2 — same op pair exists elsewhere → use prev transition ─
    arr_pair  = arr_op
    obs2_hits = [i + 1 for i, p in enumerate(ops_list[:-1]) if p == arr_pair]
    print("  [4] PATHAN OBS 2 — SAME ARRIVING OP ELSEWHERE → PREV TRANSITION  [scored xy=2, yx=1, sign+xy=1, sign+yx=1]")
    if obs2_hits:
        for hit in obs2_hits:
            if hit > 1:
                prev_op  = ops_list[hit - 2]
                xy2, yx2, sxy2, syx2 = compute_variants(root, *prev_op)
                print(f"      Arriving op (x:{arr_pair[0]}, y:{arr_pair[1]}) also at Op {hit}")
                print(f"      Prev Op {hit-1}: x:{prev_op[0]}  y:{prev_op[1]}")
                print(f"      Pred C (Obs2): xy={xy2:02d}  yx={yx2:02d}  sign+xy={sxy2:02d}  sign+yx={syx2:02d}")
            else:
                print(f"      Arriving op also at Op {hit} (no prev — it is Op 1)")
    else:
        print(f"      Arriving op (x:{arr_pair[0]}, y:{arr_pair[1]}) not repeated elsewhere.")
    print()

    # ── 5. Pathan Obs 3 — transitions starting with x=rx ────────────────────
    print(f"  [5] PATHAN OBS 3 — TRANSITIONS WITH SOURCE x=rx={rx}  [scored xy=1, yx=1 per match (excl root-depart/arriving)]")
    rx_transitions = []
    for i, val in enumerate(group_index[:-1]):
        if val // 10 == rx:
            op = ops_list[i]
            rx_transitions.append((i + 1, val, group_index[i + 1], op))
    if rx_transitions:
        for (op_num, src, dst, op) in rx_transitions:
            mark = ' ← ROOT DEPART' if internal_pos and op_num == internal_pos[0] else ''
            oXY, oYX, oS, oT = compute_variants(root, *op)
            print(f"      Op {op_num:>2}: {src:02d}→{dst:02d}  x:{op[0]}  y:{op[1]}  →  xy={oXY:02d}  yx={oYX:02d}{mark}")
    else:
        print(f"      No transitions with source tens-digit={rx} found.")
    print()

    # ── 5C. Root-op near-miss — 1D variants NOT in chain (Rule 6) ──────────
    nm_root_op = dep_op if internal_pos else arr_op
    rnx_d, rny_d = nm_root_op
    nm_ops_set = set(ops_list)
    nm_1d_disp = set()
    for xv in ALL_OPS: nm_1d_disp.add((xv, rny_d))
    for yv in ALL_OPS: nm_1d_disp.add((rnx_d, yv))
    nm_1d_disp.add((rny_d, rnx_d))
    nm_1d_disp.discard((rnx_d, rny_d))
    nm_cands = [(vx, vy) for (vx, vy) in nm_1d_disp if (vx, vy) not in nm_ops_set]
    print(f"  [5C] ROOT-OP NEAR-MISS — 1D variants NOT yet in chain (Rule 6)  [scored xy=2, yx=1 each]")
    print(f"       Root op: (x:{rnx_d}  y:{rny_d})  →  {len(nm_cands)} single-change variants not in chain")
    if nm_cands:
        vary_x = [(vx, vy) for (vx, vy) in nm_cands if vy == rny_d]
        vary_y = [(vx, vy) for (vx, vy) in nm_cands if vx == rnx_d]
        swap_v = [(vx, vy) for (vx, vy) in nm_cands if (vx, vy) == (rny_d, rnx_d)]
        def _fmt(vx, vy):
            vxy, vyx, _, _ = compute_variants(root, vx, vy)
            return f"(x:{vx} y:{vy})→xy={vxy:02d} yx={vyx:02d}"
        if vary_x:
            print(f"       Vary-x: " + "  |  ".join(_fmt(vx, vy) for vx, vy in sorted(vary_x)))
        if vary_y:
            print(f"       Vary-y: " + "  |  ".join(_fmt(vx, vy) for vx, vy in sorted(vary_y)))
        if swap_v:
            print(f"       Swap:   " + "  |  ".join(_fmt(vx, vy) for vx, vy in swap_v))
    print()

    # ── 5B. Digit Resonance — src/dest digit alignment with rx, ry ──────────
    ry_dr = root % 10
    print(f"  [5B] DIGIT RESONANCE — src/dest digit alignment  rx={rx}  ry={ry_dr}")
    print(f"       ★★ Full match (weight 2):    dest=Root→sign+xy=SRC  |  src=SwapRoot→yx=rev(dest)  |  dest=SwapRoot→sign+yx=rev(src)")
    print(f"       ★★ Partial source (wt 2):   src_y=ry→xy  |  src_x=ry→yx  |  src_y=rx→yx")
    print(f"       ★  Partial dest (weight 1):  dest_x/y digit match→sign+xy/sign+yx variant")
    dr_any = False
    for i, src_dr in enumerate(group_index[:-1]):
        dst_dr  = group_index[i + 1]
        sx_dr, sy_dr = src_dr // 10, src_dr % 10
        dx_dr, dy_dr = dst_dr // 10, dst_dr % 10
        op_dr2  = ops_list[i]
        is_arr_dr = (i == n - 1)
        is_rs_dr  = (sx_dr == rx and sy_dr == ry_dr)
        if is_rs_dr or is_arr_dr:
            continue
        dxy, dyx, dsxy, dsyx = compute_variants(root, *op_dr2)
        is_rd_dr = (dx_dr == rx  and dy_dr == ry_dr)
        is_ss_dr = (sx_dr == ry_dr and sy_dr == rx)
        is_sd_dr = (dx_dr == ry_dr and dy_dr == rx)
        sigs_dr = []
        if is_rd_dr: sigs_dr.append(f"dest=Root→sxy={src_dr:02d}[★★]")
        if is_ss_dr: sigs_dr.append(f"src=Swap→yx={dyx:02d}[★★]")
        if is_sd_dr: sigs_dr.append(f"dest=Swap→syx={dsyx:02d}[★★]")
        if sy_dr == ry_dr:                       sigs_dr.append(f"sy=ry→xy={dxy:02d}[★]")
        if sx_dr == ry_dr and not is_ss_dr:      sigs_dr.append(f"sx=ry→yx={dyx:02d}[★]")
        if sy_dr == rx    and not is_ss_dr:      sigs_dr.append(f"sy=rx→yx={dyx:02d}[★]")
        if dx_dr == rx    and not is_rd_dr:      sigs_dr.append(f"dx=rx→sxy={dsxy:02d}[★]")
        if dy_dr == ry_dr and not is_rd_dr:      sigs_dr.append(f"dy=ry→sxy={dsxy:02d}[★]")
        if dx_dr == ry_dr and not is_sd_dr:      sigs_dr.append(f"dx=ry→syx={dsyx:02d}[★]")
        if dy_dr == rx    and not is_sd_dr:      sigs_dr.append(f"dy=rx→syx={dsyx:02d}[★]")
        if sigs_dr:
            dr_any = True
            print(f"      Op{i+1:>2} {src_dr:02d}→{dst_dr:02d} x:{op_dr2[0]} y:{op_dr2[1]}")
            print(f"           " + "  |  ".join(sigs_dr))
    if not dr_any:
        print("      No digit resonance matches found.")
    print()

    # ── 6. Repeated op pairs ─────────────────────────────────────────────────
    repeats = find_repeated_pairs(ops_list)
    print("  [6] REPEATED OP PAIRS  (My Obs — 2nd/3rd occurrence xy)")
    if repeats:
        for (xop, yop), positions in sorted(repeats.items(), key=lambda kv: kv[1][1]):
            xy, yx, sxy, syx = compute_variants(root, xop, yop)
            pos_str  = ', '.join(str(p) for p in positions)
            flags    = []
            if internal_pos and positions[0] == internal_pos[0]:
                flags.append('ROOT DEPART')
            if arr_pair == (xop, yop):
                flags.append('ARRIVING OP')
            flag_str = '  ← ' + ' + '.join(flags) if flags else ''
            print(f"      (x:{xop:<10} y:{yop:<10}) at Ops [{pos_str}]{flag_str}")
            print(f"        2nd: xy={xy:02d}  yx={yx:02d}  sign+xy={sxy:02d}  sign+yx={syx:02d}")
            if len(positions) > 2:
                print(f"        3rd occur also flagged — same values apply")
    else:
        print("      No repeated op pairs found.")
    print()

    # ── 7. First transition candidate ────────────────────────────────────────
    first_op = ops_list[0]
    xy1, yx1, sxy1, syx1 = compute_variants(root, *first_op)
    print("  [7] Op 1 (FIRST TRANSITION)  (My Obs — historically frequent TABLE winner)")
    print(f"      Op 1: x:{first_op[0]}  y:{first_op[1]}")
    print(f"      xy={xy1:02d}  yx={yx1:02d}  sign+xy={sxy1:02d}  sign+yx={syx1:02d}  (lean xy)")
    print()

    # ── 7B. Rule 9 — Direct-cut Root + direct-cut chain node ────────────────
    if (rx + 5) % 10 == ry:
        print(f"  [7B] RULE 9 — DIRECT-CUT ROOT ({root:02d}: {rx}↔{ry})  [xy=3, yx=2 when Root is direct-cut]")
        r9_found = False
        r9_seen  = set()
        for i, node in enumerate(group_index[:-1]):
            if node == root:
                continue
            nx, ny = node // 10, node % 10
            if (nx + 5) % 10 == ny:
                ox, oy    = ops_list[i]
                r9_x, r9_y = SIGN_FLIP[ox], SIGN_FLIP[oy]
                if (r9_x, r9_y) not in r9_seen:
                    r9_seen.add((r9_x, r9_y))
                    r9xy, r9yx, _, _ = compute_variants(root, r9_x, r9_y)
                    print(f"      Direct-cut node {node:02d} ({nx}↔{ny}) at Op {i+1}: x:{ox}  y:{oy}")
                    print(f"      → sign-flip both: x:{r9_x}  y:{r9_y}  →  xy={r9xy:02d}  yx={r9yx:02d}")
                    r9_found = True
        if not r9_found:
            print(f"      No other direct-cut nodes found in chain.")
        print()

    # ── 7C. Rule 10 — Double Root + double chain node ────────────────────────
    if rx == ry:
        print(f"  [7C] RULE 10 — DOUBLE ROOT ({root:02d}: {rx}={ry})  [xy=8, yx=4 when Root is double]")
        r10_found = False
        r10_seen  = set()
        for i, node in enumerate(group_index[:-1]):
            if node == root:
                continue
            nx, ny = node // 10, node % 10
            if nx == ny:
                ox, oy     = ops_list[i]
                r10_x      = SIGN_FLIP[ox]
                r10_y      = RULE10_Y_TRANSFORM[oy]
                if (r10_x, r10_y) not in r10_seen:
                    r10_seen.add((r10_x, r10_y))
                    r10xy, r10yx, _, _ = compute_variants(root, r10_x, r10_y)
                    print(f"      Double node {node:02d} ({nx}={ny}) at Op {i+1}: x:{ox}  y:{oy}")
                    print(f"      → Rule10: x:{r10_x}  y:{r10_y}  →  xy={r10xy:02d}  yx={r10yx:02d}")
                    r10_found = True
        if not r10_found:
            print(f"      No other double nodes found in chain.")
        print()

    # ── 7D. Rule 11 — Cut-root node ops ─────────────────────────────────────
    rx_cut = (rx + 5) % 10
    ry_cut = (ry + 5) % 10
    cut_node = rx_cut * 10 + ry_cut
    print(f"  [7D] RULE 11 — CUT-ROOT NODE (root={root:02d}: cut({rx})={rx_cut}, cut({ry})={ry_cut} → node {cut_node:02d})  [xy=8, yx=4]")
    r11_found = False
    r11_seen = set()
    for i, node in enumerate(group_index[:-1]):
        if node == cut_node:
            ox, oy = ops_list[i]
            r11_x = SIGN_FLIP[ox]
            r11_y = oy
            if (r11_x, r11_y) not in r11_seen:
                r11_seen.add((r11_x, r11_y))
                r11xy, r11yx, _, _ = compute_variants(root, r11_x, r11_y)
                print(f"      Node {cut_node:02d} at Op {i+1}: x:{ox}  y:{oy}")
                print(f"      → sign-flip x: x:{r11_x}  y:{r11_y}  →  xy={r11xy:02d}  yx={r11yx:02d}")
                r11_found = True
    if not r11_found:
        print(f"      Cut-node {cut_node:02d} not found in chain.")
    print()

    # ── 8. 30 STRONG PREDICTIONS ─────────────────────────────────────────────
    top4, _pred_scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
    sep('═')
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║             30  STRONG  PREDICTIONS                         ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")
    for rank, (val, score, reasons) in enumerate(top4, 1):
        # Build compact reason labels: take first significant word of each unique signal
        seen_r = set()
        lbl_parts = []
        for r in reasons:
            key = r.split()[0]
            if key not in seen_r:
                seen_r.add(key)
                lbl_parts.append(key)
        reason_str = " + ".join(lbl_parts)[:35]
        print(f"  ║  #{rank:<2} →  {val:02d}   score={score:>2}   {reason_str:<35}║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()
    # Cut-both transforms of predictions (display only — additive, no scoring change)
    _cut = lambda d: (d + 5) % 10
    _cb   = [(_cut(v // 10) * 10 + _cut(v % 10))  for (v, _, _) in top4]
    _rv   = [(v % 10) * 10 + (v // 10)             for (v, _, _) in top4]
    _pv   = [v                                      for (v, _, _) in top4]
    _cbr  = [(_cut(v % 10) * 10 + _cut(v // 10))   for (v, _, _) in top4]  # cb+rev: cut(Y)*10+cut(X)
    _cutu = [(v // 10) * 10 + _cut(v % 10)          for (v, _, _) in top4]  # cut-units: X*10+cut(Y)
    _cb_items   = [f"#{i+1}={_pv[i]:02d}→{_cb[i]:02d}"   for i in range(len(top4))]
    _rv_items   = [f"#{i+1}={_pv[i]:02d}→{_rv[i]:02d}"   for i in range(len(top4))]
    _cbr_items  = [f"#{i+1}={_pv[i]:02d}→{_cbr[i]:02d}"  for i in range(len(top4))]
    _cutu_items = [f"#{i+1}={_pv[i]:02d}→{_cutu[i]:02d}" for i in range(len(top4))]
    def _print_chunks(label, items, chunk=8):
        pad = " " * len(label)
        for i in range(0, len(items), chunk):
            prefix = label if i == 0 else pad
            print(prefix + "  ".join(items[i:i+chunk]))
    _print_chunks("  cut-both: ", _cb_items)
    _print_chunks("  reverse:  ", _rv_items)
    _print_chunks("  cb+rev:   ", _cbr_items)
    _print_chunks("  cut-units:", _cutu_items)
    print()

    sep('═')
    print()


# ── Data I/O ──────────────────────────────────────────────────────────────────

def load_data(source):
    """Parse lines into 2-D list of ints, skipping non-numeric tokens."""
    rows = []
    for line in source:
        line = line.strip()
        if not line:
            continue
        nums = []
        for token in line.split():
            try:
                nums.append(int(token))
            except ValueError:
                pass
        if nums:
            rows.append(nums)
    return rows


def get_next_number(rows, r, c):
    """Return the number that immediately follows position (r, c) in reading order."""
    row = rows[r]
    if c + 1 < len(row):
        return row[c + 1]
    if r + 1 < len(rows) and rows[r + 1]:
        return rows[r + 1][0]
    return None


# ── Formatting ────────────────────────────────────────────────────────────────

W = 72

def sep(ch='─'):
    print(ch * W)

def header(title):
    sep('═')
    print(f"  {title}")
    sep('═')


# ── Main Analysis ─────────────────────────────────────────────────────────────

def run(data_source, user_x_op=None, user_y_op=None):
    # Accept pre-parsed list[list[int]] or raw iterable of strings
    if data_source and isinstance(data_source, list) and isinstance(data_source[0], list):
        rows = data_source
    else:
        rows = load_data(data_source)

    if not rows:
        print("ERROR: No data loaded.")
        return

    # ── Step 1: EndPoint ──────────────────────────────────────────────────────
    endpoint     = rows[-1][-1]
    endpoint_pos = (len(rows) - 1, len(rows[-1]) - 1)

    header(f"ENDPOINT = {endpoint:02d}  (last row, last cell)")

    # ── Step 2: Scan ──────────────────────────────────────────────────────────
    print(f"\n  {'#':>4}  {'Location':^30}  {'Next':^6}")
    sep()

    group_index = []
    occurrence  = 0

    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            if val != endpoint:
                continue
            occurrence += 1
            if (r, c) == endpoint_pos:
                print(f"  {occurrence:>4}  Row {r+1:>3}, position {c+1:>2}"
                      f"   →   ENDPOINT  (no next)")
            else:
                nxt = get_next_number(rows, r, c)
                if nxt is not None:
                    group_index.append(nxt)
                    print(f"  {occurrence:>4}  Row {r+1:>3}, position {c+1:>2}"
                          f"   →   {nxt:02d}")

    # ── Step 3: Group Index Array ─────────────────────────────────────────────
    sep('═')
    if not group_index:
        print(f"\n  {endpoint:02d} ==►► [ empty — endpoint appears only once ]")
        print("\n  Cannot continue: no Group Index Array found.")
        sep('═')
        print()
        return None, []

    arr_str = ' │ '.join(f'{n:02d}' for n in group_index)
    print(f"\n  {endpoint:02d} ==►► [ {arr_str} ]")

    root   = group_index[-1]
    rx, ry = root // 10, root % 10
    print(f"\n  ROOT ELEMENT = {root:02d}   (x = {rx},  y = {ry})")
    sep('═')

    # ── Step 4: Transition Operations ────────────────────────────────────────
    print("\n  TRANSITION OPERATIONS:\n")
    print(f"  {'Step':<10}  {'x operation':<14}  {'y operation'}")
    sep()

    ops_list = []
    for i in range(len(group_index) - 1):
        a, b         = group_index[i], group_index[i + 1]
        ax, ay       = a // 10, a % 10
        bx, by       = b // 10, b % 10
        x_op, y_op   = find_op(ax, bx), find_op(ay, by)
        ops_list.append((x_op, y_op))
        print(f"  {a:02d} → {b:02d}     x:{x_op:<13}  y:{y_op}")

    sep('═')

    # ── Step 5: Chain Diagram ────────────────────────────────────────────────
    internal_pos, _ = find_root_positions(group_index, root)
    if len(ops_list) >= 1:
        show_chain_diagram(group_index, ops_list, root, internal_pos)

    # ── Step 5b: Last 3 rows of data grid ────────────────────────────────────
    show_last_rows_diagram(rows)

    # ── Step 6: Prediction Analysis ──────────────────────────────────────────
    _last_top4, _last_scores = [], {}
    if len(ops_list) >= 1:
        show_prediction(endpoint, root, ops_list, group_index, rows=rows)
        _last_top4, _last_scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)

    # ── Step 7: User Operation (if provided) ─────────────────────────────────
    if user_x_op and user_y_op:
        ux = normalize_op(user_x_op)
        uy = normalize_op(user_y_op)

        if ux is None or uy is None:
            bad = user_x_op if ux is None else user_y_op
            print(f"\n  ERROR: Unrecognised operation '{bad}'")
            print(f"  Valid ops: {', '.join(ALL_OPS)}")
        else:
            xy, yx, sign_xy, sign_yx = compute_variants(root, ux, uy)
            fx, fy = SIGN_FLIP[ux], SIGN_FLIP[uy]

            print(f"\n  OPERATION  →  x:{ux}   y:{uy}")
            print(f"  ROOT ELEMENT = {root:02d}  (x={rx}, y={ry})")
            sep()

            print(f"  xy       :  x:{ux}({rx})={apply_op(rx,ux)}"
                  f"   y:{uy}({ry})={apply_op(ry,uy)}"
                  f"   →   {xy:02d}")
            print(f"  yx       :  x:{uy}({rx})={apply_op(rx,uy)}"
                  f"   y:{ux}({ry})={apply_op(ry,ux)}"
                  f"   →   {yx:02d}")
            print(f"  sign+xy  :  x:{fx}({rx})={apply_op(rx,fx)}"
                  f"   y:{fy}({ry})={apply_op(ry,fy)}"
                  f"   →   {sign_xy:02d}")
            print(f"  sign+yx  :  x:{fy}({rx})={apply_op(rx,fy)}"
                  f"   y:{fx}({ry})={apply_op(ry,fx)}"
                  f"   →   {sign_yx:02d}")
            sep('═')

    # ── Step 7C: 10-C-T — unique values from TABLE 1 + TABLE 2, sorted ascending ──
    _ct_vals = set()
    for _xo, _yo in ops_list:
        for _v in compute_variants(root, _xo, _yo):
            _ct_vals.add(_v)
        _fxo, _fyo = SIGN_FLIP[_xo], SIGN_FLIP[_yo]
        for _v in compute_variants(root, _fxo, _fyo):
            _ct_vals.add(_v)
    _ct_sorted = sorted(_ct_vals)
    _ct_missing = [v for v in range(100) if v not in _ct_vals]
    print("\n  ══════════════════════════════════════════════════════════════════")
    print(f"  10-C-T  (TABLE 1 + TABLE 2)  Root={root:02d}  —  {len(_ct_sorted)} unique values")
    print("  ══════════════════════════════════════════════════════════════════")
    for _i in range(0, len(_ct_sorted), 10):
        _chunk = _ct_sorted[_i:_i+10]
        print("    " + "   ".join(f"{v:02d}" for v in _chunk))
    print("  ──────────────────────────────────────────────────────────────────")
    _miss_str = "  ".join(f"{v:02d}" for v in _ct_missing)
    print(f"  Missing ({len(_ct_missing)}): {_miss_str}")
    print("  ══════════════════════════════════════════════════════════════════\n")

    # ── Step 8: Existing Operations Table ────────────────────────────────────
    print("\n  TABLE 1 — EXISTING OPERATIONS  (ROOT ELEMENT = {root:02d})\n".format(root=root))
    print(f"  {'Op#':>4}  {'Operation':<26}  {'xy':>4}  {'yx':>4}  {'sign+xy':>8}  {'sign+yx':>8}")
    sep()

    for i, (x_op, y_op) in enumerate(ops_list):
        xy, yx, sign_xy, sign_yx = compute_variants(root, x_op, y_op)
        label    = f"x:{x_op:<10} y:{y_op}"
        print(f"  {i+1:>4}  {label:<26}  {xy:02d}    {yx:02d}    {sign_xy:02d}        {sign_yx:02d}")

    sep('═')

    # ── Step 9: Non-Existing Operations Table ────────────────────────────────
    print("\n  TABLE 2 — NON-EXISTING OPERATIONS  (ROOT ELEMENT = {root:02d})\n".format(root=root))
    print(f"  {'NE#':>4}  {'Operation':<26}  {'xy':>4}  {'yx':>4}  {'sign+xy':>8}  {'sign+yx':>8}")
    sep()

    for i, (x_op, y_op) in enumerate(ops_list):
        fx_op, fy_op             = SIGN_FLIP[x_op], SIGN_FLIP[y_op]
        xy, yx, sign_xy, sign_yx = compute_variants(root, fx_op, fy_op)
        label                    = f"x:{fx_op:<10} y:{fy_op}"
        print(f"  {i+1:>4}  {label:<26}  {xy:02d}    {yx:02d}    {sign_xy:02d}        {sign_yx:02d}")

    sep('═')

    # ── Step 10: Final Predictions Summary (repeated at bottom for quick reference)
    if len(ops_list) >= 1:
        top4, _pred_scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)
        ep_x, ep_y = endpoint // 10, endpoint % 10
        structural = ""
        if root == endpoint:
            structural = "  ROOT=EP → predict NEW"
        elif ep_x == ep_y:
            structural = f"  EP x=y={ep_x} (coin-flip, not reliable)"
        print()
        hdr = f"EP={endpoint:02d}  Root={root:02d}  Trans={len(ops_list)}"
        print("  ╔══════════════════════════════════════════════════════════════╗")
        print(f"  ║  {hdr}  ──  FINAL PREDICTIONS (30){'':<{30 - len(hdr)}}║")
        print("  ╠══════════════════════════════════════════════════════════════╣")
        for rank, (val, score, reasons) in enumerate(top4, 1):
            seen_r = set()
            lbl_parts = []
            for r in reasons:
                key = r.split()[0]
                if key not in seen_r:
                    seen_r.add(key)
                    lbl_parts.append(key)
            reason_str = " + ".join(lbl_parts)[:35]
            print(f"  ║  #{rank:<2} →  {val:02d}   score={score:>2}   {reason_str:<35}║")
        if structural:
            note = structural.strip()[:58]
            print(f"  ║  NOTE: {note:<54}║")
        print("  ╚══════════════════════════════════════════════════════════════╝")
    print()
    return root, ops_list, _last_top4, _last_scores


# ── Interactive Helpers ───────────────────────────────────────────────────────

def prompt_data():
    """Interactively collect data lines from the user. Returns list of strings."""
    sep('═')
    print("  DataProcessing — Number Sequence Analyser")
    sep('═')
    print()
    print("  Paste your data below, then type  END  on a new line and press Enter.")
    print()
    lines = []
    while True:
        try:
            line = input("  > ")
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip().upper() in ('END', 'DONE', 'STOP'):
            break
        lines.append(line)
    return lines


def prompt_operation(root):
    """Ask the user for an operation to apply to root element. Returns (x_op, y_op) or (None, None)."""
    rx, ry = root // 10, root % 10
    print()
    print(f"  ROOT ELEMENT = {root:02d}  (x={rx}, y={ry})")
    print(f"  Valid ops : {', '.join(ALL_OPS)}")
    print()

    while True:
        try:
            raw_x = input("  Enter x operation (or SKIP to skip / EXIT to quit): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None, None

        if raw_x.upper() in ('EXIT', 'QUIT', 'Q'):
            return None, None
        if raw_x.upper() in ('SKIP', 'S', ''):
            return None, None

        ux = normalize_op(raw_x)
        if ux is None:
            print(f"  ! Unknown op '{raw_x}'. Try again.")
            continue

        try:
            raw_y = input("  Enter y operation: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None, None

        uy = normalize_op(raw_y)
        if uy is None:
            print(f"  ! Unknown op '{raw_y}'. Try again.")
            continue

        return ux, uy


def prompt_result(root):
    """Ask the user for a result number. Returns int or None."""
    rx, ry = root // 10, root % 10
    print()
    print(f"  ROOT ELEMENT = {root:02d}  (x={rx}, y={ry})")
    while True:
        try:
            raw = input("  Enter result number 00-99 (or SKIP / EXIT): ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw.upper() in ('EXIT', 'QUIT', 'Q'):
            return None
        if raw.upper() in ('SKIP', 'S', ''):
            return None
        try:
            val = int(raw)
            if 0 <= val <= 99:
                return val
            print("  ! Please enter a number between 00 and 99.")
        except ValueError:
            print(f"  ! '{raw}' is not a valid number. Try again.")


def show_operation_result(root, ux, uy):
    """Print the xy / yx / sign+xy / sign+yx results for the given operation."""
    rx, ry = root // 10, root % 10
    xy, yx, sign_xy, sign_yx = compute_variants(root, ux, uy)
    fx, fy = SIGN_FLIP[ux], SIGN_FLIP[uy]

    sep()
    print(f"  OPERATION  →  x:{ux}   y:{uy}")
    print(f"  ROOT ELEMENT = {root:02d}  (x={rx}, y={ry})")
    sep()
    print(f"  xy       :  x:{ux}({rx})={apply_op(rx,ux)}"
          f"   y:{uy}({ry})={apply_op(ry,uy)}"
          f"   →   {xy:02d}")
    print(f"  yx       :  x:{uy}({rx})={apply_op(rx,uy)}"
          f"   y:{ux}({ry})={apply_op(ry,ux)}"
          f"   →   {yx:02d}")
    print(f"  sign+xy  :  x:{fx}({rx})={apply_op(rx,fx)}"
          f"   y:{fy}({ry})={apply_op(ry,fy)}"
          f"   →   {sign_xy:02d}")
    print(f"  sign+yx  :  x:{fy}({rx})={apply_op(rx,fy)}"
          f"   y:{fx}({ry})={apply_op(ry,fx)}"
          f"   →   {sign_yx:02d}")
    sep('═')


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='DataProcessing — Number sequence analyser using cut rule',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'datafile', nargs='?',
        help='Path to data file (rows of space-separated numbers).\n'
             'If omitted, enters interactive input mode.'
    )
    parser.add_argument(
        '--x-op', metavar='OP',
        help=f'X operation for root element. Valid: {", ".join(ALL_OPS)}'
    )
    parser.add_argument(
        '--y-op', metavar='OP',
        help='Y operation for root element (same valid values as --x-op)'
    )
    parser.add_argument(
        '--result', metavar='NUM', type=int,
        help='Result number (00-99) to reverse-find the operation for'
    )
    args = parser.parse_args()

    # ── File mode ─────────────────────────────────────────────────────────────
    if args.datafile:
        try:
            with open(args.datafile, 'r') as f:
                root, ops_list, last_top4, last_scores = run(f, args.x_op, args.y_op)
            if args.result is not None:
                show_result_analysis(root, args.result, ops_list, last_scores, last_top4)
        except FileNotFoundError:
            print(f"ERROR: File not found → {args.datafile}")
            sys.exit(1)
        return

    # ── Interactive mode ───────────────────────────────────────────────────────
    while True:
        lines = prompt_data()

        if not lines:
            print("\n  No data entered. Exiting.")
            break

        rows = load_data(lines)
        if not rows:
            print("\n  ! Could not parse any numbers. Please try again.\n")
            continue

        root, ops_list, last_top4, last_scores = run(rows, args.x_op, args.y_op)

        if root is None:
            continue

        while True:
            result = prompt_result(root)
            if result is None:
                break
            show_result_analysis(root, result, ops_list, last_scores, last_top4)

            ux, uy = prompt_operation(root)
            if ux is None:
                continue
            show_operation_result(root, ux, uy)

        print()
        try:
            again = input("  Load new data? (yes / no): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            again = 'no'

        if again not in ('yes', 'y'):
            print("\n  Goodbye!\n")
            break


if __name__ == '__main__':
    main()
