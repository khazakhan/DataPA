#!/usr/bin/env bash
# One RRR round, exactly as done in chat (2026-11-07).
#
#   tools/round.sh <series> <N> <result>      e.g.  tools/round.sh u 21 79
#     - copies rrr_datasets/<series><N-1>.txt to <series><N>.txt and adds the result
#     - records the round, bumps every live counter, scores ONE-MEN-ARMY
#     - prints and saves the next page rrr_outputs/<series><N+1>_full.txt
#
#   tools/round.sh show <dataset>              e.g.  tools/round.sh show rrr_datasets/u21.txt
#     - only prints the page (same tables as chat), changes nothing
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" = "show" ]; then
    b="$(basename "$2" .txt)"
    CHAT_PAGE_ROUND="$(echo "$b" | tr a-z A-Z)" python3 DataProcessing.py < "$2" 2>/dev/null
    exit 0
fi

s="$1"; n="$2"; res="$3"
prev="rrr_datasets/${s}$((n - 1)).txt"
cur="rrr_datasets/${s}${n}.txt"
R="$(echo "$s" | tr a-z A-Z)${n}"
next="$(echo "$s" | tr a-z A-Z)$((n + 1))"
[ -f "$prev" ] || { echo "missing $prev"; exit 1; }
[ -f "$cur" ] && { echo "$cur already exists (round already done?)"; exit 1; }

cp "$prev" "$cur"
res=$((10#$res)); printf '%02d\n' "$res" >> "$cur"
# SHADOW FINAL 4 (pre-registered challenger, tools/shadow_f4.py): pick from the
# chart BEFORE this result (no-op if already logged), then score it
python3 tools/shadow_f4.py predict "$prev" "$R" >/dev/null
python3 tools/shadow_f4.py score "$R" "$res"

# result op on the ROOT (x/y), needed by last_move.py
ops=$(python3 - "$prev" "$res" <<'PY'
import sys, io, contextlib
sys.path.insert(0, '.')
with contextlib.redirect_stdout(io.StringIO()):
    import DataProcessing as D
    D.run(open(sys.argv[1]), None, None)
ep = D._RRR_ASK['ep']; r = int(sys.argv[2])
print(D.OP_ABBREV[D.find_op(ep // 10, r // 10)], D.OP_ABBREV[D.find_op(ep % 10, r % 10)])
PY
)
export OMA_OFF=1
python3 tools/record_round.py "$R" "$prev" "$res" | tail -1
python3 tools/last_move.py "$R" "$prev" "$res" $ops | tail -1
python3 tools/bump_live.py "$R" | grep -i 'missing\|bumped' || true
unset OMA_OFF
python3 tools/oma.py --result "$R" "$res" | tail -1
CHAT_PAGE_ROUND="$R" CHAT_PAGE_MD="rrr_outputs/${s}$((n + 1)).md" python3 DataProcessing.py < "$cur" 2>/dev/null | tee "rrr_outputs/${s}$((n + 1))_full.txt"
python3 tools/oma.py "$cur" --score "$next" | tail -n +2
python3 tools/shadow_f4.py predict "$cur" "$next"
