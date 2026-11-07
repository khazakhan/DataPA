# Running the RRR rounds locally (same tables as in chat)

Everything the chat shows comes from `DataProcessing.py`; the chat only copies its tables.

## See the current page (changes nothing)
```
tools/round.sh show rrr_datasets/u21.txt          # page for the next round (U22)
python3 DataProcessing.py < rrr_datasets/u21.txt   # same thing
```
The page includes table 4 (RRR next operation), MegaStar/PowerStar, ONE-MEN-ARMY, EPROOTGEN,
the OPEN / CLOSE digit line, OCJP FINAL 4 with operations, FINAL 8, BOOSTER, ALL COMBINED,
count 2+, All + booster of booster, the 80-number list and every live counter.
Saved copies: `rrr_outputs/<round>_full.txt` (full page) and `rrr_outputs/<round>.md` (chat summary).

## Do a round (after a result)
```
tools/round.sh u 22 <result>     # U22 result -> makes u22.txt, records, bumps counters, prints U23 page
git add -A && git commit -m "U22 = <result>" && git push
```

## Series
Active: series U (`rrr_datasets/u*.txt`). Parked: T (t27.txt), S (s82.txt), F, N, O ...
History used by the studies: `rrr_records/history_all.json` (1,293 rounds, series b..s).
Studies: `tools/*_study.py` (each prints its own test on all rounds).
