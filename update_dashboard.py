#!/usr/bin/env python3
"""
Trade Analysis Dashboard Update Script
=====================================

This script automates the entire pipeline from data fetching to dashboard deployment.
Now supports multi-season architecture with active/static season management.

Usage:
    python update_dashboard.py [--dry-run] [--skip-git]

Options:
    --dry-run    Show what would be done without executing
    --skip-git   Run pipeline but don't commit/push to GitHub
"""

import subprocess
import shutil
import os
import sys
import argparse
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
import logging

# Add pipeline utils to path for season configuration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'pipeline'))
from utils.season_config import get_season_config, validate_season_operation
from utils.logging_config import setup_logging, get_operation_logger

# Configuration
PIPELINE_DIR = "pipeline"  # Directory containing all pipeline scripts

# Initialize comprehensive logging (Requirement 5.5, 6.3, 12.5)
logger = setup_logging('Dashboard Update Pipeline', log_dir='logs')
op_logger = get_operation_logger(__name__)

# CSV files used by pipeline (still in pipeline/)
REQUIRED_FILES = [
    "league_trades_analysis_pipeline.csv",
    "team_identity_mapping.csv",
    "3team_trades_analysis.json"
]

# JSON files generated directly to dashboard/frontend/public/ by scripts
DASHBOARD_JSON_FILES = [
    "api-trades.json",
    "api-teams.json",
    "api-stats-summary.json",
    "api-standings.json",
    "api-playoff-scenarios.json",
    "waiver-wire-page.json",
    "api-draft-order.json"
]

# Cumulative files that need to be copied to frontend
CUMULATIVE_FILES = [
    "trades.json",
    "cumulative_processed_waiver_transactions.json"
]

PIPELINE_STAGES = [
    ("Stage 0: Detect Current Week", "python3 scripts/detect_current_week.py"),
    ("Stage 1: Fetch Trades (Active Seasons Only)", "python3 stage1_fetch_trades.py"),
    ("Stage 2: Extract Assets", "python3 stage2_extract_assets.py"),
    ("Stage 3: Cache Values", "python3 stage3_cache_values.py"),
    ("Stage 4: Generate Analysis", "python3 stage4_final.py"),
    ("Stage 5: Waiver Wire Analysis (Active Seasons Only)", "python3 stage5_waiver_wire.py"),
    ("Stage 5a: Fetch Player Stats", "python3 scripts/fetch_player_stats.py"),
    ("Stage 5b: Fetch Lineup Data", "python3 scripts/fetch_lineup_data.py"),
    ("Stage 6: Analyze 2026 Pick Ownership", "python3 analyze_2026_pick_ownership.py"),
    ("Stage 7: Generate Playoff Bracket", "python3 generate_playoff_bracket.py"),
    ("Stage 7a: Calculate Progressive Draft Order", "python3 scripts/calculate_progressive_draft_order.py"),
    ("Stage 8: Generate Dashboard JSON from Cumulative Files", "python3 scripts/generate_dashboard_json_from_cumulative.py"),
    ("Stage 8a: Generate Trade Metrics", "python3 scripts/generate_trade_metrics.py"),
    ("Stage 9: Generate Waiver Wire JSON from Cumulative Files", "python3 scripts/generate_waiver_wire_dashboard_json_from_cumulative.py"),
    ("Stage 10: Fetch Current Standings", "python3 scripts/fetch_standings.py"),
    ("Stage 11: Run Playoff Simulations", "python3 scripts/simulate_playoff_scenarios.py"),
    ("Stage 12: Update Dashboard JSON with Playoff Data", "python3 scripts/generate_dashboard_json_from_cumulative.py")
]

# Lines of captured output to echo per stream when a stage SUCCEEDS. Full output
# is always echoed on failure. Kept generous enough to show per-week fetch counts
# and dedupe summaries, which are what actually reveal a silently-wrong run.
SUCCESS_OUTPUT_TAIL_LINES = 40

# Substrings that promote a line out of the success tail and into the run summary.
# The June 2026 outage hid for 35 days because a caught, logged error scrolled
# into discarded stdout; these patterns make that class of failure visible even
# when the stage exits 0.
WARNING_MARKERS = ("ERROR", "CRITICAL", "Traceback", "WARNING", "non-critical", "failed", "Failed")


