#!/usr/bin/env python3
"""
Calculate Progressive Draft Order with Certainty Tracking

Determines which picks are locked vs uncertain based on playoff results
available through current week. Outputs draft order with scenarios for
uncertain picks.

Usage:
    python calculate_progressive_draft_order.py

Output:
    pipeline/draft_order_2026_progressive.json
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import (
    fetch_bracket_data,
    identify_special_games,
    get_special_game_participants
)
from utils.week_config import load_week_config
from config import get_config

# Get league ID from config
config = get_config()
LEAGUE_ID = config.league_id

# Constants
TIER_DEFINITIONS = {
    "Early": {"picks": [1, 2, 3, 4], "description": "Top tier picks"},
    "Mid": {"picks": [5, 6, 7, 8], "description": "Mid-round picks"},
    "Late": {"picks": [9, 10, 11, 12], "description": "Late-round picks"}
}


class PickCertainty(str, Enum):
    """Pick certainty states"""
    LOCKED = "locked"
    PENDING = "pending"
    UNKNOWN = "unknown"


@dataclass
class PickScenario:
    """Possible outcome for an uncertain pick"""
    roster_id: int
    team_name: str
    condition: str
    current_owner_roster_id: Optional[int] = None
    current_owner_team_name: Optional[str] = None
    traded: bool = False


@dataclass
class LockedPick:
    """Finalized draft pick"""
    pick_number: int
    pick_label: str
    tier: str
    certainty: str  # "locked"
    original_owner: Dict[str, Any]
    current_owner: Dict[str, Any]
    traded: bool = False


@dataclass
class UncertainPick:
    """Uncertain draft pick with scenarios"""
    pick_number: int
    pick_label: str
    tier: str
    certainty: str  # "pending" or "unknown"
    scenarios: List[Dict[str, Any]]
    pending_game: Optional[str] = None


def load_standings_data() -> Dict:
    """Load regular season standings data"""
    standings_file = Path(__file__).parent.parent / "standings_data.json"
    with open(standings_file) as f:
        return json.load(f)


def load_team_identity_mapping() -> Dict[str, Dict]:
    """
    Load team identity mapping CSV.
    
    Returns:
        Dict mapping sleeper_username -> team info with roster_id and team_name
    """
    mapping_file = Path(__file__).parent.parent / "team_identity_mapping.csv"
    import pandas as pd
    df = pd.read_csv(mapping_file)
    
    mapping = {}
    for _, row in df.iterrows():
        username = row['sleeper_username']
        mapping[username] = {
            'roster_id': row['roster_id'],
            'team_name': row['current_team_name'],
            'real_name': row['real_name']
        }
    
    return mapping


def load_pick_ownership(team_mapping: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Load and invert pick ownership data.
    
    Converts from "Team -> picks they own" to "Pick -> current owner"
    
    Args:
        team_mapping: Username -> roster_id/team_name mapping
    
    Returns:
        Dict mapping "round_origin" -> current owner info
        Example: {"1_roster_7": {"current_owner_roster_id": 5, "current_owner_name": "..."}}
    """
    ownership_file = Path(__file__).parent.parent / "2026_pick_ownership_detailed.json"
    with open(ownership_file) as f:
        ownership_data = json.load(f)
    
    # Invert: origin_team + round -> current owner
    pick_ownership = {}
    
    for team_data in ownership_data:
        current_owner_username = team_data['Team']
        current_owner_info = team_mapping.get(current_owner_username, {})
        
        for pick_detail in team_data.get('Pick_Details', []):
            round_num = pick_detail['round']
            origin_username = pick_detail['origin_team']
            origin_info = team_mapping.get(origin_username, {})
            
            # Key: "round_originRosterId"
            key = f"{round_num}_{origin_info.get('roster_id', origin_username)}"
            
            pick_ownership[key] = {
                'origin_roster_id': origin_info.get('roster_id'),
                'origin_username': origin_username,
                'current_owner_roster_id': current_owner_info.get('roster_id'),
                'current_owner_username': current_owner_username,
                'current_owner_team_name': current_owner_info.get('team_name', current_owner_username),
                'traded': not pick_detail['is_own_pick']
            }
    
    return pick_ownership


