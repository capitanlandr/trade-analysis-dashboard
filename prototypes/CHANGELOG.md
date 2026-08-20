# CHANGELOG — KTC Historical Value Acquisition

All timestamps in local server time. Working dir: `/local/home/lndahayo/projects/trade-analysis-dashboard`.
This task is **read-only** against production (Sleeper API, my Prod API Gateway, KTC). No DynamoDB writes, no deploys, no git commits. All output lands under `data/ktc_history/`.

---

## 2026-08-10 — Step 1: Enumerate my players

- **What:** Defined "my players" as the union of all players rostered across my two Sleeper leagues (season_2 `1180814327660371968`, season_3 `1312166810505719808`, per `backend-api/fantasy-backend/ingestion_lambda/seasons.yaml`).
- **How (read-only GETs):**
  - `GET https://api.sleeper.app/v1/league/<id>/rosters` for both leagues → cached to `data/ktc_history/raw/_sleeper_rosters_<id>.json`.
  - `GET https://api.sleeper.app/v1/players/nfl` (master, ~14 MB) → cached to `data/ktc_history/raw/_sleeper_players_nfl.json`.
  - Also probed my Prod API (`/api/health`, `/api/stats`, `/api/teams`, `/api/trades`) — these are trade-centric and expose player *names* only (no sleeper_id), so Sleeper rosters are the authoritative joinable identity source. League ID confirmed from `/api/health` = `1312166810505719808`.
- **Result:** 382 distinct rostered player IDs, all QB/RB/WR/TE, 0 missing from the Sleeper master. Written to `data/ktc_history/my_players.json` (+ `my_players_all.json`, identical here since all rostered players are skill-position).

## 2026-08-10 — Step 2: Acquisition-method probe (cheapest first)

- **2a — KTC embedded JSON endpoint: SUCCESS. This is the chosen method.**
  - The dynasty-rankings listing page (`GET https://keeptradecut.com/dynasty-rankings?page={N}&filters=QB|WR|RB|TE|RDP&format={0|1}`) embeds `var playersArray = [...]` with `playerName`, `playerID`, `slug` (e.g. `jahmyr-gibbs-1415`), `position`, `team`, `age` for every ranked player — a perfect resolver source. (`history` arrays are empty on the listing page.)
  - Each **per-player page** (`GET https://keeptradecut.com/dynasty-rankings/players/<slug>`) embeds two JS objects `var playerSuperflex = {...}` and `var playerOneQB = {...}`. Each has an `overallValue` array of `{"d":"YYMMDD","v":<value>}` points — a **daily dynasty-value time series**. For Jahmyr Gibbs: **1247 points spanning 2023-03-10 → 2026-08-10 (today)**, per format.
  - Proof snippet (Gibbs, playerOneQB.overallValue): first `{"d":"230310","v":6609}`, last `{"d":"260810","v":9999}`. Raw sample saved to `data/ktc_history/raw/_probe_player_gibbs.html`.
  - **Why chosen:** it is the cheapest method (a single HTML GET per player yields the *full* historical series for BOTH formats), no rendering/JS execution, no pixel extraction. Methods 2b/2c/2d were therefore not needed.
- **2b/2c/2d — not needed / not escalated to.** No open dataset search, HTML-graph scraping, or screen-grab required because 2a provably returns dated historical values. (Recorded here per the "log why you escalated / didn't" requirement.)

## 2026-08-10 — Step 3: Resolver (my players → KTC slugs)

