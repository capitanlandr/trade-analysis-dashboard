# Dynasty Value Over Time — Results

Daily reconstruction of all **12 teams' dynasty value** (roster players + draft-pick
treasury) for the league **"Dynasuiiii"**, from **Season 1 startup-draft day
(2024-08-14)** through the **last Keep Trade Cut observation (2026-08-11)**, in the
league's native **Superflex (SF)** format.

## Deliverables (this directory)

| File | What it is |
|---|---|
| `team_value_daily.csv` | Tidy daily table: `date, roster_id, team, player_value, pick_value, total_value` + provenance columns. **8,736 rows = 728 continuous days × 12 teams.** |
| `dynasty_value_over_time.html` | Standalone interactive chart — 12 daily SF lines, click-to-isolate legend, hover-highlight + ranked tooltip, Total/Players/Picks toggle, rookie-draft boundary markers, light/dark. |
| `reconstruct.py` | The reconstruction engine (holdings + picks + KTC join + provenance). Re-runs in ~2s. |
| `build_chart.py` | Renders the HTML from the CSV. |
| `_coverage.json` | Machine-readable coverage counters. |

Source Sleeper pull (fetched fresh, all 3 seasons): `pipeline/season_1/season1_sleeper_raw.json`
(`pipeline/season_1/fetch_season1.py`). KTC history reused from disk (not re-hammered):
`prototypes/data/ktc_history/{ktc_history.csv, ktc_pick_history.csv}`.

## League chain (verified live 2026-08-25)

- **Season 1 (2024)** `1101631897148493824` — "Dynasuiiii", 12 rosters, `previous_league_id=None` → true origin. Startup = 22-round **auction**, completed 2024-08-14. Confirmed Superflex (roster has a `SUPER_FLEX` slot).
- **Season 2 (2025)** `1180814327660371968` — 2025 linear rookie draft 2025-04-30.
- **Season 3 (2026)** `1312166810505719808` — 2026 linear rookie draft 2026-04-27 (active; 2026 NFL season not yet started as of the data window).

`season_1` was added to `pipeline/config/seasons.yaml` (static).

## Method

### 1. Player holdings — snapshot-anchored, per league-season (validated exact)

Each completed league's `/rosters` endpoint is **frozen at that season's rollover**, giving
three ground-truth anchors: S1-final, S2-final, S3-current. The timeline is rebuilt in three
segments, each *opened* on the prior season's frozen snapshot so drift cannot accumulate:

- **S1 opening (2024-08-14)** = the startup auction results. The auction stored `roster_id`
  on a **different numbering than the league** (draft roster 2's players are league roster 6's,
  etc.). We recover the mapping **π** by maximum player-overlap bijection between the auction's
  per-roster player sets and S1-final `/rosters`, then re-key the startup by π. (π is derived in
  code, not hard-coded.) Replaying S1 transactions from the π-keyed opening reproduces **S1-final
  with 0 missing players** (4 late-offseason drops are corrected by the next segment's snapshot).
- **S2 opening** = S1-final snapshot; replay S2 transactions + add 2025 rookies on 2025-04-30
  → reproduces **S2-final EXACTLY** (0 missing / 0 extra).
- **S3 opening** = S2-final snapshot; replay S3 transactions + add 2026 rookies on 2026-04-27
  → reproduces **S3-current EXACTLY** (0 missing / 0 extra).

All transactions (`trade`, `waiver`, `free_agent`, `commissioner`; `status=complete` only) are
applied in `status_updated` order. Sleeper's leg-1 feed spans each offseason (S2 leg-1 covers
2025-01→2025-09; S3 leg-1 covers 2026-01→2026-08), so intra-league movement is complete — the
only cross-season gaps are bridged by the frozen snapshots. **End-to-end holdings validation vs.
the live current roster: 0 missing, 0 extra.**

`roster_id → owner` is identical across all three seasons, so roster continuity is by `roster_id`.
(The `pick_origin_mapping.py` roster→owner table in the pipeline disagrees with reality and was
**not** used; `team_identity_mapping.csv` matches Sleeper and supplies team names.)

### 2. Draft-pick treasury

Picks are assets keyed `(class_year, round, origin_roster)`, endowed to their origin at t0 and
reassigned by trade `draft_picks` entries in timestamp order (owner = `owner_id`). A class is
**counted** only while it is an outstanding future pick — inside its tradeable window and before
its rookie draft:

| Class | Counted window | Basis |
|---|---|---|
| 2025 | 2024-08-14 → 2025-04-30 | converts at 2025 draft |
| 2026 | 2024-08-14 → 2026-04-27 | converts at 2026 draft |
| 2027 | 2024-08-14 → end | outstanding all timeline |
| 2028 | 2025-04-30 → end | enters window after 2025 draft |
| 2029 | 2026-04-27 → end | enters window after 2026 draft |

On its rookie-draft day a class **converts**: the pick stops counting and the drafted rookie enters
player holdings (see provenance `rookie_realized`). Pick **tier** (Early/Mid/Late) comes from the
origin roster's draft slot — *exact* for drafted classes (2025 ← 2024 standings, 2026 ← 2025
standings, via each rookie draft's `slot_to_roster_id`, slot 1 = worst), and for undrafted future
classes (2027–2029) the **last completed season's standings (2025 → the 2026 draft order) are used
as the tier proxy**, since the determining seasons have not been played.

