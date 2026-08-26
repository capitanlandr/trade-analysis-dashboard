# Dynasty Value Over Time — Results (DynastyProcess edition)

Daily-rendered reconstruction of all **12 teams' dynasty value** (roster players +
draft-pick treasury) for the league **"Dynasuiiii"**, from **Season 1 startup-draft
day (2024-08-14)** through the **latest DynastyProcess (DP) weekly snapshot
(2026-08-21)**, in the league's native **Superflex (SF / 2QB)** format.

This mirrors the KTC edition (`../dynasty_value_over_time/`) — same roster+pick
day-by-day replay, same chart shape — with the **value join swapped from Keep Trade
Cut to DynastyProcess `value_2qb`**.

## Deliverables (this directory)

| File | What it is |
|---|---|
| `team_value_daily_dp.csv` | Tidy daily table: `date, roster_id, team, player_value, pick_value, total_value` + DP provenance columns. **8,856 rows = 738 continuous days × 12 teams.** |
| `dynasty_value_over_time_dp.html` | Standalone interactive chart — 12 daily SF lines, click-to-isolate legend, hover-highlight + ranked tooltip, Total/Players/Picks toggle, rookie-draft boundary markers, light/dark. |
| `dynasty_value_over_time_dp.png` | Static PNG of the 12-team total-value chart. |
| `fetch_dp.py` | Pulls DP `values.csv` weekly git-history snapshots, crosswalks to Sleeper ids, emits `dp_players_history.csv` + `dp_picks_history.csv`. |
| `reconstruct_dp.py` | The reconstruction engine (holdings + picks + DP join + provenance). |
| `build_chart_dp.py` / `render_png_dp.py` | Render HTML / PNG from the CSV. |
| `dp_players_history.csv` | Compact weekly player series: `sleeper_id, date, value_2qb` (55,000 rows). |
| `dp_picks_history.csv` | Weekly pick-tier series: `year, round, tier, date, value` (2,592 rows). |
| `_dp_fetch_meta.json` / `_coverage_dp.json` | Machine-readable cadence + coverage counters. |
| `raw_dp/` | Cached raw `values.csv` at each commit SHA (fetch is idempotent). |

## Value source: DynastyProcess `value_2qb`, WEEKLY cadence

- **Source repo:** `github.com/dynastyprocess/data`, path `files/values.csv`. Column
  `value_2qb` is used because the league is Superflex/2QB. Column `fp_id` is the
  FantasyPros id.
- **No daily feed exists.** DP publishes `values.csv` and overwrites it in place; the
  real time series lives in the file's **git commit history**. We page the GitHub
  commits API for that path, take each commit's author date + SHA, keep the **latest
  commit per ISO week**, and fetch `values.csv` at each SHA via
  `raw.githubusercontent.com/dynastyprocess/data/<SHA>/files/values.csv`.
- **True cadence is WEEKLY.** **96 weekly snapshots** span **2024-08-16 → 2026-08-21**,
  **median gap 7 days**, with **one ~63-day offseason gap** (max_gap = 63d). We do
  **not** fabricate daily points. Each player's / pick-tier's latest weekly value is
  **forward-filled ≤ 7 days** to render continuous daily lines; gaps longer than the
  7-day fill window (the offseason hole and the pre-first-snapshot days) are left as
  **line breaks**, not zeros.

### fp_id → sleeper_id crosswalk

`files/db_playerids.csv` has `fantasypros_id` + `sleeper_id`. We map
`fp_id → fantasypros_id → sleeper_id`. Crosswalk size 4,869; **99.5% of DP player
rows** with an `fp_id` resolve to a Sleeper id (`fp_map_coverage = 99.49%`).

## Method

### 1. Player holdings — copied verbatim from the KTC reconstruction (validated exact)

The roster+pick day-by-day replay is identical to the KTC edition: snapshot-anchored
per league-season across Season 1 `1101631897148493824` → Season 2
`1180814327660371968` → Season 3 `1312166810505719808`, with the startup-auction
roster-id remap (π, a max-player-overlap bijection) recovered in code. **End-to-end
holdings validation vs. the live current roster: 0 missing, 0 extra.**

### 2. Draft-pick treasury and DP pick-tier aggregation

Picks are assets keyed `(class_year, round, origin_roster)`, endowed at t0 and
reassigned by trade `draft_picks` in timestamp order; a class counts only inside its
tradeable window and before its rookie draft, then converts to the drafted rookie.

DP labels picks per **exact slot** (`"2026 Pick 1.07"`) for the near class and by
**named tier** (`"2027 Early 1st"`) for the next class. The reconstruction values picks
by **TIER** (Early = slots 1–4, Mid = 5–8, Late = 9–12, per round). We aggregate DP's
per-slot values into that tier scheme by **averaging the DP slot values within each
`(year, round, tier)`** on each snapshot date, and read named-tier rows directly.

