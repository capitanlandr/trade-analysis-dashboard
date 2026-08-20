#!/usr/bin/env bash
# revert.sh — undo all file changes made by the Prod-vs-KTC comparison task.
#
# This task ONLY created new files under data/ktc_comparison/; it modified no
# pre-existing repo files, so there are no .bak restores. Reverting removes what
# it created, in reverse order of creation. Safe to run more than once.
set -euo pipefail
cd "$(dirname "$0")/../.."   # -> repo root

echo "Reverting Prod-vs-KTC comparison outputs..."

# --- Local KTC dashboard variant: stop server + tunnel, restore dashboard files ---
echo "Stopping KTC dashboard dev server + reverse tunnel (if running)..."
lsof -ti:5173 2>/dev/null | xargs -r kill 2>/dev/null || true
pkill -f "R 5173:localhost:5173" 2>/dev/null || true
PUB="dashboard/frontend/public"
for j in api-trades api-teams api-stats-summary api-trade-metrics; do
  if [ -f "$PUB/$j.json.ktc-backup" ]; then
    mv -f "$PUB/$j.json.ktc-backup" "$PUB/$j.json"
    echo "  restored $PUB/$j.json"
  fi
done
if [ -f dashboard/frontend/.env.ktc-backup ]; then
  mv -f dashboard/frontend/.env.ktc-backup dashboard/frontend/.env
  echo "  restored dashboard/frontend/.env"
fi
rm -f data/ktc_comparison/build_ktc_dashboard_data.py

# 7-8. Report, CHANGELOG, this revert script
rm -f data/ktc_comparison/comparison_report.md
rm -f data/ktc_comparison/CHANGELOG.md

# 4-6. Impact recomputation outputs + script
rm -f data/ktc_comparison/manager_rankings_compare.csv
rm -f data/ktc_comparison/trade_verdicts_compare.csv
rm -f data/ktc_comparison/recompute_impact.py

# 2-3. Per-asset comparison output + script
rm -f data/ktc_comparison/asset_value_comparison.csv
rm -f data/ktc_comparison/build_comparison.py

# Remove the directory if now empty (leave it if other files remain)
rmdir data/ktc_comparison 2>/dev/null || true

echo "Revert complete."
echo "Note: this task did NOT touch the repo-root CHANGELOG.md / revert.sh (those belong to the KTC-history task)."
echo "It also left data/ktc_history/ (the acquired KTC dataset) intact."
