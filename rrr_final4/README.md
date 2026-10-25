# OCJP FINAL 4: how it was chosen (2026-10-15)

1. Every round file with a known next result (series b c d f h i j k, 536 rounds) was run with `RRR3_DUMP2` set. The dump holds OCJP with places and forms, plus every list.
2. Walk-forward: the first 100 rounds are used only for learning. In each later round, 4 of the OCJP numbers are picked using only earlier rounds, then checked against the result.

| Method (436 rounds) | Hits | Rate |
|---|---|---|
| votes in never-repaired lists (SHIPPED) | 36 | 8.3% |
| weighted votes, all lists | 40 | 9.2% (uses repaired lists, replay flattered) |
| plain votes, all lists | 35 | 8.0% |
| combined naive Bayes | 30 | 6.9% |
| random 4 of OCJP | 16.8 | 3.9% |
| op pair seen most | 12 | 2.8% |
| any 4 of 100 | — | 4.0% |

The shipped rule gets 8.3% on the old series and 8.2% on J/K, with p < 0.001 against 4%. It is about twice chance and still misses about 92 rounds in 100.

`methods_backtest.py` and `final4_backtest.py` need the json dumps, which are re-created by running the round files with `RRR3_DUMP2=<path>`.

# Can the operation pick FINAL 4? (2026-10-22, after N78)

User asked for a deeper, operation-based pick ("the number is in the bag, pick it by the operations"). `ops_study.py` scores every OCJP number in each round using only earlier rounds (first 100 rounds warm-up), then checks the top 4 against the result.

Data: (A) 885 real rounds, every series b–n, re-run with today's script (`rrr_datasets/dump_all.py`); (B) 483 grid-replay rounds from the old archive `temp_data_d1175_d1386_backup.txt` (`grid_replay.py`: first t grid rows, result = first number of row t+1; grid numbers are not live results).

| Method (top 4 of OCJP) | A: 774 real rounds | B: 364 grid rounds |
|---|---|---|
| **current: votes in never-repaired lists (SHIPPED)** | **63 = 8.1%** | 17 = 4.7% |
| votes, ties broken by OCJP place hit rate | 54 = 7.0% | 24 = 6.6% |
| votes, ties broken by op hit rate | 54 = 7.0% | 16 = 4.4% |
| ops seen in the last 30 results | 54 = 7.0% | 17 = 4.7% |
| most OCJP places holding it | 45 = 5.8% | 9 = 2.5% |
| logistic model, all features (refit every 50 rounds) | 44 = 5.7% | 13 = 3.6% |
| OCJP form hit rate | 38 = 4.9% | 16 = 4.4% |
| op (x/y pair) seen most | 35 = 4.5% | 15 = 4.1% |
| x op + y op seen most | 27 = 3.5% | 20 = 5.5% |
| OCJP place hit rate | 27 = 3.5% | 17 = 4.7% |
| random 4 of OCJP | 32 = 4.1% | 15 = 4.1% |

**Conclusion:** no operation-based score beats the shipped rule. The ops on their own (op, x op, y op, place, form) pick at the random rate: the result's operation carries no memory from earlier rounds. Combined A+B, current 80/1138 = 7.0% vs best alternative 78/1138 = 6.9%. FINAL 4 left unchanged.

# Declared block as FINAL 4? (2026-10-23, after N148)

User asked again for a FINAL 4 change after 25 rounds without a hit (series N: 7/148 = 4.7%). On series N, STRONG #12–15 (declared number and its neighbours) held 14/148 = 9.5% — but that was picked after looking. Out-of-sample check on all 954 replayed rounds (`rrr_datasets/dump_all.py`, today's script):

| Pick | older series (807) | series N (147) |
|---|---|---|
| **FINAL 4 shipped** | **67 = 8.3%** | 7 = 4.8% |
| STRONG #1–4 | 50 = 6.2% | 6 = 4.1% |
| STRONG #9–12 | 53 = 6.6% | 10 = 6.8% |
| STRONG #12–15 | 55 = 6.8% | 14 = 9.5% |
| STRONG #13–16 | 48 = 5.9% | 13 = 8.8% |

The N advantage of the declared block does not hold on the older rounds; the shipped rule is still best overall (74/954 = 7.8% vs 69/954 = 7.2%). FINAL 4 left unchanged.