def _echo_stream(label, text, tail_lines=None):
    """Print a captured stream, optionally only its last `tail_lines` lines."""
    if not text or not text.strip():
        return
    lines = text.strip().splitlines()
    truncated = tail_lines is not None and len(lines) > tail_lines
    shown = lines[-tail_lines:] if truncated else lines

    if truncated:
        print(f"   ── {label} (last {tail_lines} of {len(lines)} lines) ──")
    else:
        print(f"   ── {label} ──")
    for line in shown:
        print(f"   │ {line}")


def _collect_warnings(*streams):
    """Return lines from the given streams that look like suppressed problems."""
    hits = []
    for text in streams:
        if not text:
            continue
        for line in text.splitlines():
            if any(marker in line for marker in WARNING_MARKERS):
                hits.append(line.strip())
    return hits


def run_command(cmd, description="", dry_run=False, cwd=None):
    """Run a shell command with error handling.

    Captures stdout and stderr so the caller can inspect them, but ALWAYS echoes
    them onward. Pipeline stages log through the `logging` module, which writes to
    stderr, so discarding stderr on success hides every caught-and-logged error
    the stages emit. Returns (ok, warnings) where warnings are lines that look
    like suppressed failures inside an otherwise-successful stage.
    """
    print(f"🔄 {description}")
    if cwd:
        print(f"   Working directory: {cwd}")
    print(f"   Command: {cmd}")

    if dry_run:
        print("   [DRY RUN - Not executed]")
        return True, []

    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, cwd=cwd)
        _echo_stream("stdout", result.stdout, tail_lines=SUCCESS_OUTPUT_TAIL_LINES)
        _echo_stream("stderr", result.stderr, tail_lines=SUCCESS_OUTPUT_TAIL_LINES)

        warnings = _collect_warnings(result.stdout, result.stderr)
        if warnings:
            print(f"   ⚠️  Completed with {len(warnings)} warning line(s) - see run summary")
        else:
            print("   ✅ Completed cleanly")
        return True, warnings

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        # Full output on failure, never truncated.
        _echo_stream("stdout", e.stdout)
        _echo_stream("stderr", e.stderr)
        return False, _collect_warnings(e.stdout, e.stderr)


def validate_season_configuration():
    """
    Validate season configuration before pipeline execution.
    
    Returns:
        tuple: (is_valid, season_config, active_seasons, static_seasons)
        
    Raises:
        SystemExit: If configuration is invalid
    """
    print("   Validating season configuration...")
    
    try:
        # Load and validate season configuration
        season_config = get_season_config()
        
        active_seasons = season_config.get_active_seasons()
        static_seasons = season_config.get_static_seasons()
        
        print(f"   Active seasons: {active_seasons}")
        print(f"   Static seasons: {static_seasons}")
        
        # Validate that we have at least one active season
        if not active_seasons:
            print("   ❌ No active seasons configured. Pipeline requires at least one active season.")
            return False, None, [], []
        
        # Validate league IDs for active seasons
        for season_name in active_seasons:
            season_info = season_config.get_season_info(season_name)
            if not season_info or not season_info.league_id:
                print(f"   ❌ Active season '{season_name}' missing league_id")
                return False, None, [], []
            
            # Check for placeholder values
            placeholder_patterns = ['placeholder', 'TODO', 'CHANGE_ME', 'xxx']
            if any(pattern.lower() in season_info.league_id.lower() for pattern in placeholder_patterns):
                print(f"   ❌ Active season '{season_name}' has placeholder league_id: {season_info.league_id}")
                return False, None, [], []
        
        print("   ✅ Season configuration validated successfully")
        logger.info("Season configuration validated successfully")
        return True, season_config, active_seasons, static_seasons
        
    except Exception as e:
        print(f"   ❌ Season configuration validation failed: {e}")
        logger.error(f"Season configuration validation failed: {e}")
        return False, None, [], []


