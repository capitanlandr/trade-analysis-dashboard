# Three-Way Valuation Insights — DynastyProcess vs KeepTradeCut vs FantasyCalc

_Superflex · 12-team · PPR. Merged player set (in all 3 sources): **N=349**. DP data 2026-08-07 (value_2qb), KTC SF latest 2026-08-10, FC current._

**Three lenses:** DP = analyst opinion (FantasyPros Superflex ECR → exponential curve). KTC = stated preference (crowd keep/trade/cut survey, hard-capped 9999). FC = revealed preference (~1M real completed trades, uncapped).

## 1. Position over/under-valuation (Superflex)

Δranks = consensus rank − source rank, averaged per position. **Positive = that source values the position HIGHER (better rank) than the cross-source consensus.** Mean rank-percentile in parentheses.

| Position | DP Δ (pctile) | KTC Δ (pctile) | FC Δ (pctile) | Verdict |
|---|---|---|---|---|
| QB | +5.8 (58) | -10.6 (53) | +4.9 (58) | DP highest, KTC lowest |
| RB | -5.6 (46) | +4.0 (48) | +1.6 (48) | KTC highest, DP lowest |
| WR | +1.5 (51) | +2.3 (51) | -3.7 (49) | KTC highest, FC lowest |
| TE | +0.3 (48) | -1.7 (47) | +1.4 (48) | FC highest, KTC lowest |

**QB verdict:** In Superflex, QBs are pushed up hardest by **DP (+5.8 ranks vs consensus)**; KTC -10.6; FC +4.9. The gap between the most-QB-friendly and least-QB-friendly source is **16.4 rank spots** on the average QB.

## 2. Top-asset concentration & curve shape

| Source | #1 value | #1/#10 | #1/#25 | #1/#50 | top-10 share of top-50 | half-life (ranks to halve #1) |
|---|---|---|---|---|---|---|
| DP | 10232 | 1.32x | 1.75x | 2.70x | 28.1% | 31 |
| KTC | 9999 | 1.27x | 1.58x | 1.85x | 26.4% | 62 |
| FC | 10456 | 1.44x | 1.94x | 2.61x | 29.4% | 30 |

**#1 overall / top-3 in each source:**
- **DP:** Josh Allen (10232), Ja'Marr Chase (9076), Lamar Jackson (8949)
- **KTC:** Josh Allen (9999), Jahmyr Gibbs (9999), Bijan Robinson (9993)
- **FC:** Josh Allen (10456), Jahmyr Gibbs (10186), Bijan Robinson (10173)

