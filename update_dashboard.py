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
DASHBOARD_ROOT = "."       # Root of git repo (where files get copied for Vercel)

REQUIRED_FILES = [
    "league_trades_analysis_pipeline.csv",
    "team_identity_mapping.csv", 
    "3team_trades_analysis.json"
]

PIPELINE_STAGES = [
    ("Stage 1: Fetch Trades", "python3 stage1_fetch_trades.py"),
    ("Stage 2: Extract Assets", "python3 stage2_extract_assets.py"),
    ("Stage 3: Cache Values", "python3 stage3_cache_values.py"),
    ("Stage 4: Generate Analysis", "python3 stage4_final.py"),
    ("Stage 5: Analyze 2026 Pick Ownership", "python3 analyze_2026_pick_ownership.py"),
    ("Stage 6: Generate Playoff Bracket", "python3 generate_playoff_bracket.py"),
    ("Stage 7: Generate Dashboard JSON", "python3 scripts/generate_dashboard_json.py")
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

def check_tyreek_value():
    """
    Check if Tyreek Hill's value is abnormal (> 1000).
    Returns True if value needs fixing, False otherwise.
    """
    cache_file = os.path.join(PIPELINE_DIR, 'asset_values_cache.csv')
    try:
        df = pd.read_csv(cache_file)
        tyreek_rows = df[df['asset_name'] == 'Tyreek Hill']
        
        if tyreek_rows.empty:
            print("   ℹ️  No Tyreek Hill entries found")
            return False
        
        # Check if any value_current is abnormally high (> 1000)
        abnormal_values = tyreek_rows[tyreek_rows['value_current'] > 1000]
        
        if not abnormal_values.empty:
            max_value = abnormal_values['value_current'].max()
            print(f"   ⚠️  Tyreek Hill has abnormal value: {max_value}")
            return True
        else:
            print(f"   ✅ Tyreek Hill value is normal (≤ 1000)")
            return False
            
    except FileNotFoundError:
        print(f"   ⚠️  {cache_file} not found, skipping Tyreek check")
        return False
    except Exception as e:
        print(f"   ⚠️  Error checking Tyreek value: {e}")
        return False

def fix_tyreek_value(dry_run=False):
    """
    Fix Tyreek Hill's abnormal value by setting it to 801.
    This is the fix_tyreek_value.py logic without the git push.
    """
    print(f"\n🔧 Fixing Tyreek Hill's value...")
    
    if dry_run:
        print("   [DRY RUN - Would fix Tyreek value]")
        return True
    
    cache_file = os.path.join(PIPELINE_DIR, 'asset_values_cache.csv')
    try:
        df = pd.read_csv(cache_file)
        tyreek_mask = df['asset_name'] == 'Tyreek Hill'
        
        # Update value_current to 801
        df.loc[tyreek_mask, 'value_current'] = 801
        df.loc[tyreek_mask, 'value_source_current'] = 'Manual fix (Oct 31 value)'
        
        df.to_csv(cache_file, index=False)
        print("   ✅ Fixed Tyreek Hill's value to 801")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to fix Tyreek value: {e}")
        return False

def copy_files_to_dashboard(dry_run=False):
    """Copy the 3 required files from pipeline/ to git root for Vercel."""
    print(f"\n📁 Copying files from {PIPELINE_DIR}/ to git root...")
    
    all_copied = True
    for filename in REQUIRED_FILES:
        src = os.path.join(PIPELINE_DIR, filename)
        dst = os.path.join(DASHBOARD_ROOT, filename)
        
        if not os.path.exists(src):
            print(f"   ❌ Source file {src} not found!")
            all_copied = False
            continue
            
        if dry_run:
            print(f"   [DRY RUN] Would copy {src} → {dst}")
        else:
            try:
                shutil.copy2(src, dst)
                print(f"   ✅ Copied {src} → {dst}")
            except Exception as e:
                print(f"   ❌ Failed to copy {src}: {e}")
                all_copied = False
    
    return all_copied

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
    
    # Step 0: Check and fix Tyreek value if needed (before Stage 3)
    print("\n🔍 Checking Tyreek Hill's value...")
    needs_tyreek_fix = check_tyreek_value()
    
    # Step 1: Run Python Pipeline (Stages 1-3) from pipeline directory
    print("\n📊 Running Python Pipeline (Stages 1-3)...")
    for stage_name, command in PIPELINE_STAGES[:3]:  # Only stages 1-3
        if not run_command(command, stage_name, args.dry_run, cwd=PIPELINE_DIR):
            print(f"\n❌ Pipeline failed at: {stage_name}")
            sys.exit(1)
    
    # Step 1.5: Fix Tyreek value if needed (after Stage 3, before Stage 4)
    if needs_tyreek_fix:
        if not fix_tyreek_value(args.dry_run):
            print("\n❌ Failed to fix Tyreek value.")
            sys.exit(1)
        print("   ✅ Tyreek value fixed, continuing with Stage 4...")
    
    # Step 2: Continue with remaining pipeline stages (4-7) from pipeline directory
    print("\n📊 Running remaining pipeline stages (4-7)...")
    for stage_name, command in PIPELINE_STAGES[3:]:  # Stages 4-7
        if not run_command(command, stage_name, args.dry_run, cwd=PIPELINE_DIR):
            print(f"\n❌ Pipeline failed at: {stage_name}")
            sys.exit(1)
    
    # Step 3: Verify output files in pipeline directory
    print(f"\n📋 Checking output files in {PIPELINE_DIR}/...")
    all_files_exist = True
    for filename in REQUIRED_FILES:
        filepath = os.path.join(PIPELINE_DIR, filename)
        if not check_file_exists(filepath):
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ Some required files are missing. Pipeline may have failed.")
        sys.exit(1)
    
    # Step 4: Copy files to dashboard
    if not copy_files_to_dashboard(args.dry_run):
        print("\n❌ Failed to copy files to dashboard directory.")
        sys.exit(1)
    
    # Step 5: Deploy (unless skipped)
    if not args.skip_git:
        if not git_deploy(args.dry_run):
            print("\n❌ Deployment failed.")
            sys.exit(1)
    else:
        print("\n⏭️  Skipping git deployment (--skip-git flag)")
    
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