def log_season_processing_summary(active_seasons, static_seasons):
    """
    Log comprehensive summary of which seasons will be processed vs skipped.
    
    Args:
        active_seasons: List of active season names
        static_seasons: List of static season names
    """
    print("\n" + "=" * 60)
    print("MULTI-SEASON PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    
    print(f"🔄 ACTIVE SEASONS (will be processed):")
    for season in active_seasons:
        print(f"   • {season} - Daily incremental fetch")
    
    print(f"🔒 STATIC SEASONS (will be skipped):")
    for season in static_seasons:
        print(f"   • {season} - Immutable historical data")
    
    if not active_seasons:
        print("⚠️  No active seasons to process!")
    
    if not static_seasons:
        print("ℹ️  No static seasons configured")
    
    print("=" * 60)
    
    # Also log to file
    logger.info(f"Active seasons to process: {active_seasons}")
    logger.info(f"Static seasons to skip: {static_seasons}")


def update_season_metadata(season_config, active_seasons):
    """
    Update season metadata after successful pipeline execution.

    Stage 1 (stage1_fetch_trades.py) already manages last_incremental_fetch
    timestamps correctly by setting them to the most recent trade's created
    timestamp when new trades are found, and leaving them unchanged otherwise.
    This function only updates the top-level metadata timestamp and saves the
    config that Stage 1 has already modified.

    Args:
        season_config: SeasonConfiguration instance
        active_seasons: List of active season names that were processed
    """
    try:
        print("   Saving season metadata after successful pipeline run...")
        logger.info("Saving season metadata after successful pipeline run...")

        # Save updated configuration (Stage 1 already set per-season timestamps)
        season_config.save('pipeline/config/seasons.yaml')
        print("   ✅ Season metadata saved successfully")
        logger.info("Season metadata saved successfully")

    except Exception as e:
        print(f"   ❌ Failed to save season metadata: {e}")
        logger.error(f"Failed to save season metadata: {e}")
        # Don't fail the entire pipeline for metadata update issues
        print("   ⚠️  Continuing despite metadata save failure...")
        logger.warning("Continuing despite metadata save failure...")


def copy_cumulative_files_to_frontend():
    """
    Copy cumulative data files to frontend public directory.
    
    Returns:
        bool: True if successful, False otherwise
    """
    print("   Copying cumulative files to frontend public directory...")
    logger.info("Copying cumulative files to frontend public directory...")
    
    source_dir = Path(PIPELINE_DIR)
    target_dir = Path("dashboard/frontend/public")
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    success = True
    for filename in CUMULATIVE_FILES:
        source_file = source_dir / filename
        target_file = target_dir / filename
        
        if source_file.exists():
            try:
                shutil.copy2(source_file, target_file)
                size = target_file.stat().st_size
                print(f"   ✓ Copied {filename} ({size:,} bytes)")
                logger.info(f"Copied {filename} ({size:,} bytes)")
            except Exception as e:
                print(f"   ❌ Failed to copy {filename}: {e}")
                logger.error(f"Failed to copy {filename}: {e}")
                success = False
        else:
            print(f"   ⚠️  Source file not found: {source_file}")
            logger.warning(f"Source file not found: {source_file}")
            # Don't fail for missing cumulative files - they might not exist yet
    
    return success


def tag_new_season3_transactions():
    """
    Ensure all new Season 3 transactions are properly tagged.
    This is handled by the individual pipeline stages, but we log the operation.
    """
    print("   Season 3 transaction tagging handled by pipeline stages:")
    print("     • Stage 1 (fetch_trades.py) - Tags new trade transactions")
    print("     • Stage 5 (waiver_wire.py) - Tags new waiver transactions")
    print("     • All new transactions automatically tagged with season: 'season_3'")
    
    logger.info("Season 3 transaction tagging configured in pipeline stages")
    logger.info("Stage 1 and Stage 5 will tag new transactions with season: 'season_3'")


def check_file_exists(filepath):
    """Check if a required file exists."""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"   ✅ {filepath} ({size:,} bytes)")
        return True
    else:
        print(f"   ❌ {filepath} - NOT FOUND")
        return False



