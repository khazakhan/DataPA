# How wide must a list be to never miss? (2026-10-17)

Every number 00–99 gets one vote per list that holds it (cell, OCJP, RECOMMENDED, RRR table, yx, WIDE, 3RRR, same op again, STRONG 20), with STRONG 20's order as the tie-break. For each past round, the place of the real result in that ranking is recorded. Script: `width_backtest.py`.

| Top… | L data (129 rounds) | Random | J+K replays (207 rounds, flattered) |
|---|---|---|---|
| 4 | 1.6% | 4% | about 10% |
| 10 | 6.2% | 10% | about 22% |
| 20 | 17.1% | 20% | about 33% |
| 50 | 48.8% | 50% | about 65–69% |
| 80 | 76.0% | 80% | about 87–91% |
| 90 | 84.5% | 90% | about 95–98% |
| 95 | 92.2% | 95% | about 98–99.5% |
| **Zero misses** | **all 100** | | **96–98** |

**Conclusion:** no list narrower than (almost) all 100 numbers holds the result every round. On L data every width hits at about the random rate. The J+K figures are flattered, because the rules were built while looking at those results. Live K was much smaller: STRONG 20 27% vs 20%.
