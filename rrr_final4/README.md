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
