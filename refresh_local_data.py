#!/usr/bin/env python3
"""
Refresh Local Dashboard Data
=============================

Updates the JSON files that localhost reads WITHOUT pushing to git.
Run this whenever you want to see updated data in your local dev server.

Usage:
    python3 refresh_local_data.py
"""

import subprocess
import sys
import os

def main():
    print("🔄 Refreshing local dashboard data...")
    print("   (This will NOT push to git)")
    print()
    
    # Get the directory where this script lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        result = subprocess.run(
            ["python3", "update_dashboard.py", "--skip-git"],
            cwd=script_dir,
            check=True
        )
        
        print()
        print("✅ Local data refreshed!")
        print("   Refresh your browser to see changes")
        print("   http://localhost:5173")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print()
        print("❌ Failed to refresh data")
        print(f"   Error: {e}")
        return 1
    except KeyboardInterrupt:
        print()
        print("⏹️  Cancelled by user")
        return 1

if __name__ == "__main__":
    sys.exit(main())