### 3. KTC value join (Superflex)

- **Players:** `(sleeper_id, date, SF)` → `ktc_history.csv`. Missing dates forward-filled from the
  last known value across gaps **≤ 7 days**. Players outside KTC's dynasty universe (kickers, DEF,
  retired/deep-bench churn — KTC only tracks ~380–500 relevant assets) resolve to **0** and are
  logged as `no_ktc`.
- **Picks:** `(year, tier, round, date, SF)` → `ktc_pick_history.csv` (same ≤7-day fill).

### 4. The pick gap and its back-cast (the one modeled estimate)

KTC's pick series exist **only for 2026, 2027, 2028 tiers** (starting 2023-09, 2024-08-31,
2025-08-16 respectively). Classes/periods with no KTC series are **back-cast** and labelled — never
presented as observed KTC:

- **2025 picks** (all of Season 1, until they convert): no KTC series ever. Anchored to the **2026
  same-tier/round** value on each date, scaled by the empirical **nearest-vs-next-class factor
  `f_near = 1.084`** (median ratio of consecutive-class same-tier SF values across the pick history).
  2025 is the *nearer* class, so `value ≈ 2026_tier × f_near`.
- **2027 before 2024-08-31 / 2028 before 2025-08-16 / all 2029:** anchored to the nearest
  KTC-covered class one step nearer, scaled by `1/f_near` (further-out discount).

All back-cast values carry `value_source = pick_backcast`. This is a class-distance estimate off
the *stable shape* of the KTC pick curve; it does not model class-specific strength.

### Provenance tags (`value_source`) — every dollar is attributed

`team_value_daily.csv` keeps the 6 canonical columns **plus** a full provenance decomposition:
`pv_ktc_actual, pv_forward_fill, pv_rookie_realized` (player) and `pk_ktc_actual, pk_backcast`
(pick), + `n_players_no_ktc`. Player+pick sub-columns sum exactly to `player_value`/`pick_value`.

## Coverage & provenance (whole 728-day window)

- **Holdings accuracy:** reconstructed current roster == live Sleeper roster, **0 discrepancies**.
- **Date continuity:** 728/728 days present, every day has all 12 teams. No gaps.
- **Player-slot KTC coverage:** **86.5%** of roster player-days carry a KTC value; the 13.5%
  `no_ktc` are dynasty-irrelevant (K/DEF/retired/transient waiver churn) and correctly valued 0.
- **Value-weighted provenance** (share of all value summed over 8,736 team-days):
  - Players = **69.2%** of total value · Picks = **30.8%**.
  - Player value: **88.8% ktc_actual**, 0.5% forward_fill, **10.7% rookie_realized**.
  - Pick value: **78.0% ktc_actual**, **22.0% pick_backcast**.

## Final-day standings by total SF value (2026-08-11)

| # | Team | Total | | # | Team | Total |
|--|--|--|--|--|--|--|
| 1 | The Federal Reserve | 157,639 | | 7 | Loading… | 119,457 |
| 2 | Lisan al-Caleb | 140,319 | | 8 | Mostly Washed | 118,932 |
| 3 | All You Need Is LOVE | 135,415 | | 9 | Cártel de Breece y Puka | 116,976 |
| 4 | Gaeta Spur FC | 129,499 | | 10 | 208 Ferrari Way | 112,621 |
| 5 | Golden Hour | 124,657 | | 11 | Omar Comin | 106,977 |
| 6 | Rashid Shaheed Truthers | 120,557 | | 12 | Mommy Rainier | 103,921 |

## Known gaps & caveats

1. **Series ends 2026-08-11, not literal "today" (2026-08-26).** That is the last KTC observation
   on disk; the ≤7-day forward-fill rule does not reach 15 days, and we do **not** fabricate values
   past the last real KTC data. This ~2-week tail is the only shortfall vs. "through today."
2. **2025 & 2029 pick values, and the first ~17 days of 2027, are back-cast estimates**
   (`pick_backcast`, 22% of pick value / ~7% of total value), not observed KTC. They use the
   class-distance shape of the existing KTC curve; class-specific strength is not modeled.
3. **Future-class pick tiers (2027–2029) use the last completed season (2025) standings as a proxy**
   for Early/Mid/Late, because the seasons that set those draft orders have not been played.
4. **Startup roster re-keying (π).** Two teams (draft rosters 4↔league 7 and 7↔league 5) had weak
   direct player overlap due to heavy Season-1 churn, but π is a clean 12-way bijection and the
   S1 replay validates to S1-final with 0 missing, so day-0 attribution is sound.
5. **Small season-boundary steps** are visible in the chart on rookie-draft days — these are the
   intentional resync to the authoritative frozen snapshot plus the rookie-class conversion, not
   noise.
6. **`no_ktc` players count 0**, matching KTC's dynasty-relevant universe; a bench kicker
   contributing nothing to dynasty value is intended, not a coverage bug.

## Reproduce

```bash
python3 pipeline/season_1/fetch_season1.py                                   # Sleeper only (polite)
python3 prototypes/data/dynasty_value_over_time/reconstruct.py               # validate + build CSV
python3 prototypes/data/dynasty_value_over_time/build_chart.py               # build HTML
```
