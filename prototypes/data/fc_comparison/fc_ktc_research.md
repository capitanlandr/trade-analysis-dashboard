# FantasyCalc historical data + FC vs KTC trade-calculator methodology — research

**Researched:** 2026-08-12 · **Method:** web_search + web_fetch (actual pages read) + direct API/GitHub probes · Read-only.
**Confidence notation:** `!` confirmed (2+ sources / primary source) · `~` likely (1 strong source) · `?` inferred/contested.

---

## Q1 — Is there an open-source Git repo (or API) of FantasyCalc HISTORICAL values? — VERDICT: **NONE FOUND** `!`

There is **no** open-source repository of FantasyCalc value *history* analogous to `dynastyprocess/data`, and the FantasyCalc API exposes **no history endpoint**.

**API probe** (`https://api.fantasycalc.com/`, polite single hits):
- `GET /values/current?isDynasty=true&numQbs=2&numTeams=12&ppr=1` → **200**, 475 players, one snapshot only.
- `GET /values/history?...` → **404**
- `GET /values/current?...&date=2024-01-01` (date param) → **404** (param ignored / no historical selection)
- `GET /values/snapshots` → **404**
- `GET /trades` → **404**

The only backward-looking signal in the current payload is a per-player **`trend30Day`** field (30-day value delta, e.g. Josh Allen `+475`) plus moving-standard-deviation fields — a single scalar of recent change, **not** a time series. `!` (direct probe)

**GitHub search** (`api.github.com/search/repositories?q=fantasycalc`, 14 hits): every FantasyCalc repo is a **client for the *current*-values endpoint**, not a history archive —
- `dsheehan167/go-fantasycalc` (Go client), `jdegregorio/fantasycalc-cli` (CLI), `jhastings843/dynasty-hub`, `dhdhall5/sleeper-fantasy`, `msarmento42/dynasty` (personal Sleeper+FantasyCalc dashboards). None store or publish dated FC snapshots. `!`
- FantasyCalc has **no official GitHub org** publishing data. `~`

**Closest analog (for contrast):** `dynastyprocess/data` *does* publish DP value history as CSVs via a scheduled GitHub Action — its `/files` dir contains `values.csv`, `values-players.csv`, `values-picks.csv` — but these are **DynastyProcess** values, not FantasyCalc. `!` (repo contents listed)

**Bottom line:** If we want an FC history series we must **build our own daily-snapshot scraper** of `/values/current` (there is no existing dataset or history API to consume). This matches the known dashboard limitation that FC gives only a current snapshot (`value_then == value_now`).

---

## Q2 — How does FantasyCalc's TRADE CALCULATOR compute a trade? — **Sum of market-implied values; no documented stud/consolidation adjustment** `~`