**Curve finding:** **DP** has the steepest top (biggest #1/#50 ratio, 2.7x); **KTC** is the flattest (1.8x). KTC's 9999 hard cap compresses the very top (many elite players bunch near the ceiling), so its #1/#10 ratio is smallest; DP's exponential ECR curve and FC's uncapped market both let the top breathe.

## 3. Pick premium — who buys picks most

Scale-normalized: each pick's value as **% of that source's #1 asset**, plus its **overall rank** among all assets.

| Tier | DP %#1 (rank) | KTC %#1 (rank) | FC %#1 (rank) |
|---|---|---|---|
| 2027 Early 1st | 41.8% (#43) | 71.3% (#20) | 43.0% (#38) |
| 2027 Mid 1st | 18.9% (#84) | 54.9% (#47) | 28.3% (#86) |
| 2027 Late 1st | 9.0% (#119) | 48.8% (#70) | 21.9% (#109) |
| 2027 Early 2nd | 4.5% (#153) | 37.3% (#105) | 17.6% (#142) |
| 2027 Mid 2nd | 2.3% (#187) | 34.0% (#125) | 14.6% (#178) |
| 2027 Late 2nd | 1.3% (#222) | 31.3% (#143) | 12.7% (#216) |
| 2028 1st | 15.4% (#92) | 45.8% (#83) | 19.5% (#124) |
| 2028 2nd | 1.9% (#201) | 29.3% (#160) | 12.3% (#221) |

**Mean pick value as %-of-#1 across comparable tiers:** DP 11.9%, KTC 44.1%, FC 21.2%.

**Pick-premium verdict:** **KTC buys picks most** (44.1% of #1 asset on the average comparable tier), then FC (21.2%), then DP (11.9%). 

## 4. Where the ~4% rank disagreement concentrates

Mean max-spread (max−min rank across the 3 sources) overall = **25.3** ranks.

**By position (mean max-spread):**
- QB: 29.2
- RB: 22.0
- WR: 26.2
- TE: 24.6

**By age band (mean max-spread):**
- young(<24): 27.5  (n=104)
- prime(24-26): 22.4  (n=128)
- vet(27+): 26.4  (n=117)

**Youth market loves (market rank − DP rank, +ve = market ranks higher):**
- Cyrus Allen (WR, age 23.5): market +68 (DP #268 vs KTC #223/FC #177)
- Jalen Milroe (QB, age 23.6): market +57 (DP #291 vs KTC #224/FC #244)
- Riley Leonard (QB, age 23.9): market +54 (DP #343 vs KTC #300/FC #279)
- Jaydon Blue (RB, age 22.6): market +52 (DP #263 vs KTC #212/FC #209)
- Dont'e Thornton Jr. (WR, age 23.7): market +49 (DP #318 vs KTC #260/FC #278)
- Ja'Kobi Lane (WR, age 22.3): market +48 (DP #205 vs KTC #163/FC #151)

**Proven vets DP loves (market drops them vs DP):**
- Brandon Aiyuk (WR, age 28.4): market -140 (DP #135 vs KTC #318/FC #233)
- Tyreek Hill (WR, age 32.4): market -130 (DP #151 vs KTC #325/FC #236)
- Tua Tagovailoa (QB, age 28.4): market -52 (DP #102 vs KTC #176/FC #132)
- Aaron Rodgers (QB, age 42.7): market -49 (DP #168 vs KTC #253/FC #181)
- Jauan Jennings (WR, age 29.1): market -48 (DP #163 vs KTC #211/FC #210)
- Devaughn Vele (WR, age 28.7): market -42 (DP #273 vs KTC #314/FC #315)

**Biggest 3-way spreads (most contested assets):**
- Brandon Aiyuk (WR, age 28.4): spread 183 — DP #135, KTC #318, FC #233
- Tyreek Hill (WR, age 32.4): spread 174 — DP #151, KTC #325, FC #236
- Anthony Richardson Sr. (QB, age 24.2): spread 142 — DP #107, KTC #249, FC #216
- Cyrus Allen (WR, age 23.5): spread 91 — DP #268, KTC #223, FC #177
- Aaron Rodgers (QB, age 42.7): spread 85 — DP #168, KTC #253, FC #181
- Malik Benson (WR, age 23.8): spread 78 — DP #316, KTC #340, FC #262
- Deshaun Watson (QB, age 30.9): spread 77 — DP #190, KTC #263, FC #186
- Tua Tagovailoa (QB, age 28.4): spread 74 — DP #102, KTC #176, FC #132

**Where it lives:** disagreement concentrates in **QBs** and the **young(<24) band**, confirming the youth-vs-vet thesis — market sources (KTC/FC) reward youth/upside while DP's ECR curve rewards proven veterans.

## 5. Synthesis — how & why each calculator values things

- **DynastyProcess (analyst opinion):** a deterministic exponential of FantasyPros Superflex ECR (`value≈10295·exp(−0.0234·ecr)`). It inherits expert consensus, so it is the **slowest to move**, most **vet-friendly** (proven production ranks high), and most **QB-forward** in Superflex because ECR bakes in positional scarcity. No crowd or trade signal — pure ranking → curve.
- **KeepTradeCut (stated preference):** aggregates a crowd keep/trade/cut survey. Reacts faster than DP, leans toward **youth/upside** and name-brand rookies, but the **9999 hard cap compresses the elite tier** — the top ~10 players bunch together, muting differences among studs. Good for gut-check market consensus.
- **FantasyCalc (revealed preference):** implied values from ~1M **actual completed trades**. **Fastest to react**, uncapped so the top can separate, and it reflects what managers *actually pay* rather than say. Noisier for illiquid/rarely-traded players, but the truest read of live market clearing prices.

**Trading implications in this league:** buy players DP still ranks high but the market (KTC/FC) has soured on (aging vets) if you contend; sell youth the market over-rates vs DP if you value floor. When DP and FC agree but KTC lags, trust the trade-based signal. Use picks as currency where they're cheapest (the source valuing them lowest, DP) and cash them where richest (KTC).
