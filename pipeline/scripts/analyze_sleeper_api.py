#!/usr/bin/env python3
"""
Analyze Sleeper API capabilities for draft order system.

Investigates:
1. NFL state and week tracking
2. League metadata and playoff settings
3. Roster data during playoffs
4. Matchup structure in playoff weeks
5. Bracket/winners endpoints

Usage:
    python pipeline/scripts/analyze_sleeper_api.py <league_id>
"""

import requests
import json
import sys
from typing import Dict, Any
from collections import defaultdict


def fetch_and_display(url: str, title: str) -> Dict[str, Any]:
    """Fetch from URL and display formatted"""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nResponse ({len(json.dumps(data))} bytes):")
            print(json.dumps(data, indent=2))
            return data
        else:
            print(f"Error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Exception: {e}")
        return None


def analyze_nfl_state():
    """Analyze NFL state endpoint"""
    url = "https://api.sleeper.app/v1/state/nfl"
    data = fetch_and_display(url, "1. NFL STATE ENDPOINT")
    
    if data:
        print("\n--- KEY OBSERVATIONS ---")
        print(f"Current Week: {data.get('week')}")
        print(f"Season Type: {data.get('season_type')}")
        print(f"Season: {data.get('season')}")
        
        # Check all fields
        print("\nAll Available Fields:")
        for key, value in data.items():
            print(f"  - {key}: {value}")
    
    return data


def analyze_league(league_id: str):
    """Analyze league metadata"""
    url = f"https://api.sleeper.app/v1/league/{league_id}"
    data = fetch_and_display(url, "2. LEAGUE METADATA")
    
    if data:
        print("\n--- PLAYOFF SETTINGS ---")
        settings = data.get('settings', {})
        playoff_keys = [k for k in settings.keys() if 'playoff' in k.lower()]
        
        if playoff_keys:
            for key in playoff_keys:
                print(f"  - {key}: {settings[key]}")
        else:
            print("  No playoff-specific settings found")
        
        print("\n--- ALL SETTINGS KEYS ---")
        for key in sorted(settings.keys()):
            print(f"  - {key}")
    
    return data


def analyze_rosters(league_id: str):
    """Analyze roster data structure"""
    url = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    data = fetch_and_display(url, "3. ROSTERS DATA")
    
    if data and len(data) > 0:
        print("\n--- FIRST ROSTER SETTINGS ---")
        settings = data[0].get('settings', {})
        for key, value in settings.items():
            print(f"  - {key}: {value}")
        
        print("\n--- CHECKING FOR PLAYOFF FIELDS ---")
        playoff_fields = [k for k in settings.keys() if any(
            x in k.lower() for x in ['playoff', 'seed', 'bracket', 'rank']
        )]
        if playoff_fields:
            print("Found playoff-related fields:")
            for field in playoff_fields:
                print(f"  ✅ {field}: {settings[field]}")
        else:
            print("  ❌ No playoff-specific fields found in roster settings")
    
    return data


def analyze_matchups(league_id: str, weeks: list):
    """Analyze matchup data for multiple weeks"""
    all_matchups = {}
    
    for week in weeks:
        url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
        data = fetch_and_display(url, f"4.{week}. MATCHUPS - WEEK {week}")
        
        if data:
            all_matchups[week] = data
            
            print(f"\n--- WEEK {week} OBSERVATIONS ---")
            print(f"Total matchup entries: {len(data)}")
            
            # Unique matchup IDs
            matchup_ids = set(m.get('matchup_id') for m in data if m.get('matchup_id'))
            print(f"Unique matchup_ids: {sorted(matchup_ids) if matchup_ids else 'None'}")
            
            # Check for scores (0 = not played yet)
            has_scores = [m for m in data if m.get('points', 0) > 0]
            print(f"Matchups with scores: {len(has_scores)}/{len(data)}")
            
            # Group by matchup_id to see matchup pairs
            grouped = defaultdict(list)
            for m in data:
                if m.get('matchup_id'):
                    grouped[m['matchup_id']].append(m)
            
            print(f"\nMatchup Pairings:")
            for matchup_id, teams in sorted(grouped.items()):
                roster_ids = [t['roster_id'] for t in teams]
                points = [t.get('points', 0) for t in teams]
                print(f"  Matchup {matchup_id}: Rosters {roster_ids} - Points {points}")
            
            # Check for playoff-specific fields
            if len(data) > 0:
                print("\nFirst matchup all fields:")
                for key in sorted(data[0].keys()):
                    print(f"  - {key}")
                
                # Look for special fields
                special_fields = [k for k in data[0].keys() if any(
                    x in k.lower() for x in ['bracket', 'playoff', 'tier', 'round', 'type']
                )]
                if special_fields:
                    print("\n✅ Found playoff-specific fields:")
                    for field in special_fields:
                        print(f"  - {field}: {data[0][field]}")
                else:
                    print("\n❌ No playoff-specific fields found")
    
    return all_matchups