- FantasyCalc assigns **one value per player**, derived by "an algorithm to calculate player trade value from **almost 1 million real fantasy football trades**" — per a **FantasyCalc-authored** guest post by Josh Cordell (FantasyCalc founder). The public API "is the exact same API that powers the rankings," returning a single `value` per player (revealed-preference market value). [FantasyDataPros / Josh Cordell of FantasyCalc](https://www.fantasydatapros.com/fantasyfootball/blog/fantasycalc/1) `!`
- The trade calculator therefore **totals each side's player/pick values and reports the difference** (each side's total + the edge). FantasyCalc publishes **no** FAQ describing a stud/starter/consolidation premium, and the payload carries no per-trade adjustment field — only a `starter` boolean and `combinedValue` (redraft+dynasty). Behavior is effectively a **naive sum** of market values. `~` (inference from FC-authored value definition + API structure + absence of any documented adjustment)
- Community write-ups describe FantasyCalc-style analyzers as exactly this "add up the totals" behavior — and warn it will tell you that you "won" a stud-for-depth deal "by a landslide" because total value is higher, which is the tell-tale signature of an **un-adjusted sum**. [ponderworthy.com](https://ponderworthy.com/how-to-use-a-trade-analyzer-fantasy-football-dynasty-tool-without-ruining-your-team-1e59) `~`

---

## Q3 — How does KeepTradeCut's TRADE CALCULATOR compute a trade? — **Sum PLUS an explicit "Value Adjustment" (stud tax)** `!`

Directly from **KTC's own FAQ** ([keeptradecut.com/frequently-asked-questions](https://keeptradecut.com/frequently-asked-questions)) `!`:
- **"What is the 'Value Adjustment'?"** — *"Trading is more than simple addition. We add value to the side of the trade that's giving up more when you look at roster spots, players' 'stud' factor, etc. This is our way of countering … trade calculations that say 12 third round picks are a fair deal for DeAndre Hopkins. The actual adjustment is reverse engineered from the player the lesser side needs to have added to even the trade."*
- **"How is the 'Value Adjustment' Determined?"** — factors: *"the difference in value of the players involved, how much of a 'stud' the players involved are, the number of players of lesser value included in the trade … and a lil fancy math,"* then **reverse-engineered from the player needed to even the trade.**
- Underlying player values come from an **adapted ELO algorithm** over crowdsourced Keep/Trade/Cut votes (stated preference), tuned to reflect "the scarcity of studs." KTC Power Rankings explicitly note *"Just adding up player values isn't enough!"* and apply the same stud-vs-depth weighting.
- Corroboration: multiple secondary write-ups describe the KTC adjustment as a "package tax" / "stud tax" that rewards consolidation. [calculator.city KTC pages](https://cal3.calculator.city/ktc-trade-calculator/) `!`
- Note: KTC states it has **no official API/CSV** and forbids scraping in its T&Cs — so KTC values used elsewhere come from scrapers, and KTC likewise publishes no historical dataset.

---

## Q4 — Comparison, and what it means for our dashboard

| | FantasyCalc | KeepTradeCut |
|---|---|---|
| Value source | ~1M **real completed trades** (revealed preference) | Crowdsourced **Keep/Trade/Cut votes** via adapted ELO (stated preference) |
| Trade-calc math | **Sum** of side totals, report difference `~` | **Sum + "Value Adjustment"** (stud/consolidation premium), reverse-engineered from the evening asset `!` |
| Stud/depth handling | None documented → 2-for-1 can look "even" on raw totals | Explicitly boosts the side giving up the single best player |
| History available | **No** — snapshot only, `trend30Day` scalar `!` | No public API/CSV; no history |

**What this means for our dashboard:** our dashboard **sums asset values** on each side, so its trade math is **philosophically the same as FantasyCalc's (naive sum), NOT KTC's adjusted model.** `!` Practically:
- When we display **KTC values** in a summed view, we are **stripping KTC's headline feature** (the stud tax). A stud-for-depth package that KTC's own calculator would flag as unfair will read as "fair/even" in our summed dashboard. This is a known interpretation gap to surface to users. `~`
- FC values in a summed view are self-consistent with how FantasyCalc itself presents trades, so no philosophy mismatch there — the only FC limitation remains the **lack of history** (`value_then == value_now`). `!`
- If we want KTC-faithful trade verdicts we'd need to re-implement a consolidation adjustment (a decreasing multiplier as the number of lesser assets on a side grows, scaled by the top asset's "stud" gap) on top of summed values.

---

## Open Questions
1. **Exact FC adjustment = truly zero?** FantasyCalc publishes no trade-calc methodology page; "naive sum, no adjustment" is inferred from the FC-authored value definition + API structure + community observation, not an explicit FC statement. Confidence `~`, not `!`. Next step: inspect the FantasyCalc trade-calculator front-end JS/network calls to confirm no client-side premium is applied.
2. **KTC adjustment formula.** KTC deliberately withholds the "fancy math"; only the *inputs* (value gap, stud factor, count of lesser assets) and the reverse-engineering approach are disclosed. An exact reproduction would need empirical curve-fitting against KTC's live calculator.
3. **FC history build.** No existing dataset — a daily `/values/current` snapshot cron is the only path to an FC time series; confirm the endpoint's ToS permits archived personal use.

## Sources
1. KeepTradeCut FAQ (primary — Value Adjustment, ELO values, no API) — https://keeptradecut.com/frequently-asked-questions
2. FantasyDataPros guest post by Josh Cordell of FantasyCalc (primary — ~1M trades, API == rankings, single value) — https://www.fantasydatapros.com/fantasyfootball/blog/fantasycalc/1
3. FantasyCalc API direct probe — https://api.fantasycalc.com/values/current (200) ; /values/history, ?date=, /snapshots, /trades (404)
4. GitHub repo search `q=fantasycalc` (14 repos, all current-value clients) — https://api.github.com/search/repositories?q=fantasycalc
5. dynastyprocess/data (contrast — DP publishes history CSVs, not FC) — https://github.com/dynastyprocess/data
6. ponderworthy — critique of naive-sum trade analyzers — https://ponderworthy.com/how-to-use-a-trade-analyzer-fantasy-football-dynasty-tool-without-ruining-your-team-1e59
7. calculator.city KTC pages (secondary — "stud tax"/package adjustment) — https://cal3.calculator.city/ktc-trade-calculator/
