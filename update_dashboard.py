#!/usr/bin/env python3
"""
Trade Analysis Dashboard Update Script
=====================================

This script automates the entire pipeline from data fetching to dashboard deployment.

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
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuration
PIPELINE_DIR = "pipeline"  # Directory containing all pipeline scripts

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
    "api-waiver-wire.json",
    "api-draft-order.json"
]

PIPELINE_STAGES = [
    ("Stage 0: Detect Current Week", "python3 scripts/detect_current_week.py"),
    ("Stage 1: Fetch Trades", "python3 stage1_fetch_trades.py"),
    ("Stage 2: Extract Assets", "python3 stage2_extract_assets.py"),
    ("Stage 3: Cache Values", "python3 stage3_cache_values.py"),
    ("Stage 4: Generate Analysis", "python3 stage4_final.py"),
    ("Stage 5: Waiver Wire Analysis", "python3 stage5_waiver_wire.py"),
    ("Stage 5a: Fetch Player Stats", "python3 scripts/fetch_player_stats.py"),
    ("Stage 5b: Fetch Lineup Data", "python3 scripts/fetch_lineup_data.py"),
    ("Stage 6: Analyze 2026 Pick Ownership", "python3 analyze_2026_pick_ownership.py"),
    ("Stage 7: Generate Playoff Bracket", "python3 generate_playoff_bracket.py"),
    ("Stage 7a: Calculate Progressive Draft Order", "python3 scripts/calculate_progressive_draft_order.py"),
    ("Stage 8: Generate Dashboard JSON", "python3 scripts/generate_dashboard_json.py"),
    ("Stage 9: Generate Waiver Wire JSON", "python3 scripts/generate_waiver_wire_dashboard_json.py"),
    ("Stage 10: Fetch Current Standings", "python3 scripts/fetch_standings.py"),
    ("Stage 11: Run Playoff Simulations", "python3 scripts/simulate_playoff_scenarios.py"),
    ("Stage 12: Update Dashboard JSON with Playoff Data", "python3 scripts/generate_dashboard_json.py")
]

def run_command(cmd, description="", dry_run=False, cwd=None):
    """Run a shell command with error handling."""
    print(f"🔄 {description}")
    if cwd:
        print(f"   Working directory: {cwd}")
    print(f"   Command: {cmd}")
    
    if dry_run:
        print("   [DRY RUN - Not executed]")
        return True
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, cwd=cwd)
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   Error details: {e.stderr}")
        return False

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
        if not run_command(cmd, desc, dry_run):
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
    
    print("\nThis script will:")
    print("  • Run trade analysis pipeline (Stages 1-7)")
    print("  • Fetch current standings (Stage 8)")
    print("  • Run playoff simulations (Stage 9)")
    print("  • Update dashboard JSON files (Stage 10)")
    print("  • Deploy to GitHub/Vercel")
    
    # Step 1: Run Python Pipeline (Stages 1-10) from pipeline directory
    print("\n📊 Running Python Pipeline (Stages 1-10)...")
    for stage_name, command in PIPELINE_STAGES:
        if not run_command(command, stage_name, args.dry_run, cwd=PIPELINE_DIR):
            print(f"\n❌ Pipeline failed at: {stage_name}")
            sys.exit(1)
    
    # Step 2: Verify output files in pipeline directory
    print(f"\n📋 Checking output files in {PIPELINE_DIR}/...")
    all_files_exist = True
    for filename in REQUIRED_FILES:
        filepath = os.path.join(PIPELINE_DIR, filename)
        if not check_file_exists(filepath):
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ Some required files are missing. Pipeline may have failed.")
        sys.exit(1)
    
    # Step 3: Verify dashboard files generated
    if not verify_dashboard_files(args.dry_run):
        print("\n❌ Dashboard JSON files missing or incomplete.")
        sys.exit(1)
    
    # Step 4: Deploy (unless skipped)
    if not args.skip_git:
        if not git_deploy(args.dry_run):
            print("\n❌ Deployment failed.")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping git deployment (--skip-git flag)")
    
    # Display playoff scenarios summary
    print_playoff_summary()
    
    # Success!
    print("\n" + "=" * 50)
    if args.dry_run:
        print("🔍 DRY RUN COMPLETE - No changes were made")
        print("   Remove --dry-run flag to execute for real")
    else:
        print("🎉 DASHBOARD UPDATE COMPLETE!")
        print("   Your dashboard should update in 2-3 minutes")
        print("   Check: https://dynasuiiiianalytics.vercel.app/")
    
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