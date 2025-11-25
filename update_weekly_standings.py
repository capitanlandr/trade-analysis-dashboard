#!/usr/bin/env python3
"""
Weekly Standings and Playoff Scenarios Update Script

This script orchestrates the complete update process for standings and playoff scenarios:
1. Fetch current standings from Sleeper API
2. Run playoff scenario simulations
3. Generate dashboard JSON files
4. Display summary of updates

Usage:
    python3 update_weekly_standings.py
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def run_command(command: list, description: str, cwd: Path = None) -> bool:
    """
    Run a command and handle output.
    
    Args:
        command: Command to run as list
        description: Human-readable description
        cwd: Working directory (optional)
        
    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*80}")
    print(f"🔄 {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        print(f"✅ {description} - COMPLETE")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def load_json_file(filepath: Path) -> dict:
    """Load and return JSON file contents."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return {}


def print_summary(pipeline_dir: Path):
    """Print summary of updated data."""
    print(f"\n{'='*80}")
    print("📊 UPDATE SUMMARY")
    print(f"{'='*80}\n")
    
    # Load standings data
    standings_file = pipeline_dir / 'standings_data.json'
    if standings_file.exists():
        standings = load_json_file(standings_file)
        metadata = standings.get('metadata', {})
        divisions = standings.get('divisions', [])
        
        print(f"📅 Current Week: {metadata.get('current_week', 'N/A')}")
        print(f"📅 Season: {metadata.get('season', 'N/A')}")
        print(f"🏆 Divisions: {len(divisions)}")
        print(f"👥 Teams: {sum(len(d.get('teams', [])) for d in divisions)}")
        print(f"🕐 Last Updated: {metadata.get('last_updated', 'N/A')}")
    
    # Load playoff scenarios
    playoff_file = pipeline_dir / 'playoff_scenarios_simulated.json'
    if playoff_file.exists():
        playoff = load_json_file(playoff_file)
        results = playoff.get('results', [])
        
        print(f"\n🎲 Simulations Run: {playoff.get('num_simulations', 0):,}")
        
        # Count clinch statuses
        clinched_playoff = sum(1 for r in results if r.get('clinched_playoff'))
        clinched_division = sum(1 for r in results if r.get('clinched_division'))
        clinched_bye = sum(1 for r in results if r.get('clinched_bye'))
        eliminated = sum(1 for r in results if r.get('eliminated'))
        
        print(f"✅ Clinched Playoff: {clinched_playoff}")
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
    
    print(f"\n{'='*80}")
    print("✅ ALL UPDATES COMPLETE")
    print(f"{'='*80}\n")


def main():
    """Main execution."""
    print(f"\n{'='*80}")
    print("🏈 WEEKLY STANDINGS & PLAYOFF SCENARIOS UPDATE")
    print(f"{'='*80}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis script will:")
    print("  1. Fetch current standings from Sleeper API")
    print("  2. Generate dashboard JSON files")
    print("  3. Run 20,000 playoff scenario simulations")
    print("  4. Update dashboard with playoff data")
    print()
    
    # Determine paths
    script_dir = Path(__file__).parent
    pipeline_scripts = script_dir / 'pipeline' / 'scripts'
    
    if not pipeline_scripts.exists():
        print(f"❌ Error: Pipeline scripts directory not found: {pipeline_scripts}")
        return 1
    
    # Step 1: Fetch standings
    if not run_command(
        ['python3', 'fetch_standings.py'],
        'Step 1/3: Fetching current standings from Sleeper API',
        cwd=pipeline_scripts
    ):
        print("\n❌ Failed to fetch standings. Aborting.")
        return 1
    
    # Step 2: Generate initial dashboard JSON (needed for playoff scenarios)
    if not run_command(
        ['python3', 'generate_dashboard_json.py'],
        'Step 2/4: Generating initial dashboard JSON files',
        cwd=pipeline_scripts
    ):
        print("\n❌ Failed to generate initial dashboard files. Aborting.")
        return 1
    
    # Step 3: Run playoff simulations (uses api-standings.json)
    if not run_command(
        ['python3', 'simulate_playoff_scenarios.py'],
        'Step 3/4: Running playoff scenario simulations (20,000 iterations)',
        cwd=pipeline_scripts
    ):
        print("\n❌ Failed to run playoff simulations. Aborting.")
        return 1
    
    # Step 4: Regenerate dashboard JSON with playoff data
    if not run_command(
        ['python3', 'generate_dashboard_json.py'],
        'Step 4/4: Updating dashboard JSON with playoff scenarios',
        cwd=pipeline_scripts
    ):
        print("\n❌ Failed to update dashboard files. Aborting.")
        return 1
    
    # Print summary
    print_summary(script_dir / 'pipeline')
    
    print("💡 Next Steps:")
    print("   1. Review the updated data in the dashboard")
    print("   2. Commit and push changes to deploy:")
    print("      git add -A")
    print("      git commit -m 'Update Week X standings and playoff scenarios'")
    print("      git push origin main")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