# FINAL 4 ops flipped / stepped? (2026-10-23, after N158)

User idea: the result is often a FINAL 4 operation turned around on the EP: x and y ops swapped (yx), a sign flipped, the cut added or removed, and the step moved one up or down toward the last operation's step. `flip_study.py` builds those forms from the shipped FINAL 4 ops in all 963 replayed rounds (`rrr_datasets/dump_all.py`, today's script) and counts hits on the **new numbers only** (FINAL 4 itself left out), against their size.

| Moves | New numbers a round | Hits on new numbers | Chance | Hits / chance |
|---|---|---|---|---|
| step 1 toward last op | 2.7 | 2.5% | 2.7% | 0.94 |
| swap x/y only (yx) | 2.8 | 2.0% | 2.8% | 0.71 |
| signs flipped only | 7.7 | 7.3% | 7.7% | 0.95 |
| cut added/removed only | 11.0 | 10.9% | 11.0% | 1.00 |
| swap + signs | 14.4 | 13.2% | 14.4% | 0.91 |
| step free ±1 | 19.8 | 18.5% | 19.8% | 0.93 |
| swap + signs + cut (all) | 47.4 | 45.5% | 47.4% | 0.96 |

Every move adds numbers at or below chance. The step-toward rule used **in place of** FINAL 4 holds 49/951 = 5.2% vs shipped FINAL 4 74/951 = 7.8%. The examples (N156 23 → 07, N158 05 → 04) are real, but a move set that size catches results by chance just as often. FINAL 4 left unchanged.

## FINAL 4 tie-break (2026-10-23, after N162=67)

67 was in 2 lists (RRR table, yx) and lost the "lower number" tie-break (rank 13).
`tiebreak_study.py all.json`, 963 replayed rounds, tie-break after votes + STRONG:
lower 74, OCJP place 70, rec 77, table 73, again 77, wide 72, yx 70, found 68.
All within noise (±6 of 963), halves disagree; shipped tie-break kept.

## Star pick vs FINAL 4 (2026-10-24, after N177)

Dumped every star vote (`star` key in RRR3_DUMP2) and replayed 977 rounds
(`rrr_datasets/dump_all.py`, then `rrr_final4/star_vs_f4.py all.json`).

| Pick | Hits | Rate | Chance |
|---|---|---|---|
| FINAL 4 (shipped) | 74/977 | 7.6% | 4% |
| star top 4 | 73/977 | 7.5% | 4% |
| FINAL 4 + star top 4 (5.5 numbers) | 98/977 | 10.0% | 5.5% |
| MASTER | 21/977 | 2.1% | 1% |
| star #1 | 29/977 | 3.0% | 1% |

Star #1 vs MASTER: same pick in 420 rounds; where they differ star #1 hit 16,
MASTER 8 (sign test p about 0.15). Star #1 ahead or level in every quarter.
Kept FINAL 4 and MASTER; star #1 is tracked live as a second single pick from N178.
Note: rounds replayed after the N176 OCJP repair (places 19-20 % form) used the
new OCJP; the effect on FINAL 4 is a few numbers on ~11% of rounds.

## Tens / units digit study (2026-10-24, after N208 = 22, FINAL 4 #1 was 23)
User question: FINAL 4 often has the result's tens digit; can the units be found?
Script: `digit_study.py <all.json>` on 1018 replayed rounds.
- Tens digit of the result in FINAL 4's tens: 35.9%. FINAL 4 has 2-4 distinct tens,
  so chance is 33.5%; with results shuffled the 95% band is 31.4%-36.8%. So the tens
  is not found more often than chance. Each rank's tens: 10.4%-11.6% (chance 10%).
- When #1's tens is right (118 rounds), the units distance to #1 is 0:24, 1:21,
  2:26, 3:21, 4:20, 5:6. Apart from exact hits this is uniform: a units digit one
  off (22 vs 23) is no more common than chance.
- 15 single units-digit rules tested (#1 units ±1/cut, EP units, after units, most
  or least common units in the lists, ...). #1 units 13.9% is just FINAL 4's own
  exact hits (11.5% after removing them, chance about 9%). Most common units digit
  in the lists 12.4% (126 vs shuffle band 85-121; halves 11.2% / 13.6%), but as a
  FINAL 4 tie-break it gives 73 hits against the shipped 83 (both halves worse).
