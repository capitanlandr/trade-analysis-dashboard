#!/usr/bin/env python3
"""
Verify 2026 Pick Mapping Logic

This script demonstrates how to map:
- Trade data: "2026 Round 1" + origin_owner (roster_id or username)
- Draft order: roster_id → exact pick position (1.01, 1.02, etc.)
- DynastyProcess: "2026 Pick 1.01" → exact value

Shows the complete mapping chain for verification before updating stage3.
"""

import json
import pandas as pd
from pathlib import Path

def load_draft_order():
    """Load 2026 draft order"""
    draft_file = Path("pipeline/draft_order_2026_progressive.json")
    with open(draft_file, 'r') as f:
        return json.load(f)

def load_team_mappings():
    """Load roster_id to username mappings"""
    teams_csv = Path("pipeline/team_identity_mapping.csv")
    df = pd.read_csv(teams_csv)
    
    # Create both directions of mapping
    roster_to_username = {}
    username_to_roster = {}
    
    for _, row in df.iterrows():
        roster_id = int(row['roster_id'])
        username = str(row['sleeper_username'])
        roster_to_username[roster_id] = username
        username_to_roster[username] = roster_id
    
    return roster_to_username, username_to_roster

def create_pick_mapping(draft_order, roster_to_username):
    """
    Create mapping from (origin_owner_username, round) → pick_label
    
    Returns:
        Dict mapping (username, round) → pick_label (e.g., "1.01")
    """
    pick_mapping = {}
    
    for round_name, picks in draft_order['draft_order'].items():
        # Extract round number (round_1 → 1)
        round_num = int(round_name.split('_')[1])
        
        for pick in picks:
            original_roster_id = pick['original_owner']['roster_id']
            pick_label = pick['pick_label']
            
            # Convert roster_id to username
            username = roster_to_username.get(original_roster_id, f"roster_{original_roster_id}")
            
            key = (username, round_num)
            pick_mapping[key] = pick_label
    
    return pick_mapping

def verify_mapping():
    """Verify the complete mapping chain"""
    
    print("="*80)
    print("2026 PICK MAPPING VERIFICATION")
    print("="*80)
    
    # Load data
    print("\nLoading data...")
    draft_order = load_draft_order()
    roster_to_username, username_to_roster = load_team_mappings()
    
    print(f"✓ Loaded draft order with {draft_order['summary']['total_picks']} picks")
    print(f"✓ Loaded {len(roster_to_username)} team mappings")
    
    # Create mapping
    print("\nCreating pick mapping...")
    pick_mapping = create_pick_mapping(draft_order, roster_to_username)
    print(f"✓ Created {len(pick_mapping)} pick mappings")
    
    # Display mapping
    print("\n" + "="*80)
    print("PICK MAPPING: (username, round) → pick_label")
    print("="*80)
    
    # Group by round for clarity
    for round_num in [1, 2, 3, 4]:
        print(f"\n--- Round {round_num} ---")
        round_picks = [(k, v) for k, v in pick_mapping.items() if k[1] == round_num]
        round_picks.sort(key=lambda x: x[1])  # Sort by pick label
        
        for (username, r), pick_label in round_picks:
            print(f"  {username:25} Round {r} → {pick_label}")
    
    # Test with example from asset_values_cache
    print("\n" + "="*80)
    print("EXAMPLE USAGE FROM ACTUAL TRADES")
    print("="*80)
    
    # Example from grep output: origin='jwalters74', round='4th'
    test_cases = [
        ("jwalters74", 4, "From grep: jwalters74's 2026 Round 4"),
        ("brevinowens", 2, "From grep: brevinowens's 2026 Round 2"),
        ("lndahayo", 1, "From grep: lndahayo's 2026 Round 1"),
    ]
    
    for username, round_num, description in test_cases:
        key = (username, round_num)
        pick_label = pick_mapping.get(key, "NOT FOUND")
        
        # Get DynastyProcess name
        dp_name = f"2026 Pick {pick_label}" if pick_label != "NOT FOUND" else "N/A"
        
        print(f"\n{description}")
        print(f"  Trade data: 2026 Round {round_num} (origin: {username})")
        print(f"  Maps to: {pick_label}")
        print(f"  DynastyProcess lookup: {dp_name}")
    
    # Load DynastyProcess values
    print("\n" + "="*80)
    print("VERIFYING WITH DYNASTYPROCESS VALUES")
    print("="*80)
    
    print("\nFetching DynastyProcess values...")
    df_dp = pd.read_csv("https://github.com/dynastyprocess/data/raw/master/files/values.csv")
    
    for username, round_num, description in test_cases:
        key = (username, round_num)
        pick_label = pick_mapping.get(key)
        
        if pick_label:
            dp_name = f"2026 Pick {pick_label}"
            matches = df_dp[df_dp['player'] == dp_name]
            
            if not matches.empty:
                value = matches.iloc[0]['value_2qb']
                print(f"\n✓ {username}'s 2026 Round {round_num} = {dp_name} = {value:.2f} pts")
            else:
                print(f"\n✗ {dp_name} not found in DynastyProcess!")
    
    print("\n" + "="*80)
    print("MAPPING VERIFICATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    verify_mapping()