def get_regular_season_ranks(standings_data: Dict) -> Dict[int, int]:
    """
    Calculate regular season ranks for all teams.
    
    Returns:
        Dict mapping roster_id -> rank (1-12, lower is better)
    """
    all_teams = []
    for division in standings_data.get('divisions', []):
        for team in division.get('teams', []):
            all_teams.append(team)
    
    # Sort by wins (desc), then points_for (desc)
    sorted_teams = sorted(
        all_teams,
        key=lambda t: (t['record']['wins'], t['points_for']),
        reverse=True
    )
    
    # Assign ranks
    ranks = {}
    for idx, team in enumerate(sorted_teams, start=1):
        ranks[team['roster_id']] = idx
    
    return ranks


def get_tier_for_pick(pick_number: int) -> str:
    """Get tier label for pick number"""
    for tier_name, tier_info in TIER_DEFINITIONS.items():
        if pick_number in tier_info["picks"]:
            return tier_name
    return "Unknown"


def calculate_middle_picks(
    standings_data: Dict,
    special_game_participants: set,
    regular_season_ranks: Dict[int, int],
    pick_ownership: Dict[str, Dict]
) -> List[LockedPick]:
    """
    Calculate picks 1.03-1.08 (middle picks).
    
    These are the 6 teams NOT in special games, sorted by regular season rank.
    """
    # Get all roster IDs
    all_roster_ids = set(regular_season_ranks.keys())
    
    # Remaining teams = all teams - special game participants
    remaining_roster_ids = all_roster_ids - special_game_participants
    
    # Sort by regular season rank (worst to best)
    remaining_sorted = sorted(
        remaining_roster_ids,
        key=lambda rid: regular_season_ranks[rid],
        reverse=True
    )
    
    # Get team names
    team_name_map = {}
    for division in standings_data.get('divisions', []):
        for team in division.get('teams', []):
            team_name_map[team['roster_id']] = team['team_name']
    
    # Create locked picks for 1.03-1.08
    middle_picks = []
    for idx, roster_id in enumerate(remaining_sorted, start=3):
        pick_label = f"1.{idx:02d}"
        
        # Look up current owner from pick ownership data
        ownership_key = f"1_{roster_id}"
        ownership_info = pick_ownership.get(ownership_key, {})
        
        current_owner_roster_id = ownership_info.get('current_owner_roster_id', roster_id)
        current_owner_name = ownership_info.get('current_owner_team_name', team_name_map.get(roster_id, "Unknown"))
        is_traded = ownership_info.get('traded', False)
        
        middle_picks.append(LockedPick(
            pick_number=idx,
            pick_label=pick_label,
            tier=get_tier_for_pick(idx),
            certainty=PickCertainty.LOCKED,
            original_owner={
                "roster_id": roster_id,
                "team_name": team_name_map.get(roster_id, "Unknown"),
                "regular_season_rank": regular_season_ranks[roster_id],
                "description": f"{regular_season_ranks[roster_id]}th place (remaining team)"
            },
            current_owner={
                "roster_id": current_owner_roster_id,
                "team_name": current_owner_name
            },
            traded=is_traded
        ))
    
    return middle_picks


def create_pending_pick_scenarios(
    pick_number: int,
    pick_label: str,
    teams: List[int],
    team_name_map: Dict[int, str],
    game_name: str,
    winner_pick: bool,
    pick_ownership: Dict[str, Dict]
) -> UncertainPick:
    """
    Create an uncertain pick with two possible scenarios.
    
    Args:
        pick_number: Pick number (1-12)
        pick_label: Pick label (e.g., "1.09")
        teams: Two roster IDs that could get this pick
        team_name_map: Mapping of roster_id -> team_name
        game_name: Name of the game (e.g., "Week 17 Championship")
        winner_pick: True if this pick goes to winner, False for loser
        pick_ownership: Pick ownership data from trades
    """
    # Extract round number from pick_label (e.g., "1.09" -> 1)
    round_num = int(pick_label.split('.')[0])
    
    scenarios = []
    for roster_id in teams:
        condition = f"if {team_name_map.get(roster_id, 'Unknown')} {'wins' if winner_pick else 'loses'} {game_name}"
        
        # Look up current owner for this pick
        ownership_key = f"{round_num}_{roster_id}"
        ownership_info = pick_ownership.get(ownership_key, {})
        
        current_owner_roster_id = ownership_info.get('current_owner_roster_id', roster_id)
        current_owner_name = ownership_info.get('current_owner_team_name', team_name_map.get(roster_id, "Unknown"))
        is_traded = ownership_info.get('traded', False)
        
        scenarios.append({
            "roster_id": roster_id,
            "team_name": team_name_map.get(roster_id, "Unknown"),
            "condition": condition,
            "current_owner_roster_id": current_owner_roster_id,
            "current_owner_team_name": current_owner_name,
            "traded": is_traded
        })
    
    return UncertainPick(
        pick_number=pick_number,
        pick_label=pick_label,
        tier=get_tier_for_pick(pick_number),
        certainty=PickCertainty.PENDING,
        scenarios=scenarios,
        pending_game=game_name
    )