- **Catalog source:** `GET https://keeptradecut.com/dynasty-rankings?page={0..11}&filters=...&format=1` → each page embeds the FULL `playersArray` (500 entries, not truly paginated), giving `slug` + `playerID` + name/pos/team for KTC's entire ranked dynasty universe. Cached to `data/ktc_history/raw/rankings/`, consolidated to `data/ktc_history/ktc_catalog.json` (500 entries: 192 WR, 134 RB, 70 TE, 68 QB, 36 RDP).
- **Matcher** (`data/ktc_history/build_player_map.py`): manual-override → exact normalized name+position → exact name → fuzzy (SequenceMatcher ≥ 0.88, same position). Name normalization strips accents, punctuation, and Jr/Sr/II/III suffixes.
- **Manual overrides** (`data/ktc_history/manual_overrides.csv`) for name variants confirmed by matching position+team: Kenny→Kenneth Gainwell, Chig→Chigoziem Okonkwo, Zonovan→Bam Knight.
- **Result: 366 / 382 resolved (95.8%)** → `data/ktc_history/player_map.csv`. Methods: 362 exact_name_pos, 3 manual_override, 1 fuzzy_pos.
- **16 unresolved** — genuinely not in KTC's ranked dynasty universe (no dynasty value tracked). Retired/inactive: Russell Wilson, Philip Rivers, Tyler Lockett, Darren Waller, Joe Mixon, Nick Chubb, Austin Ekeler, Kareem Hunt, Tyrod Taylor. Deep-bench/practice-squad: Jermaine Burton, Brady Cook, Max Brosmer, Tanner Koziol, Dare Ogunbowale, Mason Rudolph, Evan Hull. Full list in `player_map.csv` (match_method=UNRESOLVED) and `_unresolved.json`.

## 2026-08-10 — Step 4: Acquire history (method 2a)

- **Script:** `data/ktc_history/fetch_ktc_history.py`. For each of the 366 resolved players it GETs `https://keeptradecut.com/dynasty-rankings/players/<slug>`, gzip-caches the raw HTML to `data/ktc_history/raw/players/<slug>.html.gz`, and parses the `overallValue` array out of both `var playerOneQB` and `var playerSuperflex`.
- **Date parsing:** KTC's `"d":"YYMMDD"` → ISO `20YY-MM-DD`.
- **Result:** 366/366 players fetched OK (0 HTTP errors, no 429/403). Consolidated tidy dataset `data/ktc_history/ktc_history.csv` with columns `player_name, sleeper_id, ktc_slug, format(1QB|SF), date, value`.
  - **908,777 rows**, **366 distinct players**, formats {1QB, SF}.
  - **Date range 2020-04-01 → 2026-08-10** (2320 distinct dates for veterans; ~1247-day rolling window is the median depth).
  - Genuine time series: **732/732 (player,format) series have >1 distinct date** (100%).
- Per-player fetch statuses recorded in `data/ktc_history/_fetch_log.json`; run log in `_fetch_run.log`.

## 2026-08-10 — Step 5: Validation & finalization

- Wrote `data/ktc_history/coverage_report.md` (fraction covered, per-format date range, per-position coverage, unresolved list with reasons, partial-series list).
- Wrote executable `revert.sh` (removes all files this task created, in reverse order; the only pre-existing file touched was creating this CHANGELOG — reverting removes the whole `data/ktc_history/` tree and CHANGELOG.md/revert.sh). No pre-existing repo files were modified, so no `.bak` backups were required.

### Politeness / safety measures applied
- Single-threaded fetching with a randomized 1.5–3.0s delay between per-player requests.
- Normal desktop User-Agent set on every request.
- Every raw response cached (gzipped) to `data/ktc_history/raw/` so re-runs never re-hit KTC.
- Back off (60s + single retry) on HTTP 429 or 403; none were encountered.
- No packages installed (used only Python 3.12 stdlib: urllib, json, csv, gzip, re). No venv created. No system config changed.

---

## 2026-08-12 — NFL Top 100 tab (DEV-ONLY, no deploy/commit)

