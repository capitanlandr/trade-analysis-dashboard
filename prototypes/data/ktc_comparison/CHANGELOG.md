# CHANGELOG — Prod DB vs KTC Value Comparison

Working dir: `/local/home/lndahayo/projects/trade-analysis-dashboard`. **Read-only against production** (GET-only to Prod API + reuse of local prod snapshots and previously-acquired KTC data). No DynamoDB writes, no deploys, no AWS mutations, no git commits. All output under `data/ktc_comparison/`. No pre-existing repo files were modified, so no `.bak` backups were needed.

---

## 2026-08-10 — Setup & method decisions

- **League format = Superflex.** Verified via Sleeper `GET /v1/league/<id>` for both leagues (`1180814327660371968`, `1312166810505719808`): each `roster_positions` contains a `SUPER_FLEX` slot. → Primary KTC comparison uses `format=SF`.
- **Prod value source = DynastyProcess/Git** (from `pipeline/asset_values_cache.csv` `value_source_*` columns), NOT KTC — so the comparison is meaningful.
- **Scale finding:** prod player `value_current` median ≈ 275 (range 0–8,579); KTC SF latest median ≈ 2,562 (range 498–9,999). Different scales → raw deltas reported but **Spearman rank correlation** used as the fair cross-scale agreement measure; whole-trade sums bridged via a linear fit (below).
- **Identity join:** prod cache uses player *names*; KTC history uses `sleeper_id`. Linked cache names → sleeper_id via `data/ktc_history/player_map.csv` (138) + Sleeper master fallback (6) = **144/144 names (100%)**.

## 2026-08-10 — Step 2-3: per-asset comparison (`build_comparison.py`)

- Wrote `data/ktc_comparison/asset_value_comparison.csv`: per player-asset occurrence, prod vs KTC value at trade date and current, with delta and `ktc_coverage` flag.
- **Trade-date alignment rule:** KTC value on the trade date; if that exact day is absent, the nearest KTC date ≤ trade date; if the trade predates KTC coverage, KTC's earliest point. Current = KTC latest date (2026-08-10).
- **Result:** 231 asset rows, **223 joined to KTC (96.5%)**, 8 `no_ktc_data` (DeAndre Hopkins, Taysom Hill, Noah Fant, Kareem Hunt, AJ Dillon, Zach Wilson, Tutu Atwell, Joe Mixon).
- **Correlation:** at-trade Pearson 0.909 / Spearman 0.826; current Pearson 0.929 / Spearman 0.961.

## 2026-08-10 — Step 4-6: impact recomputation (`recompute_impact.py`)

- **Pick/FAAB handling:** KTC does not value draft picks or FAAB. To sum whole trade sides on one scale, picks+FAAB are mapped from prod onto the KTC scale via a linear fit from the 223 dual-valued players: **`ktc ≈ 0.820·prod + 2336.5`**. Players use their actual KTC value. A **players-only** verdict is also emitted (`ktc_playersonly_*` columns) as a robustness check that doesn't rely on the fit.
- **Trade verdicts** → `trade_verdicts_compare.csv`. Winner flips vs prod: **44/103 at trade date, 33/103 current.** Flips concentrate on close trades (jwalters74, donewton).
- **Manager rankings** (net value gained, current) → `manager_rankings_compare.csv`. **8/13 managers reorder; 19/78 pairwise inversions.** Biggest movers: zachlearningtogolf +7 (10→3), donewton −8 (4→12). Stable: lndahayo #1, gnewman4 #2, 3-team #13.
- **Largest per-player rank disagreements** (current): prod bullish on Tyreek Hill (+67 rank vs KTC), Tua, Geno Smith; KTC bullish on Tank Bigsby, Tank Dell, Jacory Croskey-Merritt.

## 2026-08-10 — Step 7-8: reporting & revert

- Wrote `data/ktc_comparison/comparison_report.md` (coverage, correlation, flipped verdicts, manager reordering, largest swings, plain-English verdict, method/caveats).
- Wrote executable `revert.sh` at repo root (removes `data/ktc_comparison/` outputs in reverse order).

## 2026-08-10 — Local KTC-only dashboard variant

- **Goal:** run the trade-analysis dashboard locally with trade data / metrics / stats driven **solely by KTC numbers**, viewable from the Mac.
- **How the dashboard loads data:** Vite/React SPA (`dashboard/frontend`) that in static mode reads four value-bearing JSON files from `public/`: `api-trades.json`, `api-teams.json`, `api-stats-summary.json`, `api-trade-metrics.json`. (Standings/playoffs/draft/waivers are game-outcome/activity data unaffected by trade values — left unchanged.)
- **Generator:** `data/ktc_comparison/build_ktc_dashboard_data.py` rebuilds those four files on one consistent KTC scale: players → actual KTC SF value (at trade date / current); picks+FAAB → prod value × proportional factor (2.539 then, 2.766 now, value-weighted through origin — chosen over the linear fit so small FAAB stays small); 8 no-KTC players fall back to the proportional factor. Team totals, winners (who received more value), margins, swing, per-manager tradeCount/winRate/avgMargin/totalValueGained, stats overview + rankings, and the sharpe/significance/opponent-adjusted metrics are all recomputed (metrics formulas copied verbatim from `pipeline/scripts/generate_trade_metrics.py`).
- **Backups:** each target JSON copied to `<file>.ktc-backup` before overwrite; `dashboard/frontend/.env` copied to `.env.ktc-backup`. `.env` set to `VITE_USE_LAMBDA_API=false` (static mode) so the app reads the local KTC JSON instead of the Prod Lambda API.
- **Serve + expose:** `npx vite --host 0.0.0.0 --port 5173` on the dev desktop (log `/tmp/ktc_vite.log`). Reverse SSH forward `ssh -p 2222 -R 5173:localhost:5173 lndahayo@127.0.0.1` publishes it onto the Mac → open **http://localhost:5173** on the Mac. Verified HTTP 200 for the app and KTC JSON from the Mac side.
- **Result (KTC vs prod leaderboard by totalValueGained):** gnewman4 rises to #1 (32,875), thekylecasey #2, tylerpilgrim #3; lndahayo drops from prod's top spot (+12,756) to −8,323; jwalters74 bottoms out (−31,356). Confirms the comparison report's finding that mid/upper standings are highly source-sensitive.
- **To stop/restore:** `revert.sh` restores the four JSON files and `.env` from their `.ktc-backup` copies and kills the vite server + tunnel.

### Safety measures
- Reused already-cached KTC data (`data/ktc_history/`) and local prod snapshots (`pipeline/`); **did not re-scrape KTC**.
- The KTC-variant dashboard is a **local, read-only** view: static JSON on a local dev server. No prod data, DynamoDB, or deployed site was modified — the live dashboard still uses prod values.
- Live Prod API calls were GET-only (`/api/trades`, `/api/stats`, `/api/teams`) and cached under `data/ktc_history/raw/`.
- No packages installed (Python 3.12 stdlib only: csv, json, re, unicodedata, statistics, bisect). No venv, no system config changes.