- 4-number sets built on #1's tens (#1 band ±1 + #2, #1/#2 with units +1): 5.5%
  and 6.1% vs FINAL 4 8.2%.
Kept FINAL 4 unchanged.

## Deep diagnosis (2026-10-25, after N222 = 83, user: "6 months, FINAL 4 / MASTER 1")
Script: `diagnosis.py <all.json>`, all series b..n together (1018 replayed rounds).
- The result's digit change from the EP is uniform: tens chi2 7.8, units chi2 6.7
  (9 df, 5% cut 16.9). Every operation x/y is about equally likely, every round.
  Results 00-99 are uniform too (chi2 79.6, cut 123.2).
- One non-uniform sign (tens digit after the previous tens digit, chi2 110 / 123 / 107
  on all / halves) does not predict walk-forward: top-1 tens 10.9% (chance 10%,
  p 0.21), top-3 31.2% (chance 30%, p 0.24).
- Ordering: ranks 1-4 hold 83 results (41 by chance, ratio 2.0), ranks 5-10 1.3,
  ranks 11-40 1.0-1.1, ranks 41-100 0.84-0.93. Votes per number: 0 votes 0.91%,
  1 vote 0.97%, 2 votes 1.34%, 3 votes 1.70% (chance 1%). The best single number
  in a round is about 1.3-1.7%, so MASTER cannot be expected to hit often.
- The replay is in-sample: lists and OCJP forms were repaired on these rounds.
  Live (out of sample): FINAL 4 24 of 432 = 5.6% (17.3 by chance, p 0.07),
  MASTER 2 of 378 = 0.5% (3.8 by chance), star #1 1 of 45, step-toward 3 of 65
  (2.6 by chance). Live FINAL 4 is about a third better than chance, not proven.
- The declared cell holds 96-100 numbers, so its ~99% is by its size, not prediction.
Conclusion: with uniform digit changes, no op-based list can be much better than
its size. Kept FINAL 4; OCJP repairs keep the cell full, they are not an edge.

## Global check on all data sets (2026-10-25)
`series_check.py <new dump> [old dump]`: the current script (with the N209 and N218
OCJP forms) run on every round of all 13 series, 1029 rounds: 0 errors, OCJP holds
the result in 1026 (every series 97-100%), no OCJP hit lost against the older dump.
FINAL 4 77/1029 = 7.5%, MASTER 21/1029 = 2.0%. The older replay's 83/1018 counted
six bad rounds (n206-n211 built from the old results re-sent by mistake on
2026-10-24, result = EP): corrected figure is 7.5%, not 8.2%. No code change moved
a FINAL 4 hit in any series.

## N225 OCJP repair: % form on places 27-30 when X == Y (2026-10-25)
Result 92 (+2/cut) after 89 on EP 77; LAST row c+2/c+2 twice. Global replay after
the change, all 13 series, 1032 rounds: 0 errors, OCJP 1031/1032 (b 63/64, all
others 100%), no hit lost in any series, FINAL 4 78/1032, MASTER 21/1032.

## N235 repair: `#` form on places 19-20 (2026-10-25)

Result 04 after 62 on EP 97 (+1/c+2) fell outside OCJP and the cell. The LAST row was 09 (+1/+2), 18 (+2/+1), and place 19 held the % forms (x cut switched) but never the y cut alone. The `#` form (y cut switched, both x steps and both y steps) now runs on places 19-20 too.

Replay test (`ocjp_last_ycut_test.py`, 1032 rounds before N235):

| Form | Old hits gained | Size per round | Expected by chance |
|---|---|---|---|
| A: y cut alone | 0 | 0.17 | 1.8 |
| B: A + y step switched | 0 | 0.17 | 1.8 |
| C: full `#` form (shipped) | +1 (b) | 0.25 | 2.6 |

All at chance. C was chosen because it is the same `#` form as places 1-8. Global check over 1041 rounds: 0 errors, OCJP 1041/1041, 0 hits lost, and FINAL 4 78 is unchanged.

## Series N check after N251 = 57 (2026-10-25)

The user asked why FINAL 4 keeps missing. Replay `all4.json` (1041 rounds, 234 of them series N):

