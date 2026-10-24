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
import os
import json
import argparse
import re
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


def build_family_map():
    """Cut-pair family grouping (user-supplied, 2026-07-07): partitions 00-99
    into 12 families -- 10 digit-pair families (each digit d paired with
    cut(d)) of 8 members, a HALF-CUT family (digit2=cut(digit1)) of 10, and
    a DOUBLE family (dd) of 10. Returns ({value: family_label}, [family order])."""
    family = {}
    order = []
    digits5 = [1, 2, 3, 4, 5]
    for i in range(len(digits5)):
        for j in range(i + 1, len(digits5)):
            d1, d2 = digits5[i], digits5[j]
            label = f"{d1}{d2} FAMILY"
            order.append(label)
            s1, s2 = {d1, cut(d1)}, {d2, cut(d2)}
            for a in s1:
                for b in s2:
                    family[a * 10 + b] = label
                    family[b * 10 + a] = label
    order.append("HALF CUT FAMILY")
    for d in range(10):
        c = cut(d)
        family.setdefault(d * 10 + c, "HALF CUT FAMILY")
        family.setdefault(c * 10 + d, "HALF CUT FAMILY")
    order.append("DOUBLE FAMILY")
    for d in range(10):
        family[d * 10 + d] = "DOUBLE FAMILY"
    return family, order


FAMILY_MAP, FAMILY_ORDER = build_family_map()
FAMILY_MEMBERS = {}
for _v, _f in FAMILY_MAP.items():
    FAMILY_MEMBERS.setdefault(_f, []).append(_v)
for _f in FAMILY_MEMBERS:
    FAMILY_MEMBERS[_f].sort()

# HALF CUT FAMILY and DOUBLE FAMILY are directly single-digit-cut-adjacent to
# each other (every double dd's single-digit cuts land in HALF CUT, and vice
# versa -- e.g. 55 -> 05/50) even though they're separate rows in the TOP 30
# BY FAMILY display. User asked 2026-07-27 (D1607, "05 and 50 available...
# show the 55 also") to bridge them for cycle-closure purposes -- this is a
# closure-grouping change only, FAMILY_MAP/FAMILY_ORDER (and the 12-row
# display) stay untouched, so each still gets filtered into its own row.
_CLOSURE_GROUP = dict(FAMILY_MAP)
for _v in _CLOSURE_GROUP:
    if _CLOSURE_GROUP[_v] in ("HALF CUT FAMILY", "DOUBLE FAMILY"):
        _CLOSURE_GROUP[_v] = "HALF CUT + DOUBLE"
_CLOSURE_GROUPS = [f for f in FAMILY_ORDER if f not in ("HALF CUT FAMILY", "DOUBLE FAMILY")] + ["HALF CUT + DOUBLE"]


def family_cycle_closure(top30_vals):
    """Full cut-cycle closure of top30_vals, per family (same BFS logic used
    by the TOP 30 BY FAMILY display box) — every family's 8/10 members split
    into 4-member (or smaller) single-digit-cut cycles; a member is only
    reachable if SOME cycle-mate is already in top30_vals. Returns the union
    across all families (the same set backing TOP 30 + SIBLINGS BY DECADE)."""
    all_extended = set()
    for fam in _CLOSURE_GROUPS:
        in_fam = [v for v in top30_vals if _CLOSURE_GROUP[v] == fam]
        shown = set(in_fam)
        frontier = list(in_fam)
        while frontier:
            next_frontier = []
            for v in frontier:
                x, y = v // 10, v % 10
                for sib in (cut(x) * 10 + y, x * 10 + cut(y), cut(x) * 10 + cut(y)):
                    if _CLOSURE_GROUP.get(sib) == fam and sib not in shown:
                        shown.add(sib)
                        next_frontier.append(sib)
            frontier = next_frontier
        all_extended |= shown
    return all_extended


FAMILY_TRACKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "family_tracker_state.json")


def update_family_tracker(covered):
    """Persist the running family-coverage rate across rounds (2026-07-08,
    user-requested reference tracker -- NOT used for prediction). Returns
    (covered_count, total_count) after this update."""
    state = {"covered": 0, "total": 0}
    if os.path.exists(FAMILY_TRACKER_PATH):
        try:
            with open(FAMILY_TRACKER_PATH) as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    state["total"] = state.get("total", 0) + 1
    if covered:
        state["covered"] = state.get("covered", 0) + 1
    with open(FAMILY_TRACKER_PATH, "w") as f:
        json.dump(state, f)
    return state["covered"], state["total"]


HITRATE_TRACKER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "hitrate_tracker_state.json")


def update_hitrate_tracker(hit):
    """Persist the running top-30 hit rate across rounds (2026-07-12,
    user-requested progress bar so hit-rate trend is visible without asking
    for a manual audit each time). Returns (hits, total) after this update."""
    state = {"hits": 0, "total": 0}
    if os.path.exists(HITRATE_TRACKER_PATH):
        try:
            with open(HITRATE_TRACKER_PATH) as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    state["total"] = state.get("total", 0) + 1
    if hit:
        state["hits"] = state.get("hits", 0) + 1
    with open(HITRATE_TRACKER_PATH, "w") as f:
        json.dump(state, f)
    return state["hits"], state["total"]


def render_progress_bar(pct, width=20):
    filled = round(pct / 100 * width)
    filled = max(0, min(width, filled))
    return '█' * filled + '░' * (width - filled)


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
        all_vals = sorted(range(100), key=lambda v: len(scores.get(v, [])), reverse=True)
        full_rank = all_vals.index(result) + 1
        if rank:
            rank_str = f"Rank #{rank} of {len(top4)}"
        else:
            rank_str = f"Rank #{full_rank} of 100"
        print(f"  Score: {rscore}   {rank_str}")
        # Finger-mark zone indicator: TOP 40 / TAIL 30 (ranks 71-100) / MIDDLE
        # (widened from top-30 to top-40 on 2026-07-30, user request)
        if full_rank <= 40:
            print(f"  \U0001F449 ZONE: TOP 40 (rank #{full_rank})")
        elif full_rank > 70:
            print(f"  \U0001F449 ZONE: TAIL 30 (rank #{full_rank} of 100)")
        else:
            print(f"  \U0001F449 ZONE: MIDDLE (rank #{full_rank} of 100 -- neither top-40 nor tail-30)")
        # Family-coverage tracker (2026-07-08, reference only -- see
        # feedback_output_format.md: backtested 92.0% vs 94.2% random
        # baseline, i.e. NOT a predictive signal, just a running observation
        # the user asked to watch for themselves).
        # FIXED 2026-07-26: was checking "any same 8-member family value in
        # top-30", which could say YES even when `result` sits in the OTHER
        # 4-member cut-cycle from the one actually reachable/shown in the
        # TOP 30 BY FAMILY box (e.g. D1575 result=71, family had 12/17
        # present but those close only to {12,17,62,67} -- 71 is in the
        # separate {21,26,71,76} cycle, never shown, yet the old check said
        # "covered"). Now uses the SAME family_cycle_closure() the display
        # box uses, so "covered" means "result actually appears in the
        # printed family/siblings boxes this round" -- consistent with what
        # the user sees, not a broader family-label coincidence.
        _result_fam = FAMILY_MAP[result]
        _top30_set = set(all_vals[:40])
        _all_extended = family_cycle_closure(_top30_set)
        _fam_covered = result in _all_extended
        _fcov, _ftot = update_family_tracker(_fam_covered)
        print(f"  Family-covered: {'YES' if _fam_covered else 'NO '} "
              f"({_result_fam}; cumulative: {_fcov}/{_ftot} = {100*_fcov/_ftot:.1f}%)")
        # RESULT LOCATION (2026-07-26): user asked to always be able to see
        # where the result sits relative to the DECADE and FAMILY boxes,
        # even on a miss where it wasn't printed there. Shows the result's
        # decade + its own cut-cycle (via family_cycle_closure on just this
        # one value) and states plainly whether that cycle was the one
        # actually shown above this round. Reference/orientation only --
        # does not change scoring or claim predictive power.
        _result_decade = f"{(result // 10) * 10:02d}-{(result // 10) * 10 + 9:02d}"
        _own_cycle = sorted(family_cycle_closure({result}))
        _cycle_str = ", ".join(f"{v:02d}" for v in _own_cycle)
        print(f"  RESULT LOCATION: decade {_result_decade} | {_result_fam} cycle "
              f"[{_cycle_str}]"
              f"{' (shown above)' if _fam_covered else ' (NOT shown above this round)'}")
        # TOP 30 + SIBLINGS BY DECADE, result marked (2026-07-26): user asked
        # to always see this specific box after scoring, with the actual
        # result slotted into its decade row and marked in brackets --
        # whether or not it was already covered -- instead of only getting
        # the one-line RESULT LOCATION summary above. Reuses the same
        # family_cycle_closure(_top30_set) the run() display box computed,
        # so the set matches exactly; the result's own decade row gets the
        # result inserted at its sorted position if missing, or bracketed
        # in place if already present.
        # Red-circle marks top-30 members here too (2026-07-29, same request
        # as the run()-time box) -- combined with the existing [brackets]
        # result marker, e.g. a result that's ALSO a top-30 member prints as
        # "[🔴21]".
        _res_dec_hdr = f"  TOP 40 + SIBLINGS BY DECADE ({len(_all_extended)} numbers, \U0001F534=top-40, result marked)"
        _res_dec_lines = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _in_decade = sorted(v for v in _all_extended if _lo <= v <= _hi and v != result)
            _mark = lambda v: f"\U0001F534{v:02d}" if v in _top30_set else f"{v:02d}"
            if _lo <= result <= _hi:
                _row_vals = sorted(_in_decade + [result])
                _vals_str = ", ".join(
                    f"[{_mark(v)}]" if v == result else _mark(v) for v in _row_vals
                )
            else:
                _vals_str = ", ".join(_mark(v) for v in _in_decade) if _in_decade else "--"
            _label = f"{_lo:02d}-{_hi:02d}"
            _res_dec_lines.append(f"  {_label} : {_vals_str}")
        _rdw = max([64, len(_res_dec_hdr)] + [len(l) for l in _res_dec_lines])
        print()
        print(f"  ┌{'─' * _rdw}┐")
        print(f"  │{_res_dec_hdr:<{_rdw}}│")
        print(f"  ├{'─' * _rdw}┤")
        for l in _res_dec_lines:
            print(f"  │{l:<{_rdw}}│")
        print(f"  └{'─' * _rdw}┘")

        # RECOMMENDED BY DECADE / BY FAMILY, result marked (2026-08-02):
        # user asked for these two score-threshold boxes (see run()'s
        # version, added same day) to also appear here after scoring, with
        # the actual result bracket-marked in place -- same pattern as the
        # SIBLINGS box just above. No red-circle marks (removed from these
        # two boxes per user request); brackets are the only marker.
        _rec_cutoff_score = top4[-1][1] if top4 else 0
        _rec_set = sorted(v for v in range(100) if len(scores.get(v, [])) >= _rec_cutoff_score)

        def _rec_wrapped_rows(label, members, per_line=8):
            _indent = " " * len(f"  {label} : ")
            _rows = []
            for i in range(0, len(members), per_line):
                _chunk = ", ".join(
                    f"[{v:02d}]" if v == result else f"{v:02d}" for v in members[i:i + per_line]
                )
                _prefix = f"  {label} : " if i == 0 else _indent
                _rows.append(f"{_prefix}{_chunk}")
            return _rows if members else [f"  {label} : --"]

        def _print_rec_box(hdr, rows):
            _w = max([64, len(hdr)] + [len(l) for l in rows])
            print()
            print(f"  ┌{'─' * _w}┐")
            print(f"  │{hdr:<{_w}}│")
            print(f"  ├{'─' * _w}┤")
            for l in rows:
                print(f"  │{l:<{_w}}│")
            print(f"  └{'─' * _w}┘")

        _rec_in_dec = sorted(set(_rec_set) | {result})
        _rec_dec_hdr2 = (f"  RECOMMENDED BY DECADE ({len(_rec_set)} values, score>={_rec_cutoff_score}, "
                          f"result marked)")
        _rec_dec_lines2 = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _in_decade = [v for v in _rec_in_dec if _lo <= v <= _hi]
            _rec_dec_lines2.extend(_rec_wrapped_rows(f"{_lo:02d}-{_hi:02d}", _in_decade))
        _print_rec_box(_rec_dec_hdr2, _rec_dec_lines2)

        _rec_fam_hdr2 = (f"  RECOMMENDED BY FAMILY ({len(_rec_set)} values, score>={_rec_cutoff_score}, "
                         f"result marked)")
        _rec_fam_lines2 = []
        for _fam in FAMILY_ORDER:
            _members = [v for v in (set(_rec_set) | {result}) if FAMILY_MAP[v] == _fam]
            _rec_fam_lines2.extend(_rec_wrapped_rows(f"{_fam:<16}", sorted(_members)))
        _print_rec_box(_rec_fam_hdr2, _rec_fam_lines2)

        # Hit-rate progress bar (2026-07-12, reference only -- see
        # feedback_output_format.md: user asked for a self-serve visual so
        # they can see the trend without requesting a manual audit).
        _hit = rank is not None
        _hits, _htot = update_hitrate_tracker(_hit)
        _hpct = 100 * _hits / _htot
        print(f"  \U0001F4CA Hit Rate: [{render_progress_bar(_hpct)}] "
              f"{_hpct:.1f}% ({_hits}/{_htot})")
        sig_labels = list(dict.fromkeys(sorted(scores.get(result, []))))
        if sig_labels:
            print(f"  Signals: {' | '.join(sig_labels[:8])}")
        else:
            print(f"  Signals: none — zero-signal result")
        # WHY MISSED diagnostic (2026-07-26): only fires when result missed
        # top-30. Explains the numeric gap to the cutoff plus a cheap,
        # honest structural check (does this value's x-op/y-op individually
        # appear elsewhere in the chain — the same eligibility test CompOp
        # uses) rather than a vague "no signal fired."
        if full_rank > 40:
            _cutoff_score = top4[-1][1] if top4 and len(top4) >= 40 else 0
            _gap = max(0, _cutoff_score - rscore)
            _res_x_op = find_op(rx, result // 10)
            _res_y_op = find_op(ry, result % 10)
            _x_ops_in_chain = {ox for ox, oy in ops_list}
            _y_ops_in_chain = {oy for ox, oy in ops_list}
            _x_comp = _res_x_op in _x_ops_in_chain
            _y_comp = _res_y_op in _y_ops_in_chain
            print(f"  WHY MISSED: score={rscore} vs #40 cutoff={_cutoff_score} "
                  f"(short by {_gap} pt{'s' if _gap != 1 else ''})")
            print(f"  x-op '{_res_x_op}' {'is' if _x_comp else 'NOT'} used elsewhere in chain"
                  f" | y-op '{_res_y_op}' {'is' if _y_comp else 'NOT'} used elsewhere in chain"
                  f"{' (both present but never paired — CompOp PATTERN, but CompOp is ablated: proven net-negative in backtest, deliberately NOT scored)' if _x_comp and _y_comp else ''}")
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


def _root_ops_table(root, ops_list, strong, rec):
    """ROOT OPS box (display only): every transition step's ops applied to
    the ROOT ELEMENT, same columns as POSSIBLE OPS (ops in brackets).
    S = value is in the 30 STRONG PREDICTIONS, ★ = a ★ RECOMMENDED pick;
    S# = how many of the row's 6 values are strong. Row k lines up with
    TRANSITION OPERATIONS step k."""
    ab  = lambda op: OP_ABBREV.get(op, op)
    mk  = lambda v: ("★" if v in rec else "S" if v in strong else " ")
    SW  = 15
    hdr = (f" {'#':>2}  {'x op':<6}{'y op':<6}{'Number':<8}{'yx':<5}{'s+xy (op)':<{SW}}{'s+yx (op)':<{SW}}"
           f"{'cut xy (op)':<{SW}}{'cut sign (op)':<{SW}}{'S#':>2} ")
    iw  = len(hdr)
    ttl = f" ROOT OPS → ROOT={root:02d}  (S=strong ★=recommended) "
    out = ["╔" + ttl.center(iw, "═") + "╗", "║" + " " * iw + "║", "║" + hdr + "║", "╟" + "─" * iw + "╢"]
    per_op = {}
    hits   = {}                  # every value → highest S# of a row it appears in
    for k, (nx, ny) in enumerate(ops_list, 1):
        if '?' in (nx, ny):
            out.append("║" + f" {k:>2}  ?".ljust(iw) + "║")
            continue
        xy, yx, sxy, syx = compute_variants(root, nx, ny)
        fx, fy = ab(SIGN_FLIP[nx]), ab(SIGN_FLIP[ny])
        tx, ty = KK_CUT_TOGGLE[nx], KK_CUT_TOGGLE[ny]
        cxy  = apply_op(root // 10, tx) * 10 + apply_op(root % 10, ty)
        csxy = apply_op(root // 10, SIGN_FLIP[tx]) * 10 + apply_op(root % 10, SIGN_FLIP[ty])
        six  = [xy, yx, sxy, syx, cxy, csxy]
        ns   = sum(1 for v in six if v in strong or v in rec)
        for v in six:
            hits[v] = max(hits.get(v, 0), ns)     # strongest row it appears in
        per_op[(nx, ny)] = (ns, sorted({v for v in six if v in strong or v in rec}))
        out.append("║" + f" {k:>2}  {ab(nx):<6}{ab(ny):<6}"
                   + f"{xy:02d}{mk(xy)}".ljust(8) + f"{yx:02d}{mk(yx)}".ljust(5)
                   + f"{sxy:02d}{mk(sxy)}({fx}/{fy})".ljust(SW)
                   + f"{syx:02d}{mk(syx)}({fy}/{fx})".ljust(SW)
                   + f"{cxy:02d}{mk(cxy)}({ab(tx)}/{ab(ty)})".ljust(SW)
                   + f"{csxy:02d}{mk(csxy)}({ab(SIGN_FLIP[tx])}/{ab(SIGN_FLIP[ty])})".ljust(SW)
                   + f"{ns:>2} ║")
    out.append("╟" + "─" * iw + "╢")
    best = max((n for n, _ in per_op.values()), default=0)
    if best:
        out.append("║" + f" STRONGEST OPS ({best} of 6 values strong):".ljust(iw) + "║")
        for (nx, ny), (n, vs) in sorted(per_op.items()):
            if n == best:
                out.append("║" + (f"   x:{ab(nx):<5} y:{ab(ny):<5} → "
                                  + " ".join(f"{v:02d}{mk(v).strip()}" for v in vs)).ljust(iw) + "║")
    recd = sorted({op for op, (_, vs) in per_op.items() if any(v in rec for v in vs)})
    out.append("║" + (" ★ RECOMMENDED via: " + (", ".join(f"{ab(x)}/{ab(y)}" for x, y in recd)
                                               if recd else "none")).ljust(iw) + "║")
    out.append("╚" + "═" * iw + "╝")
    if best:
        _super_add("RO", [v for v, h in hits.items() if h == best])

    # VALUES BY OP STRENGTH box beside it: every value from all 6 columns,
    # once each, grouped by the highest S# of any row it appears in (S#6 =
    # the STRONGEST OPS first), ascending within a group, 8 per line.
    iw2  = 44
    side = ["╔" + f" ALL VALUES BY OP STRENGTH ({len(hits)}) ".center(iw2, "═") + "╗",
            "║" + " all columns, no duplicates".ljust(iw2) + "║",
            "║" + " S#  Values".ljust(iw2) + "║",
            "╟" + "─" * iw2 + "╢"]
    for n in range(6, -1, -1):
        vals = sorted(v for v, h in hits.items() if h == n)
        for k in range(0, len(vals), 8):
            head = f" {n}  " if k == 0 else "    "
            side.append("║" + (head + " ".join(f"{v:02d}{mk(v).strip() or ' '}"
                                              for v in vals[k:k + 8])).ljust(iw2) + "║")
    side.append("╟" + "─" * iw2 + "╢")
    side.append("║" + " S# = strong values in that op's row (of 6)".ljust(iw2) + "║")
    side.append("║" + " ★ = recommended, S = strong".ljust(iw2) + "║")
    side.append("╚" + "═" * iw2 + "╝")
    width = len(out[0]) + 4
    return [(o if k < len(out) else "").ljust(width) + (side[k] if k < len(side) else "")
            for k, o in enumerate(out + [""] * max(0, len(side) - len(out)))]


# ── SUPER SPECIAL vote collector ─────────────────────────────────────────────
# Every table that produces candidate numbers registers them here (display
# only); run() resets it per analysis and prints the SUPER SPECIAL
# RECOMMENDED table at the very bottom from these votes.
_SUPER_SRC = {}


def _super_add(code, values):
    _SUPER_SRC[code] = {v for v in values if 0 <= v <= 99}


SUPER_NAMES = {
    "R3": "★ RECOMMENDED (top 3)",   "S30": "30 STRONG PREDICTIONS",
    "RF": "RECOMMENDED BY FAMILY",   "KK": "KK SPECIAL FAMILY",
    "KC": "KK CHAIN FAMILY",         "PO": "POSSIBLE OPS → EP",
    "40": "40 NUMBERS (4/digit)",    "F4": "FIRST 4 ROWS → 40",
    "SW": "STARTS WITH (first 4)",   "RO": "ROOT OPS strongest ops",
    "NX": "NON-EXISTING top priority",
}


def super_special_top10(top4, scores):
    """Votes from every table: each source gives each of its numbers a
    weight of 1 - size/100 (a table covering nearly all 100 numbers says
    almost nothing, a 3-number table says a lot). Ties broken by the main
    prediction score, then by value. Returns [(v, weight, [codes])] × 10."""
    src = dict(_SUPER_SRC)
    if top4:
        src["R3"]  = {v for v, *_ in top4[:3]}
        src["S30"] = {v for v, *_ in top4[:30]}
        cutoff = top4[-1][1]
        src["RF"]  = {v for v in range(100) if len(scores.get(v, [])) >= cutoff}
    weight = {}
    for code, vals in src.items():
        w = 1 - len(vals) / 100
        for v in vals:
            weight[v] = weight.get(v, 0) + w
    order = sorted(weight, key=lambda v: (-round(weight[v], 6),
                                          -len(scores.get(v, [])), v))
    return [(v, weight[v], sorted(c for c, vals in src.items() if v in vals))
            for v in order[:10]], src


def show_super_special(top4, scores):
    """SUPER SPECIAL RECOMMENDED — 10 values combining every table (display
    only, very bottom of the page), bold triple Indian-flag border."""
    top10, src = super_special_top10(top4, scores)
    if not top10:
        return
    body = ["★★★  SUPER SPECIAL RECOMMENDED — 10 VALUES  ★★★",
            "votes from every table, weighted by how selective the table is",
            "",
            "  10 VALUES:   " + "   ".join(f"{v:02d}" for v, *_ in top10),
            "",
            f"{'Rank':>4}  {'Value':<6}{'Weight':>7}  {'Tables':>6}   Found in",
            "─" * 78]
    for k, (v, w, codes) in enumerate(top10, 1):
        body.append(f"{k:>4}   {v:02d}  {w:>8.2f}  {len(codes):>3}/{len(src):<3} " + " ".join(codes))
    body.append("─" * 78)
    names = [f"{c}={SUPER_NAMES.get(c, c)}({len(src[c])})" for c in SUPER_NAMES if c in src]
    for k in range(0, len(names), 3):
        body.append("  ".join(names[k:k + 3]))
    body.append("")
    body.append("Backtest (2026-10-01, 976 past rounds of this grid): SUPER 10 hit 9.4%")
    body.append("vs 10% pure chance -- a combined shortlist, NOT a proven edge.")

    B   = "\033[1m"
    flag = [f"\033[1;38;2;{c}m" for c in ("255;153;51", "255;255;255", "19;136;8")]
    rst  = "\033[0m"
    iw   = max(len(s) for s in body) + 2
    box  = [f" {B}{s:<{iw - 2}}{rst} " for s in body]
    for lvl in range(2, -1, -1):           # green inner, white, saffron outer
        c, w = flag[lvl], iw + 2 * (2 - lvl)
        box = ([f"{c}┏{'━' * w}┓{rst}"]
               + [f"{c}┃{rst}{s}{c}┃{rst}" for s in box]
               + [f"{c}┗{'━' * w}┛{rst}"])
    print()
    for l in box:
        print("  " + l)


def show_power_box():
    """ALL NUMBERS, NO REPEATS of the 3RRR POWER BASE table again at the very
    end of the page, below SUPER SPECIAL RECOMMENDED, in the same triple
    Indian-flag border (user's screenshots, 2026-10-08)."""
    got = _RRR3_PREV.pop('power_box', None)
    if not got:
        return
    ep, uniq = got
    body = [f"★  POWER BASE — ALL {len(uniq)} NUMBERS, NO REPEATS  (EP={ep:02d})  ★", ""]
    body += [''.join(f"  {c}" for c in uniq[k:k + 10]) for k in range(0, len(uniq), 10)]
    body += ["", "★ = also in the STRONG 20    * = also in the RECOMMENDED list",
             "+ = digits reversed of a table number whose series is there",
             "A wide list: it holds the result often by size alone, NOT a proven edge."]
    B    = "\033[1m"
    flag = [f"\033[1;38;2;{c}m" for c in ("255;153;51", "255;255;255", "19;136;8")]
    rst  = "\033[0m"
    iw   = max(len(s) for s in body) + 2
    box  = [f" {B}{s:<{iw - 2}}{rst} " for s in body]
    for lvl in range(2, -1, -1):           # green inner, white, saffron outer
        c, w = flag[lvl], iw + 2 * (2 - lvl)
        box = ([f"{c}┏{'━' * w}┓{rst}"]
               + [f"{c}┃{rst}{s}{c}┃{rst}" for s in box]
               + [f"{c}┗{'━' * w}┛{rst}"])
    print()
    for l in box:
        print("  " + l)


def show_three_box():
    """3RRR STRONG 20, CharRow (no repeats) and STRONG 20 ADJUSTMENTS again at
    the very end of the page, below everything else, in the triple
    Indian-flag border (user's screenshot, 2026-10-13)."""
    got = _RRR3_PREV.pop('three_box', None)
    if not got:
        return
    vis  = lambda t: len(re.sub(r'\x1b\[[0-9;]*m', '', t))
    flag = [f"\033[1;38;2;{c}m" for c in ("255;153;51", "255;255;255", "19;136;8")]
    rst  = "\033[0m"
    iw   = max(vis(t) for t in got) + 2
    box  = [f"{t}{' ' * (iw - vis(t))}" for t in got]
    for lvl in range(2, -1, -1):           # green inner, white, saffron outer
        c, w = flag[lvl], iw + 2 * (2 - lvl)
        box = ([f"{c}┏{'━' * w}┓{rst}"]
               + [f"{c}┃{rst}{t}{c}┃{rst}" for t in box]
               + [f"{c}┗{'━' * w}┛{rst}"])
    print()
    for l in box:
        print("  " + l)


def _root_six(root, nx, ny):
    """The 6 ROOT OPS values for one op pair, each with its (tens/units) ops:
    Number, yx, s+xy, s+yx, cut xy, cut sign."""
    ab = lambda op: OP_ABBREV.get(op, op)
    xy, yx, sxy, syx = compute_variants(root, nx, ny)
    fx, fy = SIGN_FLIP[nx], SIGN_FLIP[ny]
    tx, ty = KK_CUT_TOGGLE[nx], KK_CUT_TOGGLE[ny]
    cxy  = apply_op(root // 10, tx) * 10 + apply_op(root % 10, ty)
    csxy = apply_op(root // 10, SIGN_FLIP[tx]) * 10 + apply_op(root % 10, SIGN_FLIP[ty])
    return [(xy, ""), (yx, ""), (sxy, f"{ab(fx)}/{ab(fy)}"), (syx, f"{ab(fy)}/{ab(fx)}"),
            (cxy, f"{ab(tx)}/{ab(ty)}"),
            (csxy, f"{ab(SIGN_FLIP[tx])}/{ab(SIGN_FLIP[ty])}")]


def show_root_missing_combos(root, ops_list, strong, rec):
    """NON-EXISTING OP COMBINATIONS (display only), printed right below the
    ROOT OPS table: every x op used in TRANSITION OPERATIONS paired with
    every y op used there, keeping only pairs that never occur as a step;
    each applied to ROOT (same 6 columns). Rows ordered by priority:
    ★ recommended count, then S# (strong count), then op order.
    Thick green border."""
    ab    = lambda op: OP_ABBREV.get(op, op)
    mk    = lambda v: ("★" if v in rec else "S" if v in strong else " ")
    valid = [op for op in ops_list if '?' not in op]
    if not valid:
        return
    xs    = [o for o in ALL_OPS if o in {x for x, _ in valid}]
    ys    = [o for o in ALL_OPS if o in {y for _, y in valid}]
    seen  = set(valid)
    rows  = []
    for nx in xs:
        for ny in ys:
            if (nx, ny) in seen:
                continue
            six = _root_six(root, nx, ny)
            nr  = sum(1 for v, _ in six if v in rec)
            ns  = sum(1 for v, _ in six if v in strong or v in rec)
            rows.append((-nr, -ns, ALL_OPS.index(nx), ALL_OPS.index(ny), nx, ny, six, nr, ns))
    rows.sort()

    SW  = 15
    hdr = (f" {'Rank':>4}  {'x op':<6}{'y op':<6}{'Number':<8}{'yx':<5}{'s+xy (op)':<{SW}}"
           f"{'s+yx (op)':<{SW}}{'cut xy (op)':<{SW}}{'cut sign (op)':<{SW}}{'★#':>2} {'S#':>3} ")
    body = [f" NON-EXISTING OP COMBINATIONS → ROOT={root:02d}",
            f" {len(xs)} x ops × {len(ys)} y ops used in the transitions = {len(xs) * len(ys)} combos;"
            f" {len(seen & {(x, y) for x in xs for y in ys})} exist, {len(rows)} never occur",
            " Priority: ★ recommended first, then S# (strong values of 6)",
            "", hdr, "─" * len(hdr)]
    for k, (*_, nx, ny, six, nr, ns) in enumerate(rows, 1):
        (xy, _), (yx, _) = six[0], six[1]
        line = (f" {k:>4}  {ab(nx):<6}{ab(ny):<6}" + f"{xy:02d}{mk(xy)}".ljust(8)
                + f"{yx:02d}{mk(yx)}".ljust(5)
                + "".join(f"{v:02d}{mk(v)}({o})".ljust(SW) for v, o in six[2:])
                + f"{nr:>2} {ns:>3} ")
        body.append(line)
        if k < len(rows) and (nr, ns) != (rows[k][7], rows[k][8]) and nr + ns > 0 \
                and rows[k][7] + rows[k][8] == 0:
            body.append("·" * len(hdr))          # divider before the zero-strength rows
    body.append("─" * len(hdr))
    top = [r for r in rows if r[7] == rows[0][7] and r[8] == rows[0][8]] if rows else []
    if rows and (rows[0][7] or rows[0][8]):
        vals = sorted({v for r in top for v, _ in r[6] if v in strong or v in rec})
        _super_add("NX", vals)
        body.append(f" TOP PRIORITY: " + ", ".join(f"{ab(r[4])}/{ab(r[5])}" for r in top)
                    + "  → " + " ".join(f"{v:02d}{mk(v).strip()}" for v in vals))

    # UNIQUE VALUES box beside it: every value from the 6 columns once,
    # grouped ★ recommended / S strong / other, ascending, ×cells count.
    cnt = {}
    for r in rows:
        for v, _ in r[6]:
            cnt[v] = cnt.get(v, 0) + 1
    side = [f" UNIQUE VALUES ({len(cnt)})  from all 6 columns", ""]
    for label, test in (("★ RECOMMENDED", lambda v: v in rec),
                        ("S STRONG", lambda v: v in strong and v not in rec),
                        ("OTHER", lambda v: v not in strong and v not in rec)):
        vals = sorted(v for v in cnt if test(v))
        side.append(f" {label} ({len(vals)})")
        side.append(" " + "─" * 38)
        for k in range(0, len(vals), 4):
            side.append(" " + "".join(f"{v:02d}{mk(v).strip() or ' '} ×{cnt[v]:<3}".ljust(10)
                                      for v in vals[k:k + 4]))
        if not vals:
            side.append("  none")
        side.append("")
    side.append(" ×N = cells it appears in")

    # STARTS WITH ★ DIGITS box: the tens digits of the ★ RECOMMENDED values
    # in the UNIQUE box (e.g. 44★ 80★ → 4 and 8); every unique value
    # (★ / S / other) starting with one of them, per digit, ascending.
    digs  = sorted({v // 10 for v in cnt if v in rec})
    third = [f" STARTS WITH ★ DIGITS: {', '.join(map(str, digs)) or 'none'}",
             f" (from ★ {' '.join(f'{v:02d}' for v in sorted(v for v in cnt if v in rec)) or '-'})", ""]
    for d in digs:
        vals = sorted(v for v in cnt if v // 10 == d)
        third.append(f" {d} → {len(vals)} values")
        third.append(" " + "─" * 38)
        for k in range(0, len(vals), 4):
            third.append(" " + "".join(f"{v:02d}{mk(v).strip() or ' '} ×{cnt[v]:<3}".ljust(10)
                                       for v in vals[k:k + 4]))
        third.append("")
    if not digs:
        third.append("  no ★ recommended value in this table")
        third.append("")
    third.append(" ★ = recommended, S = strong")

    frames = [_green_frame(body), _green_frame(side), _green_frame(third)]
    widths = [len(_ANSI_RE.sub("", f[0])) for f in frames]
    print()
    for k in range(max(len(f) for f in frames)):
        line = "  " + "    ".join(f[k] if k < len(f) else " " * w
                                   for f, w in zip(frames, widths))
        print(line.rstrip())
    print()


_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def _green_frame(body):
    """Thick green border: bright-green heavy outer frame + darker-green
    double inner frame around the given lines."""
    g1, g2, rst = "\033[1;38;2;0;200;83m", "\033[38;2;0;140;60m", "\033[0m"
    iw = max(len(l) for l in body) + 2
    inner = ([f"{g2}╔{'═' * iw}╗{rst}"]
             + [f"{g2}║{rst} {l:<{iw - 2}} {g2}║{rst}" for l in body]
             + [f"{g2}╚{'═' * iw}╝{rst}"])
    return ([f"{g1}┏{'━' * (iw + 4)}┓{rst}"]
            + [f"{g1}┃{rst} {l} {g1}┃{rst}" for l in inner]
            + [f"{g1}┗{'━' * (iw + 4)}┛{rst}"])


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


DIAGRAM_ROWS = 40


def show_last_rows_diagram(rows):
    """Print transition chain for the last DIAGRAM_ROWS complete rows + trailing partial values."""
    # Separate trailing single-value rows (partial results) from complete rows
    split = len(rows)
    while split > 0 and len(rows[split - 1]) == 1:
        split -= 1
    lastN_complete = rows[max(0, split - DIAGRAM_ROWS):split]
    trailing       = rows[split:]
    last_seq       = lastN_complete + trailing   # combined display sequence

    sequence = []
    for row in last_seq:
        sequence.extend(row)

    if len(sequence) < 2:
        return

    trans_ops = []
    for i in range(len(sequence) - 1):
        a, b = sequence[i], sequence[i + 1]
        trans_ops.append((find_op(a // 10, b // 10), find_op(a % 10, b % 10)))

    # Row start offsets within `sequence`, and which edges cross a row boundary
    row_starts = []
    cumulative = 0
    for row in last_seq:
        row_starts.append(cumulative)
        cumulative += len(row)
    boundary_set = set(rs - 1 for rs in row_starts[1:])

    CONN = 9
    CELL = 15

    base_idx = split - len(lastN_complete)
    sep('═')
    print(f"\n  Last {len(lastN_complete)} rows of data grid:\n")
    for ri, row in enumerate(last_seq):
        rnum = base_idx + ri + 1
        print(f"  Row {rnum:>3}:  " + "   ".join(f"{v:02d}" for v in row))
    print()

    # One diagram block per data row — each block starts with the incoming
    # transition from the previous row's last value (if any), then runs
    # through every transition inside that row, ending on the row's own
    # last value. This keeps a row's full chain together instead of cutting
    # it off mid-row at a fixed column width.
    for ri, row in enumerate(last_seq):
        row_start = row_starts[ri]
        row_len   = len(row)
        edge_from = row_start - 1 if ri > 0 else row_start
        edge_to   = row_start + row_len - 1
        if edge_to <= edge_from:
            continue   # nothing to chain (e.g. a lone leading/pending value)

        top_line = '  '
        mid_line = '  '
        bot_line = '  '
        lbl_line = '  '

        for i in range(edge_from, edge_to):
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

        last_val  = sequence[edge_to]
        top_line += '┌────┐'
        mid_line += f'│ {last_val:02d} │'
        bot_line += '└────┘'

        print(top_line)
        print(mid_line)
        print(bot_line)
        print(lbl_line)
        print()

    # For EndPoint 10x10 Transitions — every op pair applied to EP (last value)
    _print_10x10("For EndPoint 10x10 Transitions:", sequence[-1],
                 set(trans_ops),
                 f"the T-transitions above (last {len(lastN_complete)} rows)",
                 last=trans_ops[-1])
    print()

    sep('═')
    print()


def show_next_op_after_last(rows):
    """NEXT OPERATION AFTER LAST OP — display only, does not affect scoring.

    Takes the last transition of the uploaded data (… → EP, e.g. 80 → 78 =
    x:-1 y:-2), finds every earlier transition anywhere in the uploaded data
    with that same x/y op pair, and lists the operation executed immediately
    after it (the next transition b → c)."""
    split = len(rows)
    while split > 0 and len(rows[split - 1]) == 1:
        split -= 1
    diag_base = sum(len(r) for r in rows[:max(0, split - DIAGRAM_ROWS)])

    seq, where = [], []          # flattened values + (row number, col) of each
    for ri, row in enumerate(rows):
        for ci, v in enumerate(row):
            seq.append(v)
            where.append((ri + 1, ci + 1))
    if len(seq) < 2 or seq[-1] < 0 or seq[-2] < 0:
        return

    def op_at(i):   # transition seq[i] → seq[i+1]
        a, b = seq[i], seq[i + 1]
        if a < 0 or b < 0:
            return None
        x, y = find_op(a // 10, b // 10), find_op(a % 10, b % 10)
        return None if '?' in (x, y) else (x, y)

    last_i  = len(seq) - 2
    last_op = op_at(last_i)
    if last_op is None:
        return
    ab = lambda op: OP_ABBREV.get(op, op)

    matches = []
    for i in range(last_i - 1):          # need a following transition i+1
        if op_at(i) == last_op:
            nxt = op_at(i + 1)
            if nxt is not None:
                matches.append((i, nxt))

    sep('═')
    print(f"\n  NEXT OPERATION AFTER LAST OP   (last op {seq[-2]:02d} → {seq[-1]:02d} = "
          f"x:{ab(last_op[0])}  y:{ab(last_op[1])}, searched in all uploaded data)\n")
    if not matches:
        print("  This op pair never occurred earlier in the uploaded data.\n")
        sep('═')
        print()
        return

    ep    = seq[-1]
    left  = ["", f"{'Pos':<8}{'Row':<7}{'Matched (x/y)':<22}{'Next transition':<18}{'next x op':<11}next y op",
             "─" * 74]
    # Beside it, row for row: that possible op applied to EP → its number
    # s+xy / s+yx show the sign-flipped ops they use in brackets
    # (tens op/units op), e.g. -2/c+1 → s+xy 48 (+2/c-1), s+yx 66 (c-1/+2)
    SW    = 14
    # cut xy / cut sign: same rule as the KK tables — each op cut-toggled
    # (nc↔cut, +1↔c+1 …), cut sign = toggled ops sign-flipped; ops in brackets
    rhdr  = (f" {'x op':<6}{'y op':<6}{'Number':>6}  {'yx':>3}   {'s+xy (op)':<{SW}}{'s+yx (op)':<{SW}}"
             f"{'cut xy (op)':<{SW}}{'cut sign (op)':<{SW}}")
    rtitl = f" POSSIBLE OPS → EP={ep:02d} "
    iw    = len(rhdr)
    right = ["╔" + rtitl.center(iw, "═") + "╗", "║" + rhdr + "║", "╟" + "─" * iw + "╢"]
    vals  = []                   # every value in the 4 columns, with repeats
    prio  = defaultdict(list)    # family → rows where 2+ distinct values share it
    row_vals = []                # the 4 values of each row, in table order
    for i, (nx, ny) in matches:
        tpos = f"[T{i + 1 - diag_base}]" if i >= diag_base else "-"
        rnum = where[i][0]
        mtxt = f"{seq[i]:02d} → {seq[i+1]:02d}  {ab(last_op[0])}/{ab(last_op[1])}"
        ntxt = f"{seq[i+1]:02d} → {seq[i+2]:02d}"
        left.append(f"{tpos:<8}{rnum:<7}{mtxt:<22}{ntxt:<18}{ab(nx):<11}{ab(ny)}")
        xy, yx, sxy, syx = compute_variants(ep, nx, ny)
        vals += [xy, yx, sxy, syx]
        row_vals.append((xy, yx, sxy, syx))
        byfam = defaultdict(set)
        for v in (xy, yx, sxy, syx):
            byfam[FAMILY_MAP[v]].add(v)
        for fam, members in byfam.items():
            if len(members) >= 2:
                prio[fam].append(sorted(members))
        fx, fy = ab(SIGN_FLIP[nx]), ab(SIGN_FLIP[ny])
        tx, ty = KK_CUT_TOGGLE[nx], KK_CUT_TOGGLE[ny]
        cxy    = apply_op(ep // 10, tx) * 10 + apply_op(ep % 10, ty)
        csxy   = apply_op(ep // 10, SIGN_FLIP[tx]) * 10 + apply_op(ep % 10, SIGN_FLIP[ty])
        right.append("║" + f" {ab(nx):<6}{ab(ny):<6}" + f"{xy:02d}".rjust(6) + f"{yx:02d}".rjust(5)
                     + "   " + f"{sxy:02d} ({fx}/{fy})".ljust(SW)
                     + f"{syx:02d} ({fy}/{fx})".ljust(SW)
                     + f"{cxy:02d} ({ab(tx)}/{ab(ty)})".ljust(SW)
                     + f"{csxy:02d} ({ab(SIGN_FLIP[tx])}/{ab(SIGN_FLIP[ty])})".ljust(SW) + "║")
    right.append("╚" + "═" * iw + "╝")

    # 40 NUMBERS: 4 per tens digit 0-9 from the POSSIBLE OPS values. Values
    # that occur directly rank first (by count); the rest are composed from
    # the tens digit + the most frequent units digits in the table
    # (e.g. 07 and 58 → 08).
    exact = defaultdict(int)
    units = defaultdict(int)
    for v in vals:
        exact[v] += 1
        units[v % 10] += 1
    # PRIORITY FAMILY: a family with 2+ different values in the same row
    # (e.g. 76 and 21 in one row → 12 FAMILY). Only the family paired in the
    # most rows (ties kept) gets priority; its members go first for their
    # tens digit.
    top  = max((len(r) for r in prio.values()), default=0)
    prio = {f: r for f, r in prio.items() if len(r) == top}
    fam_rank = {f: 1 for f in prio}
    mark = lambda n: ("F" if n in pset else "") + ("*" if exact[n] else "")
    pset = {v for f in fam_rank for v in FAMILY_MEMBERS[f]}
    ttl  = " 40 NUMBERS (4 per digit) "
    rows40 = []
    picks40 = []
    for d in range(10):
        pick = sorted((d * 10 + u for u in range(10)),
                      key=lambda n: (-fam_rank.get(FAMILY_MAP[n], 0), -exact[n],
                                     -units[n % 10], n))[:4]
        picks40 += pick
        rows40.append(f" {d} →  " + "  ".join(f"{n:02d}{mark(n):<2}" for n in pick) + " ")
    notes = [" * = in table, else composed",
             " F = priority family member"]
    for f, rs in sorted(prio.items()):
        pairs = sorted({tuple(r) for r in rs})
        notes.append(f" Priority: {f.replace(' FAMILY', '')} family ({len(rs)} row{'s' * (len(rs) > 1)}: "
                     + ", ".join("/".join(f"{v:02d}" for v in r) for r in pairs) + ")")
    iw2    = max([len(ttl)] + [len(r) for r in rows40] + [len(n) + 1 for n in notes])
    right2 = ["╔" + ttl.center(iw2, "═") + "╗",
              "║" + " Digit  Numbers".ljust(iw2) + "║",
              "╟" + "─" * iw2 + "╢"]
    right2 += ["║" + r.ljust(iw2) + "║" for r in rows40]
    right2 += ["╟" + "─" * iw2 + "╢"]
    right2 += ["║" + n.ljust(iw2) + "║" for n in notes]
    right2 += ["╚" + "═" * iw2 + "╝"]

    # FIRST 4 ROWS → 40 NUMBERS: the 16 values of the first 4 POSSIBLE OPS
    # rows, each expanded by cut tens / cut units / cut both / reverse
    # (66=11, 53=03, 07=02, 31=13, 71=21=26). Per tens digit: values in
    # those rows first (*), then the most-derived ones.
    src    = [v for r in row_vals[:4] for v in r]
    direct = defaultdict(int)
    derived = defaultdict(int)
    for v in src:
        direct[v] += 1
        a, b = v // 10, v % 10
        for x in {a, cut(a)}:
            for y in {b, cut(b)}:
                for n in {x * 10 + y, y * 10 + x}:
                    derived[n] += 1
    ttl3  = f" FIRST {len(row_vals[:4])} ROWS → 40 NUMBERS "
    rows3 = []
    picks3 = []
    for d in range(10):
        pick = sorted((d * 10 + u for u in range(10)),
                      key=lambda n: (-direct[n], -derived[n], -units[n % 10], n))[:4]
        picks3 += pick
        rows3.append(f" {d} →  " + "  ".join(f"{n:02d}{'*' if direct[n] else ' '} " for n in pick))
    notes3 = [" From: " + " ".join(f"{v:02d}" for v in src[:8]),
              "       " + " ".join(f"{v:02d}" for v in src[8:]),
              " * = in those rows, else cut/reverse"]
    iw3 = max([len(ttl3)] + [len(r) for r in rows3] + [len(n) + 1 for n in notes3])
    right2 += ["", "╔" + ttl3.center(iw3, "═") + "╗",
               "║" + " Digit  Numbers".ljust(iw3) + "║",
               "╟" + "─" * iw3 + "╢"]
    right2 += ["║" + r.ljust(iw3) + "║" for r in rows3]
    right2 += ["╟" + "─" * iw3 + "╢"]
    right2 += ["║" + n.ljust(iw3) + "║" for n in notes3]
    right2 += ["╚" + "═" * iw3 + "╝"]

    # STARTING DIGITS OF FIRST 4 ROWS: tens digits seen in the first 4
    # POSSIBLE OPS rows; every number in the whole POSSIBLE OPS table that
    # starts with one of them, unique and sorted, one line per digit
    # (wrapped 8 per line). Printed directly beside the POSSIBLE OPS box.
    digs  = sorted({v // 10 for r in row_vals[:4] for v in r})
    uniqv = sorted(set(vals))
    lines4 = []
    for d in digs:
        nums = [v for v in uniqv if v // 10 == d]
        for k in range(0, max(len(nums), 1), 8):
            head = f" {d} →  " if k == 0 else "      "
            lines4.append(head + "  ".join(f"{v:02d}" for v in nums[k:k + 8]))
    total = sum(1 for v in uniqv if v // 10 in digs)
    _super_add("PO", vals)
    _super_add("40", picks40)
    _super_add("F4", picks3)
    _super_add("SW", [v for v in uniqv if v // 10 in digs])
    ttl4  = f" STARTS WITH {'/'.join(map(str, digs))} "
    notes4 = [f" {total} numbers from the whole table",
              " (digits = first 4 rows)"]
    iw4 = max([len(ttl4) + 4] + [len(x) + 1 for x in lines4 + notes4])
    right4 = ["╔" + ttl4.center(iw4, "═") + "╗",
              "║" + " Digit  Numbers".ljust(iw4) + "║",
              "╟" + "─" * iw4 + "╢"]
    right4 += ["║" + x.ljust(iw4) + "║" for x in lines4]
    right4 += ["╟" + "─" * iw4 + "╢"]
    right4 += ["║" + x.ljust(iw4) + "║" for x in notes4]
    right4 += ["╚" + "═" * iw4 + "╝"]

    lw = max(len(l) for l in left) + 4
    rw = max(len(r) for r in right) + 4
    r4w = max(len(r) for r in right4) + 4
    for k in range(max(len(left), len(right), len(right2), len(right4))):
        l  = left[k] if k < len(left) else ""
        r  = right[k] if k < len(right) else ""
        r4 = right4[k] if k < len(right4) else ""
        r2 = right2[k] if k < len(right2) else ""
        print(f"  {l:<{lw}}{r:<{rw}}{r4:<{r4w}}{r2}".rstrip())
    print()

    counts = defaultdict(int)
    for _, nop in matches:
        counts[nop] += 1
    # Left: unique next-op pairs.  Right (beside it): each pair applied to EP.
    ep = seq[-1]
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    left = [f"Next-op pairs ({len(matches)} occurrences, {len(counts)} unique):", "", ""]
    left += [f"  x:{ab(nx):<5} y:{ab(ny):<5}  ×{c}" for (nx, ny), c in ranked]
    right = [f"APPLY ALL {len(counts)} UNIQUE OPS TO EP={ep:02d}",
             f"{'#':>2}  {'x op':<6}{'y op':<6}{'xy':>4}{'yx':>5}{'s+xy':>6}{'s+yx':>6}"]
    for k, ((nx, ny), c) in enumerate(ranked, 1):
        xy, yx, sxy, syx = compute_variants(ep, nx, ny)
        right.append(f"{k:>2}  {ab(nx):<6}{ab(ny):<6}  {xy:02d}   {yx:02d}    {sxy:02d}    {syx:02d}")
    right.insert(2, "─" * len(right[1]))

    # Triple border in Indian flag colours: saffron (outer), white, green (inner).
    flag = [f"\033[38;2;{c}m" for c in ("255;153;51", "255;255;255", "19;136;8")]
    rst  = "\033[0m"
    iw   = max(len(s) for s in right) + 2                 # inner width incl. 1-space pad
    body = [f" {s:<{iw - 2}} " for s in right]
    for lvl in range(2, -1, -1):                          # wrap green, then white, then saffron
        c, w = flag[lvl], iw + 2 * (2 - lvl)
        body = ([f"{c}╔{'═' * w}╗{rst}"]
                + [f"{c}║{rst}{s}{c}║{rst}" for s in body]
                + [f"{c}╚{'═' * w}╝{rst}"])
    right = body
    left  = left[:1] + [""] * 3 + left[1:]                # keep op rows beside their values
    width = max(len(s) for s in left) + 6
    for i in range(max(len(left), len(right))):
        l = left[i] if i < len(left) else ""
        r = right[i] if i < len(right) else ""
        print(f"  {l:<{width}}{r}".rstrip())
    print("\n  Pos [T#] = position in the chain diagram above (\"-\" = earlier than the diagram).\n")
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
    # Grid width varies by dataset (5, 6, or 7 columns) -- detect it from the data
    # instead of assuming 7, so this signal keeps working after a reset to a
    # narrower grid (single-value appended-result lines are width 1 and excluded).
    if rows:
        _width_counts = {}
        for _row in rows[:-1]:
            if len(_row) >= 5:
                _width_counts[len(_row)] = _width_counts.get(len(_row), 0) + 1
        _grid_width = max(_width_counts, key=_width_counts.get) if _width_counts else 7
        _col_idx = len(rows[-1])  # 0-indexed position of the prediction in its row
        if _col_idx >= _grid_width:
            _col_idx = 0
        _col_freq = {}
        for _row in rows[:-1]:
            if len(_row) == _grid_width and _col_idx < _grid_width:
                v = _row[_col_idx]
                if v < 0:
                    continue
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
    #
    # Third ablation study (2026-07-02, checkpoint audit at D497): tested every signal family
    # across BOTH the D341-D446 (106 rounds) and D447-D497 (51 rounds) windows independently,
    # then combined (157 rounds total, spanning a full dataset reset), on the ALREADY-FIXED
    # engine above. ChainMiss (all 4 variants) was the only family showing a CONSISTENT
    # positive effect on both independent windows when removed (+0.9pp on D341-D446, +7.9pp
    # on D447-D497; combined 33.1%->36.3%, +5 hits over 157 rounds). AllChainBase and
    # NearMiss-1D showed effects but flipped sign between windows (net noise, not touched,
    # per Universal Coverage rule). Obs3 showed a small consistent positive effect but was
    # fully redundant with the ChainMiss fix (identical combined hit count when both removed
    # vs ChainMiss alone) — not added, to avoid an unnecessary extra filter with zero marginal
    # benefit. ChainMiss had previously tested as protective on smaller single-window samples
    # (D273-D330, D341-D446 alone) BEFORE the CompOp/Obs1 fix — signal interactions shifted
    # once those were removed, which is why this is a re-test on the current engine, not a
    # contradiction of past findings.
    _ablated_prefixes = ('CutBoth', 'CbRev', 'Reverse', 'CutUnits', 'CutTens', 'PredNeighbor', 'TableProx',
                         'CompOp-xy', 'CompOp-yx', 'CompOp-sxy', 'CompOp-syx', 'Obs1', 'Obs1B',
                         'ChainMiss-x1D', 'ChainMiss-x1D-yx', 'ChainMiss-y1D', 'ChainMiss-y1D-yx')
    for _av in list(scores.keys()):
        _kept = [r for r in scores[_av] if not any(r.startswith(p) for p in _ablated_prefixes)]
        if _kept:
            scores[_av] = _kept
        else:
            del scores[_av]

    # Rank: sort by total weight.
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
        if len(top4) == 40:
            break
    # Forced missing-set (TYPE B NEW) slot injection — DISABLED (2026-07-05).
    # Originally forced >=10 TYPE B NEW candidates into top-30 on the assumption
    # that guaranteeing coverage would help, since ~68% of results are TYPE B.
    # Backtest-verified across all 3 dataset windows (362 rounds) that this was
    # net HARMFUL: it displaces genuinely-scored candidates near the bottom of
    # the natural top-30 with low/zero-signal forced picks. Disabling (force_n=0,
    # so this block never fires) improved every window: D341-D446 34->38 hits,
    # D447-D592 47->51, D593-current 33->35 (+10 hits / 362 rounds combined,
    # 31.5%->34.3%). See feedback_script_changes.md ("Forced TYPE B NEW slot
    # injection removed") for the full investigation (started from a user
    # question about whether TYPE B probability could be predicted in advance
    # from table size — it can, table size correlates with TYPE B rate, but
    # the actionable finding was that the existing forcing mechanism built on
    # that same intuition was actively hurting, not that a smarter dynamic
    # version helps — dynamic scaling by table size was tried first and also
    # underperformed disabling it outright).
    _miss_in_top = sum(1 for v, _, _ in top4 if v in _missing_set_final)
    _table_size = len(_tprox_set)
    _force_n = 0
    _needed_miss = max(0, _force_n - _miss_in_top)
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
        top4 = top4[:40 - len(_actual_force)]
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
    print("  ║             30  STRONG  PREDICTIONS          🔴=top-16      ║")
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
        # 🔴 renders double-width in most terminals but counts as 1 char in
        # Python's len() — trim the reason field by 1 on marked rows so the
        # right border ║ still lines up with unmarked rows.
        marked = rank <= 16
        mark = "🔴" if marked else "  "
        rwidth = 34 if marked else 35
        reason_str = " + ".join(lbl_parts)[:rwidth]
        line = f"  ║{mark}#{rank:<2} →  {val:02d}   score={score:>2}   {reason_str:<{rwidth}}║"
        if marked:
            print(f"\033[91m{line}\033[0m")
        else:
            print(line)
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print("  (🔴 = ranks 1-16, marked for visual grouping only — backtesting found")
    print("   no accuracy difference between ranks 1-16 and 17-30; see memory)")
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

_WEEK_HEADER_RE = re.compile(r'(\d{2}/\d{2}/\d{4})\s*\n\s*[Tt]o\s*\n\s*(\d{2}/\d{2}/\d{4})')


def is_weekly_archive_format(text):
    """Detect a real weekly result archive (dd/mm/yyyy ... To ... dd/mm/yyyy blocks,
    each holding 7 days of open-panna/jodi/close-panna data) rather than a plain
    numeric grid. At least 2 week-header matches avoids misfiring on a normal
    grid that happens to contain one stray date-like token."""
    return len(_WEEK_HEADER_RE.findall(text)) >= 2


def parse_weekly_archive(text):
    """Extract one JODI (the real 2-digit result) per day from a weekly archive.
    Per-day data is a repeating [open-panna-digit, open-panna-digit,
    open-panna-digit, JODI, close-panna-digit, close-panna-digit,
    close-panna-digit] pattern, but panna digits are printed one-per-line
    (single characters) while JODI is always a genuine 2-character token
    (e.g. "08", "00") -- so filtering the whole stream for tokens matching
    ^\\d{2}$ recovers the jodi reliably even when rigid 7-token positional
    chunking would break near '*' void-day runs (confirmed 2026-08-06: a
    week's '*' count doesn't always cleanly replace a whole multiple-of-7
    span, so position-based chunking silently misaligns after the first
    such week; the literal-2-digit-token filter doesn't have that failure
    mode since it never assumes a fixed token count per day).
    Weeks with fewer than 7 real values are padded with -1 at the end, per
    the established missing-value convention -- EXCEPT the single LAST week,
    which is left short if it comes up that way. A short week in the middle
    of the archive means a real void/'*' day (confirmed missing, pad it);
    a short LAST week means the live result for that day just hasn't
    happened yet (it's pending, not missing) -- padding it would fabricate
    a sentinel for a day that may still get a real result appended later,
    and would also make the endpoint/root computation use a fake -1 instead
    of the true last confirmed value (user-confirmed 2026-08-06 after a
    resend without that day's value: the day wasn't final, so it should
    reduce the window to end at the prior day, not get padded)."""
    matches = list(_WEEK_HEADER_RE.finditer(text))
    rows = []
    n = len(matches)
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < n else len(text)
        toks = text[start:end].split()
        jodis = [t for t in toks if re.fullmatch(r'\d{2}', t)]
        is_last_week = (i == n - 1)
        if not is_last_week:
            while len(jodis) < 7:
                jodis.append("-1")
        rows.append([int(v) for v in jodis])
    return rows


def load_data(source):
    """Parse lines into 2-D list of ints, skipping non-numeric tokens.
    Auto-detects a real weekly result archive (date-range headers) and routes
    it through parse_weekly_archive() instead of the normal per-line numeric
    parser, since that format needs multi-line-per-record extraction, not
    simple whitespace-split-and-int()."""
    lines = [line for line in source]
    text = "\n".join(lines)
    if is_weekly_archive_format(text):
        return parse_weekly_archive(text)

    rows = []
    for line in lines:
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


# KK Special family — add or remove the cut on an op (+1 ↔ cut+1, nc ↔ cut, …)
KK_CUT_TOGGLE = {
    'no_change': 'cut',   'cut':   'no_change',
    '+1':        'cut+1', 'cut+1': '+1',
    '-1':        'cut-1', 'cut-1': '-1',
    '+2':        'cut+2', 'cut+2': '+2',
    '-2':        'cut-2', 'cut-2': '-2',
}


def show_kk_special_family(rows, merge_counts=None, final40=None):
    """KK Special family result — display only, does not affect scoring.

    Over the same last-10-rows sequence shown in the diagram above, take the
    EndPoint (last value). Its tens digit t defines the bracket {t, cut(t)}
    (e.g. EP 08 → bracket 0/5). Every earlier cell whose tens digit is in that
    bracket contributes its own transition (cell → next cell) as an operation,
    which is applied to the EndPoint as xy / yx / sign+xy / sign+yx.

    Two extra cut-toggle columns: each op has its cut added or removed
    (+1 ↔ cut+1, nc ↔ cut, …) and is applied as xy ("cut xy"), then the
    toggled op is also sign-flipped ("cut sign": +1 → cut-1, cut+1 → -1).

    merge_counts: the KK CHAIN unique-value counts; when given, a KK MERGE
    box (special ∪ chain, no duplicates) prints beside the UNIQUE VALUES box.
    final40: the FINAL PREDICTIONS (40) values; when given together with
    merge_counts, a KK MERGE + FINAL 40 box prints beside the ranked box.
    """
    sequence = _kk_special_sequence(rows)
    if len(sequence) < 2 or sequence[-1] < 0:
        return []
    ep = sequence[-1]
    return _kk_table(sequence, ep, "KK SPECIAL FAMILY RESULT", "T",
                     "No bracket cells found in the last 10 rows.",
                     merge_counts=merge_counts, final40=final40, show_missing=True,
                     round_trip=True)


def _kk_special_sequence(rows):
    split = len(rows)
    while split > 0 and len(rows[split - 1]) == 1:
        split -= 1
    sequence = []
    for row in rows[max(0, split - 10):split] + rows[split:]:
        sequence.extend(row)
    return sequence


def show_kk_chain_family(group_index, grid_ep=None):
    """Same KK bracket rule, run over the TRANSITION CHAIN instead of the
    last 10 rows: the chain's own last value is the EP (e.g. chain ends 56 →
    bracket 5/0); chain cells whose tens digit is in that bracket lend their
    transition op (Op N), applied to that last value. Display only."""
    if len(group_index) < 2 or group_index[-1] < 0:
        return []
    return _kk_table(list(group_index), group_index[-1], "KK CHAIN FAMILY RESULT", "Op",
                     "No bracket cells found in the transition chain.",
                     show_missing=True, frame_label="WIN - WIN", rrr=True, grid_ep=grid_ep)


def kk_chain_unique_counts(group_index):
    """KK CHAIN unique values → count across all 6 value columns (silent)."""
    if len(group_index) < 2 or group_index[-1] < 0:
        return {}
    return _kk_unique_counts(_kk_entries(list(group_index), group_index[-1]))


def _kk_entries(sequence, ep):
    t       = ep // 10
    bracket = sorted({t, cut(t)})
    entries = []
    for i in range(len(sequence) - 1):
        a, b = sequence[i], sequence[i + 1]
        if a < 0 or b < 0 or a // 10 not in bracket:
            continue
        x_op, y_op = find_op(a // 10, b // 10), find_op(a % 10, b % 10)
        if x_op == '?' or y_op == '?':
            continue
        tx, ty = KK_CUT_TOGGLE[x_op], KK_CUT_TOGGLE[y_op]
        cxy  = apply_op(t, tx) * 10 + apply_op(ep % 10, ty)
        csxy = apply_op(t, SIGN_FLIP[tx]) * 10 + apply_op(ep % 10, SIGN_FLIP[ty])
        entries.append((i + 1, a, b, x_op, y_op,
                        compute_variants(ep, x_op, y_op) + (cxy, csxy)))
    return entries


def _kk_unique_counts(entries):
    """Count of each value across all 6 value columns (not once per row)."""
    counts = {}
    for *_, vals in entries:
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
    return counts


def _kk_box(title, items, cols=3, cellw=20):
    """# / Num / Count box as a list of lines, 3 entries per line."""
    inner = cols * cellw
    lines = ["  ╔" + "═" * inner + "╗",
             "  ║" + title.center(inner) + "║",
             "  ╠" + "═" * inner + "╣",
             "  ║" + "".join(" #   Num   Count    ".ljust(cellw) for _ in range(cols)) + "║",
             "  ╟" + "─" * inner + "╢"]
    for start in range(0, len(items), cols):
        line = ""
        for k, (v, c) in enumerate(items[start:start + cols]):
            line += f" {start + k + 1:>2}   {v:02d}    x{c}".ljust(cellw)
        lines.append("  ║" + line.ljust(inner) + "║")
    lines.append("  ╚" + "═" * inner + "╝")
    return lines


def _kk_vertical_box(title, values, rows=10, cellw=6):
    """Numbers-only box with values running DOWN each column, `rows` per column."""
    ncols = max(1, -(-len(values) // rows))
    inner = max(ncols * cellw, len(title) + 4)
    blank = "  ║" + " " * inner + "║"
    # 5 header lines, same as _kk_box, so rows line up with boxes beside it
    lines = ["  ╔" + "═" * inner + "╗",
             blank,
             "  ║" + title.center(inner) + "║",
             blank,
             "  ╠" + "═" * inner + "╣"]
    for r in range(rows):
        line = ""
        for c in range(ncols):
            i = c * rows + r
            if i < len(values):
                line += f"  {values[i]:02d}".ljust(cellw)
        lines.append("  ║" + line.ljust(inner) + "║")
    lines.append("  ╚" + "═" * inner + "╝")
    return lines


def _print_side_by_side(left, *rights, gap=4):
    boxes  = [left] + list(rights)
    height = max(len(b) for b in boxes)
    vis    = lambda l: len(_ANSI_RE.sub("", l))     # width ignoring colour codes
    pad    = lambda l, w: l + " " * max(0, w - vis(l))
    widths = [max((vis(l) for l in b), default=0) for b in boxes]
    print()
    for i in range(height):
        parts = [(b[i] if i < len(b) else "") for b in boxes]
        line  = pad(parts[0], widths[0])
        for j in range(1, len(boxes)):
            line += " " * gap + pad(parts[j].lstrip(), widths[j] - 2)
        print(line.rstrip())


def _kk_missing_combos_box(first, rest, ep, n_exist, cellw=8):
    """# / x op / y op / xy / yx box: every x/y op combination (10 × 10) that
    never occurs as a row of the table, applied to EP. `first` = combos of
    ops already used in the table, `rest` = combos with any other op."""
    inner = max(5 * cellw, 40)
    lines = ["  ╔" + "═" * inner + "╗",
             "  ║" + "NON-EXISTING x/y COMBINATIONS".center(inner) + "║",
             "  ║" + f"10 x ops × 10 y ops − {n_exist} existing = {len(first) + len(rest)}".center(inner) + "║",
             "  ╠" + "═" * inner + "╣",
             "  ║" + (" #".ljust(cellw) + "x op".ljust(cellw) + "y op".ljust(cellw)
                      + "xy".ljust(cellw) + "yx").ljust(inner) + "║",
             "  ╟" + "─" * inner + "╢"]

    def row(i, xo, yo):
        xy, yx, *_ = compute_variants(ep, xo, yo)
        return "  ║" + (f" {i:>2}".ljust(cellw) + OP_ABBREV[xo].ljust(cellw)
                        + OP_ABBREV[yo].ljust(cellw) + f"{xy:02d}".ljust(cellw)
                        + f"{yx:02d}").ljust(inner) + "║"

    n = 0
    if first:
        lines.append("  ║" + " ops used in table:".ljust(inner) + "║")
        for xo, yo in first:
            n += 1
            lines.append(row(n, xo, yo))
    if rest:
        if first:
            lines.append("  ╟" + "┄" * inner + "╢")
        lines.append("  ║" + " with ops not used in table:".ljust(inner) + "║")
        for xo, yo in rest:
            n += 1
            lines.append(row(n, xo, yo))
    lines.append("  ╚" + "═" * inner + "╝")
    return lines


# KK Round Trip — drop the cut from an op (cut-1 → -1, cut → nc); plain ops stay
KK_CUT_REMOVE = {
    'no_change': 'no_change', 'cut':   'no_change',
    '+1':        '+1',        'cut+1': '+1',
    '-1':        '-1',        'cut-1': '-1',
    '+2':        '+2',        'cut+2': '+2',
    '-2':        '-2',        'cut-2': '-2',
}


def _yellow_dotted_frame(body):
    """Yellow dotted-line border around the given lines."""
    y, rst = "\033[1;38;2;255;214;0m", "\033[0m"
    iw = max(len(l) for l in body) + 2
    return ([f"  {y}┌{'┄' * iw}┐{rst}"]
            + [f"  {y}┆{rst} {l:<{iw - 2}} {y}┆{rst}" for l in body]
            + [f"  {y}└{'┄' * iw}┘{rst}"])


def _kk_round_trip_box(entries, ep, pos_prefix):
    """KK ROUND TRIP OPCODE — display only.

    Only the table rows whose source starts with cut(EP tens digit) take part.
    They cancel like nested brackets, newest rows first: of the cancelled rows
    the first pairs with the last, the rows between pair two by two. With an
    odd number of rows the oldest one stays outside every bracket — that row
    is the target. Its op with the cut removed (c-1 → -1, cut → nc) is the
    round trip opcode, applied to EP in the same 6 value columns."""
    t    = ep // 10
    rows = [e for e in entries if e[1] // 10 == cut(t)]
    tag  = lambda e: f"[{pos_prefix}{e[0]}]"
    body = [f"KK ROUND TRIP OPCODE:   (EP={ep:02d}, rows whose source starts with {cut(t)})", ""]
    if not rows:
        return _yellow_dotted_frame(body + [f"No rows start with {cut(t)} — no round trip."])

    target = rows[0] if len(rows) % 2 else None
    rest   = rows[1:] if target else rows
    pairs  = []
    if rest:
        pairs.append((rest[0], rest[-1]))
        inner = rest[1:-1]
        pairs += [(inner[i], inner[i + 1]) for i in range(0, len(inner), 2)]
    body.append(f"Rows ({len(rows)}):  " + "  ".join(f"{tag(e)} {e[1]:02d}→{e[2]:02d}" for e in rows))
    for k, (p, q) in enumerate(pairs):
        kind = "outer" if k == 0 and len(pairs) > 1 else "inner" if k else "pair "
        body.append(f"Cancelled ({kind}):  {tag(p)} {p[1]:02d}→{p[2]:02d} ({OP_ABBREV[p[3]]}/{OP_ABBREV[p[4]]})"
                    f"   ↔   {tag(q)} {q[1]:02d}→{q[2]:02d} ({OP_ABBREV[q[3]]}/{OP_ABBREV[q[4]]})")
    body.append("")
    if target is None:
        return _yellow_dotted_frame(body + ["All rows cancelled — no remaining target row."])

    pos, a, b, x_op, y_op, _ = target
    rx, ry = KK_CUT_REMOVE[x_op], KK_CUT_REMOVE[y_op]
    body += [f"Remaining target:     {tag(target)} {a:02d} → {b:02d}    x: {OP_ABBREV[x_op]}   y: {OP_ABBREV[y_op]}",
             f"Round trip opcode:    x: {OP_ABBREV[rx]}   y: {OP_ABBREV[ry]}    (cut removed)", ""]

    KW = 15
    xy, yx, sxy, syx = compute_variants(ep, rx, ry)[:4]
    tx, ty = KK_CUT_TOGGLE[rx], KK_CUT_TOGGLE[ry]
    cxy    = apply_op(t, tx) * 10 + apply_op(ep % 10, ty)
    csxy   = apply_op(t, SIGN_FLIP[tx]) * 10 + apply_op(ep % 10, SIGN_FLIP[ty])
    ab     = OP_ABBREV
    cells  = [(xy, ab[rx], ab[ry]), (yx, ab[ry], ab[rx]),
              (sxy, ab[SIGN_FLIP[rx]], ab[SIGN_FLIP[ry]]), (syx, ab[SIGN_FLIP[ry]], ab[SIGN_FLIP[rx]]),
              (cxy, ab[tx], ab[ty]), (csxy, ab[SIGN_FLIP[tx]], ab[SIGN_FLIP[ty]])]
    body += [f"{'x op':<7} {'y op':<7} "
             + "".join(f"{h:<{KW}}" for h in ('xy (op)', 'yx (op)', 'sign+xy (op)',
                                               'sign+yx (op)', 'cut xy (op)', 'cut sign (op)')),
             '─' * (16 + 6 * KW),
             f"{ab[rx]:<7} {ab[ry]:<7} " + "".join(f"{v:02d} ({o1}/{o2})".ljust(KW) for v, o1, o2 in cells)]
    return _yellow_dotted_frame(body)


# RRR — next operation derived from an existing one (user's rule, 2026-10-03):
#   new x = old y with its cut switched (added/removed) and its sign flipped
#   new y = old x with its cut switched, then one step down (nc → cut-1)
RRR_Y_NEXT = {
    'no_change': 'cut-1', '+1':    'cut',       '+2':    'cut+1',
    'cut-2':     'cut+2', 'cut-1': '-2',        'cut':   '-1',
    'cut+1':     'no_change', 'cut+2': '+1',    '-2':    '+2',
    '-1':        'cut-2',
}


def rrr_next_op(x_op, y_op):
    """RRR rule: (old x, old y) → (new x, new y)."""
    return SIGN_FLIP[KK_CUT_TOGGLE[y_op]], RRR_Y_NEXT[x_op]


def _rrr_frame(body):
    """Bold magenta heavy border with a centred RRR label."""
    m, rst = "\033[1;38;2;233;30;140m", "\033[0m"
    vis = lambda l: len(re.sub(r"\033\[[0-9;]*m", "", l))    # width ignoring colour codes
    iw = max(vis(l) for l in body) + 2
    return ([f"  {m}┏{'━' * iw}┓{rst}"]
            + [f"  {m}┃{rst} {l}{' ' * (iw - 2 - vis(l))} {m}┃{rst}" for l in body]
            + [f"  {m}┗{'━' * iw}┛{rst}"])


# RRR live record (results the user gave one by one after each declaration,
# 2026-10-03): the only change that beat chance is the running value's tens
# digit getting cut. Update these counts when more results are recorded.
RRR_LIVE = {
    'results': 998, 'tens_cut': 131, 'short_list': 188,
    'table_rounds': 988, 'table_hits': 127, 'table_chance': 33, 'declared': 953, 'declared_hits': 17,
    'band_hits': 85, 'units_hits': 85, 'second_hits': 20,
    'same_tens': 26,
    'rrr3_rounds': 684, 'rrr3_hits': 37, 'rrr3_rec_rounds': 685, 'rrr3_rec_hits': 250,
    'rrr3_same_rounds': 657, 'rrr3_same_hits': 12, 'rrr3_wide_rounds': 644, 'rrr3_wide_hits': 72, 'rrr3_yx_rounds': 639, 'rrr3_yx_hits': 73,
    'rrr3_strong_rounds': 635, 'rrr3_strong_hits': 125, 'rrr3_same2_rounds': 632, 'rrr3_same2_hits': 12,
    'rrr3_turn_rounds': 639, 'rrr3_turn_hits': 13, 'rrr3_sameyx_rounds': 639, 'rrr3_sameyx_hits': 6,
    'power_rounds': 574, 'power_hits': 423,
}


def _rrr_declared(grid_ep):
    """RRR DECLARED lines — display only. From the running value (grid EP):
    the tens-cut decade, one number (cut / c-1), the 5-number band around it,
    its units digit alone, the 18-number short list (decade + units digit
    elsewhere), a 2nd number (c+1 / c-1) and the decade that is not expected."""
    t, u  = grid_ep // 10, grid_ep % 10
    d1    = cut(t)
    L     = RRR_LIVE
    lines = [f"  RRR DECLARED  (running value = {grid_ep:02d})   — corrected from {L['results']} recorded results",
             f"    TENS-CUT DECADE   {d1}0 – {d1}9   {'tens digit cut':<28}"
             f"recorded {L['tens_cut']} of {L['results']} = {L['tens_cut'] / L['results']:.0%}  (chance 10%)"]
    num = d1 * 10 + apply_op(u, 'cut-1')
    lines.append(f"    DECLARED NUMBER   {num:02d}        {f'cut / c-1 on {grid_ep:02d}':<28}"
                 f"single number {L['declared_hits']} of {L['declared']}  (chance about 1 in 100)")
    # results mostly miss the declared number by one or two: the 5 numbers
    # around it inside the tens-cut decade (units wrap inside the decade)
    band = ' '.join(f"{d1 * 10 + (num % 10 + k) % 10:02d}" for k in range(-2, 3))
    lines.append(f"    NUMBER BAND       {band}  {'number ± 2':<22}"
                 f"recorded {L['band_hits']} of {L['results']} = {L['band_hits'] / L['results']:.0%}  (chance 5%)")
    # the declared number's units digit alone, and the same number one decade up
    lines.append(f"    UNITS DIGIT       ends in {num % 10}       {'units cut, one down':<22}"
                 f"recorded {L['units_hits']} of {L['results']} = {L['units_hits'] / L['results']:.0%}  (chance 10%)")
    # the two leans together: the tens-cut decade plus the declared units
    # digit in every other decade except the running value's own (18 numbers)
    extra = ' '.join(f"{d * 10 + num % 10:02d}" for d in range(10) if d not in (t, d1))
    lines.append(f"    SHORT LIST (18)   {d1}0 – {d1}9  and  {extra}")
    lines.append(f"    {'':<18}{'decade + units digit elsewhere':<38}"
                 f"recorded {L['short_list']} of {L['results']} = {L['short_list'] / L['results']:.0%}  (chance 18%)")
    num2 = apply_op(t, 'cut+1') * 10 + num % 10
    lines.append(f"    2nd NUMBER        {num2:02d}              {f'c+1 / c-1 on {grid_ep:02d}':<22}"
                 f"recorded {L['second_hits']} of {L['results']}  (chance about 1 in 100)")
    # what the recorded results rule out: the running value's own decade
    # rarely comes again in the next result
    lines.append(f"    SAME DECADE       {t}0 – {t}9   {'rare in the first 253':<28}"
                 f"recorded {L['same_tens']} of {L['results']} = {L['same_tens'] / L['results']:.0%}  (chance 10%)")
    # these leans come from the first 253 results; on the three datasets
    # since (76 results) every one of them is at its chance rate
    lines.append("    since result 254 (76 results): tens-cut 8, same decade 8, units digit 4, short list 11 — all at chance")
    return lines


# 3RRR — second rule from the WIN - WIN rows (display only). The last WIN - WIN
# row's source picks an earlier row of the same family (same number, or both
# digits cut: 99 ~ 44). That row's two ops cross over: the 1st crossing keeps
# old y as new x and moves old x one step further as new y (-1 → -2); when a
# later row already shows that pair, the 2nd crossing is taken: new x = the
# cut state of old y with old x's number (cut, -1 → c-1), new y = old x with
# the sign flipped (-1 → +1).
RRR3_STEP_OUT = {'+1': '+2', '-1': '-2'}


def _op_parts(op):
    """(has cut, number part) of an operation: 'cut-1' → (True, '-1')."""
    has_cut = op.startswith('cut')
    return has_cut, (op[3:] if has_cut else ('' if op == 'no_change' else op))


def _op_join(has_cut, num):
    return ('cut' + num) if has_cut else (num or 'no_change')


def rrr3_first(x_op, y_op):
    """1st crossing, or None when old x has no one-step-further form."""
    has_cut, num = _op_parts(x_op)
    if num not in RRR3_STEP_OUT:
        return None
    return y_op, _op_join(has_cut, RRR3_STEP_OUT[num])


def rrr3_second(x_op, y_op):
    """2nd crossing: (cut state of old y + number of old x, old x sign-flipped)."""
    return _op_join(_op_parts(y_op)[0], _op_parts(x_op)[1]), SIGN_FLIP[x_op]


# 3RRR, second rule: the op pairs of the WIN - WIN rows go through type
# combinations (C = cut±n, K = cut, I = ±n, N = nc). While no row has cut±n
# on both sides, the last row is crossed with cut on both sides and each
# number one step down (c+2 → c+1, cut → c-1).
RRR3_STEP_DOWN = {'+2': '+1', '+1': '', '': '-1', '-1': '-2'}
RRR3_STEP_UP   = {'-2': '-1', '-1': '', '': '+1', '+1': '+2'}


def _op_type(op):
    has_cut, num = _op_parts(op)
    return ('C' if num else 'K') if has_cut else ('I' if num else 'N')


def rrr3_both_cut(x_op, y_op):
    """Last row crossed, cut on both sides, numbers one step down; None when
    a number has no step down (-2)."""
    ny_num, nx_num = _op_parts(x_op)[1], _op_parts(y_op)[1]
    if nx_num not in RRR3_STEP_DOWN or ny_num not in RRR3_STEP_DOWN:
        return None
    return 'cut' + RRR3_STEP_DOWN[nx_num], 'cut' + RRR3_STEP_DOWN[ny_num]


def _rrr_nc_special(ep, row_ops):
    """NC/CUT SPECIAL (user, 2026-10-15): for every NEXT OPERATION row whose
    xy or yx is nc/cut, cut/nc or nc/nc, the row after it with its xy and
    yx modified every way — each side as is, sign flipped, cut switched,
    or both.  Also the trigger row's own old operation again on this EP,
    xy and yx (result 00 after 48, EP 45: Op4 90 -> 55 was c+1/cut).
    Returns [(trigger row, next row, [(number, 'x/y'), ...])]."""
    special = {('no_change', 'cut'), ('cut', 'no_change'), ('no_change', 'no_change')}
    def forms(o_):
        return list(dict.fromkeys([o_, SIGN_FLIP[o_], KK_CUT_TOGGLE[o_], KK_CUT_TOGGLE[SIGN_FLIP[o_]]]))
    out = []
    for k_ in range(len(row_ops) - 1):
        _, tx, ty = row_ops[k_][:3]
        if (tx, ty) not in special and (ty, tx) not in special:
            continue
        _, nx, ny = row_ops[k_ + 1][:3]
        seen, lst = set(), []
        for a_, b_ in ((nx, ny), (ny, nx)):
            for fx in forms(a_):
                for fy in forms(b_):
                    v_ = compute_variants(ep, fx, fy)[0]
                    if v_ not in seen:
                        seen.add(v_)
                        lst.append((v_, f"{OP_ABBREV[fx]}/{OP_ABBREV[fy]}"))
        # the trigger row's old operation again (result 00 after 48, EP 45)
        ox, oy = row_ops[k_][3:5]
        for a_, b_ in ((ox, oy), (oy, ox)):
            v_ = compute_variants(ep, a_, b_)[0]
            if v_ not in seen:
                seen.add(v_)
                lst.append((v_, f"{OP_ABBREV[a_]}/{OP_ABBREV[b_]}"))
        out.append((row_ops[k_], row_ops[k_ + 1], lst))
    return out


_X_STEP_SWITCH = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1',
                  'cut+1': 'cut+2', 'cut+2': 'cut+1', 'cut-1': 'cut-2', 'cut-2': 'cut-1'}


def _rrr_ocjp_xswitch(ep, lab):
    """OCJP companion (user, 2026-10-15: "26. 60 (-1/c+1) please include
    -2/c+1", result 50 after 33): the place's operation with the x step
    switched (1 <-> 2), y kept.  None when x has no step (nc, cut)."""
    rev = {v_: k_ for k_, v_ in OP_ABBREV.items()}
    lx, ly = lab.split('/')
    ox = _X_STEP_SWITCH.get(rev[lx])
    if ox is None:
        # x has no step (nc, cut): the y step switched instead (user,
        # 2026-10-15: "nc/+1 missed", 18 (nc/+2) -> 17 (nc/+1) after 45)
        oy = _X_STEP_SWITCH.get(rev[ly])
        if oy is None:
            return None
        return compute_variants(ep, rev[lx], oy)[0], f"{lx}/{OP_ABBREV[oy]}"
    return compute_variants(ep, ox, rev[ly])[0], f"{OP_ABBREV[ox]}/{ly}"


def _rrr_ocjp_more(ep, lab):
    """OCJP further companions (user, 2026-10-15: "+1/c-1 and +1/-1
    missed" after 09, and "-2/-1 misses" after 59 -> 04 on EP 25): the
    place's operation with the y step switched, and with both steps
    switched (-2/-2 -> -2/-1, -1/-1).  Only when both x and y carry a
    step (otherwise _rrr_ocjp_xswitch covers it)."""
    rev = {v_: k_ for k_, v_ in OP_ABBREV.items()}
    lx, ly = lab.split('/')
    ox, oy = _X_STEP_SWITCH.get(rev[lx]), _X_STEP_SWITCH.get(rev[ly])
    if ox is None or oy is None:
        return []
    return [(compute_variants(ep, rev[lx], oy)[0], f"{lx}/{OP_ABBREV[oy]}"),
            (compute_variants(ep, ox, oy)[0], f"{OP_ABBREV[ox]}/{OP_ABBREV[oy]}")]


def _rrr_ocjp_ycut(ep, lab, place=0):
    """OCJP # companions (result 86 after 04 on EP 80, nc/c+1: place 26
    held 81 (nc/+1), the same op with y cut off): when the place's x has
    no plain step (nc, cut) and y has a step, its y with the cut switched,
    for both y steps (nc/+1 -> nc/c+1, nc/c+2).  Also when x is a cut
    step (result 10 after 75 on EP 71, c-1/-1: place 6 held 14 (c-1/c-2)
    -> 10 (c-1/-1), 19 (c-1/-2)).  On the places 31-38 (°) for any x
    (result 25 after 40 on EP 12, +1/c-2: place 35 held 21 (+1/-1) and
    20* (+1/-2) -> 26 (+1/c-1), 25 (+1/c-2)).  On the places 1-8 for any
    x too (result 82 after 36 on EP 70, +1/+2: place 2 held 87 (+1/c+2)
    -> 82 (+1/+2), 81 (+1/+1)); replay of 754 rounds: 730 -> 732 hits,
    size +0.4 (3.0 expected) = chance, no loss.  When x is a plain or
    cut step, both x steps (c+1/+2 -> c+1/c+2, c+2/c+2 ...)."""
    rev = {v_: k_ for k_, v_ in OP_ABBREV.items()}
    lx, ly = lab.split('/')
    oy = rev[ly]
    if not (lx in ('nc', 'cut') or lx.startswith('c') or place > 30 or 1 <= place <= 8) or oy not in _X_STEP_SWITCH:
        return []
    # result 76 after 17 on EP 09 (series N, N31), c+2/c+2: place 19 held
    # 61 (c+1/+2) and 71+ (c+2/+2); the + companion's x step gets the y cut
    # switched too.  Replay 837 rounds: 817 -> 821 hits, size +0.64 (5.4
    # expected) = chance, no loss (only on the places 19-20: +3, +0.67)
    xs_ = [rev[lx]] + ([_X_STEP_SWITCH[rev[lx]]] if rev[lx] in _X_STEP_SWITCH else [])
    return [(compute_variants(ep, ox_, KK_CUT_TOGGLE[o_])[0], f"{OP_ABBREV[ox_]}/{OP_ABBREV[KK_CUT_TOGGLE[o_]]}")
            for ox_ in xs_ for o_ in (oy, _X_STEP_SWITCH[oy])]


def _rrr_ocjp_xcut(ep, lab, place=0):
    """OCJP % companions (result 15 after 29 on EP 40, c+2/cut: place 15
    held 65 (+2/cut), the same op with x cut off): on the places 15-18
    (y fixed at cut or nc), x with its cut switched, for both x steps
    (+2/cut -> c+2/cut, c+1/cut)."""
    rev = {v_: k_ for k_, v_ in OP_ABBREV.items()}
    lx, ly = lab.split('/')
    ox = rev[lx]
    # places 19-20 (the LAST row's own xy and yx) too, any y (result 84
    # after 70 on EP 55: place 20 held 34 (-2/-1), the result was c-2/-1)
    if not (15 <= place <= 18 and ly in ('nc', 'cut') or 19 <= place <= 20) or ox not in _X_STEP_SWITCH:
        return []
    return [(compute_variants(ep, KK_CUT_TOGGLE[o_], rev[ly])[0], f"{OP_ABBREV[KK_CUT_TOGGLE[o_]]}/{ly}")
            for o_ in (ox, _X_STEP_SWITCH[ox])]


def _rrr_ocjp_xflip(ep, lab, place=0):
    """OCJP ! companion (result 83 after 82 on EP 62, +2/+1: place 2 held
    43 (-2/+1), the same op with the x sign flipped): on the places 1-8,
    when x is a plain step (+-1, +-2), x with its sign flipped, y kept
    (-2/+1 -> +2/+1)."""
    rev = {v_: k_ for k_, v_ in OP_ABBREV.items()}
    lx, ly = lab.split('/')
    ox = rev[lx]
    if not 1 <= place <= 8 or ox not in ('+1', '+2', '-1', '-2'):
        return []
    return [(compute_variants(ep, SIGN_FLIP[ox], rev[ly])[0], f"{OP_ABBREV[SIGN_FLIP[ox]]}/{ly}")]


def _rrr_final4(cands, lists, tie_lists, place):
    """OCJP FINAL 4 (2026-10-15): among the OCJP numbers, the 4 that the
    most of the never-repaired lists also hold (RECOMMENDED, RRR table,
    same op again, WIDE, yx, 3RRR RESULT); ties: more of the other lists
    (STRONG 20, declared cell, NC/CUT SPECIAL), then the lower number
    (ranking by the earlier OCJP place instead gave 7.3%, noise).  Walk-forward on 436 past rounds
    (b c d f h i j k): 36 hits = 8.3% against 4.0% for any 4 numbers,
    the same in the old series (8.3%) and in J/K (8.2%).
    Returns [(number, [list names])]."""
    def votes(v):
        return [n_ for n_, l_ in lists.items() if v in l_]
    def tie(v):
        return sum(v in l_ for l_ in tie_lists)
    top = sorted(cands, key=lambda v: (-len(votes(v)), -tie(v), v))[:4]
    return [(v, votes(v)) for v in top]


# the old (x, y) operations of every RRR table row, set by _rrr_box
_RRR_OCJP_OLD = []


def _rrr_ocjp(ep, both_cut):
    """NEXT OPERATION-OCJP (user's screenshot, 2026-10-14): the two operations
    of the RRR table's LAST row, X/Y (xy) and Y/X (yx), worked into more
    operations on the EP.  s = sign flipped, r = cut switched.  The first 20
    are the user's list (from 61 (c-1/c-2), 52 (c-2/c-1) on EP 28); the
    next 10 (21-30) are their mirror forms; 31-38 are one operation on both
    sides with the sign flipped on one side (+1/-1), with and without cut.
    Returns (number, 'x/y', place 1-38, replaced) — every place a different
    operation (user, 2026-10-14)."""
    if len(both_cut) < 2:
        return []
    v_ = both_cut[-2][0]
    X, Y = find_op(ep // 10, v_ // 10), find_op(ep % 10, v_ % 10)
    # a LAST row with no step on either side (nc/cut, cut/nc, nc/nc,
    # cut/cut) can only make the EP's own 4 nc/cut forms; take the
    # nearest earlier row that has a step instead (result 34 after 74 on
    # EP 10: LAST row 15 nc/cut, 60 cut/nc -> OCJP was only 10 15 60 65)
    row_k = len(both_cut) - 2
    while X in ('no_change', 'cut') and Y in ('no_change', 'cut') and row_k >= 2:
        row_k -= 2
        v_ = both_cut[row_k][0]
        X, Y = find_op(ep // 10, v_ // 10), find_op(ep % 10, v_ % 10)
    # no row has a step at all (result 41 after 43 on EP 99, series N, N46:
    # the table's only row was LAST 49 cut/nc, 94 nc/cut, and OCJP was only
    # 44 49 94 99): take the LAST row's old operation (c+1/nc) instead.
    # Replay 853 rounds: 3 such rounds (I43, K34, N46), 0 -> 3 hits, but
    # OCJP then holds all 100 there — the hits come from size, not skill
    # (the previous round's operation instead: 2 of 3)
    if X in ('no_change', 'cut') and Y in ('no_change', 'cut') and _RRR_OCJP_OLD:
        X, Y = _RRR_OCJP_OLD[-1]
    if '?' in (X, Y):
        return []
    s, r = SIGN_FLIP, KK_CUT_TOGGLE
    user = [(r[s[X]], s[Y]), (r[s[Y]], s[X]), (r[s[X]], r[Y]), (r[s[Y]], r[X]),
            (s[Y], X), (s[X], s[Y]), (r[s[Y]], Y), (r[s[X]], X),
            ('cut', Y), ('cut', X), ('cut', s[Y]), ('cut', s[X]),
            ('no_change', s[Y]), ('no_change', s[X]),
            (s[X], 'cut'), (s[Y], 'cut'), (s[X], 'no_change'), (s[Y], 'no_change'),
            (X, Y), (Y, X)]
    mirror = [(s[X], Y), (s[Y], s[X]), (r[s[X]], Y), (r[s[Y]], X),
              ('no_change', Y), ('no_change', X),
              (X, 'cut'), (Y, 'cut'), (X, 'no_change'), (Y, 'no_change')]
    # 31-38 (user, 2026-10-14: "+1/-1 missed"): one operation on both sides,
    # the sign flipped on one side, with and without its cut
    same = []
    for o_ in (X, Y):
        same += [(o_, s[o_]), (s[o_], o_), (r[o_], r[s[o_]]), (r[s[o_]], r[o_])]
    # a place whose operation is already shown takes the next unused one
    # (user, 2026-10-14: "all are different operations"): every pair of
    # the two operations' forms (as is, s, r, r s), in that order
    forms = list(dict.fromkeys([X, Y, s[X], s[Y], r[X], r[Y], r[s[X]], r[s[Y]]]))
    spare = [(a_, b_) for a_ in forms for b_ in forms]
    places = user + mirror + same
    seen = set(places)                 # every place keeps its own operation first
    out, kept = [], set()
    for k_, op_ in enumerate(places):
        new_ = op_ in kept
        if new_:
            op_ = next((q_ for q_ in spare if q_ not in seen), None)
            if op_ is None:
                continue
            seen.add(op_)
        kept.add(op_)
        out.append((compute_variants(ep, op_[0], op_[1])[0], f"{OP_ABBREV[op_[0]]}/{OP_ABBREV[op_[1]]}", k_ + 1, new_))
    # 39 (result 59 after 59 on EP 04, cut/cut): the EP with both digits
    # cut, when no place above already shows it
    if ('cut', 'cut') not in kept:
        out.append((compute_variants(ep, 'cut', 'cut')[0], "cut/cut", 39, False))
    # 40 (result 20 after 64 on EP 20, nc/nc): the EP itself, when no
    # place above already shows it
    if ('no_change', 'no_change') not in kept:
        out.append((compute_variants(ep, 'no_change', 'no_change')[0], "nc/nc", 40, False))
        kept.add(('no_change', 'no_change'))
    # 41-42 (result 23 after 13 on EP 28, series N, N104: nc/cut; the
    # LAST row was 31 +1/c-2, 59 c-2/+1 and OCJP held the EP's cut/cut 73
    # and nc/nc 28 but not its nc/cut 23 or cut/nc 78; N101 left out the
    # same pair 22 77): the EP with one digit cut, always (before, only
    # when an earlier row stood in for a no-step LAST row)
    for j_, op_ in enumerate((('no_change', 'cut'), ('cut', 'no_change'))):
        if op_ not in kept:
            out.append((compute_variants(ep, op_[0], op_[1])[0],
                        f"{OP_ABBREV[op_[0]]}/{OP_ABBREV[op_[1]]}", 41 + j_, False))
            kept.add(op_)
    return out


def _rrr3_last(entries, ep):
    """(row, new x, new y, number) for the both-cut rule, or (None, reason)."""
    if not entries:
        return None, "no WIN - WIN row"
    used = next((p for p, _, _, x, y, _ in entries if _op_type(x) == 'C' and _op_type(y) == 'C'), None)
    if used is not None:
        return None, f"a row with cut±n on both sides already exists — no number from this rule"
    pos, a, b, x_op, y_op, _ = entries[-1]
    ops = rrr3_both_cut(x_op, y_op)
    if ops is None:
        return None, "last row has a -2: no step down — no number from this rule"
    nx = _rrr3_twice(ops[0], entries)
    return (pos, a, b, x_op, y_op, nx, ops[1], compute_variants(ep, nx, ops[1])[0]), ''


# the operation that turned the previous round's EP into the value that has
# just come (set by run(); empty when it cannot be worked out)
_RRR3_PREV = {}


def _rrr3_previous_op(rows, back=1):
    """(x op, y op) of the round `back` rounds ago: from the EP that round
    had — what followed the latest earlier occurrence of the value before it
    — to the value that came. None when the data does not show it."""
    flat = [v for row in rows for v in row]
    if len(flat) < back + 2 or flat[-back] < 0 or flat[-back - 1] < 0:
        return None
    prev, came = flat[-back - 1], flat[-back]
    for i in range(len(flat) - back - 2, -1, -1):
        if flat[i] == prev and flat[i + 1] >= 0:
            x_op, y_op = find_op(flat[i + 1] // 10, came // 10), find_op(flat[i + 1] % 10, came % 10)
            return None if '?' in (x_op, y_op) else (x_op, y_op)
    return None


def _rrr3_wide(entries, ep):
    """3RRR rule G — the clean single moves seen on middle rows, tried on every
    WIN - WIN row: not crossed with one side dropped to nc, one side one step
    down, or the cut switched on both sides; crossed with old y one step up
    (old x kept) or with both signs flipped. Returns [(number, label)]."""
    out = []
    def add(nx, ny):
        out.append((compute_variants(ep, nx, ny)[0], f"{OP_ABBREV[nx]}/{OP_ABBREV[ny]}"))
    for _, _, _, x_op, y_op, _ in entries:
        (cx, nx_), (cy, ny_) = _op_parts(x_op), _op_parts(y_op)
        add('no_change', y_op)
        add(x_op, 'no_change')
        if ny_ in RRR3_STEP_DOWN:
            add(x_op, _op_join(cy, RRR3_STEP_DOWN[ny_]))
        if nx_ in RRR3_STEP_DOWN:
            add(_op_join(cx, RRR3_STEP_DOWN[nx_]), y_op)
        add(KK_CUT_TOGGLE[x_op], KK_CUT_TOGGLE[y_op])
        if ny_ in RRR3_STEP_UP:
            add(_op_join(cy, RRR3_STEP_UP[ny_]), x_op)
        add(SIGN_FLIP[y_op], SIGN_FLIP[x_op])
        # crossed, old y gaining a cut, old x kept
        if not cy:
            add(_op_join(True, ny_), x_op)
    return out


def _rrr3_keep(entries, ep, x_column=()):
    """3RRR rule C — the last row crossed plainly with the cut removed on both
    sides: new x = old y without its cut, new y = old x without its cut; an
    old x that came twice in the x column (WIN - WIN rows and the chain's
    last step) drops to nc instead. Returns
    (pos, a, b, x_op, y_op, new x, new y, number, C/C already used) or None."""
    if not entries:
        return None
    pos, a, b, x_op, y_op, _ = entries[-1]
    nx = _rrr3_twice(_op_join(False, _op_parts(y_op)[1]), entries)
    ny = 'no_change' if list(x_column).count(x_op) >= 2 else _op_join(False, _op_parts(x_op)[1])
    due = any(_op_type(e[3]) == 'C' and _op_type(e[4]) == 'C' for e in entries)
    return pos, a, b, x_op, y_op, nx, ny, compute_variants(ep, nx, ny)[0], due


def _rrr3_arrived(entries, ep, grid_ep):
    """3RRR rule D — every WIN - WIN row that ends at the running value is
    crossed with the cut switched and the sign flipped on both sides.
    Returns [(pos, a, b, x_op, y_op, new x, new y, number)]."""
    rows = []
    for pos, a, b, x_op, y_op, _ in entries:
        if b != grid_ep:
            continue
        nx = _rrr3_twice(SIGN_FLIP[KK_CUT_TOGGLE[y_op]], entries)
        ny = SIGN_FLIP[KK_CUT_TOGGLE[x_op]]
        rows.append((pos, a, b, x_op, y_op, nx, ny, compute_variants(ep, nx, ny)[0]))
    return rows


def _rrr3_change(old, new):
    """(words, cost) for how one op turned into another when two rows cross."""
    if old == new:
        return 'same', 0
    if new == 'no_change':
        return 'dropped to nc', 1
    (c0, n0), (c1, n1) = _op_parts(old), _op_parts(new)
    v0, v1 = int(n0 or 0), int(n1 or 0)
    if c0 == c1:
        if v0 and v1 == -v0:
            return 'sign flipped', 1
        if abs(v1 - v0) == 1:
            return ('one step up' if v1 > v0 else 'one step down'), 1
        return 'changed', 3
    word = 'cut added' if c1 else 'cut removed'
    if v1 == v0:
        return word, 1
    if v0 and v1 == -v0:
        return word + ' + sign flipped', 2
    if abs(v1 - v0) == 1:
        return word + ' + one step', 2
    return 'changed', 3


def _rrr3_trail(entries):
    """How each WIN - WIN row came from an earlier one by crossing: for every
    row the earlier row needing the fewest changes (latest wins a tie), as
    (pos, from_pos, old y, new x, words, old x, new y, words)."""
    out = []
    for k in range(1, len(entries)):
        pos, _, _, x_op, y_op, _ = entries[k]
        best = None
        for j in range(k):
            fpos, _, _, fx, fy, _ = entries[j]
            (wx, cx), (wy, cy) = _rrr3_change(fy, x_op), _rrr3_change(fx, y_op)
            # the row just before wins whenever both its changes have a name
            if j == k - 1 and 'changed' not in (wx, wy):
                cx = cy = -1
            if best is None or cx + cy <= best[0]:
                best = (cx + cy, fpos, fy, wx, fx, wy, j)
        _, fpos, fy, wx, fx, wy, j = best
        xs = [e[3] for e in entries[:k]]
        if wx == 'same' and x_op not in xs:
            wx += f" ({OP_ABBREV[x_op]} new in x)"
        if wy == 'dropped to nc' and xs.count(fx) >= 2:
            wy += f" ({OP_ABBREV[fx]} x{xs.count(fx)} in x)"
        out.append((pos, fpos, fy, x_op, wx, fx, y_op, wy))
    return out


def _rrr3_twice(op, entries):
    """An op that already came twice in the x column is not used as a new x
    again: it drops to nc."""
    return 'no_change' if [e[3] for e in entries].count(op) >= 2 else op


def _rrr3_rows(entries, ep):
    """3RRR picks: (pos, a, b, x_op, y_op, first, used_pos, nx, ny, number) for
    every earlier WIN - WIN row in the family of the last row's source."""
    if len(entries) < 2:
        return None, []
    la     = entries[-1][1]
    family = {la, cut(la // 10) * 10 + cut(la % 10)}
    rows   = []
    for i, (pos, a, b, x_op, y_op, _) in enumerate(entries[:-1]):
        if a not in family:
            continue
        first = rrr3_first(x_op, y_op)
        used  = next((p for p, _, _, x2, y2, _ in entries[i + 1:] if (x2, y2) == first), None)
        nx, ny = rrr3_second(x_op, y_op) if (first is None or used is not None) else first
        nx = _rrr3_twice(nx, entries)
        # the same row crossed with the cut switched and the sign flipped on both sides
        sx, sy = _rrr3_twice(SIGN_FLIP[KK_CUT_TOGGLE[y_op]], entries), SIGN_FLIP[KK_CUT_TOGGLE[x_op]]
        rows.append((pos, a, b, x_op, y_op, first, used, nx, ny, compute_variants(ep, nx, ny)[0],
                     sx, sy, compute_variants(ep, sx, sy)[0]))
    return la, rows


def _rrr_box(sequence, entries, ep, pos_prefix, grid_ep=None):
    """RRR table — display only. Every WIN - WIN row (plus the chain's own
    last step, marked LAST) gives a next operation by the RRR rule, applied
    to the EP as xy and yx. With the running value (grid_ep) it also prints
    the RRR DECLARED lines and stars (★) table numbers in the tens-cut decade."""
    src = [(pos, a, b, x_op, y_op, '') for pos, a, b, x_op, y_op, _ in entries]
    a, b = sequence[-2], sequence[-1]
    if a >= 0 and b >= 0:
        lx, ly = find_op(a // 10, b // 10), find_op(a % 10, b % 10)
        if '?' not in (lx, ly):
            last = len(sequence) - 1
            if src and src[-1][0] == last:
                src[-1] = src[-1][:5] + ('LAST',)
            else:
                src.append((last, a, b, lx, ly, 'LAST'))
    KW   = 15
    head = (f"  {'Pos':<12} {'Source':<9} {'old x':<6} {'old y':<6}    "
            f"{'new x':<6} {'new y':<6}  {'xy (op)':<{KW}}{'yx (op)':<{KW}}")
    body = [f"RRR:  NEXT OPERATION → EP={ep:02d}".center(len(head)), "", head, '─' * len(head)]
    live = grid_ep is not None and grid_ep >= 0
    star = (lambda v: '★' if v // 10 == cut(grid_ep // 10) else ' ') if live else (lambda v: ' ')
    both_cut = []          # every RRR number with the types of its new x / new y
    row_ops  = []          # (pos, new x, new y) of every row, in table order
    for pos, a, b, x_op, y_op, mark in src:
        nx, ny   = rrr_next_op(x_op, y_op)
        row_ops.append((pos, nx, ny, x_op, y_op))
        xy, yx   = compute_variants(ep, nx, ny)[:2]
        nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
        both_cut += [(xy, (_op_type(nx), _op_type(ny)), f"{nxa}/{nya}"),
                     (yx, (_op_type(ny), _op_type(nx)), f"{nya}/{nxa}")]
        tag      = f"[{pos_prefix}{pos}]{mark}"
        body.append(f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                    f"{nxa:<6} {nya:<6}  " + f"{xy:02d}{star(xy)}({nxa}/{nya})".ljust(KW)
                    + f"{yx:02d}{star(yx)}({nya}/{nxa})".ljust(KW))
    _RRR_OCJP_OLD[:] = [(x_, y_) for _, _, _, x_, y_ in row_ops]
    body += ['─' * len(head),
             "  new x = old y, cut switched + sign flipped   |   new y = old x, cut switched, one step down",
             "  LAST = the chain's own last step.  Backtest (57,662 positions): table hit 6.42% vs 6.44% chance.",
             f"  Live record: table hit {RRR_LIVE['table_hits']} of {RRR_LIVE['table_rounds']} rounds (about {RRR_LIVE['table_chance']} expected by chance)."]
    # NC/CUT SPECIAL (user's screenshot, 2026-10-15, result 33 after 57):
    # a row whose xy or yx is nc/cut, cut/nc or nc/nc points to the row
    # after it; that row's xy and yx are modified every way (each side as
    # is, sign flipped, cut switched, both) — Op16 65 (nc/cut) -> Op21
    # +2/c+2 -> c+2/c-2 = 33 on EP 60
    nc_spec = _rrr_nc_special(ep, row_ops)
    if nc_spec:
        body += ["", f"  NC/CUT SPECIAL  —  after an nc/cut, cut/nc or nc/nc row: next row modified, EP={ep:02d}"]
        for trig, nxt, lst in nc_spec:
            body.append(f"  [{pos_prefix}{trig[0]}] {OP_ABBREV[trig[1]]}/{OP_ABBREV[trig[2]]}  →  "
                        f"[{pos_prefix}{nxt[0]}] xy {OP_ABBREV[nxt[1]]}/{OP_ABBREV[nxt[2]]}, yx {OP_ABBREV[nxt[2]]}/{OP_ABBREV[nxt[1]]}:")
            for k_ in range(0, len(lst), 5):
                body.append("     " + '   '.join(f"{v_:02d}{star(v_)}({lab_})" for v_, lab_ in lst[k_:k_ + 5]))
        body.append("  each side as is, sign flipped, cut switched, or both; then the trigger row's old operation again, xy and yx (all in the declared cell)")
    rrr_tbl = list(body)    # the RRR table alone, shown again under the ROUND SUMMARY
    la, picks = _rrr3_rows(entries, ep)
    row, why  = _rrr3_last(entries, ep)
    found     = [(f"{p[9]:02d}{star(p[9])}", f"A {OP_ABBREV[p[7]]}/{OP_ABBREV[p[8]]}") for p in picks]
    found    += [(f"{p[12]:02d}{star(p[12])}", f"A {OP_ABBREV[p[10]]}/{OP_ABBREV[p[11]]}") for p in picks]
    if row is not None:
        found.append((f"{row[7]:02d}{star(row[7])}", f"B {OP_ABBREV[row[5]]}/{OP_ABBREV[row[6]]}"))
    keep = _rrr3_keep(entries, ep, [r[3] for r in src])
    keep_due = keep is not None
    arrived  = _rrr3_arrived(entries, ep, grid_ep) if live else []
    found    = [(f"{d[7]:02d}{star(d[7])}", f"D {OP_ABBREV[d[5]]}/{OP_ABBREV[d[6]]}") for d in arrived] + found
    if keep_due:
        found.append((f"{keep[7]:02d}{star(keep[7])}", f"C {OP_ABBREV[keep[5]]}/{OP_ABBREV[keep[6]]}"))
    # recommended: the 3RRR numbers, the other crossing of every same-family
    # row and every RRR number above whose pair of op types (C/K/I/N on x
    # and on y) no WIN - WIN row has used yet — the new combination is due
    rec = [(p[9], f"{OP_ABBREV[p[7]]}/{OP_ABBREV[p[8]]}") for p in picks]
    rec += [(p[12], f"{OP_ABBREV[p[10]]}/{OP_ABBREV[p[11]]}") for p in picks]
    if row is not None:
        rec.append((row[7], f"{OP_ABBREV[row[5]]}/{OP_ABBREV[row[6]]}"))
    if keep is not None:
        rec.insert(0, (keep[7], f"{OP_ABBREV[keep[5]]}/{OP_ABBREV[keep[6]]}"))
    rec = [(d[7], f"{OP_ABBREV[d[5]]}/{OP_ABBREV[d[6]]}") for d in arrived] + rec
    for p in picks:
        for ops in (p[5], rrr3_second(p[3], p[4])):
            if ops is not None:
                ox = _rrr3_twice(ops[0], entries)
                rec.append((compute_variants(ep, ox, ops[1])[0], f"{OP_ABBREV[ox]}/{OP_ABBREV[ops[1]]}"))
    used_types = {(_op_type(e[3]), _op_type(e[4])) for e in entries}
    # rule E: every WIN - WIN row crossed with no change at all, when that
    # crossed pair of types has not been used yet
    plain = [(compute_variants(ep, e[4], e[3])[0], f"{OP_ABBREV[e[4]]}/{OP_ABBREV[e[3]]}")
             for e in entries if (_op_type(e[4]), _op_type(e[3])) not in used_types]
    # and every row whose x carries a cut, crossed with old y kept and only
    # that cut removed (the cut stays on the x side, comes off the y side)
    kept = [(compute_variants(ep, e[4], _op_join(False, _op_parts(e[3])[1]))[0],
             f"{OP_ABBREV[e[4]]}/{OP_ABBREV[_op_join(False, _op_parts(e[3])[1])]}")
            for e in entries if _op_parts(e[3])[0]]
    # this move gave 99, 39, 49 and 11 in series H (49 and 11 declared in
    # advance), so its numbers also go on the 3RRR RESULT line
    seen_found = {n for n, _ in found}
    for v, lab in kept:
        if f"{v:02d}{star(v)}" not in seen_found:
            found.append((f"{v:02d}{star(v)}", f"E {lab}"))
            seen_found.add(f"{v:02d}{star(v)}")
    # and the last row crossed with the cuts removed, old y also sign-flipped
    # and old x one step up (recommended only)
    turned = []
    if entries and _op_parts(entries[-1][3])[1] in RRR3_STEP_UP:
        lx, ly = entries[-1][3], entries[-1][4]
        tx = SIGN_FLIP[_op_join(False, _op_parts(ly)[1])]
        ty = _op_join(False, RRR3_STEP_UP[_op_parts(lx)[1]])
        turned = [(compute_variants(ep, tx, ty)[0], f"{OP_ABBREV[tx]}/{OP_ABBREV[ty]}")]
        # the same crossing with the cuts left where they are
        ty_c = _op_join(_op_parts(lx)[0], RRR3_STEP_UP[_op_parts(lx)[1]])
        turned.append((compute_variants(ep, SIGN_FLIP[ly], ty_c)[0], f"{OP_ABBREV[SIGN_FLIP[ly]]}/{OP_ABBREV[ty_c]}"))
        # the same crossing with old y simply kept
        ty2 = _op_join(_op_parts(lx)[0], RRR3_STEP_UP[_op_parts(lx)[1]])
        turned.append((compute_variants(ep, ly, ty2)[0], f"{OP_ABBREV[ly]}/{OP_ABBREV[ty2]}"))
    # rule F: the last row NOT crossed, with one side dropped to nc
    dropped = []
    if entries:
        lx, ly = entries[-1][3], entries[-1][4]
        dropped = [(compute_variants(ep, lx, 'no_change')[0], f"{OP_ABBREV[lx]}/nc"),
                   (compute_variants(ep, 'no_change', ly)[0], f"nc/{OP_ABBREV[ly]}")]
    # the same for the chain's own last step when it is not a WIN - WIN row
    if src and src[-1][5] == 'LAST' and (not entries or src[-1][0] != entries[-1][0]):
        cx, cy = src[-1][3], src[-1][4]
        dropped += [(compute_variants(ep, cx, 'no_change')[0], f"{OP_ABBREV[cx]}/nc"),
                    (compute_variants(ep, 'no_change', cy)[0], f"nc/{OP_ABBREV[cy]}")]
    # mirror of the last one: last row crossed, old y one step up, old x kept
    if entries and _op_parts(entries[-1][4])[1] in RRR3_STEP_UP:
        lx, ly = entries[-1][3], entries[-1][4]
        tx2 = _op_join(_op_parts(ly)[0], RRR3_STEP_UP[_op_parts(ly)[1]])
        turned.append((compute_variants(ep, tx2, lx)[0], f"{OP_ABBREV[tx2]}/{OP_ABBREV[lx]}"))
        # and the same with old x sign-flipped as it comes over
        turned.append((compute_variants(ep, tx2, SIGN_FLIP[lx])[0], f"{OP_ABBREV[tx2]}/{OP_ABBREV[SIGN_FLIP[lx]]}"))
    # rule F, second form: the same rows not crossed, one side losing its cut
    uncut = []
    f_rows = ([(entries[-1][3], entries[-1][4])] if entries else [])
    if src and src[-1][5] == 'LAST' and (not entries or src[-1][0] != entries[-1][0]):
        f_rows.append((src[-1][3], src[-1][4]))
    for fx, fy in f_rows:
        if _op_parts(fx)[0]:
            ux = _op_join(False, _op_parts(fx)[1])
            uncut.append((compute_variants(ep, ux, fy)[0], f"{OP_ABBREV[ux]}/{OP_ABBREV[fy]}"))
        if _op_parts(fy)[0]:
            uy = _op_join(False, _op_parts(fy)[1])
            uncut.append((compute_variants(ep, fx, uy)[0], f"{OP_ABBREV[fx]}/{OP_ABBREV[uy]}"))
    # rule F, third form: the same rows not crossed, both sides one step down
    # (or both one step up), cuts left where they are
    stepped = []
    for fx, fy in f_rows:
        for table in (RRR3_STEP_DOWN, RRR3_STEP_UP):
            if _op_parts(fx)[1] in table and _op_parts(fy)[1] in table:
                sx_ = _op_join(_op_parts(fx)[0], table[_op_parts(fx)[1]])
                sy_ = _op_join(_op_parts(fy)[0], table[_op_parts(fy)[1]])
                stepped.append((compute_variants(ep, sx_, sy_)[0], f"{OP_ABBREV[sx_]}/{OP_ABBREV[sy_]}"))
    # the same two rows crossed, old y kept, old x gaining a cut (the mirror
    # of the kept-y move, which takes a cut away)
    gained = [(compute_variants(ep, fy, _op_join(True, _op_parts(fx)[1]))[0],
               f"{OP_ABBREV[fy]}/{OP_ABBREV[_op_join(True, _op_parts(fx)[1])]}")
              for fx, fy in f_rows if not _op_parts(fx)[0]]
    # and the same with old x also sign-flipped as it gains the cut
    gained += [(compute_variants(ep, fy, SIGN_FLIP[_op_join(True, _op_parts(fx)[1])])[0],
                f"{OP_ABBREV[fy]}/{OP_ABBREV[SIGN_FLIP[_op_join(True, _op_parts(fx)[1])]]}")
               for fx, fy in f_rows if not _op_parts(fx)[0] and _op_parts(fx)[1]]
    # and one step DOWN on old y with old x kept
    if entries and _op_parts(entries[-1][4])[1] in RRR3_STEP_DOWN:
        lx, ly = entries[-1][3], entries[-1][4]
        tx3 = _op_join(_op_parts(ly)[0], RRR3_STEP_DOWN[_op_parts(ly)[1]])
        turned.append((compute_variants(ep, tx3, lx)[0], f"{OP_ABBREV[tx3]}/{OP_ABBREV[lx]}"))
    # rule F, fourth form: the same rows crossed, cuts removed, and the other
    # side dropped to nc
    bare = []
    for fx, fy in f_rows:
        by, bx = _op_join(False, _op_parts(fy)[1]), _op_join(False, _op_parts(fx)[1])
        bare += [(compute_variants(ep, by, 'no_change')[0], f"{OP_ABBREV[by]}/nc"),
                 (compute_variants(ep, 'no_change', bx)[0], f"nc/{OP_ABBREV[bx]}")]
    # rule F, fifth form: the same rows not crossed, one side given the RRR
    # change (cut switched + sign flipped), the other side kept
    rrr_side = []
    for fx, fy in f_rows:
        ty_, tx_ = SIGN_FLIP[KK_CUT_TOGGLE[fy]], SIGN_FLIP[KK_CUT_TOGGLE[fx]]
        rrr_side += [(compute_variants(ep, fx, ty_)[0], f"{OP_ABBREV[fx]}/{OP_ABBREV[ty_]}"),
                     (compute_variants(ep, tx_, fy)[0], f"{OP_ABBREV[tx_]}/{OP_ABBREV[fy]}")]
    # rule F, sixth form: the same rows with the ± numbers removed on both
    # sides (a cut stays a cut, anything else becomes nc) — crossed and not
    numberless = []
    for fx, fy in f_rows:
        nx_, ny_ = _op_join(_op_parts(fx)[0], ''), _op_join(_op_parts(fy)[0], '')
        numberless += [(compute_variants(ep, ny_, nx_)[0], f"{OP_ABBREV[ny_]}/{OP_ABBREV[nx_]}"),
                       (compute_variants(ep, nx_, ny_)[0], f"{OP_ABBREV[nx_]}/{OP_ABBREV[ny_]}")]
    # rule B's other steps: the last row crossed with a cut on both sides,
    # the two numbers stepped down/up, up/down and up/up (rule B itself is
    # down/down)
    b_steps = []
    if entries:
        lx, ly = entries[-1][3], entries[-1][4]
        for ty_tab, tx_tab in ((RRR3_STEP_DOWN, RRR3_STEP_UP), (RRR3_STEP_UP, RRR3_STEP_DOWN),
                               (RRR3_STEP_UP, RRR3_STEP_UP)):
            if _op_parts(ly)[1] in ty_tab and _op_parts(lx)[1] in tx_tab:
                bx_, by_ = _op_join(True, ty_tab[_op_parts(ly)[1]]), _op_join(True, tx_tab[_op_parts(lx)[1]])
                b_steps.append((compute_variants(ep, bx_, by_)[0], f"{OP_ABBREV[bx_]}/{OP_ABBREV[by_]}"))
    rec += plain + kept + turned + dropped + uncut + gained + stepped + bare + rrr_side + numberless + b_steps
    rec += [(v, lab) for v, types, lab in both_cut if types not in used_types] if entries else []
    rec_votes = {}
    for v, _ in rec:
        rec_votes[v] = rec_votes.get(v, 0) + 1
    first_seen = {}
    for v, lab in rec:
        first_seen.setdefault(v, (v, lab))
    rec = list(first_seen.values())
    rec_items = [f"{v:02d}{star(v).strip()} ({lab})" for v, lab in rec]
    rec_lines = [f"  ★ 3RRR RECOMMENDED on EP={ep:02d}  →  " + ('   '.join(rec_items[:5]) if rec_items else "none this round")]
    rec_lines += ["       " + '   '.join(rec_items[k:k + 7]) for k in range(5, len(rec_items), 7)]
    same = None
    if _RRR3_PREV.get('op'):
        px, py = _RRR3_PREV['op']
        same = (compute_variants(ep, px, py)[0], f"{OP_ABBREV[px]}/{OP_ABBREV[py]}")
        if same[0] not in [v for v, _ in rec]:
            rec.append(same)
        # the same operation crossed (yx), and crossed the user's way: old y
        # without its cut becomes x, old x sign-flipped becomes y
        tx, ty = _op_join(False, _op_parts(py)[1]), SIGN_FLIP[px]
        same_yx = (compute_variants(ep, py, px)[0], f"{OP_ABBREV[py]}/{OP_ABBREV[px]}")
        same_turn = (compute_variants(ep, tx, ty)[0], f"{OP_ABBREV[tx]}/{OP_ABBREV[ty]}")
        for extra in (same_yx, same_turn):
            if extra[0] not in [v for v, _ in rec]:
                rec.append(extra)
    # the operation of the round before last, again (seen on 47 and 03 in series I)
    same2 = None
    if _RRR3_PREV.get('op2'):
        qx, qy = _RRR3_PREV['op2']
        same2 = (compute_variants(ep, qx, qy)[0], f"{OP_ABBREV[qx]}/{OP_ABBREV[qy]}")
        if same2[0] not in [v for v, _ in rec]:
            rec.append(same2)
    # the EP itself, nothing changed (5 of 354 recorded results were the chain EP)
    if ep not in [v for v, _ in rec]:
        rec.append((ep, "nc/nc"))
    # and the EP with both digits cut (the 48 -> 28 miss)
    ep_cut = compute_variants(ep, 'cut', 'cut')[0]
    if ep_cut not in [v for v, _ in rec]:
        rec.append((ep_cut, "cut/cut"))
    in_rec = {v for v, _ in rec}
    # yx of every recommended value: the same two operations, crossed
    abbrev_op = {v: k for k, v in OP_ABBREV.items()}
    rec_yx = {}
    for _, lab in rec:
        lx_, _, ly_ = lab.partition('/')
        if lx_ in abbrev_op and ly_ in abbrev_op and lx_ != ly_:
            v = compute_variants(ep, abbrev_op[ly_], abbrev_op[lx_])[0]
            if v not in in_rec:
                rec_yx.setdefault(v, (v, f"{ly_}/{lx_}"))
    rec_yx = list(rec_yx.values())
    in_rec |= {v for v, _ in rec_yx}
    wide, wide_votes = {}, {}
    for v, lab in _rrr3_wide(entries, ep):
        if v not in in_rec:
            wide.setdefault(v, (v, lab))
            wide_votes[v] = wide_votes.get(v, 0) + 1
    wide = list(wide.values())
    rec_items = [f"{v:02d}{star(v).strip()} ({lab})" for v, lab in rec]
    rec_lines = [f"  ★ 3RRR RECOMMENDED on EP={ep:02d}  →  " + ('   '.join(rec_items[:5]) if rec_items else "none this round")]
    rec_lines += ["       " + '   '.join(rec_items[k:k + 7]) for k in range(5, len(rec_items), 7)]
    yx_items = [f"{v:02d}{star(v).strip()} ({lab})" for v, lab in rec_yx]
    rec_lines += [f"    3RRR RECOMMENDED yx on EP={ep:02d}  →  " + ('   '.join(yx_items[:5]) if yx_items else "none this round")]
    rec_lines += ["       " + '   '.join(yx_items[k:k + 7]) for k in range(5, len(yx_items), 7)]
    wide_items = [f"{v:02d}{star(v).strip()} ({lab})" for v, lab in wide]
    rec_lines += [f"    3RRR WIDE on EP={ep:02d}  →  " + ('   '.join(wide_items[:6]) if wide_items else "none this round")]
    rec_lines += ["       " + '   '.join(wide_items[k:k + 7]) for k in range(6, len(wide_items), 7)]
    # STRONG 16: at most 16 numbers.  Ranking chosen by testing 1,700 ways
    # of weighting the sources on all 363 recorded rounds, each series held
    # out in turn: numbers inside the tens-cut decade first, then the 3RRR
    # RESULT line, then the order of the lists (rules A-F, same operation,
    # RRR table, yx, wide).  Votes per rule, the RRR table, yx and wide added
    # nothing as weights, so they only set the order.
    strong_votes, strong_lab = {}, {}
    for group in (rec, rec_yx, wide):
        for v, lab in group:
            strong_lab.setdefault(v, lab)
            strong_votes.setdefault(v, 0)
    for v, _, lab in both_cut:
        strong_lab.setdefault(v, lab)
        strong_votes.setdefault(v, 0)
    for n, _ in found:
        if int(n[:2]) in strong_votes:
            strong_votes[int(n[:2])] += 1
    # the operation of the last round and of the round before last, again,
    # each get a seat: a repeat came 7 times in 357 rounds (lag 1) and 4 in
    # 350 (lag 2, three of them in series I) against about 3.5 by chance
    # the same operation crossed the user's way (yx, cut removed from old y,
    # old x sign flipped) gets a seat too: it gave 30 and 18 in series I
    for again in (same, same2, same_turn if same else None, same_yx if same else None):
        if again and again[0] in strong_votes:
            strong_votes[again[0]] += 5
    # the remaining seats are shared evenly: one rule number (recommended
    # list order), one RRR table number (table order), and so on.  Neither
    # source has earned all of them — the rule seats went 0 for 20, and the
    # round after they were handed to the table a rule number (71) came.
    # FIXED 2026-10-07: judge it over at least 10 rounds before touching it.
    taken = {v for v, n in strong_votes.items() if n >= 5}
    rule_q = [v for v, _ in rec if v not in taken]
    table_q = []
    for v, _, _ in both_cut:
        if v not in taken and v not in table_q:
            table_q.append(v)
    shared = []
    for k in range(max(len(rule_q), len(table_q))):
        for q in (rule_q, table_q):
            if k < len(q) and q[k] not in shared:
                shared.append(q[k])
    for k, v in enumerate(shared):
        strong_votes[v] = 4 - k * 0.01
    # RE-JUDGED 2026-10-07 after 0 hits in 33 rounds: the 16 is now the whole
    # RRR table first (up to 11 numbers, table order), then the number band,
    # then the seats above as fill.  The table and the band are the only two
    # sources that never depended on a rule written after a miss; together
    # they held the result 70 times in 380 rounds at about 13 numbers a
    # round (about 50 by size), though only at chance in the latest series.
    table_first = []
    for v, _, _ in both_cut:
        if v not in table_first:
            table_first.append(v)
    for k, v in enumerate(table_first[:11]):
        strong_votes[v] = 20 - k * 0.01
    # the first 5 seats go to the NUMBER BAND of the running value (declared
    # number = tens cut, units +4, then ±1, ±2): on 376 recorded rounds the
    # declared number alone hit 10 times (2.7% against 1%) and the band 35
    # times (9.3% against 5%) — the best record per number of any source.
    # No other preference for the tens-cut decade.
    band_v_ = {}    # a band number that loses a rule seat falls back to its band seat
    if live and grid_ep is not None:
        b_t, b_u = cut(grid_ep // 10), (grid_ep % 10 + 4) % 10
        for rank, step in enumerate((0, -1, 1, -2, 2)):
            v = b_t * 10 + (b_u + step) % 10
            strong_lab.setdefault(v, f"{OP_ABBREV[find_op(ep // 10, v // 10)]}/{OP_ABBREV[find_op(ep % 10, v % 10)]}")
            # 2026-10-11: 15, not 10 — a same-operation number with two
            # seats (10 votes) pushed the band's fifth number out and it
            # was the result (23 after 77); the band keeps all 5 seats
            strong_votes[v] = 15 - rank * 0.1
            band_v_[v] = 15 - rank * 0.1
    # fixed rule seats (2026-10-11), each written after a miss and each
    # taking the seat of the last RRR table number, so the list stays at 16
    # and the band keeps its 5 seats:
    #  1. result 30 after 77 — the first RRR table number with a plain step
    #     on y, that y as the cut step of the other sign (31 (+1/-2) -> 30
    #     (+1/c+2)), the user's -2 -> c+2 rule
    #  2. result 50 after 30 — the declared number's ops (x/y on the EP):
    #     y sign flipped with the cut, its step switched, put on x; x without
    #     its cut put on y (84 (-1/c-2) -> 50 (c+1/-1))
    rule_seats = []
    seat2_ = None    # seat 2's number, for its digits reversed (see rule 18 below)
    seat1_ = None    # seat 1's number, for both digits cut (see rule 20 below)
    seat7_ = None    # seat 7's number, kept by rule 20
    # record seats (2026-10-11, replay of all 423 older rounds, one seat =
    # 1% by chance): the 2nd NUMBER (c+1 / c-1 on the running value) held
    # the result 12 times (2.8%) and never had a seat; the last round's
    # operation again 8 times (1.9%).  The RRR table numbers they displace
    # held it about 1% each (positions 2 and 3: 3 times each).
    if grid_ep is not None:
        v2_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 4) % 10
        rule_seats.append((v2_, f"{OP_ABBREV[find_op(ep // 10, v2_ // 10)]}/{OP_ABBREV[find_op(ep % 10, v2_ % 10)]}"))
    if same:
        rule_seats.append((same[0], strong_lab.get(same[0], same[1])))
    for v, _, lab in both_cut:
        sx_, _, sy_ = lab.partition('/')
        if sy_ in ('-1', '-2', '+1', '+2') and sx_ in abbrev_op:
            ny_ = KK_CUT_TOGGLE[SIGN_FLIP[abbrev_op[sy_]]]
            rule_seats.append((compute_variants(ep, abbrev_op[sx_], ny_)[0], f"{sx_}/{OP_ABBREV[ny_]}"))
            seat1_ = compute_variants(ep, abbrev_op[sx_], ny_)[0]
            break
    if grid_ep is not None:
        d_v = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4) % 10
        d_x, d_y = find_op(ep // 10, d_v // 10), find_op(ep % 10, d_v % 10)
        d_n = _op_parts(SIGN_FLIP.get(d_y, d_y))[1]
        d_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        if d_n in d_sw:
            ny_, nx_ = 'cut' + d_sw[d_n], _op_join(False, _op_parts(d_x)[1])
            rule_seats.append((compute_variants(ep, ny_, nx_)[0], f"{OP_ABBREV[ny_]}/{OP_ABBREV[nx_]}"))
            seat2_ = compute_variants(ep, ny_, nx_)[0]
        #  3. result 27 after 50 — declared x step without its cut, other
        #     sign and other number (c+2 -> -1) on x, the bare cut on y
        #     (04 (c+2/+2) -> 27 (-1/cut))
        d_xn = _op_parts(d_x)[1]
        if d_xn in d_sw:
            tx_ = SIGN_FLIP[d_sw[d_xn]]
            rule_seats.append((compute_variants(ep, tx_, 'cut')[0], f"{OP_ABBREV[tx_]}/cut"))
        # seats for the earlier series J misses that had only been repaired
        # in the declared cell (user, 2026-10-11):
        #  4. result 86 after 42 — the nearest x of the declared x (step
        #     switched, c+2 -> c+1) with the declared y (96 (c+2/+2) -> 86)
        if d_xn in d_sw:
            qx_ = _op_join(_op_parts(d_x)[0], d_sw[d_xn])
            rule_seats.append((compute_variants(ep, qx_, d_y)[0], f"{OP_ABBREV[qx_]}/{OP_ABBREV[d_y]}"))
        #  5. result 10 after 86 — declared x without its cut and sign
        #     flipped, y kept (30 (+1/-2) -> 10 (-1/-2))
        if d_xn:
            qx_ = SIGN_FLIP[d_xn]
            rule_seats.append((compute_variants(ep, qx_, d_y)[0], f"{OP_ABBREV[qx_]}/{OP_ABBREV[d_y]}"))
        #  6. result 60 after 10 — the declared x with nc on y (64 (+1/c-1),
        #     65 (+1/cut) -> 60 (+1/nc))
        if d_y != 'no_change':
            rule_seats.append((compute_variants(ep, d_x, 'no_change')[0], f"{OP_ABBREV[d_x]}/nc"))
        #  7. result 77 after 60 — the first ★ row of the RRR table (number
        #     in the tens-cut decade): x without cut + sign flipped, y without
        #     cut with that sign (12 (+2/c-2) -> 77 (-2/-2))
        for v, _, lab in both_cut:
            sx_, _, sy_ = lab.partition('/')
            if v // 10 != cut(grid_ep // 10) or sx_ not in abbrev_op or sy_ not in abbrev_op:
                continue
            xn_, yn_ = _op_parts(abbrev_op[sx_])[1], _op_parts(abbrev_op[sy_])[1]
            if xn_ and yn_:
                qx_ = SIGN_FLIP[xn_]
                qy_ = qx_[0] + yn_[1:]
                rule_seats.append((compute_variants(ep, qx_, qy_)[0], f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"))
                seat7_ = compute_variants(ep, qx_, qy_)[0]
                break
        #  8. result 12 after 27 — the last round's operation again, on the
        #     running value instead of the EP (-1/cut on 27 -> 12, shown as
        #     +1/+1 on EP 01); 7 of 432 older rounds on a replay
        if _RRR3_PREV.get('op') and grid_ep >= 0:
            gv_ = compute_variants(grid_ep, *_RRR3_PREV['op'])[0]
            rule_seats.append((gv_, f"{OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]}"))
        #  9. result 42 after 12 — the declared number's operations crossed:
        #     y without its cut and its step switched put on x, x without its
        #     cut put on y (66 (nc/c-1) -> 42 (-2/nc)); seat 2 without the
        #     cut and the sign change
        d_yn = _op_parts(d_y)[1]
        if d_yn in d_sw:
            qy_ = _op_join(False, _op_parts(d_x)[1])
            rule_seats.append((compute_variants(ep, d_sw[d_yn], qy_)[0], f"{d_sw[d_yn]}/{OP_ABBREV[qy_]}"))
        # 10. result 16 after 06 — seat 8 (the last round's operation again
        #     on the running value) with its x step switched, cut kept
        #     (+2/nc on 06 = 26 -> +1/nc on 06 = 16, shown as c+1/+2 on EP 54)
        if _RRR3_PREV.get('op') and grid_ep >= 0:
            hx_, hy_ = _RRR3_PREV['op']
            if _op_parts(hx_)[1] in d_sw:
                gv_ = compute_variants(grid_ep, _op_join(_op_parts(hx_)[0], d_sw[_op_parts(hx_)[1]]), hy_)[0]
                rule_seats.append((gv_, f"{OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]}"))
    # 11. result 82 after 16 — the last round's operation again on the EP
    #     with nc on y (84 (c+1/+2) -> 82 (c+1/nc))
    if _RRR3_PREV.get('op') and _RRR3_PREV['op'][1] != 'no_change':
        hx_ = _RRR3_PREV['op'][0]
        rule_seats.append((compute_variants(ep, hx_, 'no_change')[0], f"{OP_ABBREV[hx_]}/nc"))
    # 12. result 28 after 82 — seat 5's x (declared x without its cut, sign
    #     flipped) with the +1/+2 rule on y (declared y a +1/+2 step -> c-1)
    #     (36 (c-2/+2) -> 28 (+2/c-1))
    if grid_ep is not None and d_xn and _op_parts(d_y)[1] in ('+1', '+2') and not _op_parts(d_y)[0]:
        rule_seats.append((compute_variants(ep, SIGN_FLIP[d_xn], 'cut-1')[0], f"{OP_ABBREV[SIGN_FLIP[d_xn]]}/c-1"))
    # 13. result 08 after 28 — seat 9's operation (declared operations
    #     crossed, y without its cut and step switched on x) applied on the
    #     running value instead of the EP (72 (nc/-1) -> -2/nc; on 28 = 08,
    #     shown as c-2/cut on EP 73)
    if grid_ep is not None and grid_ep >= 0 and _op_parts(d_y)[1] in d_sw:
        gv_ = compute_variants(grid_ep, d_sw[_op_parts(d_y)[1]], _op_join(False, _op_parts(d_x)[1]))[0]
        rule_seats.append((gv_, f"{OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]}"))
    # 14. result 62 after 30 — the declared operations crossed, both without
    #     their cut and both with the sign flipped (84 (c-2/c-1) -> 62
    #     (+1/+2)); seat 9 with the sign change on both sides.  Seated after
    #     the family seats below, so those and the declared cell do not move
    seat14_ = None
    if grid_ep is not None and d_xn and _op_parts(d_y)[1]:
        qx_, qy_ = SIGN_FLIP[_op_parts(d_y)[1]], SIGN_FLIP[d_xn]
        seat14_ = (compute_variants(ep, qx_, qy_)[0], f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}")
    base16_ = sorted(strong_lab, key=lambda v: (-strong_votes[v], list(strong_lab).index(v)))[:16]
    r_k = 0
    seat_set_ = {v for v, _ in rule_seats[:2]}    # the two record seats
    for nv_, nlab_ in rule_seats:
        strong_lab.setdefault(nv_, nlab_)
        if strong_votes.get(nv_, 0) >= 15:
            continue
        t_i = 10 - r_k
        # a table number that is also a record seat (2nd NUMBER, last
        # operation again) keeps its seat — the 2nd NUMBER 62 lost it after
        # 08: the table number before it goes instead
        while 0 <= t_i < len(table_first) and (table_first[t_i] in seat_set_
                                               or strong_votes.get(table_first[t_i], 0) <= 19):
            t_i -= 1
        if 0 <= t_i < len(table_first) and strong_votes.get(table_first[t_i], 0) > 19:
            strong_votes[table_first[t_i]] = band_v_.get(table_first[t_i], 4.5)
        # the 16 hold 11 seats beside the band's 5: a 12th rule seat in one
        # round does not push a band number out, it only fills a free seat
        strong_votes[nv_] = (19.905 - r_k * 0.001 if r_k < 11 and sum(x > 19 for x in strong_votes.values()) < 11
                             else 14.4 - r_k * 0.001)
        r_k += 1
    # family seats (user, 2026-10-11, after 08 came on 28): a STRONG 16
    # number and a 3RRR RESULT number of the same family — the same two
    # digits up to cut and order, like 53 and 85 (5/0 with 3/8) — bring the
    # STRONG 16 number with both digits cut (53 -> 08).  The 16 looked at
    # is the one before the rule seats (RRR table + band), so a later rule
    # seat cannot take the pair away; ranked after the rule seats above
    fam_key = lambda v: tuple(sorted((min(v // 10, cut(v // 10)), min(v % 10, cut(v % 10)))))
    fam_res = [int(n[:2]) for n, _ in found]
    fam_seats = []
    for sv_ in base16_:
        if any(fv_ != sv_ and fam_key(fv_) == fam_key(sv_) for fv_ in fam_res):
            nv_ = cut(sv_ // 10) * 10 + cut(sv_ % 10)
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats.append((nv_, f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"))
    # crossed family pair inside the STRONG 16 (user, 2026-10-11, after 30
    # came on 51): 80 and 03 are the same family with the two digits the
    # other way round — the first one's tens digit cut, then the other one's
    # tens digit (80, 03 -> 30).  The same reading gives 08 from 53 and 85.
    # The 16 looked at is the one after the rule seats; these numbers are
    # put in front of the other family numbers
    f_cl = lambda x: min(x, cut(x))
    f16_ = sorted(strong_lab, key=lambda v: (-strong_votes[v], list(strong_lab).index(v)))[:16]
    fam_x = []
    for k_, a_ in enumerate(f16_):
        for b_ in f16_[k_ + 1:]:
            if (f_cl(a_ // 10) != f_cl(a_ % 10) and f_cl(a_ // 10) == f_cl(b_ % 10)
                    and f_cl(a_ % 10) == f_cl(b_ // 10)):
                nv_ = cut(a_ // 10) * 10 + b_ // 10
                if nv_ not in [v for v, _ in fam_x]:
                    fam_x.append((nv_, f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"))
    # the 16 are full (rule seats + band): a crossed-pair number that is
    # also a 3RRR RESULT number (30 was) takes the seat of the lowest ranked
    # number above the band; giving every pair number a seat pushed four
    # earlier repairs out, so the others only fill a free seat
    fam_pre_ = dict(strong_votes)    # votes before any family seat
    for nv_, nlab_ in fam_x:
        strong_lab.setdefault(nv_, nlab_)
        if strong_votes.get(nv_, 0) >= 14.5 or nv_ not in fam_res:
            continue
        f_top = sorted((v for v in strong_votes if strong_votes[v] > 19 and v not in [x for x, _ in fam_x]),
                       key=lambda v: strong_votes[v])
        if len([v for v in strong_votes if strong_votes[v] > 19]) >= 11 and f_top:
            strong_votes[nv_] = strong_votes[f_top[0]]
            strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
        else:
            strong_votes[nv_] = 19.8
    fam_seats = fam_x + [e for e in fam_seats if e[0] not in [v for v, _ in fam_x]]
    for nv_, nlab_ in fam_seats:
        strong_lab.setdefault(nv_, nlab_)
        if strong_votes.get(nv_, 0) >= 14:
            continue
        t_i = 10 - r_k
        while 0 <= t_i < len(table_first) and (table_first[t_i] in seat_set_
                                               or strong_votes.get(table_first[t_i], 0) <= 19):
            t_i -= 1
        if 0 <= t_i < len(table_first) and strong_votes.get(table_first[t_i], 0) > 19:
            strong_votes[table_first[t_i]] = band_v_.get(table_first[t_i], 4.5)
        strong_votes[nv_] = (19.905 - r_k * 0.001 if r_k < 11 and sum(x > 19 for x in strong_votes.values()) < 11
                             else 14.4 - r_k * 0.001)
        r_k += 1
    # seat 14: the 16 are full by now, so it takes the seat of the lowest
    # ranked number above the band (never a band number, and never the
    # crossed family pair number seated just above — 30 after 51 was one)
    if seat14_:
        strong_lab.setdefault(seat14_[0], seat14_[1])
        if strong_votes.get(seat14_[0], 0) < 14.5:
            f_keep = {v for v, _ in fam_x if v in fam_res}
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[seat14_[0]] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[seat14_[0]] = 19.7
    # family rule on the EP itself (result 57 after 62, 2026-10-11): the EP
    # and a 3RRR RESULT number of the same family (02 and 70) bring the EP
    # with both digits cut (02 -> 57, cut/cut) — the user's family rule with
    # the EP in place of the STRONG 16 number; the crossed-pair reading (cut
    # of the first tens + the other tens) gives the same 57.  Goes to the
    # declared cell with the family numbers and takes the seat of the lowest
    # ranked number above the band (not a band, pair or seat 14 number)
    if ep >= 0 and any(fv_ != ep and fam_key(fv_) == fam_key(ep) for fv_ in fam_res):
        nv_ = cut(ep // 10) * 10 + cut(ep % 10)
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, 'cut/cut')]
        strong_lab.setdefault(nv_, 'cut/cut')
        if strong_votes.get(nv_, 0) < 14.5:
            f_keep = {v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.6
    # 15. result 61 after 11 — the declared x with the declared y's step
    #     switched and its cut switched (65 (c-2/+1) -> 61 (c-2/c+2)): seat 4
    #     (nearest x, declared y) mirrored to y, with the cut.  Seated last,
    #     in the seat of the lowest ranked number above the band that is not
    #     a pair, seat 14 or EP family number
    if grid_ep is not None and _op_parts(d_y)[1] in d_sw:
        qy_ = KK_CUT_TOGGLE[_op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])]
        nv_ = compute_variants(ep, d_x, qy_)[0]
        strong_lab.setdefault(nv_, f"{OP_ABBREV[d_x]}/{OP_ABBREV[qy_]}")
        if strong_votes.get(nv_, 0) < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10)})
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.5
    # crossed family pair, second number (user, 2026-10-11, after 03 came
    # on 61: "08 existed in STRONG 16"): 85 and 08 are a crossed pair and
    # bring 30 by the rule above — the same number with its digits reversed
    # comes too (30 -> 03: the pair's second number 08 with its 8 cut).
    # Goes to the declared cell with the family numbers
    fam_rev_ = set()    # reversed pair numbers that took a seat
    for xv_, _ in list(fam_x):
        nv_ = (xv_ % 10) * 10 + xv_ // 10
        if nv_ == xv_:
            continue
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        # the 16 are full: the reversed number sits in the seat of its own
        # pair number (03 in the seat of 30), unless that one is also a
        # 3RRR RESULT number (30 after 51 was) or has no family seat above the band
        strong_votes.setdefault(nv_, 0)
        if (strong_votes[nv_] < 14.5 and strong_votes.get(xv_, 0) > 19 and fam_pre_.get(xv_, 0) <= 19
                and xv_ not in fam_res):
            strong_votes[nv_] = strong_votes[xv_]
            strong_votes[xv_] = band_v_.get(xv_, 14.3)
            fam_rev_.add(nv_)
    # 16. result 99 after 55 — the declared x without its step, only the cut,
    #     with the declared y (09 (c+1/c-2) -> 99 (cut/c-2)); beside seat 6
    #     (declared x with nc on y).  Seated last, in the seat of the lowest
    #     ranked number above the band that no later rule holds
    if grid_ep is not None and _op_parts(d_x)[0] and d_xn:
        nv_ = compute_variants(ep, 'cut', d_y)[0]
        strong_lab.setdefault(nv_, f"cut/{OP_ABBREV[d_y]}")
        if strong_votes.get(nv_, 0) < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10)} | fam_rev_)
            if _op_parts(d_y)[1] in d_sw:
                f_keep.add(compute_variants(ep, d_x, KK_CUT_TOGGLE[_op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])])[0])
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.3
    # 17. result 66 after 71 — nc on x with the declared y's step switched
    #     (25 (c+1/-2) -> 66 (nc/-1)): seat 6 (declared x with nc on y)
    #     mirrored, with the nearest y.  Seated last, in the seat of the
    #     lowest ranked number above the band that no later rule holds
    if grid_ep is not None and _op_parts(d_y)[1] in d_sw:
        qy_ = _op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])
        nv_ = compute_variants(ep, 'no_change', qy_)[0]
        strong_lab.setdefault(nv_, f"nc/{OP_ABBREV[qy_]}")
        if strong_votes.get(nv_, 0) < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10)} | fam_rev_
                      | {compute_variants(ep, d_x, KK_CUT_TOGGLE[qy_])[0]})
            if _op_parts(d_x)[0] and d_xn:
                f_keep.add(compute_variants(ep, 'cut', d_y)[0])
            # seat 12's number (28 after 82) is the lowest rule seat there
            if d_xn and _op_parts(d_y)[1] in ('+1', '+2') and not _op_parts(d_y)[0]:
                f_keep.add(compute_variants(ep, SIGN_FLIP[d_xn], 'cut-1')[0])
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.2
    # 18. result 72 after 66 (user: "27 exists in STRONG 16, same family") —
    #     seat 2's number (the declared operations crossed: 10 (c+1/c-1) ->
    #     27 (c+2/+1)) also with its digits reversed (27 -> 72, +2/c+1: the
    #     same steps with the cut moved to y).  Goes to the declared cell
    #     with the family numbers; seated last, in the seat of the lowest
    #     ranked number above the band that no later rule holds
    if seat2_ is not None and seat2_ % 11:
        nv_ = (seat2_ % 10) * 10 + seat2_ // 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10), seat2_} | fam_rev_)
            if _op_parts(d_y)[1] in d_sw:
                qy_ = _op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])
                f_keep |= {compute_variants(ep, d_x, KK_CUT_TOGGLE[qy_])[0], compute_variants(ep, 'no_change', qy_)[0]}
            if _op_parts(d_x)[0] and d_xn:
                f_keep.add(compute_variants(ep, 'cut', d_y)[0])
            if d_xn and _op_parts(d_y)[1] in ('+1', '+2') and not _op_parts(d_y)[0]:
                f_keep.add(compute_variants(ep, SIGN_FLIP[d_xn], 'cut-1')[0])
            # seat 3's and seat 13's numbers (27 after 50, 08 after 28)
            if d_xn in d_sw:
                f_keep.add(compute_variants(ep, SIGN_FLIP[d_sw[d_xn]], 'cut')[0])
            if grid_ep >= 0 and _op_parts(d_y)[1] in d_sw:
                f_keep.add(compute_variants(grid_ep, d_sw[_op_parts(d_y)[1]], _op_join(False, d_xn))[0])
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.1
    # 19. result 10 after 72 — seat 14's move on the last round's operation
    #     instead of the declared one: crossed, both without their cut, both
    #     signs flipped (+2/c+1 -> -1/-2 = 10 on EP 22).  Goes to the declared
    #     cell with the family numbers; seated last, in the seat of the
    #     lowest ranked number above the band that no later rule holds
    if _RRR3_PREV.get('op') and _op_parts(_RRR3_PREV['op'][0])[1] and _op_parts(_RRR3_PREV['op'][1])[1]:
        qx_, qy_ = SIGN_FLIP[_op_parts(_RRR3_PREV['op'][1])[1]], SIGN_FLIP[_op_parts(_RRR3_PREV['op'][0])[1]]
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10)} | fam_rev_)
            if seat2_ is not None:
                f_keep |= {seat2_, (seat2_ % 10) * 10 + seat2_ // 10}
            if grid_ep is not None:
                if _op_parts(d_y)[1] in d_sw:
                    ky_ = _op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])
                    f_keep |= {compute_variants(ep, d_x, KK_CUT_TOGGLE[ky_])[0], compute_variants(ep, 'no_change', ky_)[0]}
                    if grid_ep >= 0:
                        f_keep.add(compute_variants(grid_ep, d_sw[_op_parts(d_y)[1]], _op_join(False, d_xn))[0])
                if _op_parts(d_x)[0] and d_xn:
                    f_keep.add(compute_variants(ep, 'cut', d_y)[0])
                if d_xn and _op_parts(d_y)[1] in ('+1', '+2') and not _op_parts(d_y)[0]:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[d_xn], 'cut-1')[0])
                if d_xn in d_sw:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[d_sw[d_xn]], 'cut')[0])
                # seat 4's, seat 6's and seat 11's numbers (86 after 42, 60
                # after 10, 82 after 16)
                if d_xn in d_sw:
                    f_keep.add(compute_variants(ep, _op_join(_op_parts(d_x)[0], d_sw[d_xn]), d_y)[0])
                f_keep.add(compute_variants(ep, d_x, 'no_change')[0])
            f_keep.add(compute_variants(ep, _RRR3_PREV['op'][0], 'no_change')[0])
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            else:
                strong_votes[nv_] = 19.05
    # 20. result 88 after 10 (family: 33 was in the STRONG 16) — seat 1's
    #     number (first RRR table number with a plain y step, that y as the
    #     cut step of the other sign: 32 (c+2/+2) -> 33 (c+2/c-2)) also with
    #     both digits cut (33 -> 88, +2/-2: both cuts removed).  Goes to the
    #     declared cell with the family numbers; seated last, in the seat of
    #     the lowest ranked number above the band that no later rule holds
    if seat1_ is not None:
        nv_ = cut(seat1_ // 10) * 10 + cut(seat1_ % 10)
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_keep = ({v for v, _ in fam_x if v in fam_res} | ({seat14_[0]} if seat14_ else set())
                      | {cut(ep // 10) * 10 + cut(ep % 10)} | fam_rev_)
            if seat2_ is not None:
                f_keep |= {seat2_, (seat2_ % 10) * 10 + seat2_ // 10}
            if grid_ep is not None:
                if _op_parts(d_y)[1] in d_sw:
                    ky_ = _op_join(_op_parts(d_y)[0], d_sw[_op_parts(d_y)[1]])
                    f_keep |= {compute_variants(ep, d_x, KK_CUT_TOGGLE[ky_])[0], compute_variants(ep, 'no_change', ky_)[0]}
                    if grid_ep >= 0:
                        f_keep.add(compute_variants(grid_ep, d_sw[_op_parts(d_y)[1]], _op_join(False, d_xn))[0])
                if _op_parts(d_x)[0] and d_xn:
                    f_keep.add(compute_variants(ep, 'cut', d_y)[0])
                if d_xn and _op_parts(d_y)[1] in ('+1', '+2') and not _op_parts(d_y)[0]:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[d_xn], 'cut-1')[0])
                if d_xn in d_sw:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[d_sw[d_xn]], 'cut')[0])
                # seat 4's, seat 6's and seat 11's numbers (86 after 42, 60
                # after 10, 82 after 16)
                if d_xn in d_sw:
                    f_keep.add(compute_variants(ep, _op_join(_op_parts(d_x)[0], d_sw[d_xn]), d_y)[0])
                f_keep.add(compute_variants(ep, d_x, 'no_change')[0])
            if _RRR3_PREV.get('op'):
                f_keep.add(compute_variants(ep, _RRR3_PREV['op'][0], 'no_change')[0])
                if _op_parts(_RRR3_PREV['op'][0])[1] and _op_parts(_RRR3_PREV['op'][1])[1]:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[_op_parts(_RRR3_PREV['op'][1])[1]],
                                                SIGN_FLIP[_op_parts(_RRR3_PREV['op'][0])[1]])[0])
            # seats 5, 8, 9 and 10 (10 after 86, 12 after 27, 42 after 12, 16
            # after 06)
            if grid_ep is not None:
                if d_xn:
                    f_keep.add(compute_variants(ep, SIGN_FLIP[d_xn], d_y)[0])
                if _op_parts(d_y)[1] in d_sw:
                    f_keep.add(compute_variants(ep, d_sw[_op_parts(d_y)[1]], _op_join(False, d_xn))[0])
                if _RRR3_PREV.get('op') and grid_ep >= 0:
                    hx_, hy_ = _RRR3_PREV['op']
                    f_keep.add(compute_variants(grid_ep, hx_, hy_)[0])
                    if _op_parts(hx_)[1] in d_sw:
                        f_keep.add(compute_variants(grid_ep, _op_join(_op_parts(hx_)[0], d_sw[_op_parts(hx_)[1]]), hy_)[0])
            f_keep |= {seat1_} | ({seat7_} if seat7_ is not None else set())
            f_all = [v for v in strong_votes if strong_votes[v] > 19]
            f_top = sorted((v for v in f_all if v not in f_keep), key=lambda v: strong_votes[v])
            if len(f_all) >= 11 and f_top:
                strong_votes[nv_] = strong_votes[f_top[0]]
                strong_votes[f_top[0]] = band_v_.get(f_top[0], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 19.0
    # 21. result 36 after 88 (user: "31 exists") — the band number one under
    #     the declared number (32 -> 31, -2/+2) also with its units digit cut
    #     (31 -> 36, -2/c+2: the cut put on y; the same family).  Goes to the
    #     declared cell with the family numbers; in the STRONG 16 it takes
    #     the 5th seat — the only seat it can have without pushing out a
    #     number one of the 31 earlier rounds needed (found by trying each)
    if live and grid_ep is not None and grid_ep >= 0:
        bv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 3) % 10
        nv_ = (bv_ // 10) * 10 + cut(bv_ % 10)
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            k_ = 6
            if len(f_all) >= 11 and k_ < len(f_all):
                strong_votes[nv_] = strong_votes[f_all[k_]]
                strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 18.9
    # 22. result 21 after 36 — the last round's operation with the cut moved
    #     to the other side and both steps switched (-2/c+2 -> c-1/+1 = 21 on
    #     EP 80).  Goes to the declared cell with the family numbers; in the
    #     STRONG 16 it takes a fixed seat above the band (see rule 21)
    if _RRR3_PREV.get('op') and all(_op_parts(o_)[1] in ('+1', '+2', '-1', '-2') for o_ in _RRR3_PREV['op']) \
            and _op_parts(_RRR3_PREV['op'][0])[0] != _op_parts(_RRR3_PREV['op'][1])[0]:
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        qx_, qy_ = (_op_join(not _op_parts(o_)[0], m_sw[_op_parts(o_)[1]]) for o_ in _RRR3_PREV['op'])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            k_ = 3    # the first place that keeps all 33 earlier rounds (tried 0-3)
            if len(f_all) >= 11 and k_ < len(f_all):
                strong_votes[nv_] = strong_votes[f_all[k_]]
                strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 18.8
    # 23. result 67 after 21 — rule 22's number with its x step switched,
    #     the nearest x (57 (-2/c+2) -> 67 (-1/c+2)), as seat 4 does for the
    #     declared number.  STRONG 16 only; fixed seat above the band
    if _RRR3_PREV.get('op') and all(_op_parts(o_)[1] in ('+1', '+2', '-1', '-2') for o_ in _RRR3_PREV['op']) \
            and _op_parts(_RRR3_PREV['op'][0])[0] != _op_parts(_RRR3_PREV['op'][1])[0]:
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        hx_, hy_ = _RRR3_PREV['op']
        qx_ = _op_join(not _op_parts(hx_)[0], _op_parts(hx_)[1])
        qy_ = _op_join(not _op_parts(hy_)[0], m_sw[_op_parts(hy_)[1]])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        strong_lab.setdefault(nv_, f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}")
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            k_ = 5    # the only place of 0-7 that keeps all 34 earlier rounds
            if len(f_all) >= 11 and k_ < len(f_all):
                strong_votes[nv_] = strong_votes[f_all[k_]]
                strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 18.7
    # 24. result 82 after 19 — the 2nd NUMBER (c+1 / c-1 on the running
    #     value) with both steps switched: c+2 / c-2 on the running value
    #     (19 -> 82; shown as +2/-2 on EP 64).  Goes to the declared cell
    #     with the family numbers
    if live and grid_ep is not None and grid_ep >= 0:
        nv_ = ((grid_ep // 10 + 7) % 10) * 10 + (grid_ep % 10 + 3) % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            # the 11 seats above the band are full (each place was tried and
            # pushed out a number an earlier series J round needed): since
            # the list was widened to 20 it sits just under the band
            strong_votes[nv_] = 18.65 if sum(strong_votes[v] > 19 for v in strong_votes) < 11 else 14.45
    # 25. result 06 after 16 — the declared number with its digits reversed
    #     (60 -> 06; the same family).  Goes to the declared cell with the
    #     family numbers; fixed seat above the band when one can be had
    if live and grid_ep is not None and grid_ep >= 0:
        dv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4) % 10
        nv_ = (dv_ % 10) * 10 + dv_ // 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            # no place among the 11 above the band either (all tried): it
            # sits just under the band, in the widened list of 20
            strong_votes[nv_] = 18.62 if len(f_all) < 11 else 14.44
    # the SAME OPERATION AGAIN number keeps a seat (2026-10-11): it held the
    # result 3 times in 35 series J rounds (11, 26, 19) — the best record of
    # any single number — but the later rule seats had pushed it out of the
    # 16 (51 on the round after 19).  If it has no seat it takes a fixed one
    # above the band
    if same and strong_votes.get(same[0], 0) < 14.5:
        strong_lab.setdefault(same[0], same[1])
        f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
        k_ = 2    # the first place that keeps all 35 earlier rounds (tried 0-3)
        if len(f_all) >= 11 and k_ < len(f_all):
            strong_votes[same[0]] = strong_votes[f_all[k_]]
            strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
        elif len(f_all) < 11:
            strong_votes[same[0]] = 18.6
    # seat 5's number keeps a seat (result 16 after 82, 2026-10-11): the
    # declared x without its cut and sign flipped, y kept (36 (+1/-2) -> 16
    # (-1/-2)) was already a rule seat but the later seats had pushed it out
    if grid_ep is not None and d_xn:
        nv_ = compute_variants(ep, SIGN_FLIP[d_xn], d_y)[0]
        if strong_votes.get(nv_, 0) < 14.5:
            strong_lab.setdefault(nv_, f"{OP_ABBREV[SIGN_FLIP[d_xn]]}/{OP_ABBREV[d_y]}")
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            k_ = 3    # places 2 and 3 keep every earlier round; 3 leaves the same-operation seat alone
            if len(f_all) >= 11 and k_ < len(f_all):
                strong_votes[nv_] = strong_votes[f_all[k_]]
                strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 18.5
    # 26. result 74 after 52 — a both-cut family pair in the strong list (24
    #     and 79: the same family, same digit order, each the other with both
    #     digits cut) brings the number between them: the lower one with its
    #     tens digit cut = the higher one with its units digit cut (74).  Goes
    #     to the declared cell with the family numbers, sits just under the band
    #     Only pairs among the seats above the band, and not a family whose
    #     two digits are the same class (00 and 55)
    p20_ = [v for v in strong_lab if strong_votes.get(v, 0) > 19]
    for a_ in p20_:
        b_ = cut(a_ // 10) * 10 + cut(a_ % 10)
        if a_ < b_ and b_ in p20_ and f_cl(a_ // 10) != f_cl(a_ % 10):
            for nv_ in ((b_ // 10) * 10 + a_ % 10,):    # the lower one with its tens digit cut
                lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
                if nv_ not in [v for v, _ in fam_seats]:
                    fam_seats = fam_seats + [(nv_, lab_)]
                strong_lab.setdefault(nv_, lab_)
                if strong_votes.get(nv_, 0) < 14.42:
                    strong_votes[nv_] = 14.42
    # 27. result 43 after 74 — seat 2's number with its x step switched, the
    #     nearest x (declared 28 (c-1/c-1): 53 (c+2/-1) -> 43 (c+1/-1)).
    #     STRONG 20 only; sits just under the band
    if grid_ep is not None and d_n in d_sw:
        qx_, qy_ = 'cut' + d_n, _op_join(False, _op_parts(d_x)[1])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        strong_lab.setdefault(nv_, f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}")
        if strong_votes.get(nv_, 0) < 14.41:
            strong_votes[nv_] = 14.41
    # 28. result 68 after 43 — the SAME OPERATION AGAIN number mirrored (the
    #     last round's operation with both signs flipped) with its x step
    #     switched, the nearest x (c+1/-1 -> c-1/+1 = 78 -> c-2/+1 = 68 on EP
    #     37).  Goes to the declared cell with the family numbers, sits just
    #     under the band
    if _RRR3_PREV.get('op') and all(_op_parts(o_)[1] in ('+1', '+2', '-1', '-2') for o_ in _RRR3_PREV['op']):
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        hx_, hy_ = _RRR3_PREV['op']
        qx_ = _op_join(_op_parts(hx_)[0], m_sw[SIGN_FLIP[_op_parts(hx_)[1]]])
        qy_ = _op_join(_op_parts(hy_)[0], SIGN_FLIP[_op_parts(hy_)[1]])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.405:
            strong_votes[nv_] = 14.405
    # 29. result 85 after 68 — the RRR table's LAST row (the chain's own last
    #     step) gives two numbers, x/y and y/x; when the y/x one has a seat
    #     (21 (c-1/nc)) the x/y one sits too (85 (nc/c-1)).  STRONG 20 only;
    #     sits just under the band
    if grid_ep is not None and len(both_cut) >= 2:
        top_ = sorted(strong_votes, key=lambda v: -strong_votes[v])[:20]
        if both_cut[-1][0] in top_:
            nv_ = both_cut[-2][0]
            strong_lab.setdefault(nv_, both_cut[-2][2])
            if strong_votes.get(nv_, 0) < 14.403:
                strong_votes[nv_] = 14.403
    # 30. result 86 after 35 — the last round's operation again on the EP
    #     with nc on x (06 (+2/c-1) -> 86 (nc/c-1)), as rule 11 does with nc
    #     on y.  STRONG 20 only; fixed seat above the band (the places under
    #     the band were all held by rules 24-28)
    if grid_ep is not None and _RRR3_PREV.get('op') and _RRR3_PREV['op'][0] != 'no_change':
        hy_ = _RRR3_PREV['op'][1]
        nv_ = compute_variants(ep, 'no_change', hy_)[0]
        strong_lab.setdefault(nv_, f"nc/{OP_ABBREV[hy_]}")
        strong_votes.setdefault(nv_, 0)
        if strong_votes[nv_] < 14.5:
            f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
            k_ = 8    # the only place of 0-10 that keeps all 44 earlier rounds
            if len(f_all) >= 11 and k_ < len(f_all):
                strong_votes[nv_] = strong_votes[f_all[k_]]
                strong_votes[f_all[k_]] = band_v_.get(f_all[k_], 14.3)
            elif len(f_all) < 11:
                strong_votes[nv_] = 18.4
    # 31. result 06 after 86 — the declared operation (the declared number
    #     read on the EP: 30 = +2/nc on EP 10) applied on the running value
    #     instead of the EP (+2/nc on 86 = 06).  Goes to the declared cell
    #     with the family numbers, sits just under the band
    if grid_ep is not None and grid_ep >= 0 and grid_ep != ep:
        nv_ = compute_variants(grid_ep, d_x, d_y)[0]
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.301:
            strong_votes[nv_] = 14.301
    # 32. result 33 after 65 — a 3RRR RESULT number that is a STRONG 20
    #     number above the band with both digits cut (88 (c-2/c-1) -> 33
    #     (-2/-1), the same family).  Goes to the declared cell with the
    #     family numbers, sits just under the band
    p20_ = [v for v in strong_lab if strong_votes.get(v, 0) > 19]
    for n_, _ in found:
        nv_ = int(n_[:2])
        if cut(nv_ // 10) * 10 + cut(nv_ % 10) in p20_:
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.4:
                strong_votes[nv_] = 14.4
    # 33. result 23 after 33 — two STRONG 20 numbers above the band with the
    #     same y, one a step under the EP's tens and one a step over (13
    #     (-1/+2) and 33 (+1/+2)), bring the number between them, nc on x (23
    #     (nc/+2)).  Goes to the declared cell with the family numbers; takes
    #     the lowest seat above the band (the places under it were all held)
    p20_ = [v for v in strong_lab if strong_votes.get(v, 0) > 19]
    for a_ in p20_:
        if a_ // 10 == (ep // 10 - 1) % 10 and ((ep // 10 + 1) % 10) * 10 + a_ % 10 in p20_:
            nv_ = (ep // 10) * 10 + a_ % 10
            lab_ = f"nc/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            strong_votes.setdefault(nv_, 0)
            if strong_votes[nv_] < 14.5:
                f_all = sorted((v for v in strong_votes if strong_votes[v] > 19), key=lambda v: strong_votes[v])
                if len(f_all) >= 11:    # the lowest seat above the band; fires in 1 of 50 rounds
                    strong_votes[nv_] = strong_votes[f_all[0]]
                    strong_votes[f_all[0]] = band_v_.get(f_all[0], 14.3)
                else:
                    strong_votes[nv_] = 18.3
    # 34. result 65 after 23 — the RRR table's LAST row number (the chain's
    #     own last step, x/y) mirrored on y, its y sign flipped (69 (-1/+2)
    #     -> 65 (-1/-2)).  STRONG 20 only; sits under the band
    if grid_ep is not None and len(both_cut) >= 2:
        lx_, _, ly_ = both_cut[-2][2].partition('/')
        ab_ = {v: k for k, v in OP_ABBREV.items()}
        if lx_ in ab_ and ly_ in ab_ and _op_parts(ab_[ly_])[1] in SIGN_FLIP:
            qy_ = _op_join(_op_parts(ab_[ly_])[0], SIGN_FLIP[_op_parts(ab_[ly_])[1]])
            nv_ = compute_variants(ep, ab_[lx_], qy_)[0]
            strong_lab.setdefault(nv_, f"{lx_}/{OP_ABBREV[qy_]}")
            if strong_votes.get(nv_, 0) < 14.3005:
                strong_votes[nv_] = 14.3005
    # 35. result 08 after 65 — the 2nd NUMBER (c+1 / c-1 on the running
    #     value) with its x sign flipped and its y step switched, c-1 / c-2
    #     on the running value (65 -> 08; 2nd NUMBER 29, rule 24's number 38).
    #     Goes to the declared cell with the family numbers.  No STRONG 20
    #     seat: all 11 seats above the band and the places under it were
    #     tried (2026-10-12) and each pushes an older round's result out
    if grid_ep is not None and grid_ep >= 0:
        nv_ = ((grid_ep // 10 + 4) % 10) * 10 + (grid_ep % 10 + 3) % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        strong_votes.setdefault(nv_, 0)
    # 36. result 19 after 08 — the 2nd NUMBER's operation (the 2nd NUMBER
    #     read on the EP: 62 = +1/+1 on EP 51) applied on the running value
    #     instead of the EP (+1/+1 on 08 = 19), as rule 31 does for the
    #     declared number.  Goes to the declared cell with the family
    #     numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0 and grid_ep != ep:
        s2_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 4) % 10
        nv_ = compute_variants(grid_ep, find_op(ep // 10, s2_ // 10), find_op(ep % 10, s2_ % 10))[0]
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3004:
            strong_votes[nv_] = 14.3004
    # 37. result 48 after 19 — the 2nd NUMBER read on the EP (73 = -1/+1 on
    #     EP 82) mirrored on x, its x sign flipped (+1/+1 = 93), with both
    #     digits cut, the same family (c+1/c+1 = 48).  Goes to the declared
    #     cell with the family numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        s2_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 4) % 10
        sx_, sy_ = find_op(ep // 10, s2_ // 10), find_op(ep % 10, s2_ % 10)
        if SIGN_FLIP[sx_] != sx_:
            qx_, qy_ = KK_CUT_TOGGLE[SIGN_FLIP[sx_]], KK_CUT_TOGGLE[sy_]
            nv_ = compute_variants(ep, qx_, qy_)[0]
            lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3003:
                strong_votes[nv_] = 14.3003
    # 38. result 30 after 48 — the operation of two rounds back again on
    #     this EP (19 came by c+1/-2; c+1/-2 on EP 72 = 30), as the SAME
    #     OPERATION AGAIN number does for the last round.  Goes to the
    #     declared cell with the family numbers, sits under the band
    if grid_ep is not None and _RRR3_PREV.get('op2'):
        qx_, qy_ = _RRR3_PREV['op2']
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3002:
            strong_votes[nv_] = 14.3002
    # 39. result 96 after 30 — the 2nd NUMBER read on the EP (94 = c-2/+2
    #     on EP 62) with rule 12's y: a +1/+2 step on y becomes c-1 (-> 96
    #     (c-2/c-1)).  STRONG 20 only; sits under the band
    if grid_ep is not None and grid_ep >= 0:
        s2_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 4) % 10
        sx_, sy_ = find_op(ep // 10, s2_ // 10), find_op(ep % 10, s2_ % 10)
        if sy_ in ('+1', '+2'):
            nv_ = compute_variants(ep, sx_, 'cut-1')[0]
            strong_lab.setdefault(nv_, f"{OP_ABBREV[sx_]}/c-1")
            if strong_votes.get(nv_, 0) < 14.3995:
                strong_votes[nv_] = 14.3995
    # 40. result 71 after 96 — rule 28's number (the last round's operation
    #     with both signs flipped and its x step switched: c-2/c-1 -> c+1/c+1
    #     = 76 on EP 10) also with its units digit cut, the y cut switched
    #     (-> c+1/+1 = 71).  Goes to the declared cell with the family
    #     numbers, sits under the band
    if _RRR3_PREV.get('op') and all(_op_parts(o_)[1] in ('+1', '+2', '-1', '-2') for o_ in _RRR3_PREV['op']):
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        hx_, hy_ = _RRR3_PREV['op']
        qx_ = _op_join(_op_parts(hx_)[0], m_sw[SIGN_FLIP[_op_parts(hx_)[1]]])
        qy_ = _op_join(not _op_parts(hy_)[0], SIGN_FLIP[_op_parts(hy_)[1]])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3001:
            strong_votes[nv_] = 14.3001
    # 41. result 46 after 71 — the 3RRR RESULT "C" number (the kept
    #     operation, 56 (-1/nc) on EP 66) with its x step switched, the
    #     nearest x (-> 46 (-2/nc)), as rules 23 and 27 do.  Goes to the
    #     declared cell with the family numbers, sits under the band
    if grid_ep is not None and keep_due and _op_parts(keep[5])[1] in ('+1', '+2', '-1', '-2'):
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        qx_ = _op_join(_op_parts(keep[5])[0], m_sw[_op_parts(keep[5])[1]])
        nv_ = compute_variants(ep, qx_, keep[6])[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[keep[6]]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30005:
            strong_votes[nv_] = 14.30005
    # 42. result 78 after 46 — the declared operations crossed, both signs
    #     flipped and both steps switched, the cuts staying with their
    #     operations (declared 90 (c-1/-1) on EP 51: -1/c-1 -> +1/c+1 ->
    #     +2/c+2 = 78).  Goes to the declared cell with the family numbers,
    #     sits under the band
    if grid_ep is not None and all(_op_parts(o_)[1] in ('+1', '+2', '-1', '-2') for o_ in (d_x, d_y)):
        m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
        qx_, qy_ = (_op_join(_op_parts(o_)[0], m_sw[SIGN_FLIP[_op_parts(o_)[1]]]) for o_ in (d_y, d_x))
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30004:
            strong_votes[nv_] = 14.30004
    # 43. result 31 after 20 — the SAME OPERATION AGAIN number mirrored: the
    #     last round's operation with both signs flipped (c-1/c+2 -> c+1/c-2
    #     = 31 on EP 78; rule 28 is this number with its x step switched).
    #     Goes to the declared cell with the family numbers, sits under the
    #     band
    if grid_ep is not None and _RRR3_PREV.get('op') and all(SIGN_FLIP[o_] != o_ for o_ in _RRR3_PREV['op']):
        qx_, qy_ = (SIGN_FLIP[o_] for o_ in _RRR3_PREV['op'])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30003:
            strong_votes[nv_] = 14.30003
    # 44. result 71 after 31 — the last round's operation with its x sign
    #     flipped and its y without the cut (c+1/c-2 -> c-1/-2 = 71 on EP
    #     33); the crossed form of this move (17 (-2/c-1)) already stands in
    #     the same-operation list.  Goes to the declared cell with the
    #     family numbers, sits under the band
    if grid_ep is not None and _RRR3_PREV.get('op') and SIGN_FLIP[_RRR3_PREV['op'][0]] != _RRR3_PREV['op'][0] \
            and _op_parts(_RRR3_PREV['op'][1])[0] and _op_parts(_RRR3_PREV['op'][1])[1]:
        qx_, qy_ = SIGN_FLIP[_RRR3_PREV['op'][0]], _op_join(False, _op_parts(_RRR3_PREV['op'][1])[1])
        nv_ = compute_variants(ep, qx_, qy_)[0]
        lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30002:
            strong_votes[nv_] = 14.30002
    # 45. result 36 after 71 — the 2nd NUMBER one above: c+1 / cut on the
    #     running value (71 -> 36; 2nd NUMBER 35, the POWER BASE number one
    #     above the declared number 26 - this is the one a decade up from
    #     it).  Goes to the declared cell with the family numbers, sits
    #     under the band
    if grid_ep is not None and grid_ep >= 0:
        nv_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 5) % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30001:
            strong_votes[nv_] = 14.30001
    # 46. result 43 after 36 — rule 24's number (c+2 / c-2 on the running
    #     value: 36 -> 09) read on the EP and mirrored, both signs flipped
    #     (09 = -2/-2 on EP 21 -> +2/+2 = 43).  Goes to the declared cell
    #     with the family numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        r24_ = ((grid_ep // 10 + 7) % 10) * 10 + (grid_ep % 10 + 3) % 10
        sx_, sy_ = find_op(ep // 10, r24_ // 10), find_op(ep % 10, r24_ % 10)
        if SIGN_FLIP[sx_] != sx_ and SIGN_FLIP[sy_] != sy_:
            qx_, qy_ = SIGN_FLIP[sx_], SIGN_FLIP[sy_]
            nv_ = compute_variants(ep, qx_, qy_)[0]
            lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[qy_]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300005:
                strong_votes[nv_] = 14.300005
    # 47. result 68 after 43 — the EP itself, nc/nc (operations on EP 68
    #     -> 68).  Goes to the declared cell with the family numbers, sits
    #     under the band
    if grid_ep is not None:
        nv_ = ep
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, 'nc/nc')]
        strong_lab.setdefault(nv_, 'nc/nc')
        if strong_votes.get(nv_, 0) < 14.300004:
            strong_votes[nv_] = 14.300004
    # 48. result 20 after 93 — a STRONG 20 number above the band with nc on
    #     x (25 (nc/+1)) brings the same number with its y cut toggled (20
    #     (nc/c+1)) (user, 2026-10-12).  Goes to the declared cell with the
    #     family numbers, sits under the band
    for a_ in [v for v in strong_lab if strong_votes.get(v, 0) > 19]:
        if a_ // 10 == ep // 10 and a_ != ep:
            nv_ = (a_ // 10) * 10 + cut(a_ % 10)
            lab_ = f"nc/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300003:
                strong_votes[nv_] = 14.300003
    # 49. result 01 after 20 — a STRONG 20 number under the band with a
    #     plain step of one on y (00 (c+2/-1)) brings the same number with
    #     the step dropped, nc on y (01 (c+2/nc)).  Goes to the declared cell
    #     with the family numbers, sits under the band
    o49_ = list(strong_lab)
    for a_ in [v for v in sorted(o49_, key=lambda v: (-strong_votes.get(v, 0), o49_.index(v)))[:20]
               if strong_votes.get(v, 0) < 14.6]:
        if (a_ % 10 - ep % 10) % 10 in (1, 9):
            nv_ = (a_ // 10) * 10 + ep % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/nc"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300002:
                strong_votes[nv_] = 14.300002
    # 50. result 02 after 09 — the band number one under the declared number
    #     with the cut toggled on its x (52 (c-2/c-1) -> 02 (-2/c-1)), the
    #     CharRow "one below" number: nc / c-2 on the running value (09 ->
    #     02).  Goes to the declared cell with the family numbers, sits under
    #     the band
    if grid_ep is not None and grid_ep >= 0:
        nv_ = (grid_ep // 10) * 10 + (grid_ep % 10 + 3) % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000015:
            strong_votes[nv_] = 14.3000015
    # 51. result 21 after 48 — rule 50's number (the band number one under
    #     the declared number with the cut toggled on its x) with the sign of
    #     its x flipped too (91 (c+1/+1) -> 41 (+1/+1) -> 21 (-1/+1)), the
    #     CharRow third-row "one below" number.  Goes to the declared cell
    #     with the family numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        n1_ = (grid_ep // 10) * 10 + (grid_ep % 10 + 3) % 10
        d_ = (n1_ // 10 - ep // 10) % 10
        k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
        nv_ = ((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + n1_ % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000014:
            strong_votes[nv_] = 14.3000014
    # 52. result 84 after 63 — the CharRow last-operation-step numbers: a
    #     CharRow number with a plain cut on x (44 (cut/c+2)) takes the steps
    #     of the RRR table's LAST row in place of that cut (+1/+1 -> +1 and
    #     -1: 04 and 84 (-1/c+2)).  Go to the declared cell with the family
    #     numbers, sit under the band
    if grid_ep is not None and grid_ep >= 0 and len(both_cut) >= 2:
        t52_, u52_ = cut(grid_ep // 10), (grid_ep % 10 + 4) % 10
        b52_ = [t52_ * 10 + u52_, (t52_ * 10 + u52_ + 10) % 100, t52_ * 10 + (u52_ - 1) % 10, t52_ * 10 + (u52_ + 1) % 10]
        b52_ += [compute_variants(ep, SIGN_FLIP[find_op(ep % 10, v % 10)], SIGN_FLIP[find_op(ep // 10, v // 10)])[0]
                 for v in b52_[:4]]
        c52_ = [((v // 10 + 5) % 10) * 10 + v % 10 for v in b52_]
        s52_ = [st_ for d_ in '12' if d_ in both_cut[-2][2] for st_ in (int(d_), -int(d_))]
        for v in c52_:
            if (v // 10 - ep // 10) % 10 == 5:
                for st_ in s52_:
                    nv_ = ((ep // 10 + st_) % 10) * 10 + v % 10
                    lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
                    if nv_ not in [w for w, _ in fam_seats]:
                        fam_seats = fam_seats + [(nv_, lab_)]
                    strong_lab.setdefault(nv_, lab_)
                    if strong_votes.get(nv_, 0) < 14.3000013:
                        strong_votes[nv_] = 14.3000013
    # 53. result 30 after 25 — the band number one above the declared number
    #     (70 (+2/-1)) with the sign of its x flipped (30 (-2/-1)), a STRONG
    #     20 ADJUSTMENTS number.  Goes to the declared cell with the family
    #     numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        n1_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 5) % 10
        d_ = (n1_ // 10 - ep // 10) % 10
        k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
        nv_ = ((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + n1_ % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000012:
            strong_votes[nv_] = 14.3000012
    # 54. result 06 after 30 — the band number two above the declared number
    #     (86 (-1/nc)) with the sign of its x flipped (06 (+1/nc)), a STRONG
    #     20 ADJUSTMENTS number; rule 53 one step further.  Goes to the
    #     declared cell with the family numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        n1_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 6) % 10
        d_ = (n1_ // 10 - ep // 10) % 10
        k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
        nv_ = ((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + n1_ % 10
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000011:
            strong_votes[nv_] = 14.3000011
    # 55. result 71 after 82 — a number that is on the 3RRR RESULT line and
    #     also a STRONG 20 number above the band (26 (+1/nc)) brings itself
    #     with both digits cut (71 (c+1/cut)); rule 32 the other way round.
    #     Goes to the declared cell with the family numbers, sits under the
    #     band (a seat above the fill numbers pushed 82 and 06 out of two
    #     older rounds)
    p20_ = [v for v in strong_lab if strong_votes.get(v, 0) > 19]
    for n_, _ in found:
        a_ = int(n_[:2])
        if a_ in p20_:
            nv_ = cut(a_ // 10) * 10 + cut(a_ % 10)
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300001:
                strong_votes[nv_] = 14.300001
    # 56. result 30 after 30 — the after number itself comes again (the
    #     running value 30 -> 30, c-2/c-1 on EP 06).  Goes to the declared
    #     cell with the family numbers, sits under the band
    if grid_ep is not None and grid_ep >= 0:
        nv_ = grid_ep
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000009:
            strong_votes[nv_] = 14.3000009
    # 57. result 17 after 30 — the first 3RRR RESULT number (27 (-1/c+2))
    #     with its x step switched, the nearest x (-> 17 (-2/c+2)); rule 41
    #     for the first number of the line.  Goes to the declared cell with
    #     the family numbers, sits under the band
    if grid_ep is not None and found:
        a_ = int(found[0][0][:2])
        fx_, fy_ = find_op(ep // 10, a_ // 10), find_op(ep % 10, a_ % 10)
        if _op_parts(fx_)[1] in ('+1', '+2', '-1', '-2'):
            m_sw = {'+1': '+2', '+2': '+1', '-1': '-2', '-2': '-1'}
            qx_ = _op_join(_op_parts(fx_)[0], m_sw[_op_parts(fx_)[1]])
            nv_ = compute_variants(ep, qx_, fy_)[0]
            lab_ = f"{OP_ABBREV[qx_]}/{OP_ABBREV[fy_]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000008:
                strong_votes[nv_] = 14.3000008
    # 58. result 08 after 17 — the first 3RRR RESULT number itself (08
    #     (c+2/-2)); it was on the result line but not in the declared cell.
    #     Goes to the declared cell with the family numbers, sits under the
    #     band
    if grid_ep is not None and found:
        nv_ = int(found[0][0][:2])
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000007:
            strong_votes[nv_] = 14.3000007
    # 59. result 39 after 21 — the first STRONG 20 number above the band
    #     with a cut and a step on x (99 (c-2/c+1)) brings the same number
    #     with its x sign flipped (39 (c+2/c+1)).  Goes to the declared cell
    #     with the family numbers, sits under the band
    for a_ in sorted([v for v in strong_lab if strong_votes.get(v, 0) > 19], key=lambda v: -strong_votes[v]):
        hc_, st_ = _op_parts(find_op(ep // 10, a_ // 10))
        if hc_ and st_:
            nv_ = compute_variants(ep, SIGN_FLIP[find_op(ep // 10, a_ // 10)], find_op(ep % 10, a_ % 10))[0]
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000006:
                strong_votes[nv_] = 14.3000006
            break
    # 60. result 25 after 93 — a CharRow number whose operation is cut/nc
    #     (70 on EP 20) brings the same operation turned over, nc/cut (25):
    #     the EP with its y cut.  Goes to the declared cell with the family
    #     numbers and takes a STRONG 20 seat under the band (user, 2026-10-13:
    #     "repair it in Strong 20 and CharRow")
    if grid_ep is not None and grid_ep >= 0:
        t60_, u60_ = cut(grid_ep // 10), (grid_ep % 10 + 4) % 10
        b60_ = [t60_ * 10 + u60_, (t60_ * 10 + u60_ + 10) % 100, t60_ * 10 + (u60_ - 1) % 10, t60_ * 10 + (u60_ + 1) % 10]
        b60_ += [compute_variants(ep, SIGN_FLIP[find_op(ep % 10, v % 10)], SIGN_FLIP[find_op(ep // 10, v // 10)])[0]
                 for v in b60_[:4]]
        f60_ = [((v // 10 + 5) % 10) * 10 + v % 10 for v in b60_]
        for v in list(f60_):                      # the x-sign-changed rows
            d_ = (v // 10 - ep // 10) % 10
            k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
            f60_.append(((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + v % 10)
        q60_ = list(dict.fromkeys(f60_))          # repeats take a family pair's number reversed
        q60_ = [(a_, b_) for i_, a_ in enumerate(q60_) for b_ in q60_[i_ + 1:]
                if a_ % 5 == b_ % 5 and (a_ // 10) % 5 == (b_ // 10) % 5]
        q60_ = [int(f"{a_:02d}"[::-1]) for a_, b_ in q60_] + [int(f"{b_:02d}"[::-1]) for a_, b_ in q60_]
        s60_ = set()
        for k_, v in enumerate(f60_):
            if v in s60_:
                while q60_ and (q60_[0] in s60_ or q60_[0] in f60_[k_:]):
                    q60_.pop(0)
                if q60_:
                    v = q60_.pop(0)
            s60_.add(v)
        if cut(ep // 10) * 10 + ep % 10 in s60_:
            nv_ = (ep // 10) * 10 + cut(ep % 10)
            if nv_ not in [w for w, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, 'nc/cut')]
            strong_lab.setdefault(nv_, 'nc/cut')
            if strong_votes.get(nv_, 0) < 14.5:
                strong_votes[nv_] = 14.5
    # 61. result 54 after 25 — the first STRONG 20 number above the band
    #     with a plain cut on y (55 (+2/cut)) brings the same number with its
    #     y one step down (54 (+2/c-1)).  Goes to the declared cell with the
    #     family numbers, sits under the band (a seat at 14.5 broke 7 older hits)
    for a_ in sorted([v for v in strong_lab if strong_votes.get(v, 0) > 19], key=lambda v: -strong_votes[v]):
        if (a_ % 10 - ep % 10) % 10 == 5:
            nv_ = (a_ // 10) * 10 + (a_ % 10 - 1) % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/c-1"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000005:
                strong_votes[nv_] = 14.3000005
            break
    # 62. result 70 after 06 — the declared number two decades up (50 -> 70),
    #     the step after the POWER BASE's one decade up.  Goes to the declared
    #     cell with the family numbers and sits under the band (a seat at 14.5
    #     broke 6 older hits)
    nv_ = ((cut(grid_ep // 10) + 2) % 10) * 10 + (grid_ep % 10 + 4) % 10
    lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
    if nv_ not in [v for v, _ in fam_seats]:
        fam_seats = fam_seats + [(nv_, lab_)]
    strong_lab.setdefault(nv_, lab_)
    if strong_votes.get(nv_, 0) < 14.3000004:
        strong_votes[nv_] = 14.3000004
    # 63. result 71 after 44 (user's rule) — the first STRONG 20 number above
    #     the band with a plain step on x and a plain cut on y (26 (+2/cut))
    #     brings its opposite, the cut moved over to x (71 (c+2/nc)).  Goes to
    #     the declared cell with the family numbers and sits under the band
    #     (a seat at 14.5 gained 2 hits but broke 6 older ones)
    for a_ in sorted([v for v in strong_lab if strong_votes.get(v, 0) > 19], key=lambda v: -strong_votes[v]):
        if (a_ % 10 - ep % 10) % 10 == 5 and (a_ // 10 - ep // 10) % 10 in (1, 2, 8, 9):
            nv_ = cut(a_ // 10) * 10 + ep % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/nc"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000003:
                strong_votes[nv_] = 14.3000003
            break
    # 64. result 17 after 50 — the same STRONG 20 number as rule 63 (step on
    #     x, plain cut on y: 32 (+1/cut)) also brings its full opposite, x
    #     sign flipped and the cut taken off y (17 (-1/nc)).  Goes to the
    #     declared cell with the family numbers and sits under the band (a seat
    #     at 14.5 gained 2 hits but broke 6 older ones)
    for a_ in sorted([v for v in strong_lab if strong_votes.get(v, 0) > 19], key=lambda v: -strong_votes[v]):
        if (a_ % 10 - ep % 10) % 10 == 5 and (a_ // 10 - ep // 10) % 10 in (1, 2, 8, 9):
            nv_ = ((2 * (ep // 10) - a_ // 10) % 10) * 10 + ep % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/nc"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000002:
                strong_votes[nv_] = 14.3000002
            break
    # 65. result 55 after 97 — the 2nd number (c+1 / c-1 on the after number,
    #     51 (c+1/c-2)) with its y sign flipped (55 (c+1/c+2)).  Goes to the
    #     declared cell with the family numbers and sits under the band (a seat
    #     at 14.5 broke 5 older hits)
    s65_ = ((grid_ep // 10 + 6) % 10) * 10 + (grid_ep % 10 + 4) % 10
    y65_ = find_op(ep % 10, s65_ % 10)
    if SIGN_FLIP.get(y65_, y65_) != y65_:
        nv_ = compute_variants(ep, find_op(ep // 10, s65_ // 10), SIGN_FLIP[y65_])[0]
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.3000001:
            strong_votes[nv_] = 14.3000001
    # 66. result 72 after 55 — a STRONG 20 rule seat (seat 1: the first both-
    #     cut number with y sign flipped and cut toggled, 12 (+2/c-2) ->
    #     72 (-2/c-2)) lost its seat and was in no list.  Every rule seat
    #     now also goes to the declared cell; the 20 do not change
    for nv_, nlab_ in rule_seats:
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, nlab_)]
    # 67. result 68 after 72 (user's rule) — the star pick 28 (+1/-2): where
    #     a side has a plain step (+1/-1, +2/-2), the cut and nc on that side
    #     come too (68 (cut/-2), 18 (nc/-2), 25 (+1/cut), 20 (+1/nc)).  The
    #     star pick is worked out here the same way as in the ROUND SUMMARY
    #     (the 20 do not move: these numbers sit under the band; a seat at
    #     14.5 gained 2 hits and broke 3, the cut number alone gained 1 and
    #     broke 2)
    star_turn_ = []
    star67_ = None
    if grid_ep is not None:
        s67_ = sorted(order_ := list(strong_lab), key=lambda v: (-strong_votes[v], order_.index(v)))[:20]
        k67_ = {}
        for k_list in (s67_, [cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4 + k_) % 10 for k_ in range(-2, 3)],
                       [v_ for v_, _, _ in both_cut], [v_ for v_, _ in rec], [v_ for v_, _ in rec_yx],
                       [v_ for v_, _ in wide], [int(n_[:2]) for n_, _ in found],
                       [a_[0] for a_ in (same, same2, same_turn if same else None, same_yx if same else None) if a_]):
            for v_ in set(k_list):
                k67_[v_] = k67_.get(v_, 0) + 1
        if k67_:
            a_ = sorted(k67_, key=lambda v_: (-k67_[v_], v_))[0]
            star67_ = a_
            x67_, y67_ = find_op(ep // 10, a_ // 10), find_op(ep % 10, a_ % 10)
            if x67_ in ('+1', '-1', '+2', '-2'):
                star_turn_ += [compute_variants(ep, 'cut', y67_)[0], compute_variants(ep, 'no_change', y67_)[0]]
            if y67_ in ('+1', '-1', '+2', '-2'):
                star_turn_ += [compute_variants(ep, x67_, 'cut')[0], compute_variants(ep, x67_, 'no_change')[0]]
        for nv_ in star_turn_:
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000009:
                strong_votes[nv_] = 14.30000009
    # 68. result 45 after 68 (series K) — a star pick turn with a plain cut
    #     on y (46 (cut/cut)) comes with its y one step down (45 (cut/c-1)),
    #     as rule 61 does for the STRONG 20.  Declared cell only
    for a_ in list(star_turn_):
        if find_op(ep % 10, a_ % 10) == 'cut':
            nv_ = (a_ // 10) * 10 + (a_ % 10 - 1) % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/c-1"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000008:
                strong_votes[nv_] = 14.30000008
    # 69. result 73 after 45 (series K) — the first STRONG 20 number above
    #     the band with a cut and a step on x and a plain step on y
    #     (23 (c-2/+1)) comes with the cut taken off x (73 (-2/+1)); the
    #     adjustments flip the x sign and toggle the y cut, never the x cut.
    #     Declared cell only (a seat at 14.5 broke 5 older hits, gained none)
    for a_ in sorted([v for v in strong_lab if strong_votes.get(v, 0) > 19], key=lambda v: -strong_votes[v]):
        x69_, y69_ = find_op(ep // 10, a_ // 10), find_op(ep % 10, a_ % 10)
        if _op_parts(x69_)[0] and _op_parts(x69_)[1] and y69_ in ('+1', '-1', '+2', '-2'):
            nv_ = compute_variants(ep, _op_parts(x69_)[1], y69_)[0]
            lab_ = f"{OP_ABBREV[_op_parts(x69_)[1]]}/{OP_ABBREV[y69_]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000007:
                strong_votes[nv_] = 14.30000007
            break
    # 70. result 21 after 91 (series K) — the LAST row of the RRR next-
    #     operation table: its number with a plain cut on y (22 (c+1/cut))
    #     comes with its y one step down (21 (c+1/c-1)), as rules 61 and 68.
    #     Declared cell only
    for v_, _, l_ in both_cut[-2:]:
        if l_.partition('/')[2] == 'cut':
            nv_ = (v_ // 10) * 10 + (v_ % 10 - 1) % 10
            lab_ = f"{l_.partition('/')[0]}/c-1"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000006:
                strong_votes[nv_] = 14.30000006
    # 71. result 28 after 19 (series K) — the RRR table row that gave the
    #     star pick (Op14 30 -> 21, -1/+1 -> 61 (c-2/c-1)): its own old
    #     operation applied again on this EP, xy and yx (28 (-1/+1),
    #     46 (+1/-1)).  Declared cell only
    for i_, (v_, _, _) in enumerate(both_cut):
        if star67_ is not None and v_ == star67_ and i_ // 2 < len(src):
            ox_, oy_ = src[i_ // 2][3], src[i_ // 2][4]
            for nv_, lab_ in ((compute_variants(ep, ox_, oy_)[0], f"{OP_ABBREV[ox_]}/{OP_ABBREV[oy_]}"),
                              (compute_variants(ep, oy_, ox_)[0], f"{OP_ABBREV[oy_]}/{OP_ABBREV[ox_]}")):
                if nv_ not in [v for v, _ in fam_seats]:
                    fam_seats = fam_seats + [(nv_, lab_)]
                strong_lab.setdefault(nv_, lab_)
                if strong_votes.get(nv_, 0) < 14.30000005:
                    strong_votes[nv_] = 14.30000005
            break
    # 72. result 24 after 28 (series K) — RECOMMENDED F, the last row not
    #     crossed with both sides one step down / up (24 (-1/-2), 46 (+1/nc)),
    #     was in RECOMMENDED only.  These numbers go to the declared cell
    for nv_, lab_ in stepped:
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30000004:
            strong_votes[nv_] = 14.30000004
    # 73. result 55 after 94 (series K) — RECOMMENDED F, first form: the last
    #     row / chain's last step not crossed, one side dropped to nc (55 (-2/nc),
    #     76, 85, 74), was in RECOMMENDED only — as rule 72 for the third form.
    #     These numbers go to the declared cell
    for nv_, lab_ in dropped:
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30000003:
            strong_votes[nv_] = 14.30000003
    # 74. result 62 after 22 (series K) — the STRONG 20 seats below the band
    #     (#17-#20) with their y cut toggled, as the adjustments box shows them
    #     (67 (-1/-1) -> 62 (-1/c-1)).  Declared cell only
    o74_ = list(strong_lab)
    for a_ in sorted(o74_, key=lambda v: (-strong_votes[v], o74_.index(v)))[16:20]:
        x74_, y74_ = find_op(ep // 10, a_ // 10), find_op(ep % 10, a_ % 10)
        if y74_ in KK_CUT_TOGGLE:
            nv_ = compute_variants(ep, x74_, KK_CUT_TOGGLE[y74_])[0]
            lab_ = f"{OP_ABBREV[x74_]}/{OP_ABBREV[KK_CUT_TOGGLE[y74_]]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000002:
                strong_votes[nv_] = 14.30000002
    # 75. result 54 after 22 (series K) — rules 53 and 54 on the other side of
    #     the band: the band numbers one and two below the declared number
    #     (75 (+1/c-2), 74 (+1/+2)) with the sign of their x flipped (55, 54),
    #     STRONG 20 ADJUSTMENTS numbers.  Declared cell only
    if grid_ep is not None and grid_ep >= 0:
        for off_ in (3, 2):
            n1_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + off_) % 10
            d_ = (n1_ // 10 - ep // 10) % 10
            k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
            nv_ = ((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + n1_ % 10
            lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000001:
                strong_votes[nv_] = 14.30000001
    # 76. result 96 after 34 (series K) — the 3RRR WIDE list (rule G: single
    #     moves seen on middle rows, tried on every row) held 96 (c+1/+2) but
    #     the cell did not.  The wide numbers go to the declared cell
    for nv_, lab_ in wide:
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000009:
            strong_votes[nv_] = 14.300000009
    # 77. result 36 after 96 (series K) — the 3RRR RESULT line held 36 as its
    #     4th number (94 65 66 36) but only the first number was in the cell.
    #     Every 3RRR RESULT number goes to the declared cell
    for n77_, _ in found:
        nv_ = int(n77_[:2])
        lab_ = f"{OP_ABBREV[find_op(ep // 10, nv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, nv_ % 10)]}"
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000008:
            strong_votes[nv_] = 14.300000008
    # 78. result 89 after 85 (series K) — the RRR: NEXT OPERATION table held
    #     89 (+1/-1) (Op33 yx) but the cell did not.  Every number of the
    #     table goes to the declared cell
    for nv_, _, lab_ in both_cut:
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000007:
            strong_votes[nv_] = 14.300000007
    # 79. result 45 after 89 (series K) — the SAME OPERATION AGAIN crossed
    #     the user's way (old y without its cut, old x sign flipped) gave
    #     45 (-1/-1) but the cell did not hold it.  Both crossed forms of the
    #     last round's operation (yx, and yx turned) go to the declared cell
    for again_ in ((same_yx, same_turn) if same else ()):
        nv_, lab_ = again_
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000006:
            strong_votes[nv_] = 14.300000006
    # 80. result 57 after 31 (series K) — NEXT OPERATION-OCJP place 35 held
    #     57 (-1/-1) but the cell did not.  The OCJP places 31-38 (one
    #     operation on both sides, sign flipped on one side) go to the cell
    for nv_, lab_, k_, _ in _rrr_ocjp(ep, both_cut):
        if k_ <= 30:
            continue
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000005:
            strong_votes[nv_] = 14.300000005
    # 83. result 38 after 02 (series K) — NEXT OPERATION-OCJP place 26 (a
    #     mirror form ^) held 38 (nc/-1) but the cell did not.  The OCJP
    #     mirror places 21-30 go to the cell too (rule 80 extended)
    for nv_, lab_, k_, _ in _rrr_ocjp(ep, both_cut):
        if not 20 < k_ <= 30:
            continue
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000003:
            strong_votes[nv_] = 14.300000003
    # 84. result 45 after 38 (series K) — NEXT OPERATION-OCJP place 15 (one
    #     of the user's places 1-20) held 45 (-1/cut) but the cell did not.
    #     The places 1-20 go to the cell too: with rules 80 and 83 every
    #     OCJP place (1-38) is now in the declared cell
    for nv_, lab_, k_, _ in _rrr_ocjp(ep, both_cut):
        if k_ > 20:
            continue
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000002:
            strong_votes[nv_] = 14.300000002
    # 85. result 86 after 04 (series K) — 86 (nc/c+1) was outside the cell
    #     and outside OCJP; OCJP place 26 held 81 (nc/+1).  The new OCJP #
    #     forms (x without a step, y cut switched) go to the cell
    for o_ in _rrr_ocjp(ep, both_cut):
        for nv_, lab_ in _rrr_ocjp_ycut(ep, o_[1], o_[2]):
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000000015:
                strong_votes[nv_] = 14.3000000015
    # 86. result 47 after 60 (series K) — 47 (c-2/-1) was outside the cell;
    #     OCJP place 21 (a mirror place ^) held it as its + form, the x
    #     step switched (57 c-1/-1 -> 47 c-2/-1).  The + forms of the
    #     mirror places 21-30 go to the cell (rule 83 extended)
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 20 < o_[2] <= 30:
            continue
        w_ = _rrr_ocjp_xswitch(ep, o_[1])
        if not w_:
            continue
        nv_, lab_ = w_
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30000000125:
            strong_votes[nv_] = 14.30000000125
    # 87. result 57 after 99 (series K) — 57 (-1/-1) was outside the cell;
    #     OCJP place 18 held it as a * form (46 -2/-2, both steps switched).
    #     The * forms of the places 11-20 go to the cell
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 10 < o_[2] <= 20:
            continue
        for nv_, lab_ in _rrr_ocjp_more(ep, o_[1]):
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.3000000011:
                strong_votes[nv_] = 14.3000000011
    # 88. result 49 after 78 (series K) — 49 (nc/c-1) was outside the cell;
    #     OCJP place 13 held it as its + form (48 nc/c-2, y step switched).
    #     The + forms of the places 9-14 (x fixed at cut or nc) go to the cell
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 9 <= o_[2] <= 14:
            continue
        w_ = _rrr_ocjp_xswitch(ep, o_[1])
        if not w_:
            continue
        nv_, lab_ = w_
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30000000105:
            strong_votes[nv_] = 14.30000000105
    # 89. result 39 after 77 (series K) — 39 (+1/-2) was outside the cell;
    #     OCJP place 35 held it as a * form (30 +1/-1, y step switched).
    #     The * forms of the places 31-38 go to the cell (rule 87 extended)
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 31 <= o_[2] <= 38:
            continue
        for nv_, lab_ in _rrr_ocjp_more(ep, o_[1]):
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300000001025:
                strong_votes[nv_] = 14.300000001025
    # 90. result 65 after 41 (series L) — 65 (c-1/cut) was outside the cell;
    #     OCJP place 16 held it as its + form (the x step switched).  The +
    #     forms of the places 15-20 go to the cell (fills the gap between
    #     rule 88, places 9-14, and rule 86, places 21-30)
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 15 <= o_[2] <= 20:
            continue
        w_ = _rrr_ocjp_xswitch(ep, o_[1])
        if not w_:
            continue
        nv_, lab_ = w_
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.30000000102:
            strong_votes[nv_] = 14.30000000102
    # 91. result 86 after 80 (series M) — 86 (c+1/c-2) was outside the cell;
    #     OCJP place 32 held it as its + form (96 c+2/c-2, x step switched).
    #     The + forms of the places 31-38 go to the cell (rule 89 gave
    #     those places only their * forms)
    for o_ in _rrr_ocjp(ep, both_cut):
        if not 31 <= o_[2] <= 38:
            continue
        w_ = _rrr_ocjp_xswitch(ep, o_[1])
        if not w_:
            continue
        nv_, lab_ = w_
        if nv_ not in [v for v, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, lab_)]
        strong_lab.setdefault(nv_, lab_)
        if strong_votes.get(nv_, 0) < 14.300000001015:
            strong_votes[nv_] = 14.300000001015
    # 92. result 83 after 82 (series M) — 83 (+2/+1) was outside the cell
    #     and outside OCJP; OCJP place 2 held 43 (-2/+1), the same op with
    #     the x sign flipped.  The new OCJP ! forms (places 1-8, x sign
    #     flipped) go to the cell
    for o_ in _rrr_ocjp(ep, both_cut):
        for nv_, lab_ in _rrr_ocjp_xflip(ep, o_[1], o_[2]):
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.30000000101:
                strong_votes[nv_] = 14.30000000101
    # 93. result 72 after 81 (series N) — 72 (-2/-2) was outside the cell;
    #     OCJP place 26 (a mirror place ^) held it as a * form (both steps
    #     switched).  Rules 86-91 gave the + and * forms only to some place
    #     ranges; now the + , * and % forms of every OCJP place go to the
    #     cell, so the cell holds every OCJP number
    for o_ in _rrr_ocjp(ep, both_cut):
        w_ = _rrr_ocjp_xswitch(ep, o_[1])
        for nv_, lab_ in ([w_] if w_ else []) + _rrr_ocjp_more(ep, o_[1]) + _rrr_ocjp_xcut(ep, o_[1], o_[2]):
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300000001005:
                strong_votes[nv_] = 14.300000001005
    # 81. result 33 after 57 (series K, user's screenshot) — the NC/CUT
    #     SPECIAL numbers (the row after an nc/cut, cut/nc or nc/nc row,
    #     modified every way) go to the declared cell
    for _, _, lst_ in nc_spec:
        for nv_, lab_ in lst_:
            if nv_ not in [v for v, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, lab_)]
            strong_lab.setdefault(nv_, lab_)
            if strong_votes.get(nv_, 0) < 14.300000004:
                strong_votes[nv_] = 14.300000004
    order = list(strong_lab)
    if os.environ.get('RRR3_DUMP'):
        import json
        with open(os.environ['RRR3_DUMP'], 'w') as fh:
            json.dump({'ep': ep, 'grid_ep': grid_ep, 'order': order,
                       'rec': {v: rec_votes.get(v, 1) for v, _ in rec}, 'yx': [v for v, _ in rec_yx],
                       'wide': wide_votes, 'found': [int(n[:2]) for n, _ in found],
                       'table': [v for v, _, _ in both_cut]}, fh)
    # widened from 16 to 20 on the user's request (2026-10-11): 24 rules
    # were competing for the 11 seats above the band and the last two
    # (rules 24, 25) could not be seated without pushing an older one out
    strong = sorted(order, key=lambda v: (-strong_votes[v], order.index(v)))[:20]
    if os.environ.get('RRR3_DUMP2'):
        if os.environ.get('RRR3_VOTES'):
            print('VOTES', [(v, strong_votes[v]) for v in sorted(order, key=lambda v: (-strong_votes[v], order.index(v)))[:26]], file=sys.stderr)
        import json
        with open(os.environ['RRR3_DUMP2'], 'w') as fh:
            json.dump({'ep': ep, 'grid_ep': grid_ep, 'strong': strong,
                       'table': [[v, lab] for v, _, lab in both_cut],
                       'ocjp': [o[0] for o in _rrr_ocjp(ep, both_cut)]
                               + [w[0] for w in (_rrr_ocjp_xswitch(ep, o[1]) for o in _rrr_ocjp(ep, both_cut)) if w]
                               + [m[0] for o in _rrr_ocjp(ep, both_cut) for m in _rrr_ocjp_more(ep, o[1])]
                               + [m[0] for o in _rrr_ocjp(ep, both_cut) for m in _rrr_ocjp_ycut(ep, o[1], o[2])]
                               + [m[0] for o in _rrr_ocjp(ep, both_cut) for m in _rrr_ocjp_xcut(ep, o[1], o[2])]
                               + [m[0] for o in _rrr_ocjp(ep, both_cut) for m in _rrr_ocjp_xflip(ep, o[1], o[2])],
                       'ncspec': [v for _, _, l_ in nc_spec for v, _ in l_],
                       'ocjp_full': [[o[0], o[1], o[2], 'base'] for o in _rrr_ocjp(ep, both_cut)]
                                    + [[w[0], w[1], o[2], 'plus'] for o in _rrr_ocjp(ep, both_cut)
                                       for w in [_rrr_ocjp_xswitch(ep, o[1])] if w]
                                    + [[m[0], m[1], o[2], 'star'] for o in _rrr_ocjp(ep, both_cut)
                                       for m in _rrr_ocjp_more(ep, o[1])]
                                    + [[m[0], m[1], o[2], 'ycut'] for o in _rrr_ocjp(ep, both_cut)
                                       for m in _rrr_ocjp_ycut(ep, o[1], o[2])]
                                    + [[m[0], m[1], o[2], 'xcut'] for o in _rrr_ocjp(ep, both_cut)
                                       for m in _rrr_ocjp_xcut(ep, o[1], o[2])]
                                    + [[m[0], m[1], o[2], 'xflip'] for o in _rrr_ocjp(ep, both_cut)
                                       for m in _rrr_ocjp_xflip(ep, o[1], o[2])],
                       'rule_seats': [v for v, _ in rule_seats], 'fam_seats': [v for v, _ in fam_seats],
                       'rec': [v for v, _ in rec], 'yx': [v for v, _ in rec_yx], 'wide': [v for v, _ in wide],
                       'found': [int(n[:2]) for n, _ in found],
                       'again': [a[0] if a else None for a in (same, same2, same_turn if same else None,
                                                               same_yx if same else None)]}, fh)
    # drawn as a green table: ribbon label, then 4 numbers a row, each with
    # its rank and the operation applied to the EP
    s_g, s_rib, s_rst = "\033[1;32m", "\033[1;97;42m", "\033[0m"
    s_cells = [f"#{k + 1:<2} {v:02d} ({strong_lab[v]})" for k, v in enumerate(strong)]
    s_cw = max([len(c) for c in s_cells] + [16]) + 2
    s_per = 4
    s_tw = s_per * s_cw + s_per - 1
    s_title = f"★  3RRR STRONG 20   —   operations applied on EP={ep:02d}  ★"
    strong_lines = [f"  {s_g}┌{'─' * s_tw}┐{s_rst}",
                    f"  {s_g}│{s_rst}{s_rib}{s_title:^{s_tw}}{s_rst}{s_g}│{s_rst}",
                    f"  {s_g}├{'┬'.join('─' * s_cw for _ in range(s_per))}┤{s_rst}"]
    for s_k in range(0, max(len(s_cells), 1), s_per):
        s_row = s_cells[s_k:s_k + s_per] + [''] * (s_per - len(s_cells[s_k:s_k + s_per]))
        if s_k:
            strong_lines.append(f"  {s_g}├{'┼'.join('─' * s_cw for _ in range(s_per))}┤{s_rst}")
        strong_lines.append(f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c:<{s_cw - 1}}" for c in s_row)
                            + f"{s_g}│{s_rst}")
    strong_lines.append(f"  {s_g}└{'┴'.join('─' * s_cw for _ in range(s_per))}┘{s_rst}")
    s_tbl_n = len(strong_lines)
    # STRONG 20 ADJUSTMENTS (user, 2026-10-12): beside each STRONG 20 number,
    # two one-step adjustments of its operation given beforehand — its y
    # with the cut toggled (25 (nc/+1) -> 20 (nc/c+1)) and its x with the
    # sign flipped.  Display only, counted separately; on the 13 re-run
    # rounds the STRONG 20 missed these two caught 4 and 3
    def _adj_lab(v_):
        return f"{OP_ABBREV[find_op(ep // 10, v_ // 10)]}/{OP_ABBREV[find_op(ep % 10, v_ % 10)]}"
    a_cells, strong_adj = [], []
    for k, v in enumerate(strong):
        a_y = (v // 10) * 10 + cut(v % 10)
        a_d = (v // 10 - ep // 10) % 10
        a_c = 5 if a_d in (3, 4, 5, 6, 7) else 0
        a_s = (a_d - a_c) % 10
        a_x = ((ep // 10 + a_c - a_s) % 10) * 10 + v % 10
        a_nums = [a_y] + ([a_x] if a_x != v else [])
        strong_adj += a_nums
        a_cells.append(f"#{k + 1:<2} {v:02d} ({strong_lab[v]}) → " + ', '.join(f"{n_:02d} ({_adj_lab(n_)})" for n_ in a_nums))
    # 82. result 93 after 23 (series K) — STRONG 20 ADJUSTMENTS #4 98
    #     (c+2/nc) with its y cut toggled gave 93 (c+2/cut) but the cell did
    #     not hold it.  The y-cut-toggled column of the adjustments goes to
    #     the declared cell (cell only, the STRONG 20 is already chosen)
    for v in strong:
        nv_ = (v // 10) * 10 + cut(v % 10)
        if nv_ not in [w for w, _ in fam_seats]:
            fam_seats = fam_seats + [(nv_, _adj_lab(nv_))]
    # result 85 after 25 on EP 90 (series N, N28): STRONG 20 ADJUSTMENTS #4
    #     05 (+1/cut) with its x sign flipped gave 85 (-1/cut) but the cell
    #     did not hold it.  The x-sign-flipped column of the adjustments goes
    #     to the declared cell too, so every adjustments number is in it
    for v in strong_adj:
        if v not in [w for w, _ in fam_seats]:
            fam_seats = fam_seats + [(v, _adj_lab(v))]
    # result 44 after 99 on EP 81 (series M, M1): STRONG 20 #14 44
    # (c+1/c-2) was outside the cell.  Every STRONG 20 number is in the
    # declared cell (cell only); on the M re-run 6 of 11 rounds had 1-2
    # STRONG 20 numbers outside it
    for v in strong:
        if v not in [w for w, _ in fam_seats]:
            fam_seats = fam_seats + [(v, _adj_lab(v))]
    # result 88 after 63 on EP 05 (series M, M21): 88 (-2/c-2) was STRONG
    # 20 #20 99 (-1/c-1) with both steps switched (1 <-> 2) and outside the
    # cell.  A STRONG 20 number with a step on both sides brings itself with
    # both steps switched (cell only); on M1-M21 it adds 0.9 numbers a round
    for v in strong:
        sx_, sy_ = (v // 10 - ep // 10) % 10, (v % 10 - ep % 10) % 10
        sw_ = {1: 2, 2: 1, 9: 8, 8: 9, 6: 7, 7: 6, 4: 3, 3: 4}
        if sx_ in sw_ and sy_ in sw_:
            nv_ = ((ep // 10 + sw_[sx_]) % 10) * 10 + (ep % 10 + sw_[sy_]) % 10
            if nv_ not in [w for w, _ in fam_seats]:
                fam_seats = fam_seats + [(nv_, _adj_lab(nv_))]
    if os.environ.get('RRR3_DUMP2'):
        import json
        with open(os.environ['RRR3_DUMP2']) as fh:
            d2_ = json.load(fh)
        d2_['fam_seats'] = [v for v, _ in fam_seats]
        with open(os.environ['RRR3_DUMP2'], 'w') as fh:
            json.dump(d2_, fh)
    a_per = 2
    a_cw = max([len(c) for c in a_cells] + [2 * s_cw - 1, 56]) + 2
    a_tw = a_per * a_cw + a_per - 1
    a_after = f"after {grid_ep:02d}, on EP={ep:02d}" if grid_ep is not None and grid_ep >= 0 else f"on EP={ep:02d}"
    a_new = len(set(strong_adj) - set(strong))
    a_title = (f"★  STRONG 20 ADJUSTMENTS  —  {a_after}  —  y cut toggled, x sign flipped  —  "
               f"{len(strong)} + {a_new} new = {len(strong) + a_new} numbers  ★")
    strong_lines += [f"  {s_g}┌{'─' * a_tw}┐{s_rst}",
                     f"  {s_g}│{s_rst}{s_rib}{a_title:^{a_tw}}{s_rst}{s_g}│{s_rst}",
                     f"  {s_g}├{'┬'.join('─' * a_cw for _ in range(a_per))}┤{s_rst}"]
    for a_k in range(0, len(a_cells), a_per):
        a_row = a_cells[a_k:a_k + a_per] + [''] * (a_per - len(a_cells[a_k:a_k + a_per]))
        strong_lines.append(f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c:<{a_cw - 1}}" for c in a_row)
                            + f"{s_g}│{s_rst}")
    # the total printed in the box too (user, 2026-10-12): the count, the
    # new numbers the adjustments add and all the numbers together, ascending
    a_newl = sorted(set(strong_adj) - set(strong))
    a_alll = sorted(set(strong_adj) | set(strong))
    a_foot = [f"TOTAL {len(a_alll)} numbers  =  {len(strong)} STRONG + {len(a_newl)} new from the adjustments"]
    for a_name, a_list in ((f"NEW ({len(a_newl)})", a_newl), (f"ALL ({len(a_alll)})", a_alll)):
        a_pre, a_room = f"{a_name}: ", max((a_tw - 2 - len(a_name) - 2) // 3, 1)
        for a_k in range(0, len(a_list), a_room):
            a_foot.append((a_pre if not a_k else ' ' * len(a_pre)) + ' '.join(f"{n_:02d}" for n_ in a_list[a_k:a_k + a_room]))
    strong_lines.append(f"  {s_g}├{'┴'.join('─' * a_cw for _ in range(a_per))}┤{s_rst}")
    strong_lines += [f"  {s_g}│{s_rst} {l_:<{a_tw - 1}}{s_g}│{s_rst}" for l_ in a_foot]
    strong_lines.append(f"  {s_g}└{'─' * a_tw}┘{s_rst}")
    # 40RRR FINAL-RESULT-TABLE: every recommended number in four columns —
    # the STRONG 16 first, then the rest of the recommended, yx and wide
    # lists in their own order, each with the operation applied to the EP
    f_all = strong + [v for v in order if v not in strong]
    f_cells = [f"{k + 1:>2}. {v:02d} ({strong_lab[v]})" for k, v in enumerate(f_all)]
    f_cw = max([len(c) for c in f_cells] + [16]) + 2
    f_per = 4
    f_tw = f_per * f_cw + f_per - 1
    f_title = f"★  40RRR FINAL-RESULT-TABLE  —  all {len(f_all)} recommended numbers on EP={ep:02d}  ★"
    final_lines = [f"  {s_g}┌{'─' * f_tw}┐{s_rst}",
                   f"  {s_g}│{s_rst}{s_rib}{f_title:^{f_tw}}{s_rst}{s_g}│{s_rst}",
                   f"  {s_g}├{'┬'.join('─' * f_cw for _ in range(f_per))}┤{s_rst}"]
    for f_k in range(0, max(len(f_cells), 1), f_per):
        f_row = f_cells[f_k:f_k + f_per] + [''] * (f_per - len(f_cells[f_k:f_k + f_per]))
        final_lines.append(f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c:<{f_cw - 1}}" for c in f_row)
                           + f"{s_g}│{s_rst}")
    final_lines.append(f"  {s_g}└{'┴'.join('─' * f_cw for _ in range(f_per))}┘{s_rst}")
    # POWER BASE: only four numbers.  Chosen by comparing seven ways of
    # picking four on all 423 recorded rounds: the declared number of the
    # running value (tens cut, units +4), the same number one decade up, and
    # the declared number one below and one above.  36 hits in 423 rounds =
    # 8.5% against 4% by chance; in the latest series 7 in 170 = chance.
    power_lines = []
    if live and grid_ep is not None:
        p_t, p_u = cut(grid_ep // 10), (grid_ep % 10 + 4) % 10
        p_decl = p_t * 10 + p_u
        p_four = [(p_decl, "declared number"), ((p_decl + 10) % 100, "one decade up"),
                  (p_t * 10 + (p_u - 1) % 10, "one below"), (p_t * 10 + (p_u + 1) % 10, "one above")]
        p_cells = [f"{v:02d} ({OP_ABBREV[find_op(ep // 10, v // 10)]}/{OP_ABBREV[find_op(ep % 10, v % 10)]})"
                   for v, _ in p_four]
        # second row (user's screenshot, 2026-10-08): each number's operations
        # reversed — x and y crossed and both signs flipped — applied to the EP
        p_rev = []
        for v, _ in p_four:
            rx = SIGN_FLIP[find_op(ep % 10, v % 10)]
            ry = SIGN_FLIP[find_op(ep // 10, v // 10)]
            p_rev.append(f"{compute_variants(ep, rx, ry)[0]:02d} ({OP_ABBREV[rx]}/{OP_ABBREV[ry]})")
        # third row (user's screenshot, 2026-10-08): the yx number of the RRR
        # table's last row and that operation reversed; the first STRONG 16
        # number and the same with the cut taken off its y operation
        p_third = []
        if both_cut:
            lv, _, llab = both_cut[-1]
            lx_, _, ly_ = llab.partition('/')
            p_third.append((f"{lv:02d} ({llab})", "RRR last row yx"))
            if lx_ in abbrev_op and ly_ in abbrev_op:
                rx, ry = SIGN_FLIP[abbrev_op[ly_]], SIGN_FLIP[abbrev_op[lx_]]
                p_third.append((f"{compute_variants(ep, rx, ry)[0]:02d} ({OP_ABBREV[rx]}/{OP_ABBREV[ry]})",
                                "that, reversed"))
        if strong:
            sx_, _, sy_ = strong_lab[strong[0]].partition('/')
            p_third.append((f"{strong[0]:02d} ({strong_lab[strong[0]]})", "STRONG 20 first"))
            if sx_ in abbrev_op and sy_ in abbrev_op:
                uy = _op_join(False, _op_parts(abbrev_op[sy_])[1])
                p_third.append((f"{compute_variants(ep, abbrev_op[sx_], uy)[0]:02d} ({sx_}/{OP_ABBREV[uy]})",
                                "its y without the cut"))
        p_third += [('', '')] * (4 - len(p_third))
        # fourth row (user's screenshot, 2026-10-08 evening): the xy number of
        # the RRR table's last row (only its yx was in the third row)
        p_fourth = []
        if len(both_cut) >= 2:
            xv_, _, xlab_ = both_cut[-2]
            p_fourth.append((f"{xv_:02d} ({xlab_})", "RRR last row xy"))
        p_fourth += [('', '')] * (4 - len(p_fourth))
        # partner numbers (user's screenshot, 2026-10-08): wherever a cell's y
        # operation is a plain -1, -2, +1 or +2, the same x with the y step
        # switched (-1 <-> -2, +1 <-> +2) is added after a comma
        p_swap = {'-1': '-2', '-2': '-1', '+1': '+2', '+2': '+1'}

        def p_pair(cell):
            px_, _, py_ = cell[4:-1].partition('/') if cell else ('', '', '')
            if py_ not in p_swap or px_ not in abbrev_op:
                return cell
            pv = compute_variants(ep, abbrev_op[px_], abbrev_op[p_swap[py_]])[0]
            return f"{cell}, {pv:02d} ({px_}/{p_swap[py_]})"

        # cut numbers (user's screenshot, 2026-10-08): only in those same cells
        # (plain y step), each of the two numbers is followed by the same number
        # with the cut put on its y step: 75 (c+1/+2), 70 (c+1/c+2), 74 (c+1/+1),
        # 79 (c+1/c+1).  The second pair goes on the cell's second line.
        def p_cut(cell):
            parts = cell.split(', ')
            if len(parts) != 2:
                return [cell]
            out, extra = [], []
            for part in parts:
                px_, _, py_ = part[4:-1].partition('/')
                cy = KK_CUT_TOGGLE[abbrev_op[py_]]
                out.append(f"{part}, {compute_variants(ep, abbrev_op[px_], cy)[0]:02d} ({px_}/{OP_ABBREV[cy]})")
                # user's screenshot 2 (2026-10-08): where the y step is -2 (so the
                # cell holds -2 and c-2) c+2 is added too; the same for -1 -> c+1
                if py_ in ('-1', '-2'):
                    ey = KK_CUT_TOGGLE[SIGN_FLIP[abbrev_op[py_]]]
                    extra.append(f"{compute_variants(ep, abbrev_op[px_], ey)[0]:02d} ({px_}/{OP_ABBREV[ey]})")
            lines_ = out + ([', '.join(extra)] if extra else [])
            return [l + ',' for l in lines_[:-1]] + lines_[-1:]

        # x side (user's screenshot, 2026-10-08 evening): the same family on the
        # x operation of the cell's first number, its y kept — x cut, x step
        # switched, that cut, and for a minus step the opposite cut steps
        def p_xfam(cell):
            px_, _, py_ = cell[4:-1].partition('/') if cell else ('', '', '')
            if px_ not in p_swap or py_ not in abbrev_op:
                return []
            xo, xs = abbrev_op[px_], abbrev_op[p_swap[px_]]
            fam = [KK_CUT_TOGGLE[xo], xs, KK_CUT_TOGGLE[xs]]
            if px_ in ('-1', '-2'):
                fam += [KK_CUT_TOGGLE[SIGN_FLIP[xo]], KK_CUT_TOGGLE[SIGN_FLIP[xs]]]
            ent = [f"{compute_variants(ep, fx, abbrev_op[py_])[0]:02d} ({OP_ABBREV[fx]}/{py_})" for fx in fam]
            return [', '.join(ent[k:k + 2]) for k in range(0, len(ent), 2)]

        def p_join(ylines, xlines):
            if not xlines:
                return ylines
            return ylines[:-1] + [ylines[-1] + ','] + [l + ',' for l in xlines[:-1]] + xlines[-1:]

        # declared-number cell only (user's screenshot, 2026-10-08 evening):
        # from its x/y, y gets the cut and the opposite sign, x loses its cut
        # (c-1/-2 -> -1/c+2), and the same with the x step switched (-2/c+2)
        def p_decl_extra(cell):
            px_, _, py_ = cell[4:-1].partition('/')
            if px_ not in abbrev_op or py_ not in abbrev_op:
                return []
            ny_ = _op_join(True, _op_parts(SIGN_FLIP[abbrev_op[py_]])[1])
            nx_ = _op_join(False, _op_parts(abbrev_op[px_])[1])
            xs_ = [nx_] + ([abbrev_op[p_swap[OP_ABBREV[nx_]]]] if OP_ABBREV[nx_] in p_swap else [])
            # updated the same evening: the two operations are then swapped —
            # the new y goes to x and the new x goes to y (-1/c+2 -> c+2/-1)
            # second rule (user's screenshot, same evening): x loses its cut and
            # changes sign, y stays as it is (c+1/+2 -> -1/+2)
            fx_ = SIGN_FLIP[nx_]
            out_ = [', '.join(f"{compute_variants(ep, ny_, x_)[0]:02d} ({OP_ABBREV[ny_]}/{OP_ABBREV[x_]})"
                              for x_ in xs_),
                    f"{compute_variants(ep, fx_, abbrev_op[py_])[0]:02d} ({OP_ABBREV[fx_]}/{py_})"]
            # along with those two, the same with the sign of the second
            # operation changed (c-2/-1, c-2/-2 -> c-2/+1, c-2/+2), user's
            # screenshot 2026-10-09
            fl_ = [x_ for x_ in xs_ if SIGN_FLIP[x_] != x_]
            if fl_:
                out_.insert(1, ', '.join(
                    f"{compute_variants(ep, ny_, SIGN_FLIP[x_])[0]:02d} ({OP_ABBREV[ny_]}/{OP_ABBREV[SIGN_FLIP[x_]]})"
                    for x_ in fl_))
                # ... and those crossed with the cut put on the new x only
                # (c+1/-1 -> -1/c+1 -> c-1/c+1), user's screenshot 2026-10-09
                out_.insert(2, ', '.join(
                    f"{compute_variants(ep, cf_, ny_)[0]:02d} ({OP_ABBREV[cf_]}/{OP_ABBREV[ny_]})"
                    for cf_ in (_op_join(True, _op_parts(SIGN_FLIP[x_])[1]) for x_ in fl_)))
                # ... and the last of the sign-changed pair with the cut put on
                # its y only (cut/+2 -> cut/c+2: 26 -> 21 on EP 74), user's
                # screenshot 2026-10-09
                if len(fl_) == 2:
                    gy_ = _op_join(True, _op_parts(SIGN_FLIP[fl_[-1]])[1])
                    out_.insert(3, f"{compute_variants(ep, ny_, gy_)[0]:02d} ({OP_ABBREV[ny_]}/{OP_ABBREV[gy_]})")
            # format c+2/nc (user's screenshot, 2026-10-09): x a cut step and y
            # nc — the two numbers of the first rule again with both cut
            # (cut/+2 -> nc/c+2: 00 -> 55, 09 -> 54 on EP 58)
            if px_ in ('c+1', 'c-1', 'c+2', 'c-2') and py_ == 'nc':
                bx_ = KK_CUT_TOGGLE[ny_]
                out_.append(', '.join(
                    f"{compute_variants(ep, bx_, KK_CUT_TOGGLE[x_])[0]:02d} ({OP_ABBREV[bx_]}/{OP_ABBREV[KK_CUT_TOGGLE[x_]]})"
                    for x_ in xs_))
            # third rule (user's screenshot, same evening): x a plain step and y
            # a cut step (+1/c+1).  Crossed, the cut step keeps only its cut and
            # the plain step gets the cut, the other sign and the other number:
            # +1/c+1 -> cut/c-2  (95 on EP 89 gives 32)
            if px_ in p_swap and py_ in ('c+1', 'c-1', 'c+2', 'c-2'):
                ty_ = KK_CUT_TOGGLE[SIGN_FLIP[abbrev_op[p_swap[px_]]]]
                out_.append(f"{compute_variants(ep, 'cut', ty_)[0]:02d} (cut/{OP_ABBREV[ty_]})")
            return out_

        p_rows = []
        p_groups = []
        p_user = set()
        for cells_, labs_ in ((p_cells, [t for _, t in p_four]), (p_rev, ['operations reversed'] * 4),
                              ([c for c, _ in p_third], [t for _, t in p_third]),
                              ([c for c, _ in p_fourth], [t for _, t in p_fourth])):
            cols_ = [p_join(p_cut(p_pair(c)), p_xfam(c)) for c in cells_]
            if cells_ is p_cells:
                p_base_n = len(cols_[0])
                cols_[0] = p_join(cols_[0], p_decl_extra(cells_[0]))
                # RRR last row (user's screenshot, 2026-10-09): its new x
                # operation with the cut added, in the xy and in the yx
                # number (+1/-2 -> c+1/-2 and -2/+1 -> -2/c+1)
                if len(both_cut) >= 2:
                    lx_, _, ly_ = both_cut[-2][2].partition('/')
                    if lx_ in abbrev_op and ly_ in abbrev_op:
                        cx_ = _op_join(True, _op_parts(abbrev_op[lx_])[1])
                        cxa_ = OP_ABBREV[cx_]
                        cols_[0] = p_join(cols_[0], [
                            f"{compute_variants(ep, cx_, abbrev_op[ly_])[0]:02d} ({cxa_}/{ly_}), "
                            f"{compute_variants(ep, abbrev_op[ly_], cx_)[0]:02d} ({ly_}/{cxa_})"])
                        # that yx number with its tens digit cut and the digits
                        # reversed (30 -> 80 -> 08 on EP 45), user's screenshot
                        # 2026-10-09; shown with its own operations on the EP
                        yv_ = compute_variants(ep, abbrev_op[ly_], cx_)[0]
                        yr_ = (yv_ % 10) * 10 + cut(yv_ // 10)
                        yl_ = f"{yr_:02d} ({OP_ABBREV[find_op(ep // 10, yr_ // 10)]}/{OP_ABBREV[find_op(ep % 10, yr_ % 10)]})"
                        # ... and the same with nc on y (cut/-1 -> cut/nc: 36 ->
                        # 37 on EP 87), user's screenshot 2026-10-09
                        if yr_ % 10 != ep % 10:
                            yn_ = (yr_ // 10) * 10 + ep % 10
                            yl_ += f", {yn_:02d} ({OP_ABBREV[find_op(ep // 10, yn_ // 10)]}/nc)"
                        cols_[0] = p_join(cols_[0], [yl_])
                        # where that operation is a bare cut (cut/-1 and -1/cut),
                        # also nc in its place (nc/-1 and -1/nc: 38 and 29 on
                        # EP 39), user's screenshot 2026-10-09
                        if cx_ == 'cut':
                            cols_[0] = p_join(cols_[0], [
                                f"{compute_variants(ep, 'no_change', abbrev_op[ly_])[0]:02d} (nc/{ly_}), "
                                f"{compute_variants(ep, abbrev_op[ly_], 'no_change')[0]:02d} ({ly_}/nc)"])
                        # case c-1/nc (user's screenshot, 2026-10-09): x a cut
                        # step and y nc — x without the cut, and y the cut step
                        # of the other sign in place of nc (c-1/nc -> -1/c+1)
                        if ly_ == 'nc' and cxa_ in ('c+1', 'c-1', 'c+2', 'c-2'):
                            ux_ = _op_join(False, _op_parts(cx_)[1])
                            uy_ = KK_CUT_TOGGLE[SIGN_FLIP[ux_]]
                            cols_[0] = p_join(cols_[0], [
                                f"{compute_variants(ep, ux_, uy_)[0]:02d} ({OP_ABBREV[ux_]}/{OP_ABBREV[uy_]})"])
                        # that yx number with a cut step on x (c+2/c-2), user's
                        # screenshot 2026-10-09: x loses the cut, changes sign
                        # and takes the other number (c+2 -> -1), and the same
                        # for its neighbour step (c+1 -> -2)
                        if ly_ in ('c+1', 'c-1', 'c+2', 'c-2'):
                            sg_ = '-' if ly_[1] == '+' else '+'
                            cols_[0] = p_join(cols_[0], [', '.join(
                                f"{compute_variants(ep, sg_ + n_, cx_)[0]:02d} ({sg_ + n_}/{cxa_})"
                                for n_ in (p_swap[ly_[1:]][1], ly_[2]))])
                            # ... and the first of them with only the cut on y
                            # (-2/c-1 -> -2/cut), user's screenshot 2026-10-09
                            if cxa_ in ('c+1', 'c-1', 'c+2', 'c-2'):
                                fx_ = sg_ + p_swap[ly_[1:]][1]
                                cols_[0] = p_join(cols_[0], [
                                    f"{compute_variants(ep, fx_, 'cut')[0]:02d} ({fx_}/cut)"])
                        # along with that xy number, the same with the sign of
                        # its y changed (cut/c-2 -> cut/c+2), user's screenshot
                        fy_ = SIGN_FLIP[abbrev_op[ly_]]
                        if fy_ != abbrev_op[ly_]:
                            # ... and with only the cut left on y (cut/cut: 56 on EP 01)
                            cols_[0] = p_join(cols_[0], [
                                f"{compute_variants(ep, cx_, fy_)[0]:02d} ({cxa_}/{OP_ABBREV[fy_]}), "
                                f"{compute_variants(ep, cx_, 'cut')[0]:02d} ({cxa_}/cut)"])
                    # RRR last row +1/+1 or +2/+2 (user's screenshot, 2026-10-09):
                    # x becomes nc and y takes the other step (+1 -> +2, +2 -> +1)
                    if lx_ == ly_ and lx_ in ('+1', '+2'):
                        cols_[0] = p_join(cols_[0], [
                            f"{compute_variants(ep, 'no_change', abbrev_op[p_swap[ly_]])[0]:02d} (nc/{p_swap[ly_]})"])
            if cells_ is p_cells:
                # numbers made by the declared-cell rules: marked ☆ wherever
                # they stand in the table (user, 2026-10-09); ★ and * stay
                p_user = {int(e) for l in cols_[0][p_base_n:] for e in re.findall(r'(\d\d) \(', l)}
            p_groups.append((cols_, labs_))
        # reverse numbers in the declared cell (user's screenshot, 2026-10-09):
        # a declared-cell number whose digits reversed stand in another cell
        # of the table (40 and 04) brings that number into the declared cell
        # declared number nc/cut (user's screenshot, 2026-10-09; 52 on EP 57):
        # its tens digit cut (02), both digits cut (07), and the digits
        # reversed of the declared number and of those two (25, 20, 70)
        if p_groups and p_cells and p_cells[0][3:] == '(nc/cut)':
            dv_ = int(p_cells[0][:2])
            n1_ = cut(dv_ // 10) * 10 + dv_ % 10
            n2_ = cut(dv_ // 10) * 10 + cut(dv_ % 10)
            rv2_ = lambda v: (v % 10) * 10 + v // 10
            n_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
            n_new = []
            for v in (n1_, n2_, rv2_(n1_), rv2_(dv_), rv2_(n2_)):
                if f"{v:02d}" not in n_have:
                    n_have.add(f"{v:02d}")
                    n_new.append(f"{v:02d} ({OP_ABBREV[find_op(ep // 10, v // 10)]}/{OP_ABBREV[find_op(ep % 10, v % 10)]})")
            if n_new:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(n_new[k:k + 2]) for k in range(0, len(n_new), 2)])
                p_user |= {int(e[:2]) for e in n_new}
        # cut/cut in the declared cell (user's screenshot, 2026-10-09): the
        # number of cut/nc with its digits reversed (EP 56: cut/nc = 06 -> 60)
        if p_groups and any('(cut/cut)' in l for l in p_groups[0][0][0]):
            cn_ = compute_variants(ep, 'cut', 'no_change')[0]
            rn_ = (cn_ % 10) * 10 + cn_ // 10
            if not any(l.startswith(f"{rn_:02d} (") or f", {rn_:02d} (" in l for l in p_groups[0][0][0]):
                p_groups[0][0][0] = p_join(p_groups[0][0][0], [
                    f"{rn_:02d} ({OP_ABBREV[find_op(ep // 10, rn_ // 10)]}/{OP_ABBREV[find_op(ep % 10, rn_ % 10)]})"])
                p_user.add(rn_)
        if p_groups:
            p_ent = re.compile(r'\d\d \([^)]*\)')
            d_have = [e[:2] for l in p_groups[0][0][0] for e in p_ent.findall(l)]
            o_ent = {}
            for gi_, (cols_, _) in enumerate(p_groups):
                for ci_, col_ in enumerate(cols_):
                    if gi_ or ci_:
                        for l in col_:
                            for e in p_ent.findall(l):
                                o_ent.setdefault(e[:2], e)
            d_rev = []
            for n_ in d_have:
                r_ = n_[::-1]
                if r_ in o_ent and r_ not in d_have and o_ent[r_] not in d_rev:
                    d_rev.append(o_ent[r_])
            if d_rev:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(d_rev[k:k + 2]) for k in range(0, len(d_rev), 2)])
                p_user |= {int(e[:2]) for e in d_rev}
        # declared number like c+1/+1 (user's screenshot, 2026-10-09): the
        # declared-cell numbers whose x is the cut step of the other sign and
        # other number (c+1 -> c-2: 74, 76, 73 on EP 40) also without that
        # cut on x, y kept (24, 26, 23)
        if p_groups and p_cells and p_cells[0]:
            dx_ = p_cells[0][4:-1].partition('/')[0]
            dstep_ = _op_parts(abbrev_op[dx_])[1] if dx_ in abbrev_op else ''
            if dstep_ in p_swap:
                tp_ = SIGN_FLIP[abbrev_op[p_swap[dstep_]]]          # plain: +1 -> -2
                ta_ = OP_ABBREV[KK_CUT_TOGGLE[tp_]]                  # with cut: c-2
                t_new, t_have = [], {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
                for l in p_groups[0][0][0]:
                    for ex_, ey_ in re.findall(r'\d\d \(([^/)]*)/([^)]*)\)', l):
                        if ex_ == ta_ and ey_ in abbrev_op:
                            tv_ = f"{compute_variants(ep, tp_, abbrev_op[ey_])[0]:02d}"
                            if tv_ not in t_have:
                                t_have.add(tv_)
                                t_new.append(f"{tv_} ({OP_ABBREV[tp_]}/{ey_})")
                # ... and each of those with its digits reversed (14 -> 41 on
                # EP 90), user's screenshot 2026-10-09
                for e in list(t_new):
                    rr_ = e[1] + e[0]
                    if rr_ not in t_have:
                        t_have.add(rr_)
                        rv_ = int(rr_)
                        t_new.append(f"{rr_} ({OP_ABBREV[find_op(ep // 10, rv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, rv_ % 10)]})")
                if t_new:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                               [', '.join(t_new[k:k + 2]) for k in range(0, len(t_new), 2)])
                    p_user |= {int(e[:2]) for e in t_new}
        # nearest x of the declared x (c+2 -> c+1) already standing in the
        # declared cell (81 (c+1/c+2) on EP 24): that x also with the declared
        # y (96 (c+2/+2) -> 86 (c+1/+2)), user's screenshot 2026-10-11
        if p_groups and p_cells and p_cells[0]:
            dx_, _, dy_ = p_cells[0][4:-1].partition('/')
            if dx_ in abbrev_op and dy_ in abbrev_op:
                nc_, ns_ = _op_parts(abbrev_op[dx_])
                if ns_ in p_swap:
                    nx_ = _op_join(nc_, p_swap[ns_])
                    na_ = OP_ABBREV[nx_]
                    n_ents = [e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(([^/)]*)/', l)]
                    nv_ = compute_variants(ep, nx_, abbrev_op[dy_])[0]
                    if any(x == na_ for _, x in n_ents) and f"{nv_:02d}" not in {v for v, _ in n_ents}:
                        p_groups[0][0][0] = p_join(p_groups[0][0][0], [f"{nv_:02d} ({na_}/{dy_})"])
                        p_user.add(nv_)
        # declared cell: every number whose y is the bare cut also with nc on
        # y, x kept (65 (+1/cut) -> 60 (+1/nc) on EP 50), user's screenshot
        # 2026-10-11
        if p_groups:
            c_ents = [e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(([^/)]*)/([^)]*)\)', l)]
            c_have, c_new = {v for v, _, _ in c_ents}, []
            for _, cx_, cy_ in c_ents:
                if cy_ == 'cut' and cx_ in abbrev_op:
                    cv_ = f"{compute_variants(ep, abbrev_op[cx_], 'no_change')[0]:02d}"
                    if cv_ not in c_have:
                        c_have.add(cv_)
                        c_new.append(f"{cv_} ({cx_}/nc)")
            if c_new:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(c_new[k:k + 2]) for k in range(0, len(c_new), 2)])
                p_user |= {int(e[:2]) for e in c_new}
        # declared cell: the ★ rows of the RRR table (number inside the
        # tens-cut decade) modified — x without its cut and sign flipped, y
        # without its cut and with that same sign (12★ (+2/c-2), 16★ (+2/c+2)
        # on EP 99 -> 77 (-2/-2)), user's screenshot 2026-10-11
        if p_groups and grid_ep is not None:
            s_dec = cut(grid_ep // 10)
            s_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
            s_new = []
            for sv_, _, slab_ in both_cut:
                sx_, _, sy_ = slab_.partition('/')
                if sv_ // 10 != s_dec or sx_ not in abbrev_op or sy_ not in abbrev_op:
                    continue
                xn_, yn_ = _op_parts(abbrev_op[sx_])[1], _op_parts(abbrev_op[sy_])[1]
                if not xn_ or not yn_:
                    continue
                nx_ = SIGN_FLIP[xn_]
                ny_ = nx_[0] + yn_[1:]
                nv_ = f"{compute_variants(ep, nx_, ny_)[0]:02d}"
                if nv_ not in s_have:
                    s_have.add(nv_)
                    s_new.append(f"{nv_} ({OP_ABBREV[nx_]}/{OP_ABBREV[ny_]})")
            if s_new:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(s_new[k:k + 2]) for k in range(0, len(s_new), 2)])
                p_user |= {int(e[:2]) for e in s_new}
        # declared cell: declared y a +1 / +2 step (plain or cut) — the cut
        # steps of the other sign too, x kept (21 (-1/+1) on EP 30 -> 24
        # (-1/c-1), 23 (-1/c-2)); the mirror of the -1/-2 -> c+1/c+2 rule.
        # Result 23 after 77, user 2026-10-11
        if p_groups and p_cells and p_cells[0]:
            dx_, _, dy_ = p_cells[0][4:-1].partition('/')
            if dx_ in abbrev_op and dy_ in abbrev_op and _op_parts(abbrev_op[dy_])[1] in ('+1', '+2'):
                m_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
                m_new = []
                for my_ in ('cut-1', 'cut-2'):
                    mv_ = f"{compute_variants(ep, abbrev_op[dx_], my_)[0]:02d}"
                    if mv_ not in m_have:
                        m_have.add(mv_)
                        m_new.append(f"{mv_} ({dx_}/{OP_ABBREV[my_]})")
                if m_new:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [', '.join(m_new)])
                    p_user |= {int(e[:2]) for e in m_new}
        # declared cell: the first rule's two numbers (y cut + sign changed
        # put on x, x without its cut put on y, and that step switched) also
        # with the cut step on x switched (60 (c+2/-1), 69 (c+2/-2) on EP 91
        # -> 50 (c+1/-1), 59 (c+1/-2)).  Result 50 after 30, user 2026-10-11
        if p_groups and p_cells and p_cells[0]:
            dx_, _, dy_ = p_cells[0][4:-1].partition('/')
            if dx_ in abbrev_op and dy_ in abbrev_op:
                yn_ = _op_parts(SIGN_FLIP[abbrev_op[dy_]])[1]
                if yn_ in p_swap:
                    ny_ = 'cut' + p_swap[yn_]
                    nx_ = _op_join(False, _op_parts(abbrev_op[dx_])[1])
                    w_xs = [nx_] + ([abbrev_op[p_swap[OP_ABBREV[nx_]]]] if OP_ABBREV[nx_] in p_swap else [])
                    w_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
                    w_new = []
                    for x_ in w_xs:
                        wv_ = f"{compute_variants(ep, ny_, x_)[0]:02d}"
                        if wv_ not in w_have:
                            w_have.add(wv_)
                            w_new.append(f"{wv_} ({OP_ABBREV[ny_]}/{OP_ABBREV[x_]})")
                    if w_new:
                        p_groups[0][0][0] = p_join(p_groups[0][0][0], [', '.join(w_new)])
                        p_user |= {int(e[:2]) for e in w_new}
        # declared cell: a number whose x is the declared x step without its
        # cut, other sign and other number (c+2 -> -1) and whose y is a cut
        # step — also with only the cut on y (25 (-1/c-2) on EP 32 -> 27
        # (-1/cut)); the user's "only the cut on y" rule.  Result 27 after 50
        if p_groups and p_cells and p_cells[0]:
            dx_ = p_cells[0][4:-1].partition('/')[0]
            dn_ = _op_parts(abbrev_op[dx_])[1] if dx_ in abbrev_op else ''
            if dn_ in p_swap:
                tp_ = SIGN_FLIP[abbrev_op[p_swap[dn_]]]
                o_ents = [e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(([^/)]*)/([^)]*)\)', l)]
                ov_ = f"{compute_variants(ep, tp_, 'cut')[0]:02d}"
                if ov_ not in {v for v, _, _ in o_ents} and any(
                        x == OP_ABBREV[tp_] and y in ('c+1', 'c-1', 'c+2', 'c-2') for _, x, y in o_ents):
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [f"{ov_} ({OP_ABBREV[tp_]}/cut)"])
                    p_user.add(int(ov_))
        # declared cell: the last round's operation again, on the running
        # value instead of the EP (-1/cut on 27 -> 12, shown with its
        # operation on the EP: +1/+1 on 01).  Result 12 after 27, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0 and _RRR3_PREV.get('op'):
            gv_ = compute_variants(grid_ep, *_RRR3_PREV['op'])[0]
            if f"{gv_:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                p_groups[0][0][0] = p_join(p_groups[0][0][0], [
                    f"{gv_:02d} ({OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]})"])
                p_user.add(gv_)
        # declared cell: the declared number's operations crossed — y without
        # its cut and its step switched put on x, x without its cut put on y
        # (66 (nc/c-1) on EP 62 -> 42 (-2/nc)).  Result 42 after 12, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0:
            cv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4) % 10
            cx_, cy_ = find_op(ep // 10, cv_ // 10), find_op(ep % 10, cv_ % 10)
            cn_ = _op_parts(cy_)[1]
            if cn_ in p_swap:
                nx_, ny_ = abbrev_op[p_swap[cn_]], _op_join(False, _op_parts(cx_)[1])
                nv_ = compute_variants(ep, nx_, ny_)[0]
                if f"{nv_:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [f"{nv_:02d} ({OP_ABBREV[nx_]}/{OP_ABBREV[ny_]})"])
                    p_user.add(nv_)
        # declared cell: the last round's operation again on the running
        # value, with its x step switched and the cut kept (+2/nc on 06 = 26
        # -> +1/nc on 06 = 16, shown with its operation on the EP: c+1/+2 on
        # 54).  Result 16 after 06, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0 and _RRR3_PREV.get('op'):
            hx_, hy_ = _RRR3_PREV['op']
            if _op_parts(hx_)[1] in p_swap:
                gv_ = compute_variants(grid_ep, _op_join(_op_parts(hx_)[0], p_swap[_op_parts(hx_)[1]]), hy_)[0]
                if f"{gv_:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [
                        f"{gv_:02d} ({OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]})"])
                    p_user.add(gv_)
        # declared cell: the last round's operation again on the EP with nc
        # on y (84 (c+1/+2) on EP 22 -> 82 (c+1/nc)).  Result 82 after 16,
        # 2026-10-11
        if p_groups and _RRR3_PREV.get('op') and _RRR3_PREV['op'][1] != 'no_change':
            hx_ = _RRR3_PREV['op'][0]
            hv_ = compute_variants(ep, hx_, 'no_change')[0]
            if f"{hv_:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                p_groups[0][0][0] = p_join(p_groups[0][0][0], [f"{hv_:02d} ({OP_ABBREV[hx_]}/nc)"])
                p_user.add(hv_)
        # declared cell: two earlier rules together — the declared x without
        # its cut and sign flipped (30 (+1/-2) -> 10 (-1/-2)) with the cut
        # steps of the other sign on a +1/+2 declared y (-> c-1, c-2):
        # 36 (c-2/+2) on EP 04 -> 28 (+2/c-1), 27 (+2/c-2).  Result 28 after
        # 82, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0:
            cv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4) % 10
            cx_, cy_ = find_op(ep // 10, cv_ // 10), find_op(ep % 10, cv_ % 10)
            if _op_parts(cx_)[1] and cy_ in ('+1', '+2'):
                fx_ = SIGN_FLIP[_op_parts(cx_)[1]]
                f_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
                f_new = []
                for fy_ in ('cut-1', 'cut-2'):
                    fv_ = f"{compute_variants(ep, fx_, fy_)[0]:02d}"
                    if fv_ not in f_have:
                        f_have.add(fv_)
                        f_new.append(f"{fv_} ({OP_ABBREV[fx_]}/{OP_ABBREV[fy_]})")
                if f_new:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [', '.join(f_new)])
                    p_user |= {int(e[:2]) for e in f_new}
        # declared cell: the crossed declared operations (y without its cut
        # and step switched on x, x without its cut on y — the rule of result
        # 42) applied on the running value instead of the EP (72 (nc/-1) ->
        # -2/nc; on 28 = 08, shown with its operation on the EP: c-2/cut on
        # 73).  Result 08 after 28, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0:
            cv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4) % 10
            cx_, cy_ = find_op(ep // 10, cv_ // 10), find_op(ep % 10, cv_ % 10)
            if _op_parts(cy_)[1] in p_swap:
                gv_ = compute_variants(grid_ep, abbrev_op[p_swap[_op_parts(cy_)[1]]], _op_join(False, _op_parts(cx_)[1]))[0]
                if f"{gv_:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                    p_groups[0][0][0] = p_join(p_groups[0][0][0], [
                        f"{gv_:02d} ({OP_ABBREV[find_op(ep // 10, gv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, gv_ % 10)]})"])
                    p_user.add(gv_)
        # declared cell: the family numbers (user, 2026-10-11) — a STRONG 16
        # number and a 3RRR RESULT number of the same family (53 and 85)
        # bring the STRONG 16 number with both digits cut (53 -> 08)
        if p_groups and fam_seats:
            g_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
            g_new = [f"{v:02d} ({lab})" for v, lab in fam_seats if f"{v:02d}" not in g_have]
            if g_new:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(g_new[k:k + 2]) for k in range(0, len(g_new), 2)])
                p_user |= {int(e[:2]) for e in g_new}
        # declared cell: the whole NUMBER BAND (declared number ± 1, ± 2
        # inside the tens-cut decade) — the cell had 50, 52, 54 and the
        # result was 51.  Result 51 after 08, 2026-10-11
        if p_groups and grid_ep is not None and grid_ep >= 0:
            b_have = {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}
            b_new = []
            for k_ in (-2, -1, 0, 1, 2):
                bv_ = cut(grid_ep // 10) * 10 + (grid_ep % 10 + 4 + k_) % 10
                if f"{bv_:02d}" not in b_have:
                    b_new.append(f"{bv_:02d} ({OP_ABBREV[find_op(ep // 10, bv_ // 10)]}/{OP_ABBREV[find_op(ep % 10, bv_ % 10)]})")
            if b_new:
                p_groups[0][0][0] = p_join(p_groups[0][0][0],
                                           [', '.join(b_new[k:k + 2]) for k in range(0, len(b_new), 2)])
                p_user |= {int(e[:2]) for e in b_new}
        # declared cell: the SAME OPERATION AGAIN number (the last round's
        # operation on this EP) — it had a STRONG 16 seat but was not in the
        # cell.  Result 26 after 99 (cut/c-2 again), 2026-10-11
        if p_groups and same:
            if f"{same[0]:02d}" not in {e for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)}:
                p_groups[0][0][0] = p_join(p_groups[0][0][0], [
                    f"{same[0]:02d} ({OP_ABBREV[find_op(ep // 10, same[0] // 10)]}/{OP_ABBREV[find_op(ep % 10, same[0] % 10)]})"])
                p_user.add(same[0])
        for cols_, labs_ in p_groups:
            h_ = max(len(c) for c in cols_)
            p_rows.append([[c[k] if k < len(c) else '' for c in cols_] for k in range(h_)] + [labs_])
        # stars (user, 2026-10-08): ★ = the number is also in the STRONG 16,
        # * = it is also in the RECOMMENDED list
        p_recv = {r_[0] for r_ in rec}

        def p_star(m):
            v = int(m.group(1))
            return m.group(0) + ('★' if v in strong else '*' if v in p_recv else '') + ('☆' if v in p_user else '')

        p_rows = [[[re.sub(r'(\d\d) \([^)]*\)', p_star, c) for c in line] for line in grp] for grp in p_rows]
        p_cw = max([len(c) for grp in p_rows for line in grp for c in line] + [21]) + 2
        p_tw = 4 * p_cw + 3
        p_rib = "\033[1;30;43m"
        p_title = f"★  POWER BASE  —  4 numbers, operations applied on EP={ep:02d}  ★"
        power_lines = [f"  {s_g}┌{'─' * p_tw}┐{s_rst}",
                       f"  {s_g}│{s_rst}{p_rib}{p_title:^{p_tw}}{s_rst}{s_g}│{s_rst}",
                       f"  {s_g}├{'┬'.join('─' * p_cw for _ in range(4))}┤{s_rst}"]
        for k, grp in enumerate(p_rows):
            if k:
                power_lines.append(f"  {s_g}├{'┼'.join('─' * p_cw for _ in range(4))}┤{s_rst}")
            power_lines += [f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c:<{p_cw - 1}}" for c in line) + f"{s_g}│{s_rst}"
                            for line in grp]
        power_lines.append(f"  {s_g}└{'┴'.join('─' * p_cw for _ in range(4))}┘{s_rst}")
        # beside the table (user's screenshot, 2026-10-08 evening): every POWER
        # BASE number once, no repeats, ascending, with its ★ / * mark
        p_seen = {}
        p_added = []
        for grp in p_rows:
            for line in grp:
                for c in line:
                    for m in re.finditer(r'(\d\d) \([^)]*\)([★*]?)', c):
                        p_seen.setdefault(int(m.group(1)), m.group(2))
        # reversed numbers (user's screenshot, 2026-10-08 evening): 16 is in the
        # box and the 6 series is there too (60, 68), so its reverse 61 is added.
        # One pass over the table's own numbers; the added ones carry a +
        p_tens = {v // 10 for v in p_seen}
        for v in sorted(p_seen):
            rv_ = (v % 10) * 10 + v // 10
            if rv_ not in p_seen and rv_ // 10 in p_tens:
                p_seen[rv_] = '★' if rv_ in strong else '*' if rv_ in p_recv else '+'
                p_added.append(rv_)
        p_uniq = [f"{v:02d}{p_seen[v] or ' '}" for v in sorted(p_seen)]
        _RRR3_PREV['power_box'] = (ep, list(p_uniq))
        u_per = 6
        u_tw = u_per * 5 + 1
        u_title = f"★ ALL {len(p_uniq)} NUMBERS, NO REPEATS ★"
        u_box = [f"{s_g}┌{'─' * u_tw}┐{s_rst}",
                 f"{s_g}│{s_rst}{p_rib}{u_title:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                 f"{s_g}├{'─' * u_tw}┤{s_rst}"]
        for k in range(0, len(p_uniq), u_per):
            u_row = ''.join(f"  {c}" for c in p_uniq[k:k + u_per])
            u_box.append(f"{s_g}│{s_rst}{u_row:<{u_tw}}{s_g}│{s_rst}")
        u_box.append(f"{s_g}└{'─' * u_tw}┘{s_rst}")
        # under it (user's screenshot, 2026-10-09): only the star-marked numbers
        # (★ STRONG 16, * RECOMMENDED, ☆ declared-cell rules) as one table
        p_marked = [f"{v:02d}{(p_seen[v] if p_seen[v] in ('★', '*') else '') + ('☆' if v in p_user else '')}"
                    for v in sorted(p_seen) if p_seen[v] in ('★', '*') or v in p_user]
        m_title = f"★ {len(p_marked)} STAR-MARKED NUMBERS ★"
        u_box += [' ' * (u_tw + 2),
                  f"{s_g}┌{'─' * u_tw}┐{s_rst}",
                  f"{s_g}│{s_rst}{p_rib}{m_title:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"{s_g}├{'─' * u_tw}┤{s_rst}"]
        for k in range(0, len(p_marked), 5):
            m_row = ''.join(f"  {c:<4}" for c in p_marked[k:k + 5])
            u_box.append(f"{s_g}│{s_rst}{m_row:<{u_tw}}{s_g}│{s_rst}")
        u_box.append(f"{s_g}└{'─' * u_tw}┘{s_rst}")
        # under that (user's screenshot, 2026-10-09): the declared cell and the
        # star-marked numbers merged into one table, each number once
        p_declv = {int(e) for l in p_groups[0][0][0] for e in re.findall(r'(\d\d) \(', l)} if p_groups else set()
        p_mark_of = lambda v: (('★' if v in strong else '*' if v in p_recv else '')
                               + ('☆' if v in p_user else ''))
        p_merged = [f"{v:02d}{p_mark_of(v)}" for v in sorted(
            p_declv | {v for v in p_seen if p_seen[v] in ('★', '*') or v in p_user})]
        g_title = f"★ DECLARED + STAR-MARKED: {len(p_merged)} ★"
        u_box += [' ' * (u_tw + 2),
                  f"{s_g}┌{'─' * u_tw}┐{s_rst}",
                  f"{s_g}│{s_rst}{p_rib}{g_title:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"{s_g}├{'─' * u_tw}┤{s_rst}"]
        for k in range(0, len(p_merged), 5):
            m_row = ''.join(f"  {c:<4}" for c in p_merged[k:k + 5])
            u_box.append(f"{s_g}│{s_rst}{m_row:<{u_tw}}{s_g}│{s_rst}")
        u_box.append(f"{s_g}└{'─' * u_tw}┘{s_rst}")
        # under that (user's screenshot, 2026-10-09): only the declared cell's
        # own numbers, each once, ascending, with the count
        p_donly = [f"{v:02d}{p_mark_of(v)}" for v in sorted(p_declv)]
        d_title = f"★ DECLARED CELL ONLY: {len(p_donly)} ★"
        u_box += [' ' * (u_tw + 2),
                  f"{s_g}┌{'─' * u_tw}┐{s_rst}",
                  f"{s_g}│{s_rst}{p_rib}{d_title:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"{s_g}├{'─' * u_tw}┤{s_rst}"]
        for k in range(0, len(p_donly), 5):
            m_row = ''.join(f"  {c:<4}" for c in p_donly[k:k + 5])
            u_box.append(f"{s_g}│{s_rst}{m_row:<{u_tw}}{s_g}│{s_rst}")
        u_box.append(f"{s_g}└{'─' * u_tw}┘{s_rst}")
        # under that (user's screenshot, 2026-10-11): the numbers 00-99 that
        # do NOT stand in the declared cell, each once, ascending
        p_dnon = [f"{v:02d}{p_mark_of(v)}" for v in range(100) if v not in p_declv]
        n_t1, n_t2 = "★ NON-EXISTING FROM ★", f"DECLARED CELL: {len(p_dnon)}"
        u_box += [' ' * (u_tw + 2),
                  f"{s_g}┌{'─' * u_tw}┐{s_rst}",
                  f"{s_g}│{s_rst}{p_rib}{n_t1:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"{s_g}│{s_rst}{p_rib}{n_t2:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"{s_g}├{'─' * u_tw}┤{s_rst}"]
        for k in range(0, len(p_dnon), 5):
            m_row = ''.join(f"  {c:<4}" for c in p_dnon[k:k + 5])
            u_box.append(f"{s_g}│{s_rst}{m_row:<{u_tw}}{s_g}│{s_rst}")
        u_box.append(f"{s_g}└{'─' * u_tw}┘{s_rst}")
        while len(power_lines) < len(u_box):
            power_lines.append(' ' * (p_tw + 4))
        power_lines = [l + ('  ' + u_box[k] if k < len(u_box) else '') for k, l in enumerate(power_lines)]
        # CharRow (user's name; first DoRow Table), the add-on above the POWER BASE
        # (user's screenshot, 2026-10-12):
        # the four numbers of its first row and the four of its "operations
        # reversed" row, each with the cut toggled on the x operation only —
        # taken off where x has it, put on where it has not.  8 numbers
        def _xcut(v_):
            n_ = ((v_ // 10 + 5) % 10) * 10 + v_ % 10
            return f"{n_:02d} ({OP_ABBREV[find_op(ep // 10, n_ // 10)]}/{OP_ABBREV[find_op(ep % 10, n_ % 10)]})"
        x_rows = [([_xcut(v) for v, _ in p_four], 'x cut toggled'),
                  ([_xcut(int(c[:2])) for c in p_rev], 'reversed, x cut toggled')]
        # two more rows (user, 2026-10-13; the table renamed CharRow): the
        # numbers of the two rows above with only the sign of the x operation
        # changed, - to + and + to - (nc and cut have no sign and stay)
        def _xsign(c_):
            v_ = int(c_[:2])
            d_ = (v_ // 10 - ep // 10) % 10
            k_ = 5 if d_ in (3, 4, 5, 6, 7) else 0
            n_ = ((ep // 10 + k_ - (d_ - k_)) % 10) * 10 + v_ % 10
            return f"{n_:02d} ({OP_ABBREV[find_op(ep // 10, n_ // 10)]}/{OP_ABBREV[find_op(ep % 10, n_ % 10)]})"
        x_rows += [([_xsign(c) for c in x_rows[0][0]], 'x cut toggled, x sign changed'),
                   ([_xsign(c) for c in x_rows[1][0]], 'reversed, x cut, x sign changed')]
        # duplicates (user's screenshot, 2026-10-13): the first cell of a
        # repeated number stays; a later cell takes a number from the table's
        # own family pairs — two CharRow numbers of the same family (36 and
        # 86), the first of them with its digits reversed (36 -> 63).  When
        # the pairs' first numbers run out, their second numbers reversed
        def _x_lab(n_):
            return f"{n_:02d} ({OP_ABBREV[find_op(ep // 10, n_ // 10)]}/{OP_ABBREV[find_op(ep % 10, n_ % 10)]})"
        x_flat = [int(c[:2]) for cells_, _ in x_rows for c in cells_]
        x_uniq = list(dict.fromkeys(x_flat))
        x_pairs = [(a_, b_) for i_, a_ in enumerate(x_uniq) for b_ in x_uniq[i_ + 1:]
                   if a_ % 5 == b_ % 5 and (a_ // 10) % 5 == (b_ // 10) % 5]
        x_queue = [(int(f"{a_:02d}"[::-1]), a_, b_) for a_, b_ in x_pairs] \
            + [(int(f"{b_:02d}"[::-1]), b_, a_) for a_, b_ in x_pairs]
        x_seen, x_new = set(), []
        for k_, v_ in enumerate(x_flat):
            x_note = None
            if v_ in x_seen:
                while x_queue and (x_queue[0][0] in x_seen or x_queue[0][0] in x_flat[k_:]):
                    x_queue.pop(0)
                if x_queue:
                    r_, f_, o_ = x_queue.pop(0)
                    x_note = f"was {v_:02d}; {f_:02d}+{o_:02d}, {f_:02d} reversed"
                    v_ = r_
                else:
                    x_note = "repeat, no family pair left"
            x_seen.add(v_)
            x_new.append((v_, x_note))
        x_rows = [([_x_lab(v_) for v_, _ in x_new[4 * k_:4 * k_ + 4]],
                   [n_ or lab_ for _, n_ in x_new[4 * k_:4 * k_ + 4]])
                  for k_, (_, lab_) in enumerate(x_rows)]
        # last-operation steps (user's screenshot, 2026-10-13): the steps of
        # the RRR table's LAST row (new x and new y: +1/+1 has only 1, so +1
        # and -1; a 2 brings +2 and -2) are put in place of a plain cut on
        # the x operation of a CharRow number (45 (cut/-2) -> 05 (+1/-2) and
        # 85 (-1/-2)).  Only new numbers are added; nothing when there is no
        # plain cut on x or the LAST row has no step
        x_steps = []
        if len(both_cut) >= 2:
            for d_ in '12':
                if d_ in both_cut[-2][2]:
                    x_steps += [int(d_), -int(d_)]
        x_have, x_add = set(v_ for v_, _ in x_new), []
        for v_, _ in x_new:
            if (v_ // 10 - ep // 10) % 10 == 5:
                for st_ in x_steps:
                    n_ = ((ep // 10 + st_) % 10) * 10 + v_ % 10
                    if n_ not in x_have:
                        x_have.add(n_)
                        x_add.append((n_, f"from {v_:02d}: x cut -> {st_:+d}"))
        for k_ in range(0, len(x_add), 4):
            x_grp = x_add[k_:k_ + 4] + [None] * (4 - len(x_add[k_:k_ + 4]))
            x_rows.append(([_x_lab(g_[0]).replace(' (', '+ (', 1) if g_ else '' for g_ in x_grp],
                           [g_[1] if g_ else '' for g_ in x_grp]))
        # y cut again (user's screenshot, 2026-10-13, after 82 came from 87
        # (c+2/cut)): a CharRow number with a plain cut on its y operation
        # takes the cut on y again, which drops it to nc (87 -> 82 (c+2/nc)).
        # Written in the same cell after a comma with a + mark; only new
        # numbers
        x_ycut = {}
        for v_ in [w_ for w_, _ in x_new] + [w_ for w_, _ in x_add]:
            if (v_ % 10 - ep % 10) % 10 == 5 and v_ not in x_ycut:
                n_ = (v_ // 10) * 10 + ep % 10
                if n_ not in x_have:
                    x_have.add(n_)
                    x_ycut[v_] = n_
        # operation turned over (user, 2026-10-13, after 25 came beside 70
        # (cut/nc)): a CharRow number whose operation is cut/nc brings the
        # same operation turned over, nc/cut — the EP with its y cut.  Same
        # cell, after a comma, + mark; only a new number
        for v_ in [w_ for w_, _ in x_new] + [w_ for w_, _ in x_add]:
            if v_ == cut(ep // 10) * 10 + ep % 10 and v_ not in x_ycut:
                n_ = (ep // 10) * 10 + cut(ep % 10)
                if n_ not in x_have:
                    x_have.add(n_)
                    x_ycut[v_] = n_
        y_done = set()
        for cells_, _ in x_rows:
            for k_, c_ in enumerate(cells_):
                if c_ and int(c_[:2]) in x_ycut and int(c_[:2]) not in y_done:
                    y_done.add(int(c_[:2]))
                    cells_[k_] = c_ + ', ' + _x_lab(x_ycut[int(c_[:2])]).replace(' (', '+ (', 1)
        x_title = (f"★  CharRow  —  {len(x_have)} numbers, x only: cut toggled, then sign changed; "
                   f"repeats replaced; last-op steps for x cut; y cut again; cut/nc turned, on EP={ep:02d}  ★")
        # the CharRow numbers once each, beside the STRONG 20 table (user's
        # screenshots, 2026-10-13): no repeats, table order, each with its
        # operation on the EP
        c_nums = []
        for v_ in dict.fromkeys([v_ for v_, _ in x_new] + [v_ for v_, _ in x_add]):
            c_nums.append(v_)
            if v_ in x_ycut:
                c_nums.append(x_ycut[v_])        # right after the number it came from
        # + = added from the last operation's steps or by the y cut again (user, 2026-10-13)
        c_plus = set(v_ for v_, _ in x_add) | set(x_ycut.values())
        c_cells = [_x_lab(v_).replace(' (', '+ (', 1) if v_ in c_plus else _x_lab(v_) for v_ in c_nums]
        c_per = max(3, -(-len(c_cells) // max(s_tbl_n - 4, 1)))
        c_cw = max([len(c) for c in c_cells] + [12]) + 2
        c_head = f"★ CharRow — {len(c_nums)} numbers, no repeats ★"
        c_tw = max(c_per * (c_cw + 1), len(c_head) + 2, 49)
        c_box = [f"{s_g}┌{'─' * c_tw}┐{s_rst}",
                 f"{s_g}│{s_rst}{p_rib}{c_head:^{c_tw}}{s_rst}{s_g}│{s_rst}",
                 f"{s_g}├{'─' * c_tw}┤{s_rst}"]
        for k_ in range(0, len(c_cells), c_per):
            c_row = ''.join(f" {c:<{c_cw}}" for c in c_cells[k_:k_ + c_per])
            c_box.append(f"{s_g}│{s_rst}{c_row:<{c_tw}}{s_g}│{s_rst}")
        if c_plus:
            c_box.append(f"{s_g}│{s_rst}{' + = last-op steps, y cut again, or cut/nc turned':<{c_tw}}{s_g}│{s_rst}")
        c_box.append(f"{s_g}└{'─' * c_tw}┘{s_rst}")
        # the RRR: NEXT OPERATION table beside them too, to the right of the
        # CharRow box (user's screenshot, 2026-10-13)
        n_tw = max(len(l_) for l_ in rrr_tbl) + 2
        n_box = [f"{s_g}┌{'─' * n_tw}┐{s_rst}"]
        n_box += [f"{s_g}│{s_rst}{p_rib}{l_.strip():^{n_tw}}{s_rst}{s_g}│{s_rst}" if k_ == 0
                  else f"{s_g}│{s_rst}{l_:<{n_tw}}{s_g}│{s_rst}" for k_, l_ in enumerate(rrr_tbl)]
        n_box.append(f"{s_g}└{'─' * n_tw}┘{s_rst}")
        c_box = [(c_box[k_] if k_ < len(c_box) else ' ' * (c_tw + 2))
                 + ('  ' + n_box[k_] if k_ < len(n_box) else '')
                 for k_ in range(max(len(c_box), len(n_box)))]
        for k_, l_ in enumerate(c_box):
            if k_ < s_tbl_n:
                strong_lines[k_] += '  ' + l_
            else:
                strong_lines.insert(k_, ' ' * (s_tw + 4) + '  ' + l_)
        # NEXT OPERATION-OCJP below the CharRow box, in the triple
        # Indian-flag border (user's screenshot, 2026-10-14): the LAST row's
        # two operations worked into 30 operations on the EP
        ocjp_final4 = []
        o_list = _rrr_ocjp(ep, both_cut)
        if o_list:
            # a grid like the STRONG 20 box: 5 columns, 6 rows, every place
            # shown, repeats too (user's screenshot, 2026-10-14)
            # every place also with its x step switched, after the comma, + mark
            # (user, 2026-10-15: 26. 60 (-1/c+1) -> 50 (-2/c+1))
            o_sw = [_rrr_ocjp_xswitch(ep, lab_) for _, lab_, _, _ in o_list]
            # and the y step switched, and both switched, after a second
            # comma, * mark (user, 2026-10-15: -2/-2 -> -2/-1; +2/c-2 -> +1/c-1)
            o_mo = [_rrr_ocjp_more(ep, lab_) for _, lab_, _, _ in o_list]
            # and, when x has no step, y with its cut switched, # mark
            # (result 86 after 04: 81 (nc/+1) -> 86 (nc/c+1))
            o_yc = [[m_ + ('#',) for m_ in _rrr_ocjp_ycut(ep, lab_, k_)] for _, lab_, k_, _ in o_list]
            # and, on places 15-20, x with its cut switched, % mark
            # (result 15 after 29: 65 (+2/cut) -> 15 (c+2/cut); 84 after 70)
            o_yc = [yc_ + [m_ + ('%',) for m_ in _rrr_ocjp_xcut(ep, lab_, k_)] for yc_, (_, lab_, k_, _) in zip(o_yc, o_list)]
            # and, on places 1-8, x with its sign flipped, ! mark
            # (result 83 after 82: 43 (-2/+1) -> 83 (+2/+1))
            o_xf = [_rrr_ocjp_xflip(ep, lab_, k_) for _, lab_, k_, _ in o_list]
            o_cells = [f"{k_:>2}. {v_:02d} ({lab_}){'~' if n_ else ''}{'' if k_ > 38 else ' °' if k_ > 30 else ' ^' if k_ > 20 else ''}"
                       + (f", {w_[0]:02d}+ ({w_[1]})" if w_ else '')
                       + ''.join(f", {m_[0]:02d}* ({m_[1]})" for m_ in mo_)
                       + ''.join(f", {m_[0]:02d}{m_[2]} ({m_[1]})" for m_ in yc_)
                       + ''.join(f", {m_[0]:02d}! ({m_[1]})" for m_ in xf_)
                       for (v_, lab_, k_, n_), w_, mo_, yc_, xf_ in zip(o_list, o_sw, o_mo, o_yc, o_xf)]
            o_cw = max(len(c) for c in o_cells) + 2
            o_per = 5 if o_cw < 40 else 3
            o_uniq = sorted(set(v_ for v_, _, _, _ in o_list) | {w_[0] for w_ in o_sw if w_}
                            | {m_[0] for mo_ in o_mo for m_ in mo_} | {m_[0] for yc_ in o_yc for m_ in yc_}
                            | {m_[0] for xf_ in o_xf for m_ in xf_})
            o_gw = o_per * (o_cw + 1) - 1
            o_body = [f"★  NEXT OPERATION-OCJP  —  from the LAST row {both_cut[-2][0]:02d} ({both_cut[-2][2]}),"
                      f" {both_cut[-1][0]:02d} ({both_cut[-1][2]})  on EP={ep:02d}  ★", "",
                      '┌' + '┬'.join('─' * o_cw for _ in range(o_per)) + '┐']
            for k_ in range(0, len(o_cells), o_per):
                if k_:
                    o_body.append('├' + '┼'.join('─' * o_cw for _ in range(o_per)) + '┤')
                row_ = o_cells[k_:k_ + o_per] + [''] * (o_per - len(o_cells[k_:k_ + o_per]))
                o_body.append('│' + '│'.join(f" {c:<{o_cw - 1}}" for c in row_) + '│')
            o_body.append('└' + '┴'.join('─' * o_cw for _ in range(o_per)) + '┘')
            o_body += ["", f"ALL ({len(o_uniq)}): " + ' '.join(f"{v_:02d}" for v_ in o_uniq),
                       "1-20 = the user's operations;  21-30 ^ = mirror forms;  31-38 ° = one operation, sign flipped on one side;  39 = EP cut/cut;  40 = EP itself nc/nc",
                       "after the comma, + = the same place with its x step switched (1 <-> 2), y kept (-1/c+1 -> -2/c+1);",
                       "  when x is nc or cut, the y step switched instead (nc/+2 -> nc/+1)",
                       "after the next commas, * = the y step switched, and both steps switched (-2/-2 -> -2/-1, -1/-1)",
                       "# = x is nc, cut or a cut step (any x on places 31-38): y with its cut switched, both y steps (nc/+1 -> nc/c+1, nc/c+2; c-1/c-2 -> c-1/-2, -1)",
                       "% = places 15-18 (y fixed at cut or nc) and 19-20 (any y): x with its cut switched, both x steps (+2/cut -> c+2/cut, c+1/cut; -2/-1 -> c-2/-1)",
                       "! = places 1-8 with a plain step on x: x with its sign flipped, y kept (-2/+1 -> +2/+1)",
                       "~ = that place repeated an operation already shown, so it takes the next unused one (none left = place empty)",
                       "built from the two operations: sign flipped, cut switched on / off.  Re-run of 140 J/K rounds:",
                       "  41 hits, about 47 expected by its size alone — a list to watch, not a proven edge"]
            o_flag = [f"\033[1;38;2;{c}m" for c in ("255;153;51", "255;255;255", "19;136;8")]
            o_iw = max(len(l_) for l_ in o_body) + 2
            o_box = [f" \033[1m{l_:<{o_iw - 2}}{s_rst} " for l_ in o_body]
            for lvl in range(2, -1, -1):           # green inner, white, saffron outer
                c_, w_ = o_flag[lvl], o_iw + 2 * (2 - lvl)
                o_box = ([f"{c_}┏{'━' * w_}┓{s_rst}"] + [f"{c_}┃{s_rst}{l_}{c_}┃{s_rst}" for l_ in o_box]
                         + [f"{c_}┗{'━' * w_}┛{s_rst}"])
            _RRR3_PREV['ocjp'] = o_uniq
            strong_lines += [' ' * (s_tw + 4) + '  ' + l_ for l_ in o_box]
            # OCJP FINAL 4 below the OCJP box (user, 2026-10-15: "mark only 4
            # as prediction final numbers"), chosen by _rrr_final4
            f4_lists = {'RECOMMENDED': [v for v, _ in rec], 'RRR table': [v for v, _, _ in both_cut],
                        'same op again': [a_[0] for a_ in (same, same2, same_turn if same else None,
                                                           same_yx if same else None) if a_],
                        'WIDE': [v for v, _ in wide], 'yx': [v for v, _ in rec_yx],
                        '3RRR RESULT': [int(n_[:2]) for n_, _ in found]}
            f4_place = {}
            for v_, _, k_, _ in o_list:
                f4_place.setdefault(v_, k_)
            for (_, _, k_, _), w_, mo_, yc_ in zip(o_list, o_sw, o_mo, o_yc):
                for x_ in ([w_] if w_ else []) + mo_ + yc_:
                    f4_place.setdefault(x_[0], k_)
            ocjp_final4 = _rrr_final4(o_uniq, f4_lists,
                                      [strong, [v for v, _ in fam_seats], [v for _, _, l_ in nc_spec for v, _ in l_]],
                                      f4_place)
            f4_body = [f"★  OCJP FINAL 4  —  after {grid_ep:02d}, EP={ep:02d}  ★", ""]
            for k_, (v_, nm_) in enumerate(ocjp_final4):
                f4_body.append(f"{k_ + 1}. {v_:02d} ({OP_ABBREV[find_op(ep // 10, v_ // 10)]}/{OP_ABBREV[find_op(ep % 10, v_ % 10)]})"
                               f"   in {len(nm_)} lists: {', '.join(nm_) if nm_ else '-'}")
            f4_body += ["", "the OCJP numbers most of the never-repaired lists also hold",
                        "(RECOMMENDED, RRR table, same op again, WIDE, yx, 3RRR RESULT)",
                        "walk-forward, 436 past rounds: 36 hits = 8.3%; any 4 numbers = 4.0%",
                        "about twice chance, but it still misses about 92 rounds in 100"]
            # OCJP MASTER (user, 2026-10-16: "finally we are going to use
            # this one result only"): FINAL 4's #1 as the one exact pick
            if ocjp_final4:
                m_ = ocjp_final4[0][0]
                f4_body += ["", f"OCJP MASTER (one exact pick) = #1  {m_:02d} "
                                f"({OP_ABBREV[find_op(ep // 10, m_ // 10)]}/{OP_ABBREV[find_op(ep % 10, m_ % 10)]})",
                            "#1 was the result in 15 of 590 past rounds = 2.5% (one number by chance = 1%);",
                            "live K46-K99: 3 of 54. It misses most rounds"]
            f4_w = max(len(l_) for l_ in f4_body) + 2
            strong_lines += [' ' * (s_tw + 4) + '  ' + f"{s_g}┌{'─' * f4_w}┐{s_rst}"]
            strong_lines += [' ' * (s_tw + 4) + '  ' + f"{s_g}│{s_rst} \033[1m{l_:<{f4_w - 2}}{s_rst} {s_g}│{s_rst}" for l_ in f4_body]
            strong_lines += [' ' * (s_tw + 4) + '  ' + f"{s_g}└{'─' * f4_w}┘{s_rst}"]
        # the three tables (STRONG 20, CharRow no repeats, STRONG 20
        # ADJUSTMENTS) once more at the very end of the page, in the triple
        # Indian-flag border (user's screenshot, 2026-10-13)
        # ROUND SUMMARY above them (user's screenshot, 2026-10-13): the number
        # the round comes after, the EP the operations are applied on, and
        # what the declared number and the same-operation-again number are
        def _s_lab(n_):
            return f"{n_:02d} ({OP_ABBREV[find_op(ep // 10, n_ // 10)]}/{OP_ABBREV[find_op(ep % 10, n_ % 10)]})"
        r_band = ' '.join(f"{p_t * 10 + (p_u + k_) % 10:02d}" for k_ in range(-2, 3))
        r_2nd = ((grid_ep // 10 + 6) % 10) * 10 + p_u
        r_rows = [("After number", f"{grid_ep:02d}", "the last result; the round comes after it"),
                  ("Operations on EP", f"{ep:02d}", "the number every operation is applied on"),
                  ("Declared number", _s_lab(p_decl), f"cut / c-1 on the after number {grid_ep:02d}"),
                  ("Decade", f"{p_t}0-{p_t}9", "the after number's tens digit cut"),
                  ("Band", r_band, "the declared number and 1, 2 either side"),
                  ("2nd number", _s_lab(r_2nd), f"c+1 / c-1 on the after number {grid_ep:02d}"),
                  ("Same operation again", _s_lab(same[0]) if same else "-",
                   "the last round's operation applied again on this EP"),
                  ("3RRR result line", ' '.join(n_[:2] for n_, _ in found[:4]) or "-", "the 3RRR RESULT numbers"),
                  ("POWER BASE", ', '.join(_s_lab(v_) for v_, _ in p_four), "declared, decade up, one below, one above")]
        # star picks (user, 2026-10-13: "apply * mark on accurate prediction
        # result"): the three numbers the most lists agree on — STRONG 20,
        # band, RRR table, RECOMMENDED, yx, wide, 3RRR RESULT, same-operation
        # lines; one vote a list, ties by lower number.  The first one takes
        # the star.  Re-run of 94 rounds: star 6, three picks 11 (chance 1
        # and 3) — it is a pick, not a promise
        k_votes = {}
        for k_list in (strong, [p_t * 10 + (p_u + k_) % 10 for k_ in range(-2, 3)], [v_ for v_, _, _ in both_cut],
                       [v_ for v_, _ in rec], [v_ for v_, _ in rec_yx], [v_ for v_, _ in wide],
                       [int(n_[:2]) for n_, _ in found],
                       [a_[0] for a_ in (same, same2, same_turn if same else None, same_yx if same else None) if a_]):
            for v_ in set(k_list):
                k_votes[v_] = k_votes.get(v_, 0) + 1
        k_top = sorted(k_votes, key=lambda v_: (-k_votes[v_], v_))[:3]
        _RRR3_PREV['star_picks'] = k_top
        if os.environ.get('RRR3_DUMP2') and os.path.exists(os.environ['RRR3_DUMP2']):
            import json
            with open(os.environ['RRR3_DUMP2']) as fh:
                d2_ = json.load(fh)
            d2_['star'] = [[v_, k_votes[v_]] for v_ in sorted(k_votes, key=lambda v_: (-k_votes[v_], v_))]
            with open(os.environ['RRR3_DUMP2'], 'w') as fh:
                json.dump(d2_, fh)
        if k_top:
            r_rows.append(("Star picks", ',  '.join(('★ ' if k_ == 0 else '') + _s_lab(v_) + f" [{k_votes[v_]}]"
                                                     for k_, v_ in enumerate(k_top)),
                           "most lists agree on these; [n] = lists; ★ = first pick"))
        if star_turn_:
            r_rows.append(("Star pick turns", ', '.join(_s_lab(v_) for v_ in star_turn_),
                           "the ★ pick with each plain step turned to cut and to nc"))
        # HOT 20 (2026-10-14): the 20 numbers that came most often in the
        # whole data so far (ties: lower number).  Walk-forward on 2,823 older
        # rounds of series J: 23% against 20% by chance — a small edge, the
        # only one found; shown beside STRONG 20, which it does not change
        h_cnt = {}
        for v_ in _RRR3_PREV.get('flat', []):
            h_cnt[v_] = h_cnt.get(v_, 0) + 1
        hot20 = sorted(h_cnt, key=lambda v_: (-h_cnt[v_], v_))[:20]
        _RRR3_PREV['hot20'] = hot20
        if hot20:
            r_rows.append(("HOT 20", ' '.join(f"{v_:02d}" for v_ in hot20),
                           "came most often in all the data (23% vs 20%)"))
        if ocjp_final4:
            r_rows.append(("OCJP FINAL 4", '  '.join(_s_lab(v_) for v_, _ in ocjp_final4),
                           "OCJP numbers most never-repaired lists hold (8.3% vs 4%)"))
            r_rows.append(("OCJP MASTER", _s_lab(ocjp_final4[0][0]),
                           "FINAL 4's #1: one exact pick (2.5% vs 1%)"))
        r_w = [max(len(r_[k_]) for r_ in r_rows) + 2 for k_ in range(3)]
        r_tw = sum(r_w) + 2
        r_title = f"★  ROUND SUMMARY  —  after {grid_ep:02d}, operations on EP={ep:02d}  ★"
        r_tw = max(r_tw, len(r_title) + 2)
        r_w[2] += r_tw - (sum(r_w) + 2)
        r_box = [f"  {s_g}┌{'─' * r_tw}┐{s_rst}",
                 f"  {s_g}│{s_rst}{p_rib}{r_title:^{r_tw}}{s_rst}{s_g}│{s_rst}",
                 f"  {s_g}├{'┬'.join('─' * w_ for w_ in r_w)}┤{s_rst}"]
        r_box += [f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c_:<{w_ - 1}}" for c_, w_ in zip(r_, r_w)) + f"{s_g}│{s_rst}"
                  for r_ in r_rows]
        r_box.append(f"  {s_g}└{'┴'.join('─' * w_ for w_ in r_w)}┘{s_rst}")
        # SUMMARY NUMBERS below the OCJP FINAL 4 / MASTER rows (user,
        # 2026-10-23): every two-digit number in the summary's value column
        # (After number and EP left out), no repeats, ascending, one row a
        # decade 00-09 .. 90-99, each number in its own units slot
        u_nums = sorted({int(v_) for r_ in r_rows if r_[0] not in ("After number", "Operations on EP")
                         for v_ in re.findall(r'\b\d\d\b', r_[1])})
        u_title = f"★  SUMMARY NUMBERS  —  {len(u_nums)}, no repeats, after {grid_ep:02d}, EP={ep:02d}  ★"
        u_rows = [(f"{d_}0-{d_}9", ' '.join(f"{d_ * 10 + k_:02d}" if d_ * 10 + k_ in u_nums else '  '
                                             for k_ in range(10))) for d_ in range(10)]
        u_w = [max(len(a_) for a_, _ in u_rows) + 2, len(u_rows[0][1]) + 2]
        u_tw = max(sum(u_w) + 1, len(u_title) + 2)
        u_w[1] = u_tw - 1 - u_w[0]
        r_box += [f"  {s_g}┌{'─' * u_tw}┐{s_rst}",
                  f"  {s_g}│{s_rst}{p_rib}{u_title:^{u_tw}}{s_rst}{s_g}│{s_rst}",
                  f"  {s_g}├{'─' * u_w[0]}┬{'─' * u_w[1]}┤{s_rst}"]
        r_box += [f"  {s_g}│{s_rst} {a_:<{u_w[0] - 1}}{s_g}│{s_rst} {b_:<{u_w[1] - 1}}{s_g}│{s_rst}" for a_, b_ in u_rows]
        r_box.append(f"  {s_g}└{'─' * u_w[0]}┴{'─' * u_w[1]}┘{s_rst}")
        # the RRR: NEXT OPERATION table below the ROUND SUMMARY (user's
        # screenshots, 2026-10-13)
        t_tw = max(len(l_) for l_ in rrr_tbl) + 2
        t_box = [f"  {s_g}┌{'─' * t_tw}┐{s_rst}"]
        t_box += [f"  {s_g}│{s_rst}{p_rib}{l_.strip():^{t_tw}}{s_rst}{s_g}│{s_rst}" if k_ == 0
                  else f"  {s_g}│{s_rst}{l_:<{t_tw}}{s_g}│{s_rst}" for k_, l_ in enumerate(rrr_tbl)]
        t_box.append(f"  {s_g}└{'─' * t_tw}┘{s_rst}")
        _RRR3_PREV['three_box'] = r_box + t_box + list(strong_lines)
        x_lines = [f"  {s_g}┌{'─' * p_tw}┐{s_rst}",
                   f"  {s_g}│{s_rst}{p_rib}{x_title:^{p_tw}}{s_rst}{s_g}│{s_rst}",
                   f"  {s_g}├{'┬'.join('─' * p_cw for _ in range(4))}┤{s_rst}"]
        for k, (x_cells, x_lab) in enumerate(x_rows):
            if k:
                x_lines.append(f"  {s_g}├{'┼'.join('─' * p_cw for _ in range(4))}┤{s_rst}")
            for line in (x_cells, x_lab):
                x_lines.append(f"  {s_g}│{s_rst}" + f"{s_g}│{s_rst}".join(f" {c:<{p_cw - 1}}" for c in line)
                               + f"{s_g}│{s_rst}")
        x_lines.append(f"  {s_g}└{'┴'.join('─' * p_cw for _ in range(4))}┘{s_rst}")
        power_lines = x_lines + power_lines
        power_lines += [f"     box: + = digits reversed of a table number whose series is already there ({len(p_added)} added)",
                        "     reversed = the two operations crossed and both signs flipped (c+1/+1 becomes -1/c-1)",
                       "     after a comma = same x, y step switched (-1 <-> -2, +1 <-> +2), only for a plain y step",
                       "     each of those two is followed by the same number with the cut on its y step (+2 -> c+2)",
                       "     where the y step is -1 or -2 the opposite cut step is added too (-2, c-2 -> c+2)",
                       "     then the same on the x operation of the cell's first number, its y kept",
                       "     declared number only: y cut + sign changed, x without its cut, the two swapped; and that step switched",
                       "     and those two with the sign of the second operation changed (c-2/-1 -> c-2/+1)",
                       "     and those crossed with the cut put on the new x only (c+1/-1 -> c-1/c+1)",
                       "     and the last of that pair with the cut put on its y only (cut/+2 -> cut/c+2)",
                       "     declared number only, last: x without its cut and sign changed, y kept (c+1/+2 -> -1/+2)",
                       "     declared number only, x plain step + y cut step: +1/c+1 -> cut/c-2",
                       "     declared number only, x cut step + y nc: the first rule's two numbers with both cut",
                       "     declared cell, last line: RRR last row xy and yx with the cut added to its new x operation",
                       "     and that xy number with the sign of its y changed, and with only the cut on y (cut/c+2, cut/cut)",
                       "     that yx number with its tens digit cut and the digits reversed (30 -> 08), and that with nc on y",
                       "     where that operation is a bare cut: also nc in its place (cut/-1, -1/cut -> nc/-1, -1/nc)",
                       "     that xy number as cut step / nc: x without the cut, y the cut step of the other sign (c-1/nc -> -1/c+1)",
                       "     that yx number with a cut step on x: x without cut, other sign, both numbers (c+2/c-2 -> -1/c-2, -2/c-2)",
                       "     and the first of those with only the cut on y (-2/c-1 -> -2/cut)",
                       "     RRR last row +1/+1 or +2/+2: also nc on x and the other step on y (+1/+1 -> nc/+2)",
                       "     declared cell numbers with the cut step of the other sign and number on x (c+1 -> c-2): also without that cut",
                       "     and each of those with its digits reversed (14 -> 41)",
                       "     nearest x of the declared x already in the cell: that x with the declared y (96 c+2/+2 -> 86 c+1/+2)",
                       "     declared cell: every number with a bare cut on y also with nc on y (65 +1/cut -> 60 +1/nc)",
                       "     declared cell: ★ rows of the RRR table, x without cut + sign flipped, y without cut, same sign (+2/c-2 -> -2/-2)",
                       "     declared cell: declared y a +1/+2 step — the cut steps of the other sign too (-1/+1 -> -1/c-1, -1/c-2)",
                       "     declared cell: the first rule's two numbers also with the cut step on x switched (c+2/-1 -> c+1/-1)",
                       "     declared cell: x = declared x step without cut, other sign and number, y a cut step — also only the cut on y (-1/c-2 -> -1/cut)",
                       "     declared cell: the last round's operation again, on the running value instead of the EP (-1/cut on 27 -> 12)",
                       "     declared cell: declared operations crossed, y without its cut and step switched on x, x without its cut on y (nc/c-1 -> -2/nc)",
                       "     declared cell: the last round's operation again on the running value with its x step switched (+2/nc on 06 -> +1/nc on 06 = 16)",
                       "     declared cell: the last round's operation again on the EP with nc on y (c+1/+2 -> c+1/nc)",
                       "     declared cell: declared x without its cut + sign flipped, with the cut steps of the other sign on a +1/+2 declared y (c-2/+2 -> +2/c-1, +2/c-2)",
                       "     declared cell: the crossed declared operations (nc/-1 -> -2/nc) applied on the running value instead of the EP (-2/nc on 28 = 08)",
                       "     declared cell: a STRONG 20 number and a 3RRR RESULT number of the same family (53 and 85) bring that STRONG 20 number with both digits cut (53 -> 08)",
                       "     declared cell: the whole NUMBER BAND (declared number ± 1, ± 2) is in the cell (50, 52, 54 -> also 51, 53)",
                       "     declared cell: the SAME OPERATION AGAIN number (the last round's operation on this EP) is in the cell (cut/c-2 again -> 26)",
                       "     declared cell: the EP and a 3RRR RESULT number of the same family (02 and 70) bring the EP with both digits cut (02 -> 57)",
                       "     declared cell: the first 3RRR RESULT number itself is in the cell (08)",
                       "     declared cell: every RRR: NEXT OPERATION table number, xy and yx (89 (+1/-1))",
                       "     declared cell: the SAME OPERATION AGAIN crossed, yx and yx turned (old y cut removed, old x sign flipped) (+1/-1 -> 45 (-1/-1))",
                       "     declared cell: the NEXT OPERATION-OCJP places 31-38, one operation on both sides (-1/-1 -> 57)",
                       "     declared cell: NC/CUT SPECIAL, the row after an nc/cut, cut/nc or nc/nc row modified every way (+2/c+2 -> c+2/c-2 = 33)",
                       "     declared cell: STRONG 20 ADJUSTMENTS, every seat with its y cut toggled (98 (c+2/nc) -> 93 (c+2/cut))",
                       "     declared cell: STRONG 20 ADJUSTMENTS, every seat with its x sign flipped too (05 (+1/cut) -> 85 (-1/cut))",
                       "     declared cell: the NEXT OPERATION-OCJP mirror places 21-30 (nc/-1 -> 38)",
                       "     declared cell: the NEXT OPERATION-OCJP places 1-20 (-1/cut -> 45), so every OCJP place is in the cell",
                       "     declared cell: every 3RRR RESULT number, not only the first (94 65 66 36 -> 36)",
                       "     declared cell: the 3RRR WIDE list numbers (96 (c+1/+2))",
                       "     declared cell: the band numbers one and two below the declared number with their x sign flipped (74 (+1/+2) -> 54 (-1/+2))",
                       "     declared cell: the STRONG 20 seats below the band with y cut toggled (67 (-1/-1) -> 62 (-1/c-1))",
                       "     declared cell: RECOMMENDED F, the last row not crossed with one side dropped to nc (55 (-2/nc))",
                       "     declared cell: RECOMMENDED F, the last row not crossed with both sides one step down / up (24 (-1/-2))",
                       "     declared cell: the RRR table row that gave the star pick, its old operation again on this EP, xy and yx (-1/+1 -> 28, 46)",
                       "     declared cell: the LAST row of the next-operation table, its number with a cut on y comes with y one step down (22 (c+1/cut) -> 21 (c+1/c-1))",
                       "     declared cell: the first STRONG 20 number above the band with a cut and step on x and a plain step on y, the cut taken off x (23 (c-2/+1) -> 73 (-2/+1))",
                       "     declared cell: a star pick turn with a cut on y comes with its y one step down (46 (cut/cut) -> 45 (cut/c-1))",
                       "     declared cell: the star pick with each plain step (+1/-1, +2/-2) turned to cut and to nc (28 (+1/-2) -> 68 18 25 20)",
                       "     declared cell: every STRONG 20 rule seat, also the ones that lost their seat (72 (-2/c-2))",
                       "     declared cell: the 2nd number with its y sign flipped (51 (c+1/c-2) -> 55 (c+1/c+2))",
                       "     declared cell: the same STRONG 20 number (step on x, cut on y) brings its full opposite, x sign flipped and the cut taken off y (32 (+1/cut) -> 17 (-1/nc))",
                       "     declared cell: the first STRONG 20 number above the band with a step on x and a cut on y brings its opposite, the cut moved to x (26 (+2/cut) -> 71 (c+2/nc))",
                       "     declared cell: the declared number two decades up, the step after the POWER BASE's one decade up (50 -> 70)",
                       "     declared cell: the first STRONG 20 number above the band with a plain cut on y comes with its y one step down (55 (+2/cut) -> 54 (+2/c-1))",
                       "     declared cell: a CharRow number with cut/nc brings the same operation turned over, nc/cut (70 -> 25); it also takes a STRONG 20 seat",
                       "     declared cell: the first STRONG 20 number above the band with a cut and a step on x comes with its x sign flipped (99 (c-2/c+1) -> 39 (c+2/c+1))",
                       "     declared cell: the first 3RRR RESULT number with its x step switched, the nearest x (27 (-1/c+2) -> 17 (-2/c+2))",
                       "     declared cell: the after number itself, the running value coming again (30 -> 30)",
                       "     declared cell: a 3RRR RESULT number that is also a STRONG 20 number above the band brings itself with both digits cut (26 -> 71)",
                       "     declared cell: the band number two above the declared number with its x sign flipped (86 (-1/nc) -> 06 (+1/nc))",
                       "     declared cell: the band number one above the declared number with its x sign flipped (70 (+2/-1) -> 30 (-2/-1))",
                       "     declared cell: a CharRow number with a plain cut on x takes the last operation's steps in place of the cut (44 (cut/c+2) -> 04, 84 (-1/c+2))",
                       "     declared cell: the band number one under the declared number with the cut toggled on its x and the x sign flipped (91 (c+1/+1) -> 21 (-1/+1))",
                       "     declared cell: the band number one under the declared number with the cut toggled on its x, nc / c-2 on the running value (09 -> 02)",
                       "     declared cell: a STRONG 20 number under the band with a plain step of one on y brings the same with nc on y (00 (c+2/-1) -> 01 (c+2/nc))",
                       "     declared cell: a STRONG 20 number above the band with nc on x brings the same with its y cut toggled (25 (nc/+1) -> 20 (nc/c+1))",
                       "     declared cell: the EP itself, nc/nc, is in the cell (EP 68 -> 68)",
                       "     declared cell: the c+2 / c-2 number of the running value read on the EP and mirrored, both signs flipped (09 (-2/-2) -> 43 (+2/+2))",
                       "     declared cell: the 2nd NUMBER one above, c+1 / cut on the running value (71 -> 36)",
                       "     declared cell: the last round's operation with its x sign flipped and its y without the cut (c+1/c-2 -> c-1/-2 = 71)",
                       "     declared cell: the SAME OPERATION AGAIN number mirrored, the last round's operation with both signs flipped (c-1/c+2 -> c+1/c-2 = 31)",
                       "     declared cell: the declared operations crossed, both signs flipped and both steps switched (90 (c-1/-1) -> +2/c+2 = 78)",
                       "     declared cell: the 3RRR RESULT C number with its x step switched, the nearest x (56 (-1/nc) -> 46 (-2/nc))",
                       "     declared cell: the SAME OPERATION AGAIN number mirrored with its x step switched (c-2/c-1 -> c+1/c+1 = 76) also with its units digit cut (-> 71)",
                       "     declared cell: the operation of two rounds back again on this EP is in the cell (c+1/-2 again -> 30)",
                       "     declared cell: the 2nd NUMBER with its x sign flipped (73 (-1/+1) -> 93 (+1/+1)) also with both digits cut (-> 48)",
                       "     declared cell: the 2nd NUMBER's operation applied on the running value instead of the EP (62 = +1/+1 on EP 51; +1/+1 on 08 -> 19)",
                       "     declared cell: the 2nd NUMBER with its x sign flipped and its y step switched, c-1 / c-2 on the running value (65 -> 08)",
                       "     declared cell: two STRONG 20 numbers above the band, -1 and +1 on x with the same y (13 and 33), bring the number between them, nc on x (-> 23)",
                       "     declared cell: a 3RRR RESULT number that is a STRONG 20 number above the band with both digits cut (88 -> 33) is in the cell",
                       "     declared cell: the declared operation applied on the running value instead of the EP (30 = +2/nc on EP 10; +2/nc on 86 -> 06)",
                       "     declared cell: the SAME OPERATION AGAIN number mirrored (both signs flipped) with its x step switched (c+1/-1 -> c-2/+1 = 68)",
                       "     declared cell: two STRONG 20 numbers that are each other with both digits cut (24 and 79) bring the number between them, the lower one with its tens cut (74)",
                       "     declared cell: the declared number with its digits reversed (60 -> 06)",
                       "     declared cell: the 2nd NUMBER with both steps switched, c+2 / c-2 on the running value (19 -> 82)",
                       "     declared cell: the last round's operation with the cut moved to the other side and both steps switched (-2/c+2 -> c-1/+1 = 21)",
                       "     declared cell: the band number one under the declared number (31) also with its units digit cut (-> 36)",
                       "     declared cell: the STRONG 20 number from the first RRR table number's y as a cut step (32 (c+2/+2) -> 33 (c+2/c-2)) also with both digits cut (-> 88)",
                       "     declared cell: the last round's operation crossed, both without their cut and both signs flipped (+2/c+1 -> -1/-2 = 10)",
                       "     declared cell: the STRONG 20 number from the declared operations crossed (10 (c+1/c-1) -> 27 (c+2/+1)) also with its digits reversed (-> 72)",
                       "     declared cell: the number a crossed family pair of the STRONG 20 brings (85 and 08 -> 30) also with its digits reversed (-> 03)",
                       "     declared cell: two STRONG 20 numbers of one family, digits the other way round (80 and 03): first tens digit cut + the other tens digit (-> 30)",
                       "     declared cell: the + forms of the NEXT OPERATION-OCJP places 31-38, x step switched (96 (c+2/c-2) -> 86 (c+1/c-2))",
                       "     declared cell: the + , * and % forms of every NEXT OPERATION-OCJP place, so the cell holds all of OCJP (83 (-1/-1) -> 72 (-2/-2))",
                       "     declared number nc/cut: its tens cut, both digits cut, and the digits reversed of those and of itself",
                       "     declared cell with a cut/cut number: the cut/nc number with its digits reversed",
                       "     declared cell, end: a number of it whose digits reversed stand in another cell brings that number in",
                       "     ★ = also in the STRONG 20     * = also in the RECOMMENDED list     ☆ = number from the declared-cell rules",
                       f"     in advance {RRR_LIVE['power_hits']} of {RRR_LIVE['power_rounds']};"
                       " all 423 recorded rounds: 36 = 8.5% (4% by chance), latest series 7 of 170", ""]
    res_items = [f"{n} ({r})" for n, r in found]
    res_lines = [f"  ★ 3RRR RESULT  →  " + ('   '.join(res_items[:4]) if res_items else "no number this round")]
    res_lines += ["       " + '   '.join(res_items[k:k + 5]) for k in range(4, len(res_items), 5)]
    body += ['─' * len(head), "3RRR".center(len(head)), "",
             *power_lines,
             *strong_lines,
             "     never more than 20 (16 until 2026-10-11): the RRR table, the rule seats written after misses (in place of the last table numbers), the number band (5)",
             "     and rule numbers as fill — about one round in five by size; most rounds still miss.", "",
             *final_lines,
             "     numbers 1-20 are the STRONG 20; the rest follow in the order of the lists below", "",
             *res_lines,
             *rec_lines,
             "     recommended = 3RRR numbers + rules E and F + same operation again + EP itself, EP cut + unused RRR pairs",
             "     recommended yx = each recommended value's two operations crossed (numbers not already recommended)",
             "     wide = rule G: the single moves seen on middle rows, tried on every row (numbers not already above)", "",
             "  HOW THE OPERATIONS MOVED  (each row = an earlier row crossed: old y → new x, old x → new y)"]
    trail_rows = _rrr3_trail(entries)
    if not trail_rows:
        body.append("     needs two WIN - WIN rows")
    for pos, fpos, fy, nx_, wx, fx, ny_, wy in trail_rows:
        tag = f"[{pos_prefix}{pos}] ← [{pos_prefix}{fpos}]"
        body.append(f"  {tag:<17} x: {OP_ABBREV[fy]:<4} → {OP_ABBREV[nx_]:<4} {wx:<25} "
                    f"y: {OP_ABBREV[fx]:<4} → {OP_ABBREV[ny_]:<4} {wy}")
    body += ["", "  A) NEXT: SAME-FAMILY ROW, CROSSED AGAIN"]
    if la is None:
        body.append("     needs two WIN - WIN rows — no number from this rule")
    elif not picks:
        body.append(f"     last WIN - WIN source {la:02d}: no earlier row in its family "
                    f"({la:02d} / {cut(la // 10) * 10 + cut(la % 10):02d}) — no number from this rule")
    else:
        body.append(f"  {'Pos':<12} {'Source':<9} {'old x':<6} {'old y':<6}    {'new x':<6} {'new y':<6}  "
                    f"{'xy (op)':<{KW}}1st crossing")
        for pos, a, b, x_op, y_op, first, used, nx, ny, num, sx, sy, snum in picks:
            nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
            if first is None:
                note = "no 1st crossing → 2nd"
            else:
                pair = f"{OP_ABBREV[first[0]]}/{OP_ABBREV[first[1]]}"
                note = f"{pair} used at [{pos_prefix}{used}] → 2nd" if used is not None else f"{pair} not used yet → 1st"
            tag = f"[{pos_prefix}{pos}]"
            body.append(f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                        f"{nxa:<6} {nya:<6}  " + f"{num:02d}{star(num)}({nxa}/{nya})".ljust(KW) + note)
            sxa, sya = OP_ABBREV[sx], OP_ABBREV[sy]
            body.append(f"  {'':<12} {'':<9} {'':<6} {'':<6} →  {sxa:<6} {sya:<6}  "
                        + f"{snum:02d}{star(snum)}({sxa}/{sya})".ljust(KW) + "cut switched + sign flipped")
        body += [f"     row = earlier WIN - WIN row in the family of the last row's source {la:02d}",
                 "     1st crossing: new x = old y, new y = old x one step further",
                 "     2nd crossing: new x = cut of old y + number of old x, new y = old x flipped",
                 "     also: both sides crossed with the cut switched and the sign flipped",
                 "     in every rule: a new x that already came twice in the x column drops to nc"]
    body += ["", "  B) NEXT: LAST ROW CROSSED, CUT ON BOTH SIDES"]
    if entries:
        trail = ' · '.join(f"{pos_prefix}{pos} {_op_type(x_op)}/{_op_type(y_op)}"
                           for pos, _, _, x_op, y_op, _ in entries[-6:])
        body += [f"     pairs so far: {trail}",
                 "     C = cut±n, K = cut, I = ±n, N = nc"]
    if row is None:
        body.append(f"     {why}")
    else:
        pos, a, b, x_op, y_op, nx, ny, num = row
        nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
        tag = f"[{pos_prefix}{pos}]"
        body += [f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                 f"{nxa:<6} {nya:<6}  " + f"{num:02d}{star(num)}({nxa}/{nya})".ljust(KW) + "C/C not used yet",
                 "     new x = cut + old y's number one step down, new y = cut + old x's number one step down"]
    body += ["", "  C) NEXT: LAST ROW CROSSED, CUT REMOVED ON BOTH SIDES"]
    if keep is None:
        body.append("     no WIN - WIN row")
    else:
        pos, a, b, x_op, y_op, nx, ny, num, due = keep
        nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
        tag = f"[{pos_prefix}{pos}]"
        body += [f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                 f"{nxa:<6} {nya:<6}  " + f"{num:02d}{star(num)}({nxa}/{nya})".ljust(KW)
                 + ("old x came twice in x → nc" if ny == 'no_change' and x_op != 'no_change' and x_op != 'cut' else ""),
                 "     new x = old y without its cut, new y = old x without its cut (nc when old x came twice in x)"]
    body += ["", "  D) NEXT: ROW THAT ENDS AT THE RUNNING VALUE, CROSSED, CUT SWITCHED + SIGN FLIPPED"]
    if not arrived:
        body.append("     no WIN - WIN row ends at the running value" + (f" {grid_ep:02d}" if live else "")
                    + " — no number from this rule")
    for pos, a, b, x_op, y_op, nx, ny, num in arrived:
        nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
        tag = f"[{pos_prefix}{pos}]"
        body.append(f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                    f"{nxa:<6} {nya:<6}  " + f"{num:02d}{star(num)}({nxa}/{nya})".ljust(KW))
    if arrived:
        body.append("     new x = old y, cut switched + sign flipped; new y = old x, cut switched + sign flipped")
    body += ["", "  E) NEXT: ANY ROW CROSSED UNCHANGED, WHEN THAT TYPE PAIR IS NEW  (recommended list only)",
             "     " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in plain) if plain else "none this round"),
             "     and rows whose x has a cut, crossed with old y kept and that cut removed:",
             "     " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in kept) if kept else "none this round"),
             "     and the last row crossed with one side one step up or down (the other side kept or flipped):",
             "     " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in turned) if turned else "none this round")]
    body += ["", "  F) NEXT: LAST ROW / CHAIN'S LAST STEP NOT CROSSED, ONE SIDE DROPPED TO nc  (recommended list only)",
             "     " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in dropped) if dropped else "none this round"),
             "     or one side losing its cut:  "
             + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in uncut) if uncut else "none this round"),
             "     or crossed, old y kept, old x gaining a cut (also sign flipped):",
             "       " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in gained) if gained else "none this round"),
             "     or not crossed, both sides one step down / up:  "
             + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in stepped) if stepped else "none this round"),
             "     or crossed, cuts removed, other side dropped to nc:  "
             + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in bare) if bare else "none this round"),
             "     or not crossed, one side cut switched + sign flipped, other side kept:",
             "       " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in rrr_side) if rrr_side else "none this round"),
             "     or the ± numbers removed on both sides (crossed / not crossed):",
             "       " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in numberless) if numberless else "none this round"),
             "     or rule B with the numbers stepped down/up, up/down, up/up:",
             "       " + ('   '.join(f"{v:02d}{star(v).strip()} ({lab})" for v, lab in b_steps) if b_steps else "none this round")]
    body += ["", "  SAME OPERATION AGAIN  (the previous round's operation on this EP):  "
             + (f"{same[0]:02d}{star(same[0]).strip()} ({same[1]})" if same else "not available")]
    if same:
        body += [f"     yx (crossed):  {same_yx[0]:02d}{star(same_yx[0]).strip()} ({same_yx[1]})"
                 f"     yx, cut removed from old y, old x sign flipped:  "
                 f"{same_turn[0]:02d}{star(same_turn[0]).strip()} ({same_turn[1]})",
                 f"       (in advance: yx {RRR_LIVE['rrr3_sameyx_hits']} of {RRR_LIVE['rrr3_sameyx_rounds']},"
                 f" yx with cut removed + sign flipped {RRR_LIVE['rrr3_turn_hits']} of {RRR_LIVE['rrr3_turn_rounds']})"]
    if same2:
        body += [f"     operation of the round before last, again:  {same2[0]:02d}{star(same2[0]).strip()} ({same2[1]})"
                 f"   (in advance {RRR_LIVE['rrr3_same2_hits']} of {RRR_LIVE['rrr3_same2_rounds']}; all 4 of 350)"]
    body += ["", f"  3RRR live record: result {RRR_LIVE['rrr3_hits']} of {RRR_LIVE['rrr3_rounds']} rounds with a number,"
             f" recommended {RRR_LIVE['rrr3_rec_hits']} of {RRR_LIVE['rrr3_rec_rounds']},",
             f"  same operation again {RRR_LIVE['rrr3_same_hits']} of {RRR_LIVE['rrr3_same_rounds']},"
             f" wide {RRR_LIVE['rrr3_wide_hits']} of {RRR_LIVE['rrr3_wide_rounds']},"
             f" recommended yx {RRR_LIVE['rrr3_yx_hits']} of {RRR_LIVE['rrr3_yx_rounds']},",
             f"  STRONG 20: {RRR_LIVE['rrr3_strong_hits']} of {RRR_LIVE['rrr3_strong_rounds']} (the first 99 rounds with 16 numbers).",
             "  Replay on 309 recorded rounds: result line 13 hits on 1310 numbers (13.1 by chance);",
             "  recommended list (about 23 numbers a round): 82 hits (72.0 by chance);",
             "  wide list (about 16 numbers a round): 39 hits (49.7 by chance); same operation again: 6 (3.1).",
             "  On 357 rounds: recommended yx (about 11 numbers a round) 28 hits (40.3 by chance);",
             "  same operation yx 3 hits, yx with cut removed + sign flipped 5 hits (3.6 by chance each)."]
    if live:
        body += ['─' * len(head)] + _rrr_declared(grid_ep) + ["  ★ in the table = number inside the tens-cut decade"]
    return _rrr_frame(body)


def _kk_table(sequence, ep, label, pos_prefix, empty_msg, merge_counts=None, final40=None,
              show_missing=False, frame_label=None, round_trip=False, rrr=False, grid_ep=None):
    """Shared KK bracket table: prints the per-cell table, the UNIQUE VALUES
    box (optionally with a KK MERGE box beside it) and the ranked box;
    returns the sorted unique values."""
    t       = ep // 10
    bracket = sorted({t, cut(t)})
    entries = _kk_entries(sequence, ep)

    sep('═')
    title = (f"  {label}   (EP={ep:02d}, bracket starts with "
             f"{' or '.join(str(d) for d in bracket)})")
    if not (show_missing and entries):
        print(f"\n{title}\n")
    if not entries:
        print(f"  {empty_msg}")
        if rrr:
            print()
            _RRR3_PREV['frame'] = _rrr_box(sequence, entries, ep, pos_prefix, grid_ep)
            print("\n".join(_RRR3_PREV['frame']))
        sep('═')
        print()
        return []

    KW    = 15
    table = [f"  {'Pos':<7} {'Source':<9} {'x op':<7} {'y op':<7} "
             + "".join(f"{h:<{KW}}" for h in ('xy (op)', 'yx (op)', 'sign+xy (op)',
                                               'sign+yx (op)', 'cut xy (op)', 'cut sign (op)')),
             '─' * (36 + 6 * KW)]
    counts = {}
    for pos, a, b, x_op, y_op, (xy, yx, sxy, syx, cxy, csxy) in entries:
        xab = OP_ABBREV.get(x_op, x_op)
        yab = OP_ABBREV.get(y_op, y_op)
        # every value shows the ops applied to EP in brackets (tens op/units op)
        fx, fy = OP_ABBREV[SIGN_FLIP[x_op]], OP_ABBREV[SIGN_FLIP[y_op]]
        tx, ty = KK_CUT_TOGGLE[x_op], KK_CUT_TOGGLE[y_op]
        cells  = [(xy, xab, yab), (yx, yab, xab), (sxy, fx, fy), (syx, fy, fx),
                  (cxy, OP_ABBREV[tx], OP_ABBREV[ty]),
                  (csxy, OP_ABBREV[SIGN_FLIP[tx]], OP_ABBREV[SIGN_FLIP[ty]])]
        table.append(f"  {'[' + pos_prefix + str(pos) + ']':<7} {a:02d} → {b:02d}   {xab:<7} {yab:<7} "
                     + "".join(f"{v:02d} ({o1}/{o2})".ljust(KW) for v, o1, o2 in cells))
        for v in {xy, yx, sxy, syx, cxy, csxy}:
            counts[v] = counts.get(v, 0) + 1
    table.append('─' * (36 + 6 * KW))
    if show_missing:
        # NON-EXISTING x/y COMBINATIONS — all 10 x ops × all 10 y ops minus
        # the pairs that occur as rows; combos of ops already used in the
        # table first (table order), then the rest (ALL_OPS order)
        used_x = list(dict.fromkeys(e[3] for e in entries))
        used_y = list(dict.fromkeys(e[4] for e in entries))
        pairs  = {(e[3], e[4]) for e in entries}
        first  = [(xo, yo) for xo in used_x for yo in used_y if (xo, yo) not in pairs]
        rest   = [(xo, yo) for xo in ALL_OPS for yo in ALL_OPS
                  if (xo, yo) not in pairs and (xo, yo) not in set(first)]
        # title + 2 blank lines on the left so both tables' rows line up
        left  = [title, "", ""] + table
        right = _kk_missing_combos_box(first, rest, ep, len(pairs))
        if frame_label:
            # green band + label (e.g. WIN - WIN) around the table; the box
            # beside it drops 4 lines so its header still meets the table's
            left  = _green_frame([f"★  {frame_label}  ★".center(max(len(l) for l in left)), ""] + left)
            right = [""] * 4 + right
        _print_side_by_side(left, right)
    elif frame_label:
        print()
        print("\n".join(_green_frame([f"★  {frame_label}  ★".center(max(len(l) for l in table)), "",
                                      title, ""] + table)))
    else:
        print("\n".join(table))

    if rrr:
        print()
        _RRR3_PREV['frame'] = _rrr_box(sequence, entries, ep, pos_prefix, grid_ep)
        print("\n".join(_RRR3_PREV['frame']))

    if round_trip:
        print()
        print("\n".join(_kk_round_trip_box(entries, ep, pos_prefix)))

    # Unique values box — every value once, sorted by number; count is
    # occurrences across all 6 value columns (not once per row like the ranked box)
    uniq = _kk_unique_counts(entries)
    left = _kk_box(f"{label}  (EP={ep:02d})  UNIQUE VALUES ({len(uniq)})",
                   sorted(uniq.items()))
    if merge_counts is not None:
        # KK MERGE — special ∪ chain, no duplicates, counts summed; printed beside
        merged = dict(uniq)
        for v, c in merge_counts.items():
            merged[v] = merged.get(v, 0) + c
        right = _kk_box(f"KK MERGE: SPECIAL + CHAIN  ({len(merged)} values)",
                        sorted(merged.items()))
        _print_side_by_side(left, right)
    else:
        print()
        print("\n".join(left))

    # Ranked by count (each value counted once per row)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    left = _kk_box(f"{label}  ({len(ranked)} values)", ranked)
    if merge_counts is not None and final40:
        # KK MERGE + FINAL 40 — no duplicates, each FINAL-40 value adds 1
        # to its KK MERGE count; printed beside the ranked box
        merged2 = dict(merged)
        for v in final40:
            merged2[v] = merged2.get(v, 0) + 1
        right = _kk_box(f"KK MERGE + FINAL 40  ({len(merged2)} values)",
                        sorted(merged2.items()))
        # Same values again, ascending, 10 per column running vertically
        vert = _kk_vertical_box(f"ASCENDING  ({len(merged2)} values)",
                                sorted(merged2))
        _print_side_by_side(left, right, vert)
    else:
        print()
        print("\n".join(left))
    sep('═')
    print()
    return sorted(counts)


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

_10X10_ORDER = ['cut-1', 'cut+1', 'cut-2', 'cut+2', '-1', '+1', '-2', '+2',
                'no_change', 'cut']


def _print_10x10(title, val, used, used_label, last=None):
    """10x10 grid: every x op (rows) × every y op (cols) applied to `val`
    (xy). Covers 00-99 exactly once; * = op pair in `used`; ◄ = `last`."""
    lbl = {'no_change': 'nc'}
    vx, vy = val // 10, val % 10
    print(f"\n  {title}  ({val:02d}: x = {vx}, y = {vy};"
          f"  rows = x op, cols = y op)\n")
    print("   x \\ y │" + ''.join(f"{lbl.get(o, o):>7}" for o in _10X10_ORDER))
    print("  " + "─" * 7 + "┼" + "─" * (7 * len(_10X10_ORDER)))
    for xo in _10X10_ORDER:
        cells = ''
        for yo in _10X10_ORDER:
            v = apply_op(vx, xo) * 10 + apply_op(vy, yo)
            mark = '◄' if (xo, yo) == last else ('*' if (xo, yo) in used else ' ')
            cells += f"   {v:02d}{mark} "
        print(f"  {lbl.get(xo, xo):>6} │{cells}")
    foot = f"\n  * = op pair used in {used_label}"
    if last:
        foot += f"   ◄ = last op ({lbl.get(last[0], last[0])}/{lbl.get(last[1], last[1])})"
    foot += (f"   nc/nc = {val:02d}"
             f"   cut/cut = {apply_op(vx, 'cut') * 10 + apply_op(vy, 'cut'):02d}")
    print(foot)
    print("  Note: the full grid holds every number 00-99 exactly once.")


def show_root_10x10(root, ops_list):
    """Root Element 10x10 operations — ops applied to ROOT."""
    _print_10x10("Root Element 10x10 operations", root, set(ops_list),
                 "TRANSITION OPERATIONS")


def sep(ch='─'):
    print(ch * W)

def header(title):
    sep('═')
    print(f"  {title}")
    sep('═')


# ── Main Analysis ─────────────────────────────────────────────────────────────

def run(data_source, user_x_op=None, user_y_op=None):
    _SUPER_SRC.clear()
    # Accept pre-parsed list[list[int]] or raw iterable of strings
    if data_source and isinstance(data_source, list) and isinstance(data_source[0], list):
        rows = data_source
    else:
        rows = load_data(data_source)

    if not rows:
        print("ERROR: No data loaded.")
        return

    # Flag grid rows that don't match the grid's modal width. The grid body is
    # defined by POSITION, not by each row's own length: it runs from row 0
    # through the last row anywhere in the file with len >= 5 (live single-value
    # append rows after that point are normal continuation lines, not grid rows).
    # Using position rather than length means a badly-gapped grid row -- even one
    # cut down to 3-4 tokens -- still gets checked, instead of being mistaken for
    # a live append just because it's short. The single LAST grid row is exempt:
    # exactly one row per dataset reset is allowed to be a genuinely short
    # end-of-paste line (confirmed with the user at reset time), and it stays
    # short permanently even after results get appended below it -- re-flagging
    # it every round afterward would be noise, not a real anomaly. This doesn't
    # guess or auto-pad -- whitespace-split parsing can't tell where a missing
    # value belongs (a gap collapses just like a normal separator), so any real
    # fix requires human confirmation. This just makes sure a width mismatch is
    # never missed silently.
    _last_grid_i = max((i for i, _row in enumerate(rows) if len(_row) >= 5), default=None)
    if _last_grid_i is not None and _last_grid_i > 0:
        _check_idx = range(_last_grid_i)  # grid body up to (excl.) the exempt last grid row
        _width_counts = {}
        for _i in _check_idx:
            _w = len(rows[_i])
            _width_counts[_w] = _width_counts.get(_w, 0) + 1
        _modal_width = max(_width_counts, key=_width_counts.get)
        _mismatches = [_i + 1 for _i in _check_idx if len(rows[_i]) != _modal_width]
        if _mismatches:
            print(f"  ⚠ WARNING: {len(_mismatches)} row(s) don't match the modal width "
                  f"({_modal_width} cols): rows {_mismatches[:20]}"
                  f"{' ...' if len(_mismatches) > 20 else ''}")
            print("  Confirm with the user where each gap belongs before trusting this window.")

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
                if nxt == -1:
                    print(f"  {occurrence:>4}  Row {r+1:>3}, position {c+1:>2}"
                          f"   →   ??  (unreadable cell, skipped)")
                elif nxt is not None:
                    group_index.append(nxt)
                    print(f"  {occurrence:>4}  Row {r+1:>3}, position {c+1:>2}"
                          f"   →   {nxt:02d}")

    # ── Step 3 (silent compute): Root + Transition Operations ────────────────
    # Computed here, without printing yet, so the STRONG PREDICTIONS box
    # (Step "2b" below) can print BEFORE the Group Index Array/Chain Diagram/
    # Last-rows tree/tables, matching the mandated display order — see
    # feedback_output_format.md ("2026-07-08 addition — script now matches
    # the chat-relay order").
    sep('═')
    if not group_index:
        print(f"\n  {endpoint:02d} ==►► [ empty — endpoint appears only once ]")
        print("\n  Cannot continue: no Group Index Array found.")
        sep('═')
        print()
        return None, []

    root   = group_index[-1]
    rx, ry = root // 10, root % 10

    ops_list = []
    for i in range(len(group_index) - 1):
        a, b       = group_index[i], group_index[i + 1]
        ax, ay     = a // 10, a % 10
        bx, by     = b // 10, b % 10
        x_op, y_op = find_op(ax, bx), find_op(ay, by)
        ops_list.append((x_op, y_op))

    # ── Step 2b: EP/Root check + PREDICTION ANALYSIS + STRONG PREDICTIONS
    # box — printed FIRST (before any tables), per the mandated order ───────
    _last_top4, _last_scores = [], {}
    if len(ops_list) >= 1:
        show_prediction(endpoint, root, ops_list, group_index, rows=rows)
        _last_top4, _last_scores = build_strong_predictions(root, ops_list, group_index, endpoint, rows=rows)

    # ── Step 3: Group Index Array ─────────────────────────────────────────────
    arr_str = ' │ '.join(f'{n:02d}' for n in group_index)
    print(f"\n  {endpoint:02d} ==►► [ {arr_str} ]")
    print(f"\n  ROOT ELEMENT = {root:02d}   (x = {rx},  y = {ry})")
    sep('═')
    show_root_10x10(root, ops_list)
    sep('═')

    # ── Step 4: Transition Operations ────────────────────────────────────────
    # with the ROOT OPS table beside it (each step's ops applied to ROOT)
    left = ["TRANSITION OPERATIONS:", "", f"{'Step':<10}  {'x operation':<14}  {'y operation'}",
            "─" * 44]
    for i in range(len(group_index) - 1):
        a, b       = group_index[i], group_index[i + 1]
        x_op, y_op = ops_list[i]
        left.append(f"{a:02d} → {b:02d}     x:{x_op:<13}  y:{y_op}")
    left.append("─" * 44)
    right = _root_ops_table(root, ops_list, strong={v for v, *_ in _last_top4[:30]},
                            rec=[v for v, *_ in _last_top4[:3]])
    print()
    lw = max(len(l) for l in left) + 4
    for k in range(max(len(left), len(right))):
        l = left[k] if k < len(left) else ""
        r = right[k] if k < len(right) else ""
        print(f"  {l:<{lw}}{r}".rstrip())
    show_root_missing_combos(root, ops_list, strong={v for v, *_ in _last_top4[:30]},
                             rec=[v for v, *_ in _last_top4[:3]])
    sep('═')

    # ── Step 5: Chain Diagram ────────────────────────────────────────────────
    internal_pos, _ = find_root_positions(group_index, root)
    if len(ops_list) >= 1:
        show_chain_diagram(group_index, ops_list, root, internal_pos)

    # ── Step 5b: Last 3 rows of data grid ────────────────────────────────────
    show_last_rows_diagram(rows)
    show_next_op_after_last(rows)
    _kk_vals = show_kk_special_family(rows, merge_counts=kk_chain_unique_counts(group_index),
                                      final40=[v for v, _, _ in _last_top4[:40]])
    _RRR3_PREV['op'] = _rrr3_previous_op(rows)
    _RRR3_PREV['op2'] = _rrr3_previous_op(rows, back=2)
    _RRR3_PREV['flat'] = [v for row in rows for v in row if v >= 0]
    _kk_chain_vals = show_kk_chain_family(group_index, grid_ep=endpoint)
    _super_add("KK", _kk_vals or [])
    _super_add("KC", _kk_chain_vals or [])

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
        # ── Recommended pick callout (confidence tiered by top score, not just
        # rank) -- printed BEFORE the FINAL PREDICTIONS box (2026-08-08,
        # matches the chat-relay template order the user standardized on:
        # ★ RECOMMENDED first, then the box, not the reverse).
        top_score = top4[0][1] if top4 else 0
        if top_score >= 15:
            tier = "HIGH CONFIDENCE"
        elif top_score >= 8:
            tier = "MODERATE CONFIDENCE"
        else:
            tier = "LOW CONFIDENCE — weak signal this round"
        picks = ", ".join(f"{v:02d}" for v, _, _ in top4[:3])
        print()
        print(f"  ★ RECOMMENDED: {picks}  [{tier}]")

        print()
        hdr = f"EP={endpoint:02d}  Root={root:02d}  Trans={len(ops_list)}"
        print("  ╔══════════════════════════════════════════════════════════════╗")
        print(f"  ║  {hdr}  ──  FINAL PREDICTIONS (40){'':<{30 - len(hdr)}}║")
        print("  ╠══════════════════════════════════════════════════════════════╣")
        for rank, (val, score, reasons) in enumerate(top4, 1):
            seen_r = set()
            lbl_parts = []
            for r in reasons:
                key = r.split()[0]
                if key not in seen_r:
                    seen_r.add(key)
                    lbl_parts.append(key)
            marked = rank <= 16
            mark = "🔴" if marked else "  "
            rwidth = 34 if marked else 35
            reason_str = " + ".join(lbl_parts)[:rwidth]
            line = f"  ║{mark}#{rank:<2} →  {val:02d}   score={score:>2}   {reason_str:<{rwidth}}║"
            if marked:
                print(f"\033[91m{line}\033[0m")
            else:
                print(line)
        if structural:
            note = structural.strip()[:58]
            print(f"  ║  NOTE: {note:<54}║")
        print("  ╚══════════════════════════════════════════════════════════════╝")

        # ── TOP 10 PICKS, color-tiered (2026-07-31, user requested a finer
        # breakdown than the single 3-pick ★ RECOMMENDED line: "recommended
        # and best suitable... 10 top results... color code Red, Green,
        # Blue, Yellow"). Splits the top 10 of the SAME ranking above into
        # 4 bands by rank position (not a new signal or re-ranking) --
        # 🔴 ranks 1-3 (best), 🟢 4-6, 🔵 7-8, 🟡 9-10. Purely a display
        # regrouping of already-computed scores, same as the 3-column table.
        _top10 = top4[:10]
        _tier_color = {}
        for _i in range(len(_top10)):
            if _i < 3:
                _tier_color[_i] = "\U0001F534"  # red
            elif _i < 6:
                _tier_color[_i] = "\U0001F7E2"  # green
            elif _i < 8:
                _tier_color[_i] = "\U0001F535"  # blue
            else:
                _tier_color[_i] = "\U0001F7E1"  # yellow
        _t10_hdr = "  TOP 10 PICKS (\U0001F534=ranks 1-3, \U0001F7E2=4-6, \U0001F535=7-8, \U0001F7E1=9-10)"
        _t10_lines = []
        for _i, (_v, _s, _r) in enumerate(_top10):
            _seen_t = set()
            _t_parts = []
            for _rr in _r:
                _key = _rr.split()[0]
                if _key not in _seen_t:
                    _seen_t.add(_key)
                    _t_parts.append(_key)
            _t_reason = " + ".join(_t_parts)[:34]
            _t10_lines.append(f"  {_tier_color[_i]} #{_i + 1:<2} →  {_v:02d}   score={_s:>2}   {_t_reason}")
        _t10w = max([64, len(_t10_hdr)] + [len(l) for l in _t10_lines])
        print()
        print(f"  ┌{'─' * _t10w}┐")
        print(f"  │{_t10_hdr:<{_t10w}}│")
        print(f"  ├{'─' * _t10w}┤")
        for l in _t10_lines:
            print(f"  │{l:<{_t10w}}│")
        print(f"  └{'─' * _t10w}┘")

        # ── 4-column Rank/Val/Score summary table (added 2026-07-26 as
        # 3 columns, widened to 4 columns on 2026-07-30 alongside the
        # top-30->top-40 change so all 40 entries still fit in 10 rows):
        # compact side-by-side re-layout of the SAME top-40 ranking shown
        # in the FINAL PREDICTIONS box above (col1=#1-10, col2=#11-20,
        # col3=#21-30, col4=#31-40, row-major) -- no new data, just easier
        # to scan than one long vertical list with truncated reason text.
        # Previously built by hand in chat every round; now native script
        # output like the other boxes.
        _rv_cw = 11
        _rv_hdr = f"{'Rank Val Sc':^{_rv_cw}}"
        print()
        print(f"  ┌{'─' * _rv_cw}┬{'─' * _rv_cw}┬{'─' * _rv_cw}┬{'─' * _rv_cw}┐")
        print(f"  │{_rv_hdr}│{_rv_hdr}│{_rv_hdr}│{_rv_hdr}│")
        print(f"  ├{'─' * _rv_cw}┼{'─' * _rv_cw}┼{'─' * _rv_cw}┼{'─' * _rv_cw}┤")
        for _r in range(10):
            _cells = []
            for _c in range(4):
                _idx = _c * 10 + _r
                if _idx < len(top4):
                    _val, _score, _ = top4[_idx]
                    _cell = f"#{_idx + 1:<2} {_val:02d}  s{_score:02d}"
                else:
                    _cell = ""
                _cells.append(f"{_cell:^{_rv_cw}}")
            print(f"  │{_cells[0]}│{_cells[1]}│{_cells[2]}│{_cells[3]}│")
        print(f"  └{'─' * _rv_cw}┴{'─' * _rv_cw}┴{'─' * _rv_cw}┴{'─' * _rv_cw}┘")

        # ── MIDDLE 30 + TAIL 30 -- so all 100 candidates are visible ──────
        # somewhere (TOP 40 above + MIDDLE 30 + TAIL 30 = 100, no gaps).
        # Widened from top-30 to top-40 on 2026-07-30 (user request) --
        # MIDDLE shrank from ranks 31-70 (40 items) to ranks 41-70 (30 items)
        # to keep the three zones covering 0-99 with no gaps or overlap.
        # Same full 0-99 ranking used for "Rank #X of 100" in --result mode
        # (see show_result_analysis), so all three stay consistent. Uses
        # computed padding (not hand-counted) so the border always matches
        # content width exactly, regardless of text length.
        _all_ranked = sorted(range(100), key=lambda v: len(_pred_scores.get(v, [])), reverse=True)
        _middle40 = _all_ranked[40:70]
        _tail30 = _all_ranked[70:100]

        def _print_zone_box(title, values, start_rank):
            hdr_text = f"  EP={endpoint:02d}  Root={root:02d}  Trans={len(ops_list)}  --  {title}"
            body_lines = []
            for i, val in enumerate(values):
                zrank = start_rank + i
                zscore = len(_pred_scores.get(val, []))
                zreasons = _pred_scores.get(val, [])
                seen_z = set()
                zlbl_parts = []
                for r in zreasons:
                    key = r.split()[0]
                    if key not in seen_z:
                        seen_z.add(key)
                        zlbl_parts.append(key)
                zreason_str = (" + ".join(zlbl_parts) if zlbl_parts else "zero-signal")[:38]
                body_lines.append(f"  #{zrank:<3} ->  {val:02d}   score={zscore:>2}   {zreason_str}")
            # Two-pass: compute width from the LONGEST line (header or any
            # body row) before printing anything, so no row can overflow
            # the border regardless of how many signal labels it lists.
            w = max([64, len(hdr_text)] + [len(line) for line in body_lines])
            def _line(text=""):
                print(f"  │{text:<{w}}│")
            print()
            print(f"  ┌{'─' * w}┐")
            _line(hdr_text)
            print(f"  ├{'─' * w}┤")
            for line in body_lines:
                _line(line)
            print(f"  └{'─' * w}┘")

        _print_zone_box("MIDDLE 30 (ranks 41-70)", _middle40, 41)
        _print_zone_box("TAIL 30 (ranks 71-100, least likely)", _tail30, 71)

        # ── TOP 30 BY DECADE -- same top-30 values, grouped 00-09/10-19/.../90-99
        # for quick "is my number's decade in the list" scanning. Purely a
        # re-presentation of the same top-30 list above -- does not change
        # or add to it. Boxed (┌─┐/│ │/└─┘, two-pass width like the other
        # zone boxes) to match the MIDDLE 40/TAIL 30/ML CONFIDENCE style
        # instead of a bare dashed list (2026-07-08).
        _top30_vals = sorted(v for v, _, _ in top4)
        _decade_hdr = "  TOP 40 BY DECADE (ascending, same top-40 list above)"
        _decade_lines = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _in_decade = [v for v in _top30_vals if _lo <= v <= _hi]
            _label = f"{_lo:02d}-{_hi:02d}"
            _vals_str = ", ".join(f"{v:02d}" for v in _in_decade) if _in_decade else "--"
            _decade_lines.append(f"  {_label} : {_vals_str}")
        _dw = max([64, len(_decade_hdr)] + [len(l) for l in _decade_lines])
        print()
        print(f"  ┌{'─' * _dw}┐")
        print(f"  │{_decade_hdr:<{_dw}}│")
        print(f"  ├{'─' * _dw}┤")
        for l in _decade_lines:
            print(f"  │{l:<{_dw}}│")
        print(f"  └{'─' * _dw}┘")

        # ── TOP 30 BY FAMILY -- the SAME top-30 values as above, regrouped by
        # cut-pair family instead of by decade (one row per family, only the
        # top-30 members shown -- not the full 8-10 member family). Display
        # only / reference, not a ranked or scored claim -- backtested
        # 2026-07-07: family-covers-result rate (92.0%) is NOT better than a
        # random 30-number list (94.2%), so this adds no prediction signal.
        # Boxed for the same reason as TOP 30 BY DECADE above.
        # Each row = top-30 members of that family PLUS the single-digit-cut
        # sibling(s) of each present member (2026-07-25, corrected per user:
        # "62 is there but also add 67" -- i.e. one-hop cut-tens/cut-units
        # neighbor of a value already in top-30, NOT the full 8-10 member
        # family and NOT a separate giant list). Bounded per-row, not
        # universe-wide -- replaces the earlier FAMILY-EXTENDED LIST box
        # (reverted, it expanded to the full family regardless of which
        # members were reachable, ballooning to 100/100 some rounds).
        _family_hdr = "  TOP 40 BY FAMILY (+ full cut-cycle closure of each value present)"
        _all_extended = family_cycle_closure(_top30_vals)
        _family_lines = []
        for _fam in FAMILY_ORDER:
            _shown = sorted(v for v in _all_extended if FAMILY_MAP[v] == _fam)
            _vals_str = ", ".join(f"{v:02d}" for v in _shown) if _shown else "--"
            _family_lines.append(f"  {_fam:<16}: {_vals_str}")
        _fw = max([64, len(_family_hdr)] + [len(l) for l in _family_lines])
        print()
        print(f"  ┌{'─' * _fw}┐")
        print(f"  │{_family_hdr:<{_fw}}│")
        print(f"  ├{'─' * _fw}┤")
        for l in _family_lines:
            print(f"  │{l:<{_fw}}│")
        print(f"  └{'─' * _fw}┘")

        # ── Plain TOP 30 BY FAMILY, no cut-cycle closure (2026-07-30, user
        # asked for this as a separate table alongside the closure version
        # above): same 12-row FAMILY_ORDER layout, but only the raw top-30
        # values themselves -- no sibling expansion. This is the box that
        # existed before cut-cycle closure was added on 2026-07-25; kept
        # here permanently as its own display, not a replacement.
        _family_plain_hdr = "  TOP 40 BY FAMILY (top-40 only, no closure)"
        _family_plain_lines = []
        for _fam in FAMILY_ORDER:
            _shown = sorted(v for v in _top30_vals if FAMILY_MAP[v] == _fam)
            _vals_str = ", ".join(f"{v:02d}" for v in _shown) if _shown else "--"
            _family_plain_lines.append(f"  {_fam:<16}: {_vals_str}")
        _fpw = max([64, len(_family_plain_hdr)] + [len(l) for l in _family_plain_lines])
        print()
        print(f"  ┌{'─' * _fpw}┐")
        print(f"  │{_family_plain_hdr:<{_fpw}}│")
        print(f"  ├{'─' * _fpw}┤")
        for l in _family_plain_lines:
            print(f"  │{l:<{_fpw}}│")
        print(f"  └{'─' * _fpw}┘")

        # ── Same expanded list (top-30 + siblings), laid out in ascending
        # decade rows instead of by family -- easier to scan "is my number
        # in here" (2026-07-25, user requested "sequence order 10 rows").
        # Widening this to top-40/50/70 basis was tested live 2026-07-26 and
        # REJECTED: top-40 -> 69/100, top-50 -> 78/100, top-70 -> 92/100 --
        # cut-cycle closure inflates fast because each family only has 4-10
        # members, so a handful of extra starting points closes most
        # families. 92/100 has essentially the same near-zero discriminating
        # power as the 100/100 FAMILY-EXTENDED box already reverted earlier
        # this project for that exact reason. Kept at top-30 basis.
        # Red-circle marks values that are directly in the top-30 (same visual
        # language as the FINAL PREDICTIONS box) so it's clear at a glance
        # which numbers here were actually predicted vs. added only via
        # family cut-cycle closure (2026-07-29, user requested).
        _top30_set = set(_top30_vals)
        _ext_dec_hdr = f"  TOP 40 + SIBLINGS BY DECADE ({len(_all_extended)} numbers, \U0001F534=top-40, ascending)"
        _ext_dec_lines = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _in_decade = sorted(v for v in _all_extended if _lo <= v <= _hi)
            _label = f"{_lo:02d}-{_hi:02d}"
            _vals_str = ", ".join(
                f"\U0001F534{v:02d}" if v in _top30_set else f"{v:02d}" for v in _in_decade
            ) if _in_decade else "--"
            _ext_dec_lines.append(f"  {_label} : {_vals_str}")
        _edw = max([64, len(_ext_dec_hdr)] + [len(l) for l in _ext_dec_lines])
        print()
        print(f"  ┌{'─' * _edw}┐")
        print(f"  │{_ext_dec_hdr:<{_edw}}│")
        print(f"  ├{'─' * _edw}┤")
        for l in _ext_dec_lines:
            print(f"  │{l:<{_edw}}│")
        print(f"  └{'─' * _edw}┘")

        # ── RECOMMENDED BY DECADE / BY FAMILY, score-threshold (2026-08-02,
        # replaces the ALL-100 boxes -- user correctly called those useless,
        # "no use, you gave me 0-100"). This is the honest version of "no
        # fixed range": instead of a hard top-40 COUNT cutoff (which silently
        # drops any value tied with the #40 score), include every value
        # whose score is >= the #40 cutoff score. Size floats round to round
        # (measured range 40-55 over 41 backtested rounds here) instead of
        # being forced to exactly 40. Backtested real hit rate: 39.0%
        # (16/41) vs 34.1% (14/41) for the old fixed-40 cutoff -- a genuine
        # improvement from not discarding ties, NOT a "no-miss" claim. This
        # table still misses in roughly 6 of 10 rounds; only the full 100-
        # value universe has zero misses, and that was already shown to be
        # useless. Does not change build_strong_predictions() or top4 --
        # display-only, reads the same _pred_scores dict.
        _rec_cutoff_score = top4[-1][1] if top4 else 0
        _rec_set = sorted(v for v in range(100) if len(_pred_scores.get(v, [])) >= _rec_cutoff_score)

        def _val_tag(v):
            return f"{v:02d}"

        def _wrapped_rows(label, members, per_line=8):
            _indent = " " * len(f"  {label} : ")
            _rows = []
            for i in range(0, len(members), per_line):
                _chunk = ", ".join(_val_tag(v) for v in members[i:i + per_line])
                _prefix = f"  {label} : " if i == 0 else _indent
                _rows.append(f"{_prefix}{_chunk}")
            return _rows if members else [f"  {label} : --"]

        def _print_box(hdr, rows):
            _w = max([64, len(hdr)] + [len(l) for l in rows])
            print()
            print(f"  ┌{'─' * _w}┐")
            print(f"  │{hdr:<{_w}}│")
            print(f"  ├{'─' * _w}┤")
            for l in rows:
                print(f"  │{l:<{_w}}│")
            print(f"  └{'─' * _w}┘")

        _rec_dec_hdr = (f"  RECOMMENDED BY DECADE ({len(_rec_set)} values, score>={_rec_cutoff_score}, "
                         f"no fixed range)")
        _rec_dec_lines = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _label = f"{_lo:02d}-{_hi:02d}"
            _in_decade = [v for v in _rec_set if _lo <= v <= _hi]
            _rec_dec_lines.extend(_wrapped_rows(_label, _in_decade))
        _print_box(_rec_dec_hdr, _rec_dec_lines)

        _rec_fam_hdr = (f"  RECOMMENDED BY FAMILY ({len(_rec_set)} values, score>={_rec_cutoff_score}, "
                        f"no fixed range)")
        _rec_fam_lines = []
        for _fam in FAMILY_ORDER:
            _members = [v for v in _rec_set if FAMILY_MAP[v] == _fam]
            _rec_fam_lines.extend(_wrapped_rows(f"{_fam:<16}", _members))
        _print_box(_rec_fam_hdr, _rec_fam_lines)

        # ── ML CONFIDENCE (informational secondary signal only) ──────────
        # NOT used to rank the FINAL PREDICTIONS above -- backtested
        # accuracy of this model is lower than the rule-based system (see
        # feedback_script_changes.md, "ML approach tested"). Shown for
        # transparency/completeness only. Moved to print LAST (2026-08-08,
        # after RECOMMENDED BY FAMILY) to match the chat-relay template
        # order the user standardized on -- was previously right after
        # TAIL 30, ahead of the DECADE/FAMILY/SIBLINGS/RECOMMENDED boxes.
        from ml_features import ml_confidence_ranking
        _ml_ranked = ml_confidence_ranking(_last_scores, len(ops_list), len(_last_scores))
        if _ml_ranked:
            _mw = 64
            def _mline(text=""):
                print(f"  │{text:<{_mw}}│")
            print()
            print(f"  ┌{'─' * _mw}┐")
            _mline("  ML CONFIDENCE (secondary, informational only)")
            print(f"  ├{'─' * _mw}┤")
            for i, (val, prob) in enumerate(_ml_ranked[:3], 1):
                _mline(f"  #{i}  ->  {val:02d}   ML probability: {100*prob:5.1f}%")
            _mline("  NOTE: this model's backtested accuracy is LOWER than the")
            _mline("  rule-based ranking above -- shown for transparency, not")
            _mline("  used to determine the FINAL PREDICTIONS or RECOMMENDED pick.")
            print(f"  └{'─' * _mw}┘")

        # ── MERGE: Special family & Recommended (printed very last) ──────
        # Unique union of RECOMMENDED BY FAMILY, KK SPECIAL FAMILY RESULT and
        # KK CHAIN FAMILY RESULT. Display only. Each value is tagged with the
        # letters of every source it came from: R = Recommended, K = KK,
        # C = Chain (e.g. 06RKC = in all three).
        _src_rec   = set(_rec_set)
        _src_kk    = set(_kk_vals)
        _src_chain = set(_kk_chain_vals)
        _merged    = sorted(_src_rec | _src_kk | _src_chain)
        def _mtag(v):
            return (('R' if v in _src_rec else '') + ('K' if v in _src_kk else '')
                    + ('C' if v in _src_chain else ''))
        _merge_hdr = (f"  MERGE: Special family & Recommended ({len(_merged)} unique values)")
        _merge_lines = []
        for _decade in range(10):
            _lo, _hi = _decade * 10, _decade * 10 + 9
            _in = [v for v in _merged if _lo <= v <= _hi]
            _cells = "  ".join(f"{v:02d}{_mtag(v):<3}" for v in _in).rstrip() if _in else "--"
            _merge_lines.append(f"  {_lo:02d}-{_hi:02d} : {_cells}")
        # TOTAL MERGE also adds each value's reverse (xy → yx) if missing,
        # e.g. 29 present → 92 added.
        _rev_added = sorted({(v % 10) * 10 + v // 10 for v in _merged} - set(_merged))
        _total     = sorted(set(_merged) | set(_rev_added))
        _merge_lines.append("")
        _merge_lines.extend(_wrapped_rows(f"TOTAL MERGE ({len(_total)})", _total, per_line=10))
        _merge_lines.append("")
        _merge_lines.extend(_wrapped_rows(f"REVERSE ADDED ({len(_rev_added)})", _rev_added, per_line=10))
        _merge_lines.append("")
        _all3 = _src_rec & _src_kk & _src_chain
        _merge_lines.append(f"  R = Recommended ({len(_src_rec)})   K = KK ({len(_src_kk)})   "
                            f"C = Chain ({len(_src_chain)})   in all 3 = {len(_all3)}  ")
        _print_box(_merge_hdr, _merge_lines)
    show_super_special(_last_top4, _last_scores)
    show_power_box()
    # the whole RRR / 3RRR frame once more at the very end of the page
    # (user's screenshot, 2026-10-08 evening)
    _rrr_end = _RRR3_PREV.pop('frame', None)
    if _rrr_end:
        print()
        print("\n".join(_rrr_end))
    show_three_box()
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
