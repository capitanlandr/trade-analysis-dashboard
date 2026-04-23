# Trade Value Metric Analysis

## Problem Statement

The dashboard's `totalValueGained` metric currently reports positive values for all 12 teams in the league, with a league-wide sum of +135,114. In a zero-sum trading system where every asset given away by one team is received by another, the sum across all teams should net to zero. The metric is not measuring trade success; it is measuring asset appreciation.

## How the Current Metric Works

The pipeline calculates `totalValueGained` by summing `teamXValueChange` across all of a team's trades, where `teamXValueChange = teamXValueNow - teamXValueThen`. Both `ValueNow` and `ValueThen` refer exclusively to the assets the team **received** in each trade. The assets the team **gave away** are not factored into the calculation.

This means the metric tracks how much the assets a team acquired have appreciated (or depreciated) since the trade date. It does not compare what a team received against what they sent out. Because fantasy asset values generally trend upward over time (draft picks appreciate as the draft approaches, young players appreciate during breakout seasons), the metric inflates for every team and produces the misleading result that everyone is a net winner.

### Worked Example: Landry (lndahayo)

Across 15 trades, Landry's numbers break down as follows:

| Metric | Value |
|---|---|
| Total current value of assets received | 44,288 |
| Total current value of assets given away | 42,058 |
| True net (received minus gave, current prices) | +2,230 |
| Dashboard `totalValueGained` (received appreciation only) | +23,435 |

The dashboard reports +23,435 because the assets Landry acquired appreciated by that amount. But the assets he gave away also appreciated by +20,520. The actual net position, comparing both sides at current prices, is +2,230. The dashboard overstates his trade performance by roughly 10x.

## True Net Leaderboard (Received Now minus Gave Now)

When both sides of every trade are compared at current market prices, the league-wide sum nets to exactly zero:

| Team | Trades | True Net | Dashboard |
|---|---|---|---|
| Gaeta | 10 | +10,962 | +11,121 |
| Grant | 17 | +8,635 | +15,724 |
| Kyle | 10 | +3,513 | +12,322 |
| Landry | 15 | +2,230 | +23,435 |
| Tyler | 14 | +1,663 | +12,992 |
| Jake | 7 | +1,522 | +3,530 |
| Don | 26 | +1,473 | +14,541 |
| Will | 9 | +1,103 | +6,029 |
| Brevin | 2 | -2,182 | +436 |
| Chris | 5 | -4,982 | +1,045 |
| Johnny | 29 | -11,875 | +21,949 |
| Zach | 24 | -12,062 | +11,990 |
| **TOTAL** | | **0** | **+135,114** |

The true net calculation reveals a fundamentally different picture. Johnny and Zach, who appear to be strong traders on the dashboard (+21,949 and +11,990), are the two biggest net losers (-11,875 and -12,062). Gaeta leads the true leaderboard, but his position is driven heavily by accumulating future draft picks that are currently in a pre-draft appreciation cycle.

## Why All-Positive Scores Occur

Three structural factors cause every team to appear positive under the current metric:

1. **Draft pick appreciation is the dominant force.** A 2026 Round 1 pick traded in May 2025 at a value of 2,000 might be worth 7,000 today as the draft approaches. Both sides of a trade involving future picks can show gains because the pick appreciates on one side while the player received on the other side may also appreciate (breakout performance, hype cycle). The appreciation is counted for the receiving team but the corresponding cost is never deducted from the giving team's score.

2. **The metric only tracks one side of the ledger.** For each trade, the pipeline records how the assets a team received have changed in value. It does not record how the assets a team gave away have changed in value. When both sides of a trade appreciate (which is common when the trade involves young players and future picks), both teams accumulate positive `ValueChange` independently.

3. **The league-wide sum is unbounded.** Because the metric does not enforce zero-sum accounting, the total across all teams grows as asset values inflate. The +135,114 league-wide total represents cumulative asset appreciation across all traded assets, not cumulative trade skill.

## Volatility Problem with Current-Value Metrics