def calculate_progressive_draft_order(
    standings_data: Dict,
    bracket_data: Dict,
    through_week: int,
    pick_ownership: Dict[str, Dict]
) -> Dict:
    """
    Calculate progressive draft order based on available data.
    
    Args:
        standings_data: Regular season standings
        bracket_data: Bracket data from Sleeper
        through_week: Last week with complete results
        pick_ownership: Pick ownership data from trades
    
    Returns:
        Dict with draft order and certainty info
    """
    # Identify special games
    special_games = identify_special_games(
        bracket_data['winners_bracket'],
        bracket_data['losers_bracket']
    )
    
    # Get regular season ranks
    regular_season_ranks = get_regular_season_ranks(standings_data)
    
    # Build team name map
    team_name_map = {}
    for division in standings_data.get('divisions', []):
        for team in division.get('teams', []):
            team_name_map[team['roster_id']] = team['team_name']
    
    # Track locked vs uncertain picks
    locked_picks = []
    uncertain_picks = []
    
    # Calculate based on through_week
    if through_week >= 15:
        # Week 15+ complete: Middle picks (1.03-1.08) are LOCKED
        special_game_participants = get_special_game_participants(special_games)
        middle_picks = calculate_middle_picks(
            standings_data,
            special_game_participants,
            regular_season_ranks,
            pick_ownership
        )
        locked_picks.extend(middle_picks)
    
    # Toilet Bowl (picks 1.01-1.02)
    toilet_bowl = special_games.get('toilet_bowl')
    if toilet_bowl and toilet_bowl.get('complete'):
        # Toilet Bowl complete: picks 1.01-1.02 LOCKED
        for pick_num, roster_id, desc in [(1, toilet_bowl['winner'], "Toilet Bowl Winner"),
                                            (2, toilet_bowl['loser'], "Toilet Bowl Loser")]:
            ownership_key = f"1_{roster_id}"
            ownership_info = pick_ownership.get(ownership_key, {})
            
            current_owner_roster_id = ownership_info.get('current_owner_roster_id', roster_id)
            current_owner_name = ownership_info.get('current_owner_team_name', team_name_map.get(roster_id, "Unknown"))
            is_traded = ownership_info.get('traded', False)
            
            locked_picks.append(LockedPick(
                pick_number=pick_num,
                pick_label=f"1.{pick_num:02d}",
                tier=get_tier_for_pick(pick_num),
                certainty=PickCertainty.LOCKED,
                original_owner={
                    "roster_id": roster_id,
                    "team_name": team_name_map.get(roster_id, "Unknown"),
                    "description": desc
                },
                current_owner={
                    "roster_id": current_owner_roster_id,
                    "team_name": current_owner_name
                },
                traded=is_traded
            ))
    elif toilet_bowl and toilet_bowl.get('teams'):
        # Toilet Bowl participants known but game not complete: PENDING
        uncertain_picks.extend([
            create_pending_pick_scenarios(
                1, "1.01", toilet_bowl['teams'], team_name_map,
                "Toilet Bowl", winner_pick=True, pick_ownership=pick_ownership
            ),
            create_pending_pick_scenarios(
                2, "1.02", toilet_bowl['teams'], team_name_map,
                "Toilet Bowl", winner_pick=False, pick_ownership=pick_ownership
            )
        ])
    
    # Championship and 3rd Place (picks 1.09-1.12)
    championship = special_games.get('championship')
    third_place = special_games.get('third_place')
    
    if championship and championship.get('complete') and third_place and third_place.get('complete'):
        # Both complete: picks 1.09-1.12 LOCKED
        for pick_num, roster_id, desc in [
            (9, third_place['winner'], "3rd Place Winner"),
            (10, third_place['loser'], "3rd Place Loser"),
            (11, championship['loser'], "Championship Loser"),
            (12, championship['winner'], "Championship Winner")
        ]:
            ownership_key = f"1_{roster_id}"
            ownership_info = pick_ownership.get(ownership_key, {})
            
            current_owner_roster_id = ownership_info.get('current_owner_roster_id', roster_id)
            current_owner_name = ownership_info.get('current_owner_team_name', team_name_map.get(roster_id, "Unknown"))
            is_traded = ownership_info.get('traded', False)
            
            locked_picks.append(LockedPick(
                pick_number=pick_num,
                pick_label=f"1.{pick_num:02d}",
                tier=get_tier_for_pick(pick_num),
                certainty=PickCertainty.LOCKED,
                original_owner={
                    "roster_id": roster_id,
                    "team_name": team_name_map.get(roster_id, "Unknown"),
                    "description": desc
                },
                current_owner={
                    "roster_id": current_owner_roster_id,
                    "team_name": current_owner_name
                },
                traded=is_traded
            ))
    elif championship and championship.get('teams') and third_place and third_place.get('teams'):
        # Participants known but games not complete: PENDING
        uncertain_picks.extend([
            create_pending_pick_scenarios(
                9, "1.09", third_place['teams'], team_name_map,
                "3rd Place Game", winner_pick=True, pick_ownership=pick_ownership
            ),
            create_pending_pick_scenarios(
                10, "1.10", third_place['teams'], team_name_map,
                "3rd Place Game", winner_pick=False, pick_ownership=pick_ownership
            ),
            create_pending_pick_scenarios(
                11, "1.11", championship['teams'], team_name_map,
                "Championship", winner_pick=False, pick_ownership=pick_ownership
            ),
            create_pending_pick_scenarios(
                12, "1.12", championship['teams'], team_name_map,
                "Championship", winner_pick=True, pick_ownership=pick_ownership
            )
        ])
    
    # Combine all picks and sort by pick number
    round_1_picks = []
    for pick in locked_picks:
        round_1_picks.append(asdict(pick))
    for pick in uncertain_picks:
        pick_dict = asdict(pick)
        round_1_picks.append(pick_dict)
    
    round_1_picks.sort(key=lambda p: p['pick_number'])
    
    # Generate rounds 2-4 (same draft order, different ownership)
    all_rounds = {"round_1": round_1_picks}
    
    for round_num in [2, 3, 4]:
        round_picks = []
        for pick in round_1_picks:
            # Deep copy to avoid modifying original
            import copy
            round_pick = copy.deepcopy(pick)
            round_pick['pick_label'] = f"{round_num}.{pick['pick_number']:02d}"
            
            # For locked picks, update ownership for this round
            if round_pick.get('certainty') == 'locked':
                orig_roster_id = round_pick['original_owner']['roster_id']
                ownership_key = f"{round_num}_{orig_roster_id}"
                ownership_info = pick_ownership.get(ownership_key, {})
                
                if ownership_info:
                    # Found trade data for this round
                    current_owner_roster_id = ownership_info.get('current_owner_roster_id', orig_roster_id)
                    current_owner_name = ownership_info.get('current_owner_team_name', team_name_map.get(orig_roster_id, "Unknown"))
                    is_traded = ownership_info.get('traded', False)
                    
                    round_pick['current_owner'] = {
                        "roster_id": current_owner_roster_id,
                        "team_name": current_owner_name
                    }
                    round_pick['traded'] = is_traded
            
            # For uncertain picks, update scenarios ownership for this round
            elif round_pick.get('certainty') in ['pending', 'unknown']:
                if 'scenarios' in round_pick:
                    for scenario in round_pick['scenarios']:
                        orig_roster_id = scenario['roster_id']
                        ownership_key = f"{round_num}_{orig_roster_id}"
                        ownership_info = pick_ownership.get(ownership_key, {})
                        
                        if ownership_info:
                            scenario['current_owner_roster_id'] = ownership_info.get('current_owner_roster_id', orig_roster_id)
                            scenario['current_owner_team_name'] = ownership_info.get('current_owner_team_name', team_name_map.get(orig_roster_id, "Unknown"))
                            scenario['traded'] = ownership_info.get('traded', False)
                        else:
                            # No trade, keep original owner
                            scenario['current_owner_roster_id'] = orig_roster_id
                            scenario['current_owner_team_name'] = team_name_map.get(orig_roster_id, "Unknown")
                            scenario['traded'] = False
            
            round_picks.append(round_pick)
        
        all_rounds[f"round_{round_num}"] = round_picks
    
    return {
        "season": 2025,
        "draft_year": 2026,
        "through_week": through_week,
        "determination_level": "partial" if uncertain_picks else "complete",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_picks": 48,  # 12 per round x 4 rounds
            "locked_picks": len(locked_picks) * 4,  # Same across all rounds
            "uncertain_picks": len(uncertain_picks) * 4,
            "round_1_locked": len(locked_picks),
            "round_1_uncertain": len(uncertain_picks)
        },
        "draft_order": all_rounds
    }


