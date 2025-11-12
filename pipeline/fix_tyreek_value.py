#!/usr/bin/env python3
"""
One-time fix for Tyreek Hill's incorrect value in asset_values_cache.csv
Changes value_current from 4950 to 801 (the correct value from Oct 31)
Then reruns stage 4, copies files to dashboard, and pushes to git
"""

import pandas as pd
import subprocess
import sys
import shutil
import os
from datetime import datetime

# Configuration
DASHBOARD_DIR = "trade-analysis-dashboard-clean"
REQUIRED_FILES = [
    "league_trades_analysis_pipeline.csv",
    "3team_trades_analysis.json"
]

def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        print(f"❌ Error running: {cmd}")
        sys.exit(1)
    return result

def copy_files_to_dashboard():
    """Copy the required files to dashboard directory."""
    print(f"\n{'='*80}")
    print(f"STEP 3: Copying files to {DASHBOARD_DIR}/")
    print(f"{'='*80}")
    
    if not os.path.exists(DASHBOARD_DIR):
        print(f"❌ Dashboard directory {DASHBOARD_DIR} not found!")
        return False
    
    all_copied = True
    for filename in REQUIRED_FILES:
        src = filename
        dst = os.path.join(DASHBOARD_DIR, filename)
        
        if not os.path.exists(src):
            print(f"❌ Source file {src} not found!")
            all_copied = False
            continue
            
        try:
            shutil.copy2(src, dst)
            print(f"✅ Copied {src} → {dst}")
        except Exception as e:
            print(f"❌ Failed to copy {src}: {e}")
            all_copied = False
    
    return all_copied

# Step 1: Fix Tyreek Hill's value
print("="*80)
print("STEP 1: Fixing Tyreek Hill's value in asset_values_cache.csv")
print("="*80)

df = pd.read_csv('asset_values_cache.csv')

tyreek_mask = df['asset_name'] == 'Tyreek Hill'
tyreek_count = tyreek_mask.sum()

print(f"\nFound {tyreek_count} Tyreek Hill entries")
print("\nCurrent values:")
print(df[tyreek_mask][['asset_name', 'trade_date', 'value_at_trade', 'value_current', 'value_source_current']].to_string())

# Update value_current to 801
df.loc[tyreek_mask, 'value_current'] = 801
df.loc[tyreek_mask, 'value_source_current'] = 'Manual fix (Oct 31 value)'

print("\nUpdated values:")
print(df[tyreek_mask][['asset_name', 'trade_date', 'value_at_trade', 'value_current', 'value_source_current']].to_string())

df.to_csv('asset_values_cache.csv', index=False)
print("\n✓ Saved updated asset_values_cache.csv")

# Step 2: Rerun stage 4
run_command('python3 stage4_final.py', 'STEP 2: Running stage4_final.py')

# Step 3: Generate dashboard JSON files
run_command('python3 scripts/generate_dashboard_json.py', 'STEP 3: Generating dashboard JSON files')

# Step 4: Copy files to dashboard
if not copy_files_to_dashboard():
    print("\n❌ Failed to copy files to dashboard directory.")
    sys.exit(1)

# Step 5: Git operations in dashboard directory
print("\n" + "="*80)
print("STEP 5: Deploying to GitHub/Vercel")
print("="*80)

# Change to dashboard directory
original_dir = os.getcwd()
os.chdir(DASHBOARD_DIR)

# Check if there are changes
result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
if not result.stdout.strip():
    print("ℹ️  No changes to commit in dashboard")
    os.chdir(original_dir)
else:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"fix: Tyreek Hill value correction (4950→801) - {timestamp}"
    
    run_command('git add .', 'Adding files to git')
    run_command(f'git commit -m "{commit_msg}"', 'Committing changes')
    run_command('git push origin main', 'Pushing to GitHub')
    
    print("🎉 Deployment triggered! Dashboard will update in 2-3 minutes.")
    
    # Return to original directory
    os.chdir(original_dir)

print("\n" + "="*80)
print("✓ ALL DONE!")
print("="*80)
print("\n" + "="*80)
print("✓ ALL DONE!")
print("="*80)
print("\nSummary:")
print("- Fixed Tyreek Hill's value_current: 4950 → 801")
print("- Reran stage 4 (final pipeline)")
print("- Generated dashboard JSON files")
print("- Copied files to dashboard directory")
print("- Committed and pushed to GitHub")
print("\nTyreek Hill is now accurately valued at 801 (Oct 31 value before DynastyProcess regression)")
print("Dashboard will update at: https://dynasuiiiianalytics.vercel.app/ in 2-3 minutes")