Even the corrected true net metric (received now minus gave now) has a significant limitation: it fluctuates based on external events that have nothing to do with trade negotiation skill. Gaeta's +10,962 lead is real today, but it is heavily concentrated in 2026 and 2027 draft picks that have not yet converted to players. When the 2026 NFL draft occurs and those picks become rookies, the values will reset to the drafted player's actual market price. If the picks land on mid-tier prospects, Gaeta's lead could contract significantly.

The pipeline already handles this conversion correctly for 2025 picks. A traded "2025 Round 1" pick is valued at the pick price on the trade date, but its current value reflects the actual player drafted at that position (tracked via the `PICK_LINEAGE` mapping built from Sleeper draft results). This means post-draft values are grounded in real player markets rather than speculative pick markets. The same conversion will occur for 2026 picks once that draft completes.

This lifecycle (pick appreciates toward draft, converts to rookie value, then rises or falls based on NFL performance) means any metric anchored to current market prices will swing substantially around draft season, and the teams most exposed to that swing are the ones holding the most future picks.

## Recommended Metrics Framework

No single metric captures all dimensions of trade success. The pipeline already computes the building blocks for a multi-metric framework. The following three metrics, used together, would provide a more complete and honest picture of trade performance.

### 1. Trade-Time Margin (Negotiation Skill)

**Definition:** The difference between the value of assets received and the value of assets given away, both measured at trade-time prices.

**Formula:** `marginAtTrade = (value of assets received at trade time) - (value of assets given away at trade time)`

**What it measures:** Whether a team consistently extracts more value than they give up at the moment of the deal. This is the purest measure of negotiation skill because it is locked in at execution and never changes. It isolates the quality of the deal from everything that happens afterward.

**Limitation:** It penalizes intentional buy-low strategies where a team acquires an asset they believe is undervalued by the market. A savvy trade for a slumping player at a discount would show a negative margin at trade time even if the thesis proves correct.

**Already available in pipeline:** `marginAtTrade` is computed in `stage4_final.py` line 103.

### 2. Current Margin (Portfolio Health)

**Definition:** The difference between the current value of assets received and the current value of assets given away.

**Formula:** `marginCurrent = (current value of assets received) - (current value of assets given away)`

**What it measures:** Who holds the better side of the deal today. This is the "true net" calculation from the analysis above. It captures both negotiation skill and market timing, providing a snapshot of which teams have accumulated the most value through trading.

**Limitation:** It is volatile. Values shift daily based on player performance, injuries, and proximity to the NFL draft. A team's ranking can change significantly without any new trades occurring. It also rewards exposure to appreciating asset classes (future picks near draft season) regardless of whether that appreciation was intentional or incidental.

**Already available in pipeline:** `marginCurrent` is computed in `stage4_final.py` line 104. The per-team rollup (sum of marginCurrent across all trades) is the zero-sum true net value that should replace the current `totalValueGained`.

### 3. Margin Swing (Market Vision)

**Definition:** How the margin between the two sides of a trade has changed from trade time to the present.

**Formula:** `marginSwing = marginCurrent - marginAtTrade`

**What it measures:** Whether a team's trades have gotten better or worse over time relative to the other side. A positive swing means the assets a team acquired have outperformed the assets they gave away since the trade date. This isolates the "vision" component, how well a team predicted which assets would appreciate, independent of whether they negotiated well at the time.

**Limitation:** A team that consistently overpays at trade time but picks appreciating assets would show a positive swing despite poor negotiation. The swing metric should be read alongside the trade-time margin to distinguish between teams that trade well and get lucky versus teams that trade poorly but have good asset selection instincts.

**Already available in pipeline:** `swingMargin` is computed in `stage4_final.py` lines 83-86.

### Implementation Priority

The highest-impact change is replacing `totalValueGained` with the true net calculation (sum of `marginCurrent` per team). This single change converts the leaderboard from an all-positive inflation-driven ranking to a zero-sum ranking that reflects actual trade outcomes. The trade-time margin and margin swing metrics can be surfaced as additional columns or views in a subsequent iteration.

## Data as of April 22, 2026

This analysis was conducted against the live dashboard data on April 22, 2026, covering 84 trades across season 2 (80 trades) and season 3 (4 trades) of the Dynasuiiii fantasy football league.
