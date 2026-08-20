#!/usr/bin/env bash
# revert.sh — undo all file changes made by the KTC historical-value acquisition task.
#
# This task ONLY created new files; it modified no pre-existing repo files, so there
# are no .bak restores to perform. Reverting therefore removes what it created, in
# reverse order of creation.
#
# Safe to run more than once (each step is guarded).
set -euo pipefail
cd "$(dirname "$0")"

# ===========================================================================
# NFL Top 100 tab (added 2026-08-12) — reverted first, before the KTC block
# below removes CHANGELOG.md. Restores .bak backups, removes newly created
# files, and removes ONLY this task's daily crontab entry.
# ===========================================================================
echo "Reverting NFL Top 100 tab..."

# Remove the daily crontab entry (matched by its unique tag comment); leave all
# other crontab lines untouched. No-op if no crontab / entry already gone.
if crontab -l >/dev/null 2>&1; then
  crontab -l 2>/dev/null | grep -v 'nfl-top100-daily-refresh' | crontab - || true
fi

# Restore modified frontend files from their .bak backups, then drop the .bak.
for f in \
  dashboard/frontend/src/App.tsx \
  dashboard/frontend/src/components/Layout/DashboardLayout.tsx; do
  if [ -f "$f.bak" ]; then
    mv -f "$f.bak" "$f"
    echo "  restored $f"
  fi
done

# Remove newly created files.
rm -f scripts/generate_nfl_top100.py
rm -f scripts/refresh_nfl_top100.sh
rm -f dashboard/frontend/src/pages/NflTop100.tsx
rm -f dashboard/frontend/public/nfl-top-100.json
rm -f dashboard/frontend/public/nfl-top-100.json.tmp
rm -f logs/nfl_top100_refresh.log
rm -f logs/vite_dev.log
rmdir logs 2>/dev/null || true

echo "NFL Top 100 revert complete."

echo "Reverting KTC historical-value acquisition outputs..."

# 5. Reports & finalization artifacts (created last)
rm -f data/ktc_history/coverage_report.md
rm -f data/ktc_history/_fetch_log.json
rm -f data/ktc_history/_fetch_run.log

# 4. Consolidated dataset + fetch script + raw per-player cache
rm -f data/ktc_history/ktc_history.csv
rm -f data/ktc_history/fetch_ktc_history.py
rm -rf data/ktc_history/raw/players

# 3. Resolver outputs + script + overrides + catalog
rm -f data/ktc_history/player_map.csv
rm -f data/ktc_history/_unresolved.json
rm -f data/ktc_history/build_player_map.py
rm -f data/ktc_history/manual_overrides.csv
rm -f data/ktc_history/ktc_catalog.json
rm -rf data/ktc_history/raw/rankings

# 2. Probe raw samples (rankings + player-page probes + API/Sleeper caches)
rm -f data/ktc_history/raw/_probe_rankings_p0.html
rm -f data/ktc_history/raw/_probe_player_gibbs.html
rm -f data/ktc_history/raw/_api_health.json
rm -f data/ktc_history/raw/_api_stats.json
rm -f data/ktc_history/raw/_api_teams.json
rm -f data/ktc_history/raw/_api_trades.json
rm -f data/ktc_history/raw/_sleeper_rosters_1180814327660371968.json
rm -f data/ktc_history/raw/_sleeper_rosters_1312166810505719808.json
rm -f data/ktc_history/raw/_sleeper_players_nfl.json

# 1. Player enumeration
rm -f data/ktc_history/my_players.json
rm -f data/ktc_history/my_players_all.json

# Remove now-empty directory tree if empty
rmdir data/ktc_history/raw 2>/dev/null || true
rmdir data/ktc_history 2>/dev/null || true

# 0. This task's top-level artifacts
rm -f CHANGELOG.md
echo "Revert complete. (This script removed CHANGELOG.md; delete revert.sh manually if desired.)"
