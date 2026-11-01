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

## PLAY LADDER (in the script since 2026-10-31)
The nested lists that beat chance, in order: PRIME 4, then PRIME 8, PRIME 10, + PRIME 4 FAMILY, + reversed, + PRIME 10 FAMILY.
Replay (avg size / held / chance): 4 / 23 / 11.7 · 8 / 43 / 23.4 · 10 / 48 / 29.3 · 18.3 / 76 / 53.5 · 26.4 / 101 / 77.3 · 29.1 / 114 / 85.2.
Live counters: `rrr3_lad_<step>_rounds/_hits` in RRR_LIVE. Each step's numbers are stored in `live.jsonl` under `ladder`.

## Live check at 30 rounds (P2-P31, 2026-10-31)
Lift = hits / chance, for lists present in 10 or more rounds:
- PRIME 4: 3 hits vs 1.2 (2.50)
- PRIME 8: 5 vs 2.4 (2.08)
- ONE ROW PICK: 3 vs 1.6 (1.94)
- WIDE: 7 vs 3.9 (1.81)
- PRIME 10: 5 vs 3.0 (1.67)
- rule 5: 11 vs 7.7 (1.42)
- PRIME 4 FAMILY: 3 vs 2.7 (1.12)
- STRONG 20: 4 vs 6.0 (0.67)
- RECOMMENDED: 6 vs 10.5 (0.57)
- HOT 20: 3 vs 6.0 (0.50)
- finder: 4 vs 8.0 (0.50)
- RECOMMENDED yx: 1 vs 4.2 (0.24)

The live order agrees with the replay: PRIME 4 and PRIME 8 are on top, and the wide lists are at or below chance.
Caveat: P2-P13 were back-filled with the later script, so their ONE ROW PICK and family entries are not truly live.

## LAST-row moves (from Q23 on)
The user explains each result from the LAST operation row only. `tools/last_move.py <round> <dataset> <result> <x op> <y op>`
logs the move to `last_moves.jsonl`: the LAST row's old/new ops, and which LAST ROW DIGIT MENU cells give the user's x op and y op
(new x / new y / old x / old y, as is / sign flipped / cut switched / step switched).
Plan: after about 30 explained rounds, test whether the move choice follows a rule.

## LAST-OP 4 (in the script since 2026-10-31)
The LAST-row cells are ranked by replay hit count (`LASTOP_CELLS` in DataProcessing.py). The pick is the first 4 / 8 different numbers.
Tested by series (order learned on 4 series, scored on the 5th): top 4 held 19 of 293 (chance 11.7), top 8 held 42 (chance 23.4).
Back-scored on 60 recorded live rounds: top 4 held 4 (chance 2.4).
Ranking by the user's crossed-move changes (`tools/lastop4.py`) held 0 of 8 in leave-one-out, so it was not used.
Live counters: `rrr3_lastop4` and `rrr3_lastop8`. The numbers are stored in `live.jsonl` under `lastop`.

## Series Q done (Q2-Q48), FINAL 4 miss study (2026-11-01, 78 live rounds P2-P32 + Q2-Q48)
Live hits:
- FINAL 4: 4 (chance 3.1)
- PRIME 4: 3
- PRIME 8: 8 (chance 6.2)
- PRIME 4 FAMILY: 13
- FINAL 4 FAMILY: 18 (about 15 numbers, chance 11.7)
- LAST-OP 4: 0 of 18 live

Where the 74 FINAL 4 misses landed in the ranked list:
- outside the top 40: 52
- top 21-40: 15
- top 11-20: 5
- top 5-10: 2

So most misses are not just below the FINAL 4.
14 of the 74 misses were a digit-cut family member of a FINAL 4 number, spread evenly over #1-#4 (3 3 4 4).

Replay (293 rounds):

| Pick | Held | Avg size | Chance |
|---|---|---|---|
| FINAL 4 | 20 | 4 | 11.7 |
| PRIME 4 | 23 | 4 | 11.7 |
| union of the two | 24 | 4.2 | — |
| FINAL 4 family | 57 | 14.8 | 43.3 |
| PRIME 4 family | 59 | 15.2 | 44.4 |

No 4-number change beats PRIME 4. The misses can only be covered by playing more numbers (the PLAY LADDER family step), not by a sharper 4.

## LAST op / previous op study (2026-11-01, tools/lastprev_collect.py + lastprev_study.py)
User asked to check FINAL 4 with the last operation and its previous operation. 374 rounds (F N M K O P Q R).
cost(v) = fewest changes (sign flip / cut switch / step switch) for LAST row new or old ops (xy or yx), and the row before it.
- FINAL 4 now: 25 of 374 (6.7%).
- Re-rank top 8/10/20/40 by LAST cost: 23 / 22 / 20 / 17. With prev row too: 20 / 21 / 17 / 13. LAST new only: 19 / 19 / 14 / 10.
- Result inside cost<=0/1/2 sets: LAST 3.5/23.0/60.7% vs set size 3.8/21.7/57.5%; LAST+prev 7.8/39.3/79.9% vs 7.5/38.6/80.6% -> chance.
Decision: shown as a "LAST op / previous op check" column in FINAL 4, ranking unchanged.

## SCRIPT BOOSTER gap study (2026-11-01, tools/booster_study.py)
User asked to fill the gap for every missed round of the 374 so future uploads do not miss.
650 fixed recipes (LAST / prev / prev2 / first / second row x new/old ops x xy/yx x 9 changes per side, plus EP and EP reversed).
- After the fact, some recipe makes the result in 366 of 374 rounds, but the recipes together give 97.3 different numbers per round, so this explains nothing.
- Best single recipe: 10 of 374; with 650 tried, about 10 is what luck alone gives.
- Recipes picked on the other series and tested on a held-out series: 4 recipes 8 hits (chance 14.7), 8 recipes 26 (chance 29.1), 10 recipes 37 (chance 35.8). At or below chance.
- The script as it is: FINAL 4 25 (chance 15.0), top 8 43 (29.9), top 10 47 (37.4), top 20 81 (74.8), top 40 166 (149.6). 208 results fell outside the top 40.
Decision: no per-round patches added (they lower held-out hits); FINAL 4 ranking unchanged. Re-run the study on new data: `python3 tools/lastprev_collect.py && python3 tools/booster_study.py`.

## Research pass 2 (2026-11-01, tools/research2.py, 377 rounds incl. R5-R7)
Prompted by R6 (44) and R7 (11), both made by the row before LAST from its old ops.
- prev row old ops xy/yx exact: 9 (chance 7.1); with 1 change: 38 (44.5). prev new / both: at chance.
- result repeats the last number: 9 (chance 3.8), spread K3 O2 P2 M1 Q1, never in the top 10. One of ~20 tests, p about 0.02: not trusted.
- repeat of last 5/10/20 numbers, most common x/y ops (held-out), last round's op pair again, hot tens/units digits: all at or below chance.
- the script's own ranking: top 4 25 (chance 15.1), top 8 44 (30.2), top 10 48 (37.7) above chance; top 20/40 at chance.
Decision: nothing new beats FINAL 4's slots; no change to the ranking.

## EP-row follower check (2026-11-01, after R41 = 97 via Op29 04 → 97)
- A table-4 row that starts at the EP → its second number: 101 numbers offered in 89 of 377 rounds, 3 hits (chance about 1.0). Too few to trust; watch it.
- Whole data, every number that followed the EP: 89 hits vs 101.8 chance → nothing.
