#!/usr/bin/env python3
"""
ml_features.py
---------------
Silent (no-print) re-implementation of DataProcessing.run()'s steps 1-4
(endpoint / group_index / root / ops_list), so we can call the existing,
already-validated build_strong_predictions() signal engine in a tight
walk-forward loop without capturing stdout.

Returns None from compute_context() whenever the real run() would have
bailed out (empty group_index, or fewer than 1 transition) -- callers
should skip that round.
"""

from DataProcessing import get_next_number, find_op, build_strong_predictions

# Same canonical signal-family grouping used in ablation.py, so raw
# high-cardinality labels (e.g. "repeat-pair Ops[5, 12] xy", "Rule9-node72")
# collapse into a small, stable, reusable set of ML feature columns.
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
    'Root-end-only': ['Root end-only arrive'],
    'RootOpClose': ['RootOpClose-1D-inchain'],
    'RootOpRepeat': ['RootOpRepeat-next'],
    'ArrOp-elsewhere-next': ['ArrOp-elsewhere-next'],
    'Rule9': [f'Rule9-node{s:02d}' for s in range(100)],
    'Rule10': [f'Rule10-node{s:02d}' for s in range(100)],
    'Rule11': [f'Rule11-node{s:02d}' for s in range(100)],
    'repeat-pair': ['repeat-pair'],
    # Digit-transform + TableProx + CompOp + Obs1 are permanently filtered
    # inside build_strong_predictions() (_ablated_prefixes) so in practice
    # they never appear in scores -- families kept here only as a safety net
    # in case that filter list ever shrinks.
    'CutBoth': ['CutBoth'], 'CbRev': ['CbRev'], 'Reverse': ['Reverse'],
    'CutUnits': ['CutUnits'], 'CutTens': ['CutTens'], 'PredNeighbor': ['PredNeighbor'],
    'TableProx': ['TableProx'],
}

_FAMILY_LOOKUP = [(base, fam) for fam, bases in FAMILIES.items() for base in bases]
# Longest base first, so more specific prefixes win when bases overlap.
_FAMILY_LOOKUP.sort(key=lambda t: -len(t[0]))


def canonicalize_signal(label):
    """Map a raw signal-contribution label to its stable family name.
    Returns None if no known family prefix matches (should not happen if
    FAMILIES is kept in sync with build_strong_predictions())."""
    for base, fam in _FAMILY_LOOKUP:
        if label.startswith(base):
            return fam
    return None


def compute_context(rows):
    """Replicate run() steps 1-4: endpoint, group_index, root, ops_list.

    rows: list[list[int]] -- the grid *plus* any appended single-value
    result rows available at prediction time (each a length-1 list).
    Returns dict with keys endpoint, root, rx, ry, ops_list, group_index,
    or None if the chain can't be built (mirrors run()'s early-return).
    """
    if not rows:
        return None

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
    rx, ry = root // 10, root % 10

    ops_list = []
    for i in range(len(group_index) - 1):
        a, b = group_index[i], group_index[i + 1]
        ax, ay = a // 10, a % 10
        bx, by = b // 10, b % 10
        x_op, y_op = find_op(ax, bx), find_op(ay, by)
        ops_list.append((x_op, y_op))

    if len(ops_list) < 1:
        return None

    return {
        "endpoint": endpoint,
        "root": root,
        "rx": rx,
        "ry": ry,
        "ops_list": ops_list,
        "group_index": group_index,
    }


def split_grid_and_results(rows):
    """Split a loaded file's rows into (grid_rows, results) by finding the
    longest trailing run of single-value rows -- robust to grid rows that
    have fewer than 7 tokens (e.g. masked '**' cells or historical quirks)."""
    i = len(rows)
    while i > 0 and len(rows[i - 1]) == 1:
        i -= 1
    grid = rows[:i]
    results = [r[0] for r in rows[i:]]
    return grid, results


def get_scores(rows):
    """Return (context, scores_dict) for the round defined by `rows`,
    or (None, None) if the chain can't be built. scores_dict maps
    candidate value (0-99) -> list of signal-label strings, exactly as
    build_strong_predictions() computes them for the live script."""
    ctx = compute_context(rows)
    if ctx is None:
        return None, None
    _, scores = build_strong_predictions(
        ctx["root"], ctx["ops_list"], ctx["group_index"],
        ctx["endpoint"], rows=rows,
    )
    return ctx, scores


FAMILY_NAMES = sorted(FAMILIES.keys())
_ML_MODEL_PATH = "ml_confidence_model.joblib"
_ml_model_cache = None


def _load_ml_model():
    global _ml_model_cache
    if _ml_model_cache is not None:
        return _ml_model_cache
    import os
    if not os.path.exists(_ML_MODEL_PATH):
        return None
    try:
        import joblib
        _ml_model_cache = joblib.load(_ML_MODEL_PATH)
    except Exception:
        return None
    return _ml_model_cache


def ml_confidence_ranking(scores, n_trans, table_size):
    """Informational-only secondary ranking from the trained ML confidence
    model (see train_ml_confidence_model.py). NOT used to build the real
    FINAL PREDICTIONS -- backtested accuracy is lower than the rule-based
    system (see feedback_script_changes.md, "ML approach tested"). Returns
    a list of (candidate, probability) sorted descending, or None if the
    model file isn't available."""
    bundle = _load_ml_model()
    if bundle is None:
        return None
    model, feature_cols = bundle["model"], bundle["feature_cols"]

    rows_feat = []
    for cand in range(100):
        labels = scores.get(cand, [])
        fam_counts = {fam: 0 for fam in FAMILY_NAMES}
        for lbl in labels:
            fam = canonicalize_signal(lbl)
            if fam:
                fam_counts[fam] += 1
        feat = {f"fam_{f}": fam_counts[f] for f in FAMILY_NAMES}
        feat["n_trans"] = n_trans
        feat["table_size"] = table_size
        feat["total_score"] = len(labels)
        rows_feat.append(feat)

    import pandas as pd
    X = pd.DataFrame(rows_feat)[feature_cols]
    proba = model.predict_proba(X)[:, 1]
    ranked = sorted(zip(range(100), proba), key=lambda t: -t[1])
    return ranked
