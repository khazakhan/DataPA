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
