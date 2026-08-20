# Prod DB vs KeepTradeCut — Value Comparison & Impact Analysis

_Generated 2026-08-10. Read-only against production. League format: **Superflex** (both leagues carry a SUPER_FLEX roster slot), so the primary KTC comparison uses `format=SF`._

## Plain-English verdict

**The two value systems agree strongly on *who is worth more* (rank correlation up to 0.96), but they disagree enough on *by how much* that nearly half of individual trade verdicts flip and the middle of the manager leaderboard reshuffles substantially.** The top and bottom of the manager standings are stable (your #1 and the last-place 3-team-trade bucket don't move), but six of the middle managers move by 2+ ranks, including two dramatic swings. Bottom line: **headline rankings are directionally robust, but per-trade "who won" calls and mid-pack manager standings are NOT — they are an artifact of which value source you trust.**

## 1. Coverage

| Metric | Value |
|---|---|
| Player-asset occurrences in prod trades | 231 |
| Joined to a KTC value | **223 (96.5%)** |
| No KTC data (retired / deep-bench) | 8 |
| Distinct trades analyzed | 105 (103 with 2+ clean sides) |

The 8 unjoined assets are traded-away players KTC does not track dynasty value for: DeAndre Hopkins, Taysom Hill, Noah Fant, Kareem Hunt, AJ Dillon, Zach Wilson, Tutu Atwell, Joe Mixon. They are marked `no_ktc_data` and excluded from value math (their trade sides fall back to the prod→KTC scale mapping — see Method).

## 2. Agreement (correlation)

Prod and KTC are on **different scales** (prod player values run ~0–8,600 with median ~275; KTC SF runs ~500–9,999 with median ~2,562). Raw deltas therefore look huge (mean abs delta ≈ 2,100–2,200) but that is scale, not disagreement. The meaningful signal is correlation:

| Timepoint | Pearson | Spearman (rank) | n |
|---|---|---|---|
| At trade date | 0.909 | 0.826 | 223 |
| Current (today) | 0.929 | **0.961** | 223 |

**Interpretation:** current valuations are highly rank-correlated (0.96) — the systems largely agree on ordering today. The at-trade Spearman is lower (0.83), i.e. they disagreed more about historical/point-in-time values, which is exactly where trade verdicts get decided.

## 3. Individual trade verdicts — these flip a LOT

Recomputed each trade's winner by summing each side on the KTC scale (players = actual KTC value; picks/FAAB mapped via the prod→KTC linear fit `ktc ≈ 0.820·prod + 2336.5`). A "flip" = the winning manager changes vs prod.

| Timepoint | Verdicts that flip | of trades |
|---|---|---|
| At trade date | **44** | 103 (43%) |
| Current | **33** | 103 (32%) |
| Current, **players-only** side sums (robustness) | see `trade_verdicts_compare.csv` col `ktc_playersonly_*` | |

Why so many? Most flips are on **close trades** where the two systems' small valuation differences tip a near-even margin. `jwalters74` and `donewton` appear in many flips — their trades tend to be the closest, so they are the most source-sensitive. Full lists (with prod-winner → KTC-winner) are in `trade_verdicts_compare.csv`; the flipped current-timepoint trades number 33 and include e.g.:

- 2025-09-25 `...6251264`: prod=gnewman4 → **KTC=lndahayo**
- 2026-03-10 `...1378816`: prod=tylerpilgrim → **KTC=jwalters74**
- 2026-08-03 `...2487040`: prod=jwalters74 → **KTC=cjsyregelas**

## 4. Manager rankings — stable at the ends, churny in the middle

Net value gained (current) = Σ received_now − Σ given_now, per manager, ranked. `manager_rankings_compare.csv` has the full table.

| Manager | Prod rank | KTC rank | Δ | Prod net | KTC net |
|---|---|---|---|---|---|
| lndahayo | 1 | 1 | 0 | 20,858 | 21,227 |
| gnewman4 | 2 | 2 | 0 | 11,362 | 17,462 |
| cjsyregelas | 3 | 6 | **−3** | 7,150 | 12,980 |
| donewton | 4 | 12 | **−8** | 3,359 | −18,874 |
| mgaeta23 | 5 | 5 | 0 | 3,070 | 14,482 |
| tylerpilgrim | 6 | 8 | −2 | 2,512 | 3,045 |
| thekylecasey | 7 | 4 | **+3** | 1,876 | 14,746 |
| jakeduf | 8 | 7 | +1 | 69 | 4,832 |
| brevinowens | 9 | 9 | 0 | −130 | −1 |
| zachlearningtogolf | 10 | 3 | **+7** | −612 | 14,756 |
| wkerwin | 11 | 10 | +1 | −4,342 | −5,630 |
| jwalters74 | 12 | 11 | +1 | −6,584 | −11,238 |
| 3-team | 13 | 13 | 0 | −38,588 | −67,788 |

- **8 of 13 managers reorder**; **19 of 78 pairwise orderings invert.**
- **Biggest movers:** `zachlearningtogolf` **+7** (10th → 3rd) and `donewton` **−8** (4th → 12th). Under KTC, donewton's acquisitions are valued far lower (net goes sharply negative), while zachlearningtogolf's look much better.
- **Robust:** #1 (lndahayo), #2 (gnewman4), and last place (3-team bucket) are unchanged in both systems.

## 5. Largest metric swings

**Biggest per-player valuation-rank disagreements (current, among 136 compared players)** — where prod and KTC most disagree on a player's standing:

| Player | Prod val | KTC val | Prod rank | KTC rank | Δrank |
|---|---|---|---|---|---|
| Tyreek Hill | 289 | 1,266 | 63 | 130 | −67 (prod rates him higher) |
| Tua Tagovailoa | 944 | 2,597 | 40 | 78 | −38 |
| Geno Smith | 269 | 2,160 | 67 | 99 | −32 |
| Jauan Jennings | 216 | 2,293 | 70 | 93 | −23 |
| Tank Bigsby | 75 | 2,640 | 95 | 73 | +22 (KTC rates him higher) |
| Justin Fields | 79 | 1,881 | 93 | 114 | −21 |
| Tank Dell | 80 | 2,643 | 92 | 72 | +20 |
| Jacory Croskey-Merritt | 199 | 3,085 | 75 | 56 | +19 |

These per-player gaps are the root cause of both the verdict flips and the manager-rank churn: prod is comparatively bullish on aging vets (Hill, Tua, Geno) while KTC is comparatively bullish on younger upside/depth (the Tanks, Croskey-Merritt, Roman Wilson).

## Method & caveats

- **Alignment:** prod `value_at_trade` compared to the KTC SF value on the trade date (nearest KTC date ≤ trade date when the exact day is missing; trades predating KTC coverage use KTC's earliest point). Prod `value_current` compared to KTC's latest date (2026-08-10).
- **Scale bridge for whole-trade sums:** players use actual KTC values; picks and FAAB (which KTC doesn't value) are mapped from prod onto the KTC scale with a linear fit estimated from the 223 players that have both values (`ktc ≈ 0.820·prod + 2336.5`). A players-only verdict column is included as a robustness check.
- **Correlation** uses only player assets with both values; scale-difference deltas are reported but rank stats (Spearman) are the fair cross-scale measure.
- This analysis is a *sensitivity study*, not a claim that KTC is "correct" — it quantifies how much the dashboard's conclusions depend on the choice of value source.

## Artifacts

- `asset_value_comparison.csv` — per-asset prod vs KTC (at-trade + current) with deltas and coverage flag.
- `trade_verdicts_compare.csv` — per-trade prod vs KTC winner/margin (at-trade, current, players-only) with flip flag.
- `manager_rankings_compare.csv` — per-manager prod rank vs KTC rank with rank delta.
