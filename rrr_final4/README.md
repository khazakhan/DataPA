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
