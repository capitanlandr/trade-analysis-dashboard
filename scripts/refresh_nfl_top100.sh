#!/usr/bin/env bash
# refresh_nfl_top100.sh — cron wrapper for the NFL Top 100 daily refresh.
# Runs the fetch/cross-reference script and appends a timestamped line to the log.
# Safe to re-run; on source failure the Python script preserves the last good JSON.
set -uo pipefail
REPO="/local/home/lndahayo/projects/trade-analysis-dashboard"
LOG="$REPO/logs/nfl_top100_refresh.log"
mkdir -p "$REPO/logs"
{
  echo "----- run started $(date '+%Y-%m-%d %H:%M:%S %Z') -----"
  /usr/bin/env python3 "$REPO/scripts/generate_nfl_top100.py"
  echo "----- run exit code: $? -----"
} >> "$LOG" 2>&1