def try_bracket_endpoints(league_id: str):
    """Try various bracket-related endpoints"""
    endpoints = [
        f"/v1/league/{league_id}/winners_bracket",
        f"/v1/league/{league_id}/winners_bracket/1",
        f"/v1/league/{league_id}/winners_bracket/2",
        f"/v1/league/{league_id}/winners_bracket/3",
        f"/v1/league/{league_id}/losers_bracket",
        f"/v1/league/{league_id}/losers_bracket/1",
        f"/v1/league/{league_id}/losers_bracket/2",
        f"/v1/league/{league_id}/losers_bracket/3",
        f"/v1/league/{league_id}/playoff_bracket",
        f"/v1/league/{league_id}/brackets",
        f"/v1/league/{league_id}/playoff",
        f"/v1/league/{league_id}/playoffs",
    ]
    
    print(f"\n{'=' * 80}")
    print("5. TESTING BRACKET ENDPOINTS")
    print(f"{'=' * 80}\n")
    
    found_endpoints = []
    
    for endpoint in endpoints:
        url = f"https://api.sleeper.app{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                status = "✅ EXISTS"
                found_endpoints.append(endpoint)
                data = response.json()
                print(f"{status} - {endpoint}")
                print(f"         Response: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"❌ {response.status_code} - {endpoint}")
        except Exception as e:
            print(f"❌ ERROR - {endpoint}: {e}")
    
    if found_endpoints:
        print(f"\n✅ FOUND {len(found_endpoints)} working bracket endpoints!")
        print("These endpoints should be investigated further.")
    else:
        print("\n❌ No bracket endpoints found - will need to derive from matchup data")


def summarize_findings(nfl_state, league_data, rosters_data, matchups_data):
    """Summarize key findings"""
    print(f"\n{'=' * 80}")
    print("SUMMARY OF FINDINGS")
    print(f"{'=' * 80}\n")
    
    print("WEEK TRACKING:")
    if nfl_state:
        week = nfl_state.get('week')
        season_type = nfl_state.get('season_type')
        print(f"  ✅ Sleeper provides: week={week}, season_type={season_type}")
        print(f"  ❓ Question: Does this update immediately or after week completes?")
        print(f"  ❓ Question: How to detect 'data available through week X'?")
    
    print("\nPLAYOFF BRACKET IDENTIFICATION:")
    print("  ❓ Need to check matchup data for bracket indicators")
    print("  ❓ Can we identify Championship vs 3rd Place vs Toilet Bowl?")
    
    print("\nMATCHUP DATA AVAILABILITY:")
    if matchups_data:
        for week, data in matchups_data.items():
            has_scores = len([m for m in data if m.get('points', 0) > 0])
            print(f"  Week {week}: {len(data)} matchups, {has_scores} with scores")
    
    print("\nDATA GAPS:")
    print("  - Need to determine: Which matchup is Championship vs 3rd Place")
    print("  - Need to track: Results available through week X")
    print("  - Need to calculate: Progressive draft order certainty")
    
    print("\n" + "=" * 80)


def main():
    """Run full analysis"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_sleeper_api.py <league_id>")
        print("\nExample: python analyze_sleeper_api.py 1050048277552975872")
        sys.exit(1)
    
    league_id = sys.argv[1]
    
    print("=" * 80)
    print("SLEEPER API ANALYSIS")
    print("=" * 80)
    print(f"League ID: {league_id}")
    print(f"Analysis Date: 2024-12-29")
    print(f"Current NFL: Week 17 (Playoffs)")
    print("=" * 80)
    
    # Run analyses
    nfl_state = analyze_nfl_state()
    league_data = analyze_league(league_id)
    rosters_data = analyze_rosters(league_id)
    matchups_data = analyze_matchups(league_id, weeks=[14, 15, 16, 17])
    try_bracket_endpoints(league_id)
    
    # Summarize
    summarize_findings(nfl_state, league_data, rosters_data, matchups_data)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review output to understand API capabilities")
    print("2. Identify gaps between API data and design requirements")
    print("3. Update design documents with API constraints")
    print("4. Determine what needs to be calculated vs fetched")
    print("\nOutput saved to: pipeline/sleeper_api_analysis_output.txt")


if __name__ == "__main__":
    main()