def print_playoff_summary():
    """Print summary of playoff scenarios if available."""
    import json
    
    playoff_file = os.path.join(PIPELINE_DIR, "playoff_scenarios_simulated.json")
    if not os.path.exists(playoff_file):
        return
    
    try:
        with open(playoff_file, 'r') as f:
            data = json.load(f)
        
        results = data.get('results', [])
        metadata = data.get('metadata', {})
        
        print("\n" + "=" * 50)
        print("📊 PLAYOFF SCENARIOS SUMMARY")
        print("=" * 50)
        print(f"Current Week: {metadata.get('current_week', 'N/A')}")
        print(f"Simulations: {data.get('num_simulations', 0):,}")
        
        # Count clinch statuses
        clinched_playoff = sum(1 for r in results if r.get('clinched_playoff'))
        clinched_division = sum(1 for r in results if r.get('clinched_division'))
        clinched_bye = sum(1 for r in results if r.get('clinched_bye'))
        eliminated = sum(1 for r in results if r.get('eliminated'))
        
        print(f"\n✅ Clinched Playoff: {clinched_playoff}")
        print(f"🏆 Clinched Division: {clinched_division}")
        print(f"⭐ Clinched Bye: {clinched_bye}")
        print(f"❌ Eliminated: {eliminated}")
        
        # Show top 6 playoff probabilities
        print(f"\n🎯 Top 6 Playoff Probabilities:")
        for i, result in enumerate(results[:6], 1):
            team = result.get('team_name', 'Unknown')
            prob = result.get('playoff_probability', 0)
            seed = result.get('projected_seed', 'N/A')
            print(f"  {i}. {team:<30} {prob:>5.1f}% (Seed {seed})")
        
    except Exception as e:
        print(f"   ⚠️  Could not load playoff summary: {e}")


def verify_dashboard_files(dry_run=False):
    """Verify dashboard JSON files were generated correctly."""
    print(f"\n📁 Verifying dashboard JSON files in dashboard/frontend/public/...")
    
    all_verified = True
    dashboard_dir = Path("dashboard/frontend/public")
    
    for filename in DASHBOARD_JSON_FILES:
        filepath = dashboard_dir / filename
        
        if not filepath.exists():
            print(f"   ❌ {filename} not found!")
            all_verified = False
        else:
            size = filepath.stat().st_size
            print(f"   ✅ {filename} ({size:,} bytes)")
    
    return all_verified

