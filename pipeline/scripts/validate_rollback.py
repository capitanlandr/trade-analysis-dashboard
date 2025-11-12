#!/usr/bin/env python3
"""
Validate that rollback was successful by comparing key metrics
"""

import pandas as pd
import os
import sys
import json
from pathlib import Path

def validate_rollback(backup_dir):
    """Compare current state with backup to ensure successful rollback"""
    
    print("🔍 VALIDATING ROLLBACK")
    print("="*50)
    
    backup_path = Path(backup_dir)
    if not backup_path.exists():
        print(f"❌ Backup directory not found: {backup_dir}")
        return False
    
    validation_passed = True
    
    try:
        # 1. Compare cache file row counts
        if os.path.exists('asset_values_cache.csv'):
            current_cache = pd.read_csv('asset_values_cache.csv')
            backup_cache_path = backup_path / 'asset_values_cache.csv'
            
            if backup_cache_path.exists():
                backup_cache = pd.read_csv(backup_cache_path)
                
                if len(current_cache) != len(backup_cache):
                    print(f"❌ Cache row count mismatch: {len(current_cache)} vs {len(backup_cache)}")
                    validation_passed = False
                else:
                    print(f"✓ Cache row count matches: {len(current_cache)}")
                
                # Compare key columns
                if set(current_cache.columns) != set(backup_cache.columns):
                    print(f"❌ Cache columns differ")
                    print(f"  Current: {list(current_cache.columns)}")
                    print(f"  Backup:  {list(backup_cache.columns)}")
                    validation_passed = False
                else:
                    print(f"✓ Cache columns match: {len(current_cache.columns)} columns")
            else:
                print("⚠️  No backup cache file found for comparison")
        
        # 2. Compare analysis file if exists
        if os.path.exists('league_trades_analysis_pipeline.csv'):
            current_analysis = pd.read_csv('league_trades_analysis_pipeline.csv')
            backup_analysis_path = backup_path / 'league_trades_analysis_pipeline.csv'
            
            if backup_analysis_path.exists():
                backup_analysis = pd.read_csv(backup_analysis_path)
                
                if len(current_analysis) != len(backup_analysis):
                    print(f"❌ Analysis row count mismatch: {len(current_analysis)} vs {len(backup_analysis)}")
                    validation_passed = False
                else:
                    print(f"✓ Analysis row count matches: {len(current_analysis)}")
            else:
                print("⚠️  No backup analysis file found for comparison")
        
        # 3. Validate line counts from backup snapshot
        cache_count_file = backup_path / 'cache_line_count.txt'
        if cache_count_file.exists() and os.path.exists('asset_values_cache.csv'):
            with open(cache_count_file, 'r') as f:
                backup_count = f.read().strip()
            
            current_count = len(open('asset_values_cache.csv').readlines())
            backup_number = int(backup_count.split()[0]) if backup_count else 0
            
            if current_count != backup_number:
                print(f"❌ Cache line count validation failed: {current_count} vs {backup_number}")
                validation_passed = False
            else:
                print(f"✓ Cache line count validation passed: {current_count}")
        
        # 4. Check that stage3_cache_values.py was restored
        current_stage3_path = Path('stage3_cache_values.py')
        backup_stage3_path = backup_path / 'stage3_cache_values.py'
        
        if current_stage3_path.exists() and backup_stage3_path.exists():
            current_size = current_stage3_path.stat().st_size
            backup_size = backup_stage3_path.stat().st_size
            
            if current_size != backup_size:
                print(f"❌ stage3_cache_values.py size mismatch: {current_size} vs {backup_size}")
                validation_passed = False
            else:
                print(f"✓ stage3_cache_values.py size matches: {current_size} bytes")
        
        if validation_passed:
            print("✅ ROLLBACK VALIDATION PASSED")
            print("🔄 All files successfully restored to backup state")
        else:
            print("❌ ROLLBACK VALIDATION FAILED")
            print("⚠️  Some files may not have been properly restored")
        
        return validation_passed
        
    except Exception as e:
        print(f"❌ ROLLBACK VALIDATION ERROR: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_rollback.py <backup_dir>")
        print("Example: python3 validate_rollback.py backups/pre_dynamic_columns_20251104_143022")
        sys.exit(1)
    
    backup_dir = sys.argv[1]
    success = validate_rollback(backup_dir)
    
    if success:
        print("\n🎉 Rollback validation successful!")
        print("💡 You can now run 'python3 validate_pipeline.py' to verify pipeline functionality")
    else:
        print("\n⚠️  Rollback validation failed!")
        print("🔧 Manual verification may be required")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()