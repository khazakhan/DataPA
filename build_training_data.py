#!/usr/bin/env python3
"""
build_training_data.py
-----------------------
Walk-forward feature extraction across every historical dataset window.
For each round, uses ONLY the grid + results available strictly before
that round (no leakage) to compute the same signal set the live script
uses, then emits one training row per candidate value 0-99:
    window, round_idx, candidate, <family feature counts...>, table_size,
    n_trans, is_type_b, label (1 if candidate == actual result)

Windows are processed in chronological order so a simple prefix/suffix
split by window boundary gives a strictly-time-ordered train/test split
with zero leakage (each window came strictly after the previous one).
"""
import csv
from DataProcessing import load_data
from ml_features import get_scores, split_grid_and_results, FAMILIES, canonicalize_signal

WINDOWS = [
    ("d341_446", "temp_data_d341_d446_backup.txt"),
    ("d447_592", "temp_data_d447_d592_backup.txt"),
    ("d593_818", "temp_data_d593_d818_backup.txt"),
    ("d819_live", "temp_data.txt"),
]

FAMILY_NAMES = sorted(FAMILIES.keys())


def extract_window(window_name, fname):
    rows = load_data(open(fname))
    grid, results = split_grid_and_results(rows)
    out = []
    skipped = 0
    for k in range(len(results)):
        partial = grid + [[v] for v in results[:k]]
        ctx, scores = get_scores(partial)
        if ctx is None:
            skipped += 1
            continue
        actual = results[k]
        n_trans = len(ctx["ops_list"])
        # table size (10-C-T) -- unique candidates that have ANY signal at all
        # is a reasonable proxy for "reachable set size" used elsewhere
        table_size = len(scores)
        for cand in range(100):
            labels = scores.get(cand, [])
            fam_counts = {fam: 0 for fam in FAMILY_NAMES}
            for lbl in labels:
                fam = canonicalize_signal(lbl)
                if fam:
                    fam_counts[fam] += 1
            row = {
                "window": window_name,
                "round_idx": k,
                "candidate": cand,
                "n_trans": n_trans,
                "table_size": table_size,
                "total_score": len(labels),
                "label": 1 if cand == actual else 0,
            }
            row.update({f"fam_{f}": fam_counts[f] for f in FAMILY_NAMES})
            out.append(row)
    return out, skipped


def main():
    all_rows = []
    for wname, fname in WINDOWS:
        rows, skipped = extract_window(wname, fname)
        print(f"{wname}: {len(rows)//100} rounds usable, {skipped} skipped (no chain)")
        all_rows.extend(rows)

    fieldnames = list(all_rows[0].keys())
    with open("ml_training_data.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows ({len(all_rows)//100} rounds x 100 candidates) to ml_training_data.csv")


if __name__ == "__main__":
    main()