- **What:** Added an "NFL Top 100" tab to the Fantasy Football Trade Analysis Dashboard showing the 2026 NFL Top 100 cross-referenced against league fantasy rosters, plus a per-fantasy-team Top-100 count summary. Dev-only: served on the dev desk Vite server (port 5173), no git commit/push, no Vercel/CloudFront/AWS deploy.
- **Top-100 source URL (primary):** Wikipedia "NFL Top 100 Players of 2026" via the MediaWiki API — `https://en.wikipedia.org/w/api.php?action=parse&page=NFL_Top_100_Players_of_2026&prop=wikitext&format=json&formatversion=2` (human page: `https://en.wikipedia.org/wiki/NFL_Top_100_Players_of_2026`). **Fallback:** `https://www.nfl.com/news/nfl-top-100-players-of-2026`. First run used the Wikipedia source and parsed 76 revealed players (ranks 25–100); ranks 1–24 are not yet aired and are recorded as `pendingRanks` (not hardcoded/invented).
- **New files (created):**
  - `scripts/generate_nfl_top100.py` — standalone, idempotent fetch + roster cross-reference script. Parses {rank,name,position,nflTeam} (prefers 2026 team, else 2025), matches Top-100 players to fantasy rosters by normalized name (`search_full_name` convention: lowercased, accent/punct-stripped, Jr/Sr/II/III suffixes removed), computes per-team counts, and FLAGS unmatched Top-100 entries in `unmatched[]` rather than dropping them. On all-source failure it preserves the last good JSON (atomic temp-file replace). Writes `dashboard/frontend/public/nfl-top-100.json`.
  - `scripts/refresh_nfl_top100.sh` — cron wrapper; runs the Python script and appends a timestamped entry to `logs/nfl_top100_refresh.log`.
  - `dashboard/frontend/src/pages/NflTop100.tsx` — page: (a) per-fantasy-team Top-100 count summary table, (b) ranked table of Top-100 players on fantasy teams (rank, player, pos, NFL team, fantasy team, manager), (c) flagged list of revealed Top-100 players not on any roster, plus a pending-ranks banner.
  - `dashboard/frontend/public/nfl-top-100.json` — generated data (regenerated daily).
  - `logs/nfl_top100_refresh.log`, `logs/vite_dev.log` — run/server logs.
- **Modified files (backed up to `<file>.bak` before first edit):**
  - `dashboard/frontend/src/App.tsx` — imported `NflTop100`, added `<Route path="nfl-top-100" element={<NflTop100 />} />`.
  - `dashboard/frontend/src/components/Layout/DashboardLayout.tsx` — imported `ListOrdered` icon, added `<NavItem ... href="/nfl-top-100" />`.
- **Daily auto-update (crontab entry added — exact line):**
  `30 9 * * * /local/home/lndahayo/projects/trade-analysis-dashboard/scripts/refresh_nfl_top100.sh # nfl-top100-daily-refresh`
  Runs once daily at 09:30, logs each run (timestamp + source used) to `logs/nfl_top100_refresh.log`. Only this entry was added; no unrelated crontab lines were touched.
- **Packages:** none installed (Python 3.12 stdlib only; frontend used existing lucide-react + react-router-dom).
- **Cross-reference inputs (read-only):** `dashboard/frontend/public/api-teams.json` (rosterId→teamName/realName), `data/ktc_history/raw/_sleeper_rosters_1312166810505719808.json` (active season_3 league, roster_id→players), `data/ktc_history/my_players.json` (sleeper_id→name/pos/team/search_full_name).

## 2026-08-12 — NFL Top 100 tab: advanced filtering + sorting (DEV-ONLY)

- **What:** Added filtering and sorting to the "Top-100 Players on Fantasy Rosters" table on the NFL Top 100 tab (per user request). No changes to the Recent Trades table.
- **Capabilities added in `dashboard/frontend/src/pages/NflTop100.tsx`:**
  - **Player name search** — free-text box, case-insensitive substring match on player name.
  - **Multi-select filters** (checkbox popovers, AND across categories / OR within a category) for **Position**, **NFL Team**, **Fantasy Team**, and **Manager**. Options are derived from the rostered data. Each shows a selected-count badge and a Clear action; click-outside closes.
  - **Rank range** — numeric min/max inputs, plus creative **quick-rank chips** (Top 10 / Top 25 / Top 50 / 51–100) that toggle the range.
  - **Sortable columns** — click any header (Rank, Player, Pos, NFL Team, Fantasy Team, Manager) to sort; click again to flip asc/desc. Text sorts locale-aware; rank sorts numerically; stable tiebreak by rank.
  - **Reset** button (shows active-filter count), a "no matches" empty state, and a live "N of M" result count in the section header.
- **Implementation:** two small in-file components (`MultiSelect`, `SortHeader`) + `useMemo`-derived filtered/sorted rows. No new npm packages (existing `lucide-react` icons only). `tsc --noEmit` passes clean.
- **Revert:** no new files or backups introduced — the enhancement edits `NflTop100.tsx`, which `revert.sh` already deletes as a task-created file. No revert.sh/crontab changes needed.