def git_deploy(dry_run=False):
    """Commit and push changes to trigger Vercel deployment."""
    print(f"\n🚀 Deploying to GitHub/Vercel...")
    
    # Check if there are changes (we're already in git root)
    result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
    if not result.stdout.strip():
        print("   ℹ️  No changes to commit")
        return True
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"data: update dashboard data - {timestamp}"
    
    commands = [
        ("git add .", "Adding files to git"),
        (f'git commit -m "{commit_msg}"', "Committing changes"),
        ("git push origin main", "Pushing to GitHub")
    ]
    
    for cmd, desc in commands:
        ok, _ = run_command(cmd, desc, dry_run)
        if not ok:
            return False
    
    if not dry_run:
        print("   🎉 Deployment triggered! Check Vercel dashboard for status.")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Update Trade Analysis Dashboard")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--skip-git", action="store_true", help="Run pipeline but don't commit/push")
    args = parser.parse_args()
    
    print("🏈 Trade Analysis Dashboard Update Script")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    # Step 0: Validate Season Configuration (Requirement 12.1)
    print("\n🔧 Validating Multi-Season Configuration...")
    is_valid, season_config, active_seasons, static_seasons = validate_season_configuration()
    
    if not is_valid:
        print("\n❌ Season configuration validation failed.")
        print("   Please check pipeline/config/seasons.yaml and fix any issues.")
        sys.exit(1)
    
    # Log processing summary (Requirement 12.5)
    log_season_processing_summary(active_seasons, static_seasons)
    
    print("\nThis script will:")
    print("  • Process ONLY active seasons (skip static seasons)")
    print("  • Run trade analysis pipeline (Stages 1-7)")
    print("  • Fetch current standings (Stage 8)")
    print("  • Run playoff simulations (Stage 9)")
    print("  • Generate dashboard JSON from cumulative files (Stage 10)")
    print("  • Copy cumulative files to frontend")
    print("  • Deploy to GitHub/Vercel")
    
    # Step 1: Tag Season 3 transactions (Requirement 3.4)
    print("\n🏷️  Season 3 Transaction Tagging...")
    tag_new_season3_transactions()
    
    # Step 2: Run Python Pipeline (Stages 1-12) from pipeline directory
    # Pipeline stages now only process active seasons (Requirement 12.1, 12.2)
    print(f"\n📊 Running Python Pipeline (Stages 1-12) - Active Seasons Only...")
    print(f"   Processing seasons: {', '.join(active_seasons)}")
    print(f"   Skipping static seasons: {', '.join(static_seasons)}")
    
    # Log comprehensive season processing summary (Requirement 12.5)
    op_logger.log_season_summary(active_seasons, static_seasons, [])
    
    pipeline_start_time = time.time()
    processed_stages = []
    stage_warnings = []

    for stage_name, command in PIPELINE_STAGES:
        stage_start_time = time.time()

        ok, warnings = run_command(command, stage_name, args.dry_run, cwd=PIPELINE_DIR)
        if not ok:
            stage_duration = time.time() - stage_start_time
            logger.error(f"Pipeline failed at: {stage_name} after {stage_duration:.2f}s")
            print(f"\n❌ Pipeline failed at: {stage_name}")
            sys.exit(1)

        if warnings:
            stage_warnings.append((stage_name, warnings))

        stage_duration = time.time() - stage_start_time
        processed_stages.append(stage_name)
        logger.info(f"✓ Completed {stage_name} in {stage_duration:.2f}s")

    pipeline_duration = time.time() - pipeline_start_time
    logger.info(f"✓ All {len(processed_stages)} pipeline stages completed in {pipeline_duration:.2f}s")

    # Surface warnings from stages that exited 0. A stage can succeed while
    # silently skipping its real work, which is how the June 2026 breakage stayed
    # invisible for 35 days. These do not fail the run; they make it inspectable.
    if stage_warnings:
        print(f"\n⚠️  Run summary: {len(stage_warnings)} stage(s) logged warnings")
        for stage_name, warnings in stage_warnings:
            print(f"\n   {stage_name}")
            for line in warnings[:10]:
                print(f"     • {line}")
            if len(warnings) > 10:
                print(f"     … {len(warnings) - 10} more")
    else:
        print("\n✅ Run summary: no stage warnings")
    
    # Step 3: Copy cumulative files to frontend (Requirement 12.3)
    print(f"\n📁 Copying cumulative files to frontend...")
    if not copy_cumulative_files_to_frontend():
        print("\n⚠️  Some cumulative files could not be copied, but continuing...")
    
    # Step 4: Verify output files in pipeline directory
    print(f"\n📋 Checking output files in {PIPELINE_DIR}/...")
    all_files_exist = True
    for filename in REQUIRED_FILES:
        filepath = os.path.join(PIPELINE_DIR, filename)
        if not check_file_exists(filepath):
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ Some required files are missing. Pipeline may have failed.")
        sys.exit(1)
    
    # Step 5: Verify dashboard files generated (Requirement 12.4)
    if not verify_dashboard_files(args.dry_run):
        print("\n❌ Dashboard JSON files missing or incomplete.")
        sys.exit(1)
    
    # Step 6: Update season metadata after successful execution (Requirement 3.5)
    if not args.dry_run:
        update_season_metadata(season_config, active_seasons)
    
    # Step 7: Deploy (unless skipped)
    if not args.skip_git:
        if not git_deploy(args.dry_run):
            print("\n❌ Deployment failed.")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping git deployment (--skip-git flag)")
    
    # Display playoff scenarios summary
    print_playoff_summary()
    
    # Success! (Requirement 12.5)
    print("\n" + "=" * 50)
    if args.dry_run:
        print("🔍 DRY RUN COMPLETE - No changes were made")
        print("   Remove --dry-run flag to execute for real")
    else:
        print("🎉 MULTI-SEASON DASHBOARD UPDATE COMPLETE!")
        print(f"   Processed active seasons: {', '.join(active_seasons)}")
        print(f"   Skipped static seasons: {', '.join(static_seasons)}")
        print("   Your dashboard should update in 2-3 minutes")
        print("   Check: https://dynasuiiiianalytics.vercel.app/")
    
    # Log final operation summary with comprehensive statistics (Requirement 12.5)
    logger.info("=" * 80)
    logger.info("PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info(f"Active seasons processed: {active_seasons}")
    logger.info(f"Static seasons skipped: {static_seasons}")
    logger.info(f"Total pipeline stages: {len(processed_stages)}")
    logger.info(f"Total execution time: {pipeline_duration:.2f}s")
    logger.info("=" * 80)
    
    # Log accumulated operation statistics
    op_logger.log_operation_stats()
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)