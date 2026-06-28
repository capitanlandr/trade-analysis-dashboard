# Trade Calculation Logic Assessment

**Date:** 2026-06-27
**Analyst:** Claude Code (Opus 4.6)
**Scope:** Full pipeline audit of trade scoring logic (Stages 2-4 + Dashboard JSON generation)

---

## How the System Works

The trade scoring pipeline operates in four stages:

1. **Stage 2** (`stage2_extract_assets.py`) extracts individual assets from each Sleeper API trade record: players, draft picks (with origin owner tracking), and FAAB budget.

2. **Stage 3** (`stage3_cache_values.py`) values each asset twice:
   - `value_at_trade`: Historical DynastyProcess value from the closest Git commit to the trade date (uses `value_2qb` column).
   - `value_current`: Latest DynastyProcess CSV value (uses `value_2qb` column).

3. **Stage 4** (`stage4_final.py`) sums values per side of each trade, determines winners, and calculates margins.

4. **Dashboard JSON generator** (`scripts/generate_dashboard_json_from_cumulative.py`) rolls up per-manager statistics: `totalValueGained`, `winRate`, and `tradeCount`.

---

## The Core Logic Issue: `totalValueGained` Is Not What It Appears

### What the Dashboard Presents

The "Top Performers" section ranks managers by `totalValueGained`, implying it measures who trades best.

### What It Actually Measures

```
totalValueGained = sum of (value_current - value_at_trade) for all assets a manager received
```

This is **asset appreciation**, not **trade skill**. It measures how much the assets you acquired grew (or shrank) in value after you received them.

### Why This Is Problematic

#### 1. It Is Not Zero-Sum

The sum of `totalValueGained` across all 12 managers is **+7,605** (not zero). In a closed league where every trade has two sides, a metric measuring "who trades better" should net to zero. The non-zero sum means the metric is partly measuring:

- **Market timing**: When you traded (did the overall market go up or down after?)
- **Asset class exposure**: Players as an asset class can appreciate or depreciate independently of trade quality.

#### 2. The "Winner" Metric and `totalValueGained` Measure Different Things

| Metric | What It Measures | Type |
|--------|-----------------|------|
| `winnerCurrent` | Who got the higher-value side right now | Relative (zero-sum) |
| `totalValueGained` | How much your acquired assets appreciated | Absolute (not zero-sum) |

