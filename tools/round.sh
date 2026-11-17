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
python3 tools/final10.py score "$R" "$res" 2>/dev/null || true
# score the watch lines before the page is built, so the page shows current live counts
python3 tools/master_changed_ops.py score "$R" "$res" >/dev/null 2>&1 || true
python3 tools/hunter20.py score "$R" "$res" >/dev/null 2>&1 || true

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
python3 tools/final10.py predict "$next" "rrr_outputs/${s}$((n + 1)).md"
# MASTER CHANGED OPS 4 watch line (2026-11-17, user request after AD9; display only, at chance in study)
python3 tools/master_changed_ops.py score "$R" "$res" 2>/dev/null | tail -1 || true
mc=$(python3 - "rrr_outputs/${s}$((n + 1)).md" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
m = re.search(r'### OCJP FINAL 4: EP \d\d.*?ROOT (\d\d).*?\n\|.*\n\|.*\n\| \*\*MASTER[^|]*\| \*\*(\d\d)\*\*', t)
print(m.group(1), m.group(2) if m else '')
PY
)
python3 tools/master_changed_ops.py predict "$next" $mc | tail -1
# HUNTER 20 (2026-11-17, user request; FINAL 4 + yx + STRONG 20 fill; display only, live ~26% vs 20%)
python3 tools/hunter20.py score "$R" "$res" 2>/dev/null | tail -1 || true
python3 tools/hunter20.py predict "$next" "$cur" "rrr_outputs/${s}$((n + 1)).md" | tail -1
