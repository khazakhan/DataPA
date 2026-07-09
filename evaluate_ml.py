#!/usr/bin/env python3
"""
evaluate_ml.py
--------------
Train HistGradientBoostingClassifier on the two OLDER dataset windows
(d341_446, d447_592 -- 251 rounds), evaluate on the NEWER window
(d593_818 -- 227 rounds), which is strictly chronologically later so
this is a genuine walk-forward holdout, not a random shuffle-split.

Reports top-1 / top-3 / top-30 accuracy for the ML ranking, alongside
the REAL rule-based system's top-1 / top-30 accuracy on the exact same
227 held-out rounds, computed by re-running the actual production
build_strong_predictions() (not an approximation) -- for an apples to
apples comparison.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from DataProcessing import load_data
from ml_features import get_scores, split_grid_and_results

df = pd.read_csv("ml_training_data.csv")

feature_cols = [c for c in df.columns if c.startswith("fam_")] + ["n_trans", "table_size", "total_score"]

train_df = df[df["window"].isin(["d341_446", "d447_592"])]
test_df  = df[df["window"] == "d593_818"]

X_train, y_train = train_df[feature_cols], train_df["label"]
X_test,  y_test  = test_df[feature_cols],  test_df["label"]

print(f"train rounds: {len(train_df)//100}  ({y_train.sum()} positives / {len(y_train)} rows)")
print(f"test  rounds: {len(test_df)//100}  ({y_test.sum()} positives / {len(y_test)} rows)")

clf = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.05, max_depth=4,
    class_weight="balanced", random_state=42,
)
clf.fit(X_train, y_train)

proba = clf.predict_proba(X_test)[:, 1]
test_df = test_df.copy()
test_df["proba"] = proba

ml_top1 = ml_top3 = ml_top30 = 0
n_rounds = 0
for rnd, g in test_df.groupby("round_idx"):
    n_rounds += 1
    g_sorted = g.sort_values("proba", ascending=False)
    actual_row = g[g["label"] == 1]
    if actual_row.empty:
        continue  # shouldn't happen -- every round has exactly one true candidate
    actual_val = actual_row["candidate"].iloc[0]
    ranked_vals = g_sorted["candidate"].tolist()
    rank = ranked_vals.index(actual_val) + 1
    if rank <= 1:
        ml_top1 += 1
    if rank <= 3:
        ml_top3 += 1
    if rank <= 30:
        ml_top30 += 1

print()
print("=== ML model (HistGradientBoosting), held-out window d593-818 ===")
print(f"  top-1  : {ml_top1}/{n_rounds}  ({100*ml_top1/n_rounds:.1f}%)")
print(f"  top-3  : {ml_top3}/{n_rounds}  ({100*ml_top3/n_rounds:.1f}%)")
print(f"  top-30 : {ml_top30}/{n_rounds}  ({100*ml_top30/n_rounds:.1f}%)")

# ---- Real rule-based baseline on the SAME held-out rounds ----
rows = load_data(open("temp_data_d593_d818_backup.txt"))
grid, results = split_grid_and_results(rows)

rb_top1 = rb_top3 = rb_top30 = 0
n_rb = 0
for k in range(len(results)):
    partial = grid + [[v] for v in results[:k]]
    ctx, scores = get_scores(partial)
    if ctx is None:
        continue
    from DataProcessing import build_strong_predictions
    top4, _ = build_strong_predictions(ctx["root"], ctx["ops_list"], ctx["group_index"], ctx["endpoint"], rows=partial)
    actual = results[k]
    ranked_vals = [v for v, _, _ in top4]
    n_rb += 1
    if len(ranked_vals) >= 1 and ranked_vals[0] == actual:
        rb_top1 += 1
    if actual in ranked_vals[:3]:
        rb_top3 += 1
    if actual in ranked_vals[:30]:
        rb_top30 += 1

print()
print("=== Rule-based system (current production), SAME held-out window ===")
print(f"  top-1  : {rb_top1}/{n_rb}  ({100*rb_top1/n_rb:.1f}%)")
print(f"  top-3  : {rb_top3}/{n_rb}  ({100*rb_top3/n_rb:.1f}%)")
print(f"  top-30 : {rb_top30}/{n_rb}  ({100*rb_top30/n_rb:.1f}%)")

print()
print("=== Feature importances (top 15) ===")
importances = clf.feature_importances_ if hasattr(clf, "feature_importances_") else None
if importances is None:
    # HistGradientBoostingClassifier has no feature_importances_; use permutation importance instead
    from sklearn.inspection import permutation_importance
    r = permutation_importance(clf, X_test, y_test, n_repeats=5, random_state=42, scoring="roc_auc")
    order = np.argsort(r.importances_mean)[::-1][:15]
    for i in order:
        print(f"  {feature_cols[i]:30s}  {r.importances_mean[i]:.5f}")
