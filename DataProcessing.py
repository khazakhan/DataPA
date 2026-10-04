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
    iw = max(len(l) for l in body) + 2
    return ([f"  {m}┏{'━' * iw}┓{rst}"]
            + [f"  {m}┃{rst} {l:<{iw - 2}} {m}┃{rst}" for l in body]
            + [f"  {m}┗{'━' * iw}┛{rst}"])


# RRR live record (results the user gave one by one after each declaration,
# 2026-10-03): the only change that beat chance is the running value's tens
# digit getting cut. Update these counts when more results are recorded.
RRR_LIVE = {
    'results': 211, 'tens_cut': 47, 'either_decade': 68,
    'table_rounds': 201, 'table_hits': 27, 'table_chance': 20, 'declared': 166, 'declared_hits': 5,
}


def _rrr_declared(grid_ep, last_x_op):
    """RRR DECLARED lines — display only. From the running value (grid EP):
    the tens-cut decade, a 2nd decade (tens moved by the chain's last x op,
    sign flipped) and one number (cut / c-1)."""
    t, u  = grid_ep // 10, grid_ep % 10
    d1    = cut(t)
    L     = RRR_LIVE
    lines = [f"  RRR DECLARED  (running value = {grid_ep:02d})   — corrected from {L['results']} recorded results",
             f"  ★ TENS-CUT DECADE   {d1}0 – {d1}9   {'tens digit cut':<28}"
             f"recorded {L['tens_cut']} of {L['results']} = {L['tens_cut'] / L['results']:.0%}  (chance 10%)"]
    if last_x_op is not None:
        d2 = apply_op(t, SIGN_FLIP[last_x_op])
        if d2 != d1:
            lines.append(f"    2nd DECADE        {d2}0 – {d2}9   {'tens by LAST x op, flipped':<28}"
                         f"either decade {L['either_decade']} of {L['results']} = "
                         f"{L['either_decade'] / L['results']:.0%}  (chance 19%)")
    num = d1 * 10 + apply_op(u, 'cut-1')
    lines.append(f"    DECLARED NUMBER   {num:02d}        {f'cut / c-1 on {grid_ep:02d}':<28}"
                 f"single number {L['declared_hits']} of {L['declared']}  (chance about 1 in 100)")
    return lines


def _rrr_box(sequence, entries, ep, pos_prefix, grid_ep=None):
    """RRR table — display only. Every WIN - WIN row (plus the chain's own
    last step, marked LAST) gives a next operation by the RRR rule, applied
    to the EP as xy and yx. With the running value (grid_ep) it also prints
    the RRR DECLARED lines and stars (★) table numbers in the tens-cut decade."""
    src = [(pos, a, b, x_op, y_op, '') for pos, a, b, x_op, y_op, _ in entries]
    a, b = sequence[-2], sequence[-1]
    last_x_op = None
    if a >= 0 and b >= 0:
        lx, ly = find_op(a // 10, b // 10), find_op(a % 10, b % 10)
        if '?' not in (lx, ly):
            last_x_op = lx
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
    for pos, a, b, x_op, y_op, mark in src:
        nx, ny   = rrr_next_op(x_op, y_op)
        xy, yx   = compute_variants(ep, nx, ny)[:2]
        nxa, nya = OP_ABBREV[nx], OP_ABBREV[ny]
        tag      = f"[{pos_prefix}{pos}]{mark}"
        body.append(f"  {tag:<12} {a:02d} → {b:02d}   {OP_ABBREV[x_op]:<6} {OP_ABBREV[y_op]:<6} →  "
                    f"{nxa:<6} {nya:<6}  " + f"{xy:02d}{star(xy)}({nxa}/{nya})".ljust(KW)
                    + f"{yx:02d}{star(yx)}({nya}/{nxa})".ljust(KW))
    body += ['─' * len(head),
             "  new x = old y, cut switched + sign flipped   |   new y = old x, cut switched, one step down",
             "  LAST = the chain's own last step.  Backtest (57,662 positions): table hit 6.42% vs 6.44% chance.",
             f"  Live record: table hit {RRR_LIVE['table_hits']} of {RRR_LIVE['table_rounds']} rounds (about {RRR_LIVE['table_chance']} expected by chance)."]
    if live:
        body += ['─' * len(head)] + _rrr_declared(grid_ep, last_x_op) + ["  ★ in the table = number inside the tens-cut decade"]
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
            print("\n".join(_rrr_box(sequence, entries, ep, pos_prefix, grid_ep)))
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
        print("\n".join(_rrr_box(sequence, entries, ep, pos_prefix, grid_ep)))

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