def main():
    """Main execution"""
    print("=" * 60)
    print("Progressive Draft Order Calculation")
    print("=" * 60)
    
    # Load week configuration
    print("\n1. Loading week configuration...")
    week_config = load_week_config()
    through_week = week_config.get('through_week', 14)
    print(f"   Through week: {through_week}")
    
    # Load standings data
    print("\n2. Loading regular season standings...")
    standings_data = load_standings_data()
    total_teams = sum(len(d['teams']) for d in standings_data['divisions'])
    print(f"   Teams: {total_teams}")
    
    # Load team mapping
    print("\n3. Loading team identity mapping...")
    team_mapping = load_team_identity_mapping()
    print(f"   Mapped {len(team_mapping)} teams")
    
    # Load pick ownership
    print("\n4. Loading pick ownership data...")
    pick_ownership = load_pick_ownership(team_mapping)
    print(f"   Loaded {len(pick_ownership)} pick ownership entries")
    
    # Fetch bracket data
    print(f"\n5. Fetching playoff bracket data (League ID: {LEAGUE_ID})...")
    bracket_data = fetch_bracket_data(LEAGUE_ID)
    print(f"   Winners bracket matches: {len(bracket_data['winners_bracket'])}")
    print(f"   Losers bracket matches: {len(bracket_data['losers_bracket'])}")
    
    # Calculate progressive draft order
    print("\n6. Calculating progressive draft order...")
    draft_order = calculate_progressive_draft_order(
        standings_data,
        bracket_data,
        through_week,
        pick_ownership
    )
    
    print(f"\n   Status: {draft_order['determination_level']}")
    print(f"   Locked picks: {draft_order['summary']['locked_picks']}")
    print(f"   Uncertain picks: {draft_order['summary']['uncertain_picks']}")
    
    # Display picks
    print("\n7. Draft Order Summary:")
    print("   " + "-" * 56)
    for pick in draft_order['draft_order']['round_1']:
        pick_label = pick['pick_label']
        certainty = pick['certainty']
        
        if certainty == 'locked':
            orig_team = pick['original_owner']['team_name']
            curr_team = pick['current_owner']['team_name']
            traded_marker = " (TRADED)" if pick.get('traded') else ""
            print(f"   {pick_label}: ✅ {orig_team} → {curr_team}{traded_marker}")
        else:
            scenarios = pick.get('scenarios', [])
            if scenarios:
                team1 = scenarios[0]['team_name']
                team2 = scenarios[1]['team_name'] if len(scenarios) > 1 else "Unknown"
                print(f"   {pick_label}: ⏳ {team1} OR {team2}")
    
    # Write output files
    output_file = Path(__file__).parent.parent / "draft_order_2026_progressive.json"
    dashboard_file = Path(__file__).parent.parent.parent / "dashboard/frontend/public/api-draft-order.json"
    
    print(f"\n8. Writing output files...")
    with open(output_file, 'w') as f:
        json.dump(draft_order, f, indent=2)
    print(f"   ✓ {output_file.name}")
    
    # Copy to dashboard
    dashboard_file.parent.mkdir(parents=True, exist_ok=True)
    with open(dashboard_file, 'w') as f:
        json.dump(draft_order, f, indent=2)
    print(f"   ✓ {dashboard_file.name}")
    
    print("\n✅ Progressive draft order calculation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