| Set | All 13 series | Series N | Chance |
|---|---|---|---|
| MASTER | 2.0% | 0.4% | 1% |
| FINAL 4 | 7.5% | 4.7% | 4% |
| top 8 | 13.3% | 8.5% | 8% |
| top 20 | 26.6% | 22.6% | 20% |

Per-number hit rate by votes, series N: 0v 0.98%, 1v 0.97%, 2v 1.22%, 3v 0/154. On the other 12 series: 0.89%, 0.96%, 1.30%, 1.83%. On N the votes carry no signal, and 44% of N results have 0 votes. FINAL 4 is at chance on N, and the all-series 7.5% is in-sample. No change was made.

## User swap/flip idea after N264 = 74 (2026-10-25)

FINAL 4 #2 61 (c-2/c-1), with its sides swapped and the new y sign flipped, gives c-1/c+2 = 74, the result. `swap_flip_test.py` tests this on 1070 rounds (all series plus live N up to N263). Each FINAL 4 op makes one number:

| Form | All series | Series N | Chance |
|---|---|---|---|
| swap, flip new y (user) | 3.4% | 3.8% | 3.5% |
| swap, flip new x | 2.9% | 3.8% | 3.5% |
| swap only | 2.2% | 3.0% | 2.8% |
| swap, flip both | 3.6% | 3.0% | 3.4% |

All at chance, so the rule was not added.

## User "same family" idea after N265 = 87 (2026-10-25)

FINAL 4 held 23 (c-1/c+2) and 78 (-1/+2): the same steps, with only the cuts different. 87 came 5th. Rule tested (`family_test.py`, 1071 rounds): keep at most one number per step family in FINAL 4.

| Rule | All series | Series N |
|---|---|---|
| shipped FINAL 4 | 81 | 14 |
| one per step family | 82 | 12 |
| one per step size | 82 | 13 |

With N265 included the rule is 83 vs 81 on all series and 13 vs 14 on N, a draw. It was not shipped, but it is tracked as an on-test line in the round outputs from N266 (record 1 of 1 at the start).

## How much the after-the-fact turns of FINAL 4 cover (after N272 = 79, 2026-10-25)

Since N264 the user has found three different turns of a FINAL 4 op that each matched one result. `transform_cover.py` measures, over 1078 replayed rounds, how many numbers such turns of the 4 FINAL 4 ops reach each round, and how often the result is among them:

| Turns allowed | Numbers reached | Result among them |
|---|---|---|
| swap sides and/or flip signs (8 forms) | 18.4 | 21.1% |
| + cut moved or toggled (32 forms) | 50.9 | 53.6% |
| + one step up/down | 97.6 | 98.2% |

The hit rate tracks the coverage, so some turn can almost always be found after the fact. New turns are not added as rules. User rules 1-3 stay tracked on test.

## User reverse idea after N279 = 41 (2026-10-25)

MASTER 14 with its digits reversed is 41. `reverse_test.py`, 1085 rounds: the reversed MASTER hit 0.9% (10 times) on all series and 0 of 278 on series N, against 1% chance. The reversed FINAL 4 hit 3.6% for 3.4 numbers a round, also chance. The rule was not added; it is tracked on test as rule 4 from N280.

## OCJP entry count after N283 = 96 (2026-10-25)

96 sat in OCJP four times (places 7!, 12, 19%, 31=) but had 0 votes, so FINAL 4 ranked it 100th. `ocjp_count_test.py`, 1041 rounds: the hit rate per number for 1, 2, 3, 4 and 5+ OCJP entries is 1.05%, 1.00%, 1.23%, 0.64% and 0.84%, which is flat around 1%. A FINAL 4 built from the top 4 by OCJP count hits 4.2% (chance 4%). It was not added.

## RECOMMENDED-position tie-break after N285 = 57 (2026-10-25)

55 (N282, REC #1) and 57 (N285, REC #3) both lost 2-vote tie-breaks. `rec_tiebreak_test.py`, 1041 rounds: the shipped order (votes, STRONG, lower number) hits 78 = 7.5%. Breaking ties by REC position after STRONG hits 71 = 6.8%, and REC position without STRONG hits 52 = 5.0%. The shipped order also wins on series N and in both halves, so it is kept.