**Consequence:** A manager can "win" 100% of trades but have negative `totalValueGained` (their assets lost value, but the other side's assets lost MORE). Conversely, a manager can "lose" most trades but show positive `totalValueGained` if the overall market rose.

#### 3. Real Example: The Brevinowens Paradox

- **Win rate:** 100% (2/2 trades won)
- **totalValueGained:** -1,024 (negative)

Both trades: brevinowens got the better side (won), but both sides depreciated. His side just depreciated less. The relative metric (winner) says he won. The absolute metric (totalValueGained) says he lost value.

---

## The Alternative: Net Trade Advantage (Zero-Sum)

A zero-sum metric that measures relative trade skill:

```
netAdvantage per trade = my_side_value_now - their_side_value_now
netAdvantage per manager = sum across all trades
```

This always sums to zero across the league (by construction), making it a true measure of who consistently gets the better side of trades.

### Current Rankings Comparison

| Manager | totalValueGained (current) | Net Advantage (zero-sum) | Trades |
|---------|---------------------------|--------------------------|--------|
| lndahayo | +12,888 | +7,801 | 15 |
| thekylecasey | +5,856 | +2,838 | 10 |
| tylerpilgrim | +5,834 | +756 | 15 |
| donewton | +2,115 | +5,643 | 28 |
| gnewman4 | +1,883 | +11,470 | 19 |
| jwalters74 | +867 | -6,588 | 32 |
| brevinowens | -1,024 | +449 | 2 |
| mgaeta23 | -1,222 | +4,525 | 13 |
| jakeduf | -1,824 | -707 | 10 |
| cjsyregelas | -2,539 | -5,353 | 7 |
| wkerwin | -5,417 | -3,935 | 12 |
| zachlearningtogolf | -9,812 | -16,899 | 25 |

**Key discrepancies:**
- `gnewman4` ranks #5 by `totalValueGained` (+1,883) but #1 by net advantage (+11,470). He consistently wins trades but acquired assets that depreciated.
- `jwalters74` ranks #6 by `totalValueGained` (+867, positive!) but is actually #10 by net advantage (-6,588). He is a net loser in relative terms, masked by general market appreciation.
- `mgaeta23` appears to be losing (-1,222 value gained) but is actually #4 in net advantage (+4,525) — a skilled trader whose acquired assets happened to depreciate.

---

## Additional Findings

### Specific Logic Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Non-zero-sum ranking | High | `totalValueGained` rewards market appreciation, not trade skill. Some managers appear skilled but are just benefiting from rising markets. |
| Win rate paradox | Medium | 100% win rate with negative value gained is possible and actually observed (brevinowens). |
| 57% of value changes are negative | Informational | Player depreciation is the norm in dynasty (aging). Biases `totalValueGained` negative for managers who acquire older proven players. |
| 36% winner flips | Informational | Over a third of trades have a different winner now than at trade time. Expected for dynasty value fluctuation. |
| Zero-value sides (5 trades) | Low | Some trades have one side valued at $0 at trade time (unresolved players or picks). These auto-assign that side as "loser." |
| FAAB at $1/dollar | Low | FAAB valued at 1 point per dollar vs. players valued in thousands. Makes FAAB essentially irrelevant to scoring. Probably fine since FAAB is a minor trade asset. |

### The Valuation Source Is Sound

- **Column choice:** `value_2qb` from DynastyProcess is correct for a Superflex/2QB dynasty league.
- **Historical values:** Sourced from Git commit history with closest-date matching. Solid approach with proper fallbacks.
- **2025 picks:** Use exact pick positions post-draft, player values for current. Correct.
- **2026 picks:** Use finalized draft order with DynastyProcess exact values (e.g., "2026 Pick 1.01"). Correct.
- **2027/2028 picks:** Use tiered projections (Early/Mid/Late) based on team projections. Reasonable approximation.
- **Date matching:** Searches backwards first (preferred), then forwards, with configurable search window. Good edge case handling.

### The Margin Calculation Is Correct

```python
margin_at_trade = abs(team_a_value_then - team_b_value_then)
margin_current = abs(team_a_value_now - team_b_value_now)
swing_margin = change in the winner's advantage from then to now
```

The margin and winner logic in Stage 4 is mathematically sound. The issue is not in how individual trades are scored, but in how those scores are aggregated into manager-level rankings.

---

## Recommendation

The underlying valuation pipeline (Stages 2-3) and per-trade scoring (Stage 4) are well-built. The issue is at the aggregation layer: what metric ranks managers.

**Option A (Recommended):** Show both metrics side by side:
- "Asset Appreciation" (current `totalValueGained`) — shows who acquired assets that grew in value.
- "Net Trade Advantage" (zero-sum) — shows who consistently gets the better side of trades.

The combination tells the full story: appreciation shows portfolio growth from trades, while net advantage shows relative trade skill.

**Option B:** Replace `totalValueGained` with net advantage as the primary ranking metric.

**Option C:** Use a blended score (e.g., weighted combination) that balances absolute appreciation with relative advantage.

---

## Data Summary (as of June 2026)

- **Total trades analyzed:** 94
- **Date range:** 2025-03-14 to 2026-05-05
- **Average margin at trade:** 541 points
- **Average margin current:** 968 points
- **Average swing margin:** 1,006 points
- **Maximum margin current:** 6,961 points
- **Winner flip rate:** 36.2%
- **Sum of all totalValueGained:** +7,605 (non-zero confirms the issue)
- **Sum of all netAdvantage:** 0 (zero-sum by construction)
