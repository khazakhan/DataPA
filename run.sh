#!/bin/bash
# ──────────────────────────────────────────────────────
#  DataScinceAnal — Analysis Runner
#  Usage:  ./run.sh
# ──────────────────────────────────────────────────────

DIR="/home/khazakhan/DataScinceAnal"
cd "$DIR"

clear
echo "══════════════════════════════════════════════════════"
echo "  DataScinceAnal — Paste Data & Run Analysis"
echo "══════════════════════════════════════════════════════"
echo ""
echo "  Paste your full data grid below."
echo "  When finished → type  END  on a new line + Enter."
echo ""
echo "──────────────────────────────────────────────────────"

# Collect pasted lines until user types END
> temp_data.txt
while IFS= read -r line; do
    [[ "$line" == "END" ]] && break
    echo "$line" >> temp_data.txt
done

ROW_COUNT=$(wc -l < temp_data.txt)
echo "──────────────────────────────────────────────────────"
echo "  Data saved  ($ROW_COUNT rows)  →  running analysis..."
echo ""

python3 DataProcessing.py < temp_data.txt 2>/dev/null
