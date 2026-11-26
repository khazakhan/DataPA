#!/bin/bash
# Re-run Sets 01-06 to save the 40-number list (rank_all) for every round (user 2026-11-27:
# 'which sets are best ... 4+ rounds passed'). Resumable: run again after a shutdown.
cd /home/khazakhan/DataScinceAnal
for n in 01 02 03 04 05 06; do
  python3 tools/allrounds.py holdout_sets/set$n.txt --jobs 4 --out holdout_sets/set${n}_r40.jsonl
done
echo "=== sets 01-06 rank_all done ==="
