# RRR round records (for building a robust picker)

- `live.jsonl`: one line per live round, written by `python3 tools/record_round.py <round> <dataset before result> <result> [user pick ...]`.
  Each line holds the EP, the after number, every RRR row (old/new ops), every list (FINAL 4 = top4, PRIME 10, STRONG 20,
  RECOMMENDED, rules 1-24, finder, ONE ROW PICK lines), the result and its op, every row change that makes it
  (`makers`, with the number of changes), `held_by`, and the user's pick.
  P2-P13 were back-filled on 2026-10-31 with the script as it was that day, so their lists can differ a little from what was shown live.
  From P14 on, each round is recorded live, with the same script that made the page.
- `replay/`: the 293 replay rounds of series F/N/M/K/O (+ C, 59 rounds): `pairsX.json` (dataset, result), `srcX.json` (lists per round),
  `fsX.json` (every row x change number per round). Used for the PRIME / finder / ONE ROW PICK replays.

## Studies (2026-10-31, 293 replay rounds, each series tested on a model trained on the other four)
- `tools/picker_study.py` learns which row relation and change holds the result. It got top4 11, top10 32, top20 58 against chance 11.7, 29.3 and 58.6, so it is **at chance**.
- `tools/listvote_study.py` learns a weight per list. It got top4 20, top8 37, top10 42.
- PRIME got top4 23, top8 43, top10 48, so **PRIME stays the best**. No change was made to the pick logic.
- Rerun both studies with `live.jsonl` added once there are 30 or more recorded live rounds.

## Table 4 reach study (`tools/table_reach_study.py`, 2026-10-31, 293 replay rounds, 6.6 rows per table)
| Changes allowed | Numbers the table makes | Held the result | Chance |
|---|---|---|---|
| 0 (xy/yx as shown, old and new) | 21.9 | 70 (24%) | 64.1 |
| 1 | 63.5 | 182 (62%) | 185.9 |
| 2 | 81.4 | 241 (82%) | 238.6 |
| 4 (every change) | 85.2 | 251 (86%) | 249.5 |

At every level, the table holds the result as often as the same count of random numbers would. In 14% of rounds no row can make the result with any change.
How many rows make the result within 1 change: 0 rows in 111 rounds, 1 row in 97, 2 rows in 49, 3 or more in 36.
