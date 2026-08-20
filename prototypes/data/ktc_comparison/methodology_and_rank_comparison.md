# DynastyProcess vs KeepTradeCut — Methodology & Rank Comparison

_Generated 2026-08-12. Data: DynastyProcess values.csv (747 valued players, scrape current),
KTC superflex playersArray (464 valued players, scraped 2026-08-11)._

## 1. How DynastyProcess computes value (recovered empirically)

DP publishes `ecr_2qb` (FantasyPros Superflex Expert Consensus Rank) and `value_2qb`.
The value is a **pure deterministic transform of the consensus rank** — no market signal.

Fitting all 747 (ecr, value) pairs:

    value_2qb  ≈  10295 · exp( −0.0234 · ecr_2qb )        R² = 0.9997

- Near-perfect exponential decay of value vs rank.
- Value halves roughly every ln(2)/0.0234 ≈ **30 ranks**.
- Power-law form fits terribly (R² < 0); a floor term adds nothing (c≈0).
- Anchor points: ecr 1 → ~10,057 · ecr 20 → ~6,448 · ecr 40 → ~4,038 · ecr 80 → ~1,584 · ecr 300 → ~9.

**Source note:** the actual R scripts (`R/values/build_values.R`) are sourced by the
`weekly-playervalues` GitHub Action but are NOT in the public `data` repo tree. The original
methodology artifact is `files/archives/workbooks/values-calculator.xlsx`. The equation above
was recovered by fitting the published output — it reproduces DP's numbers to R²=0.9997.

## 2. How KTC computes value (structural)

KTC's `superflexValues` carries `kept`, `traded`, `cut` counts per player — value is derived from
crowd **keep/trade/cut market votes**, i.e. revealed market sentiment, not a ranking curve.
Scale runs 0–9999.

## 3. The core difference

- **DynastyProcess = a curve over FantasyPros consensus rank.** Deterministic, production/redraft-flavored (ECR is analyst-driven).
- **KTC = crowd market sentiment** (would you keep/trade/cut). Reflects dynasty-community appetite, which leans harder into youth/upside and discounts age/injury.

## 4. Rank-order comparison (scale-free)

Across **447 players in both systems**, ranked by SF value:

    Spearman rank correlation ρ = 0.962   (strong agreement on overall ordering)

### KTC ranks MUCH higher than DynastyProcess (KTC loves youth/upside)
| Player | DP rank | KTC rank | Δ |
|---|---|---|---|
| Roman Wilson | 388 | 267 | +121 |
| Tahj Washington | 442 | 332 | +110 |
| Xavier Hutchinson | 381 | 296 | +85 |
| Jimmy Horn | 380 | 304 | +76 |
| Jalin Hyatt | 407 | 333 | +74 |
| Riley Leonard | 368 | 299 | +69 |
| Jalen Milroe | 291 | 223 | +68 |
| Treylon Burks | 357 | 294 | +63 |

### DynastyProcess ranks MUCH higher than KTC (DP loves proven vets)
| Player | DP rank | KTC rank | Δ |
|---|---|---|---|
| Brandon Aiyuk | 135 | 344 | −209 |
| Tyreek Hill | 150 | 347 | −197 |
| Anthony Richardson | 107 | 243 | −136 |
| Samaje Perine | 308 | 419 | −111 |
| Najee Harris | 285 | 385 | −100 |
| Zach Ertz | 349 | 443 | −94 |
| Marcus Mariota | 295 | 388 | −93 |
| Jonnu Smith | 340 | 429 | −89 |

**Read:** the two agree ~96% on ordering. Divergences are systematic — KTC's live market
prices **youth/upside** (rookies, dev QBs, post-hype WRs) above DP's ECR curve, while DP's
FantasyPros ECR still rewards **established veterans** (Aiyuk, Hill, Richardson, Najee, aging TEs)
that the dynasty market has soured on.
