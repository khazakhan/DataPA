#!/usr/bin/env python3
"""
evaluate_ml_cv.py
------------------
3-fold cross-WINDOW evaluation: each of the 3 historical windows takes a
turn as the held-out test set, trained on the other two. This isn't a
strict walk-forward (test window is sometimes chronologically BEFORE a
training window), but it answers a narrower question first: with more
training data pooled from 2 windows, can either model type beat the
matching rule-based baseline on the 3rd, regardless of the direction of
time? If the answer is still no, the reason is model/feature capacity,
not "not enough time-ordered history yet".
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from DataProcessing import load_data, build_strong_predictions
from ml_features import get_scores, split_grid_and_results

df = pd.read_csv("ml_training_data.csv")
feature_cols = [c for c in df.columns if c.startswith("fam_")] + ["n_trans", "table_size", "total_score"]

WINDOWS = ["d341_446", "d447_592", "d593_818"]
BACKUP_FILES = {
    "d341_446": "temp_data_d341_d446_backup.txt",
    "d447_592": "temp_data_d447_d592_backup.txt",
    "d593_818": "temp_data_d593_d818_backup.txt",
}


def eval_ranking(test_df, proba_col="proba"):
    top1 = top3 = top30 = 0
    n = 0
    for rnd, g in test_df.groupby("round_idx"):
        n += 1
        g_sorted = g.sort_values(proba_col, ascending=False)
        actual_row = g[g["label"] == 1]
        if actual_row.empty:
            continue
        actual_val = actual_row["candidate"].iloc[0]
        ranked_vals = g_sorted["candidate"].tolist()
        rank = ranked_vals.index(actual_val) + 1
        top1 += rank <= 1
        top3 += rank <= 3
        top30 += rank <= 30
    return top1, top3, top30, n


def rule_based_baseline(window):
    rows = load_data(open(BACKUP_FILES[window]))
    grid, results = split_grid_and_results(rows)
    top1 = top3 = top30 = n = 0
    for k in range(len(results)):
        partial = grid + [[v] for v in results[:k]]
        ctx, scores = get_scores(partial)
        if ctx is None:
            continue
        top4, _ = build_strong_predictions(ctx["root"], ctx["ops_list"], ctx["group_index"], ctx["endpoint"], rows=partial)
        actual = results[k]
        ranked_vals = [v for v, _, _ in top4]
        n += 1
        top1 += len(ranked_vals) >= 1 and ranked_vals[0] == actual
        top3 += actual in ranked_vals[:3]
        top30 += actual in ranked_vals[:30]
    return top1, top3, top30, n


print(f"{'fold(test)':12s} {'model':10s} {'top1':>10s} {'top3':>10s} {'top30':>12s}")
for test_w in WINDOWS:
    train_ws = [w for w in WINDOWS if w != test_w]
    train_df = df[df["window"].isin(train_ws)]
    test_df = df[df["window"] == test_w].copy()
    X_train, y_train = train_df[feature_cols], train_df["label"]
    X_test = test_df[feature_cols]

    # GBM
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_depth=4,
                                          class_weight="balanced", random_state=42)
    clf.fit(X_train, y_train)
    test_df["proba"] = clf.predict_proba(X_test)[:, 1]
    t1, t3, t30, n = eval_ranking(test_df)
    print(f"{test_w:12s} {'GBM':10s} {t1}/{n} ({100*t1/n:.1f}%)   {t3}/{n} ({100*t3/n:.1f}%)   {t30}/{n} ({100*t30/n:.1f}%)")

    # Logistic Regression (scaled)
    scaler = StandardScaler()
    Xs_train = scaler.fit_transform(X_train)
    Xs_test = scaler.transform(X_test)
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", C=0.5)
    lr.fit(Xs_train, y_train)
    test_df["proba"] = lr.predict_proba(Xs_test)[:, 1]
    t1, t3, t30, n = eval_ranking(test_df)
    print(f"{test_w:12s} {'LogReg':10s} {t1}/{n} ({100*t1/n:.1f}%)   {t3}/{n} ({100*t3/n:.1f}%)   {t30}/{n} ({100*t30/n:.1f}%)")

    # Rule-based (true production system) on the same test window
    t1, t3, t30, n = rule_based_baseline(test_w)
    print(f"{test_w:12s} {'RuleBased':10s} {t1}/{n} ({100*t1/n:.1f}%)   {t3}/{n} ({100*t3/n:.1f}%)   {t30}/{n} ({100*t30/n:.1f}%)")
    print()
