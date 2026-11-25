#!/usr/bin/env bash
# Resume the 24-set all-rounds walk-forward test after a shutdown / terminal restart.
# Every set's results file is resumable: finished rounds are skipped, only missing rounds run.
# Usage (from the repo):  nohup bash tools/resume_holdout.sh > holdout_sets/resume.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1
if pgrep -f "python3 tools/allrounds.py holdout_sets/set" >/dev/null; then
    echo "a set test is already running - not starting a second copy"; exit 0
fi
export TMPDIR="${TMPDIR:-/tmp}"
for n in 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24; do
    extra=""; [ "$n" = 24 ] && extra="--start 574"     # set24 = set13 for its first 574 cells
    echo "=== set$n ==="
    python3 tools/allrounds.py holdout_sets/set$n.txt $extra --jobs 4 --out holdout_sets/set${n}_r12.jsonl
done
echo "=== all sets done ==="