**DP pick coverage:** DP publishes only the **near draft classes** — 2024, 2025, 2026,
2027 (2026 picks appear from 2025-01-03, 2027 from 2026-01-02). The league counts
classes 2025–2029. Where DP has no series for a class/date (all of **2028 and 2029**,
plus the pre-coverage windows of 2026/2027), the pick is tagged
`value_source = dp_unavailable` and valued **0 — never fabricated**. This is why the
`dp_unavailable` share of pick-slot-days is high (61.7%); it is honest absence, not a
bug. Unlike the KTC edition there is **no back-cast** — DP either has the class or it
does not.

### 3. Provenance tags (`value_source`) — every dollar is attributed

`team_value_daily_dp.csv` carries the 6 canonical columns **plus** a DP provenance
decomposition: `pv_dp_actual, pv_forward_fill` (player) and `pk_pick_tier,
pk_dp_unavailable` (pick), + `n_players_no_dp`.

- players : `dp_actual` (exact weekly snapshot value) | `forward_fill` (last weekly
  value carried ≤7 days) | `no_dp` (outside DP's dynasty universe → 0).
- picks : `pick_tier` (DP tier value, actual or ≤7-day fill) | `dp_unavailable`
  (class/date DP does not publish → 0).

## Coverage & provenance

- **Holdings accuracy:** reconstructed current roster == live Sleeper roster,
  **0 discrepancies**.
- **Date continuity:** 738/738 days present, every day has all 12 teams. The 70 days
  in DP-coverage holes (2 pre-first-snapshot days + a 13-day and a 55-day offseason
  gap) render as **line breaks** in the chart, not zeros.
- **Player-slot DP coverage:** **89.0%** of roster player-days carry a DP value; the
  11.0% `no_dp` are dynasty-irrelevant (K/DEF/retired/deep-bench churn) and correctly
  valued 0.
- **Value-weighted provenance** (share of all value summed over team-days):
  - Players = **87.3%** of total value · Picks = **12.7%**.
  - Player value: **14.4% dp_actual**, **85.6% forward_fill** — expected, since a
    WEEKLY series rendered daily is a real snapshot 1 day in 7 and a ≤7-day carry the
    other 6. This is the documented cadence, not missing data.
  - Pick value: 100% `pick_tier` (the `dp_unavailable` classes contribute 0).

## Final-snapshot standings by total SF value (2026-08-21)

| # | Team | Total | Players | Picks |
|--|--|--|--|--|
| 1 | The Federal Reserve | 62,627 | 59,330 | 3,297 |
| 2 | Omar Comin | 46,033 | 45,997 | 36 |
| 3 | Loading… | 45,465 | 45,292 | 173 |
| 4 | 208 Ferrari Way | 44,953 | 44,864 | 89 |
| 5 | All You Need Is LOVE | 43,364 | 37,878 | 5,486 |
| 6 | Golden Hour | 39,031 | 37,877 | 1,154 |
| 7 | Lisan al-Caleb | 36,447 | 30,107 | 6,340 |
| 8 | Mostly Washed | 35,449 | 32,963 | 2,486 |
| 9 | Rashid Shaheed Truthers | 35,406 | 35,108 | 298 |
| 10 | Cártel de Breece y Puka | 34,849 | 34,338 | 511 |
| 11 | Mommy Rainier | 25,552 | 13,941 | 11,611 |
| 12 | Gaeta Spur FC | 25,308 | 21,209 | 4,099 |

(Rankings differ from the KTC edition because DP and KTC value players and picks on
different scales and philosophies. The ordering is DP's view, not a correction to KTC.)

## Known gaps & caveats

1. **Weekly cadence, daily render.** 86% of rendered player-value is forward-fill
   between weekly snapshots. The underlying signal changes at most weekly; daily lines
   are a continuous view of a weekly truth.
2. **One ~63-day offseason DP gap** (and 2 pre-first-snapshot days) exceed the 7-day
   fill window and render as line breaks. This is honest absence.
3. **Picks 2028–2029 and pre-coverage 2026/2027 windows are `dp_unavailable` = 0.** DP
   only publishes near classes; there is no back-cast here (the KTC edition estimated
   these; DP leaves them absent). This depresses pick value for teams holding far-out
   picks (visible in the picks-only toggle).
4. **Future-class pick tiers (2027–2029) use the last completed season (2025) standings
   as the Early/Mid/Late proxy**, same as the KTC edition, because the seasons that set
   those draft orders have not been played. (2028/2029 are moot here since DP does not
   value them.)
5. **`no_dp` players count 0**, matching DP's dynasty-relevant universe — intended, not
   a coverage bug.

## Reproduce

```bash
python3 prototypes/data/dynasty_value_over_time_dp/fetch_dp.py          # DP weekly snapshots (git history)
python3 prototypes/data/dynasty_value_over_time_dp/reconstruct_dp.py    # validate + build CSV
python3 prototypes/data/dynasty_value_over_time_dp/build_chart_dp.py    # build HTML
python3 prototypes/data/dynasty_value_over_time_dp/render_png_dp.py     # build PNG
```
