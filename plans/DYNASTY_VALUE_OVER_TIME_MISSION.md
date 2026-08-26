# Mission: Plot 12 Dynasty Teams' Values Over Time (KTC-backed, daily, Season 1 → now)

## Goal (Definition of Done)

Produce a chart at DAILY granularity of all 12 teams' dynasty roster+pick value over time,
from opening day of Season 1 (2024) through today, backed by Keep Trade Cut (KTC) values.
Deliverable = (a) a tidy CSV `team_value_daily.csv` (date, roster_id, team, player_value,
pick_value, total_value) and (b) a standalone interactive HTML chart with 12 daily lines
(Superflex values, since this league is SF). Commit on a NEW branch `dynasty-value-over-time`,
do NOT push to main. Write a RESULTS.md summarizing method, coverage %, and known gaps.

## Repo

/local/home/lndahayo/projects/trade-analysis-dashboard/
Work in a NEW git branch `dynasty-value-over-time`. Never commit to main.

## League chain (VERIFIED LIVE against Sleeper 2026-08-25)

- Season 1 (2024): league_id 1101631897148493824  (name "Dynasuiiii", 12 rosters, previous_league_id=None → true origin)
- Season 2 (2025): league_id 1180814327660371968
- Season 3 (2026): league_id 1312166810505719808  (active)

Sleeper leagues chain via `previous_league_id`. Season 1 was NOT in seasons.yaml (only a
`SEASON_1_LEAGUE_ID` placeholder in plans/). ADD season_1 to pipeline/config/seasons.yaml.

## What ALREADY EXISTS (do not rebuild — reuse)

1. KTC daily PLAYER value history: prototypes/data/ktc_history/ktc_history.csv
   - cols: player_name,sleeper_id,ktc_slug,format,date,value  (format ∈ {1QB,SF})
   - 908,777 rows, daily, 2020-04-01 → 2026-08-10, 366/382 players (95.8%)
   - fetcher: prototypes/data/ktc_history/fetch_ktc_history.py (gzip-cached, polite)
   - player_map.csv maps sleeper_id → ktc_slug. _unresolved.json lists the 16 misses.
2. KTC daily PICK value history: prototypes/data/ktc_history/ktc_pick_history.csv
   - cols: pick_name,slug,format,date,value ; tiers = {Early,Mid,Late} × {1st..4th} for 2026,2027,2028 ONLY
   - fetcher: fetch_ktc_pick_history.py
3. Transaction spine (Seasons 2 & 3): pipeline/trades.json, pipeline/cumulative_processed_waiver_transactions.json,
   plus per-season raw files. Season 1 transactions are NOT cached yet — fetch them.
4. 12-team identity: pipeline/team_identity_mapping.csv (roster_id, sleeper_username, real_name, team names).
5. Existing pipeline stages (reuse their Sleeper-fetch + asset-extraction logic):
   stage1_fetch_trades.py, stage2_extract_assets.py, stage5_waiver_wire.py, pick_origin_mapping.py.

## Method (the reconstruction)

### Step A — Fetch Season 1 raw data (missing)
For league 1101631897148493824: GET /v1/league/{id} (settings/scoring — confirm Superflex),
/users, /rosters, /transactions/{week} for weeks 1..18, and the startup DRAFT
(/v1/league/{id}/drafts then /v1/draft/{draft_id}/picks) to get day-one roster composition.
Sleeper season starts: 2024 opening ~ startup draft date. Use the draft completed date as day 0.

### Step B — Build the daily roster + pick treasury ledger per team
Starting state = post-startup-draft rosters (Season 1) and post-rookie-draft each subsequent year.
Replay every trade and waiver/FA transaction in timestamp order (Sleeper txns carry `status_updated`
epoch ms → the exact date). For each day from Season 1 draft day → today, hold the as-of composition:
which players (sleeper_id) and which draft picks each of the 12 rosters owns that day.
Carry roster continuity across seasons via previous_league_id and roster_id.

### Step C — Join assets to KTC value on that date
- Players: join (sleeper_id, date, format='SF') → ktc_history.csv value. Forward-fill last known
  value for gaps ≤ 7 days. For the 16 unresolved players use manual_overrides.csv / 0 and log them.
- Picks: map each owned pick to a KTC pick tier (year+round+Early/Mid/Late) using pick_origin_mapping.py
  logic + the season's standings to infer Early/Mid/Late. Join to ktc_pick_history.csv on date.

### Step D — Normalize the pick gap (the known KTC limitation)
KTC pick history only covers 2026–2028 tiers. 2024 & 2025 picks (relevant in Season 1/2) have NO KTC
series. Back-cast them: (1) once a pick converts to a real rookie (draft slot known from Sleeper draft
results), value it at that rookie's KTC value on each date; (2) BEFORE conversion, estimate the pick's
value from the KTC pick-tier curve that DOES exist — take the stable ratio of each pick tier to the
overall value distribution on a reference date and apply that ratio to reconstruct the missing year's
tiers. Document the assumption in RESULTS.md. Do NOT fabricate precise numbers without labeling them
as back-cast estimates (add a `value_source` column: ktc_actual | forward_fill | pick_backcast | rookie_realized).

### Step E — Aggregate & plot
team_value_daily.csv: one row per (date, roster_id): sum player_value + pick_value = total_value.
Render a standalone HTML (Chart.js or plotly, offline/CDN) with 12 daily lines, team names from the
identity map, a legend, hover tooltips, and season boundary markers (2024/2025/2026 draft dates).

## Guardrails
- Superflex is the league format — use format='SF' throughout, not 1QB.
- KTC fetches must reuse the existing gzip cache and stay polite (the fetchers already do this). Do NOT
  hammer KTC; the player/pick history is already on disk, only Season-1 SLEEPER data needs fetching.
- Every value must carry a `value_source` provenance tag. Back-cast estimates must be labeled, never
  presented as real KTC observations.
- Verify row counts and date continuity (no missing days) before declaring done.
- Commit on branch dynasty-value-over-time only. Do not push to main.

## Output locations
- prototypes/data/dynasty_value_over_time/team_value_daily.csv
- prototypes/data/dynasty_value_over_time/dynasty_value_over_time.html
- prototypes/data/dynasty_value_over_time/RESULTS.md (method, coverage %, gaps, back-cast assumptions)
