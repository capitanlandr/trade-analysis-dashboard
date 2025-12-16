#!/usr/bin/env python3
"""
Debug script to check waiver wire JSON generation
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

def debug_generation():
    print("=== DEBUG: Waiver Wire JSON Generation ===")
    
    # Check if files exist
    print(f"waiver_wire_analysis.csv exists: {Path('waiver_wire_analysis.csv').exists()}")
    print(f"waiver_wire_summary.json exists: {Path('waiver_wire_summary.json').exists()}")
    
    if not Path('waiver_wire_analysis.csv').exists():
        print("ERROR: waiver_wire_analysis.csv not found")
        return
    
    # Load data
    df = pd.read_csv('waiver_wire_analysis.csv')
    print(f"Loaded {len(df)} transactions from CSV")
    
    # Load summary
    analysis_summary = {}
    if Path('waiver_wire_summary.json').exists():
        with open('waiver_wire_summary.json', 'r') as f:
            analysis_summary = json.load(f)
        print(f"Loaded summary with keys: {list(analysis_summary.keys())}")
    
    # Create a minimal dashboard structure to test
    dashboard_data = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_waiver_transactions': analysis_summary.get('summary', {}).get('total_waiver_transactions', 0),
            'total_free_agent_transactions': analysis_summary.get('summary', {}).get('total_free_agent_transactions', 0),
            'successful_waivers': analysis_summary.get('summary', {}).get('successful_waivers', 0),
            'failed_waivers': analysis_summary.get('summary', {}).get('failed_waivers', 0),
        },
        'manager_activity': analysis_summary.get('manager_activity', []),
        'all_transactions': []  # Empty for now to test structure
    }
    
    print(f"Created dashboard data with keys: {list(dashboard_data.keys())}")
    print(f"Metadata: {dashboard_data['metadata']}")
    
    # Test JSON serialization
    try:
        json_str = json.dumps(dashboard_data, indent=2, default=str)
        print("JSON serialization successful")
        
        # Save test file
        with open('test_waiver_wire.json', 'w') as f:
            json.dump(dashboard_data, f, indent=2, default=str)
        print("Test file saved successfully")
        
    except Exception as e:
        print(f"JSON serialization failed: {e}")

if __name__ == "__main__":
    debug_generation()