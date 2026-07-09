#!/usr/bin/env python3
"""
train_ml_confidence_model.py
------------------------------
Trains the ML confidence model on ALL available historical data (579
rounds across 4 dataset windows) and saves it to disk for fast reuse at
runtime by DataProcessing.py's informational "ML CONFIDENCE" display.

This model is NOT used to rank the actual FINAL PREDICTIONS -- backtested
accuracy showed it underperforms the rule-based system (see
project_datascinceanal_ml_experiment memory / feedback_script_changes.md,
"ML approach tested" writeup). It's trained on all data (not held out)
because its only purpose here is to produce a labeled, informational
confidence score alongside the real predictions -- there is no accuracy
claim being made that requires a held-out test set.
"""
import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

df = pd.read_csv("ml_training_data.csv")
feature_cols = [c for c in df.columns if c.startswith("fam_")] + ["n_trans", "table_size", "total_score"]

X, y = df[feature_cols], df["label"]
print(f"Training on {len(df)//100} rounds ({y.sum()} positives / {len(y)} rows)")

clf = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.05, max_depth=4,
    class_weight="balanced", random_state=42,
)
clf.fit(X, y)

joblib.dump({"model": clf, "feature_cols": feature_cols}, "ml_confidence_model.joblib")
print("Saved ml_confidence_model.joblib")
