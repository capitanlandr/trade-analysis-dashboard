# Progressive Draft Order Determination and Dashboard Design

**Date:** December 29, 2024
**Status:** ✅ Feature Complete - Live in Production
**Purpose:** Define progressive draft order tracking and "Draft Order Projection" dashboard feature

> **Note:** Draft Order Projection page implemented at `/draft-order` route. Updates weekly with standings changes.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Progressive Determination Model](#2-progressive-determination-model)
3. [Week Tracking Architecture](#3-week-tracking-architecture)
4. [Draft Order Projection Dashboard](#4-draft-order-projection-dashboard)
5. [Implementation Design](#5-implementation-design)
6. [Data Structures](#6-data-structures)

---

## 1. Overview

### The Problem

Draft order determination is not instantaneous—it progresses week-by-week as playoff results finalize:

**Current State (Week 16 complete, Week 17 pending):**
- ✅ **Locked:** Picks 1.01-1.08 (Toilet Bowl complete, middle picks known)
- ❓ **Uncertain:** Picks 1.09-1.12 (Championship and 3rd place pending)
  - "1.12 could be Team A (if they win championship) OR Team B (if they lose)"

### The Solution

Create a **Progressive Draft Order System** that:
1. Tracks which picks are **locked** (finalized) vs **uncertain** (pending results)
2. Shows **possible outcomes** for uncertain picks
3. Updates automatically as each playoff week completes
4. Powers a dashboard "Draft Order Projection" page

### User Value

**For League Members:**
- See exactly which picks are finalized
- Understand potential draft order scenarios before playoffs complete
- Track pick value changes as playoffs progress

**For Commissioners:**
- Transparency in draft order determination
- Clear communication of when picks finalize

---

## 2. Progressive Determination Model

### Draft Order Determination Timeline

| Week | Games Completed | Picks Locked | Picks Uncertain | Notes |
|------|----------------|--------------|-----------------|-------|
| **Week 14** | Regular season ends | NONE (0 picks) | ALL 1.01-1.12 (12 picks) | Know standings, but not special game participants |
| **Week 15** | Wild Card + Consolation First Round | 1.03-1.08 (6 picks) | 1.01-1.02, 1.09-1.12 (6 picks) | Special game participants now known → middle picks finalized |
| **Week 16** | Semifinals + Toilet Bowl | 1.01-1.08 (8 picks) | 1.09-1.12 (4 picks) | Toilet Bowl complete; Championship/3rd place participants known |
| **Week 17** | Finals (Championship + 3rd Place) | ALL 1.01-1.12 (12 picks) | None | Draft order fully finalized |

### Pick Certainty Levels

Each pick has a **certainty state**:

```python
class PickCertainty(Enum):
    LOCKED = "locked"           # Finalized, no changes possible
    PENDING_RESULT = "pending"  # Game identified, awaiting result
    UNKNOWN = "unknown"         # Game not yet played, participants unknown
```

### Determination Rules by Pick

| Pick | Lock Condition | Depends On |
|------|---------------|------------|
| **1.01** | Toilet Bowl winner determined | Week 16 consolation result |
| **1.02** | Toilet Bowl loser determined | Week 16 consolation result |
| **1.03-1.08** | Remaining 6 teams identified + standings known | Week 15 completion (identifies special game participants) |
| **1.09** | 3rd place game winner determined | Week 17 consolation result |
| **1.10** | 3rd place game loser determined | Week 17 consolation result |
| **1.11** | Championship game loser determined | Week 17 championship result |
| **1.12** | Championship game winner determined | Week 17 championship result |

### Critical Insight: Middle Picks (1.03-1.08)

**The middle picks are NOT finalized after Week 14, even though they're based on regular season standings.**

**Why?** Because we need to know which 6 teams are "remaining" (not in special games).

**Example: 3-seed team finished 9th in regular season**

**After Week 14 (before playoffs):**
- Team's possible outcomes: ANY pick from 1.03 to 1.12
  - If wins championship → 1.12
  - If loses championship → 1.11
  - If wins 3rd place → 1.09
  - If loses 3rd place → 1.10
  - If doesn't make championship or 3rd place → Somewhere in 1.03-1.08

**After Week 15 (loses in Wild Card immediately):**
- Team is OUT of championship and 3rd place contention
- Now we know they're in the "remaining 6" pool for picks 1.03-1.08
- Their position in that pool: Based on 9th place regular season finish
- **BUT** their specific pick (1.03? 1.04? 1.05?) depends on which OTHER teams are also in that pool

**Scenario A:** Teams 11-12 both lose in consolation first round (play in Toilet Bowl)
- Remaining 6 teams ranked 10th, 9th, 8th, 7th, 6th, 5th
- 9th place team gets pick 1.04 (2nd worst of remaining 6)

**Scenario B:** Team 11 wins consolation semifinal (makes consolation championship)
- Now team 11 is in a special game (consolation championship)
- Remaining 6 teams ranked 12th, 10th, 9th, 8th, 7th, 6th
- 9th place team gets pick 1.03 (3rd worst of remaining 6, but 12th and 10th are worse)
- Wait no... team 12 would be in toilet bowl too...

Let me think through this more carefully with the actual bracket structure:

**Week 15 Results determine:**
- Championship participants (2 teams) → Will get 1.11 or 1.12
- 3rd place participants (2 teams) → Will get 1.09 or 1.10
- Toilet bowl participants (2 teams) → Will get 1.01 or 1.02
- **Remaining 6 teams** → Will get 1.03-1.08 in reverse regular season order

**Therefore:** After Week 15, picks 1.03-1.08 are LOCKED because we now know exactly which 6 teams are in that pool and their regular season ranks.

---

### Worked Example: "Mostly Washed" Pick Range Narrowing

**Team Profile:**
- **Team Name:** "Mostly Washed"
- **Regular Season Record:** 11-17 (9th place in standings)
- **Playoff Seeding:** 3-seed (division winner with worst record)
- **Division:** 1

#### Week 14: Regular Season Complete

**What We Know:**
- Team finished 9th in regular season standings
- Team is 3-seed in playoffs (division winner)
- Will play in Wild Card round (3-seed vs 6-seed)

**Pick Range: 1.03 to 1.12 (10 possible picks!)**

**Possible Outcomes:**
```
Championship Path:
- Wins Wild Card → Wins Semifinal → Wins Championship → Pick 1.12
- Wins Wild Card → Wins Semifinal → Loses Championship → Pick 1.11

3rd Place Path:
- Wins Wild Card → Loses Semifinal → Wins 3rd Place → Pick 1.09
- Wins Wild Card → Loses Semifinal → Loses 3rd Place → Pick 1.10

Remaining Pool Path (eliminated early):
- Loses Wild Card → Somewhere in picks 1.03-1.08
  - Exact position depends on which OTHER teams end up in remaining pool
```

#### Week 15: Lost in Wild Card

**What Happened:**
- Team lost to 6-seed in Wild Card round
- Eliminated from Championship and 3rd Place contention
- Will NOT play in any special games

**What We Now Know:**
- Special game participants identified:
  - **Championship (Week 17):** Seeds 1, 2 (had byes) + Wild Card winners
  - **3rd Place (Week 17):** Week 16 semifinal losers (2 teams)
  - **Toilet Bowl (Week 16):** Losers of consolation 9v12 and 10v11 (2 teams)
  - **Remaining 6:** Everyone else, including "Mostly Washed"

**Pick Range: 1.03 to 1.08 (narrowed to 6 picks)**

**Determining Exact Pick:**
The 6 "remaining" teams based on 2024 actual results:
1. 5th place team (eliminated from playoffs)
2. 6th place team (lost Wild Card)
3. 7th place team (consolation, didn't make Toilet Bowl)
4. 8th place team (consolation, didn't make Toilet Bowl)
5. **9th place team ("Mostly Washed")**
6. 10th place team (consolation, didn't make Toilet Bowl)

**Sorted in reverse order (worst gets best pick):**
- Pick 1.03 → 10th place team
- **Pick 1.04 → 9th place team ("Mostly Washed")** ✅ LOCKED
- Pick 1.05 → 8th place team
- Pick 1.06 → 7th place team
- Pick 1.07 → 6th place team
- Pick 1.08 → 5th place team

#### Week 16: Toilet Bowl Complete

**What Happened:**
- Toilet Bowl game played and completed
- Championship and 3rd Place participants now in semifinals

**What's Locked:**
- Picks 1.01-1.08 (8 picks total)
- "Mostly Washed" confirmed at 1.04

**Still Uncertain:**
- Picks 1.09-1.12 (4 picks - awaiting Week 17 results)

#### Week 17: All Finals Complete

**What Happened:**
- Championship game determines 1.11 and 1.12
- 3rd Place game determines 1.09 and 1.10

**What's Locked:**
- All picks 1.01-1.12
- "Mostly Washed" finalized at 1.04

### Key Insight for Implementation

**After Week 15, we can lock picks 1.03-1.08 because:**

1. We know the 6 special game participants:
   - 2 in Championship (Week 17)
   - 2 in 3rd Place (Week 17)
   - 2 in Toilet Bowl (Week 16)

2. The remaining 6 teams are "everyone else"

3. These 6 teams sort by regular season standing (reverse order)

4. No more changes possible - they can't make special games anymore

**This is the critical unlock moment for the middle picks!**

---

## 3. Week Tracking Architecture

### Enhanced Week Configuration

Extend [`pipeline/config/current_week.json`](../pipeline/config/current_week.json):

```json
{
  "season_year": 2024,
  "season_phase": "playoffs",
  
  "weeks": {
    "nfl_calendar_week": 17,
    "regular_season_week": 14,
    "playoff_week": 3
  },
  
  "playoff_results": {
    "through_week": 16,
    "weeks_available": [15, 16],
    "weeks_pending": [17]
  },
  
  "draft_order_state": {
    "determination_level": "partial",
    "locked_picks": 8,
    "uncertain_picks": 4,
    "last_updated": "2024-12-29T12:00:00Z"
  },
  
  "last_updated": "2024-12-29T12:00:00Z"
}
```

### Configuration Fields Explained

**`weeks` object:**
- `nfl_calendar_week`: Current NFL week number (1-18)
- `regular_season_week`: Final regular season week (always 14)
- `playoff_week`: Current playoff round (1=Week 15, 2=Week 16, 3=Week 17)

**`playoff_results` object:**
- `through_week`: Last week with complete results available
- `weeks_available`: Array of weeks with results fetched
- `weeks_pending`: Array of weeks not yet complete

**`draft_order_state` object:**
- `determination_level`: "none", "partial", "complete"
- `locked_picks`: Number of finalized first-round picks (0-12)
- `uncertain_picks`: Number of pending first-round picks (12-0)

### Determination Levels

```python
class DraftOrderDeterminationLevel(Enum):
    NONE = "none"           # Before Week 14 ends
    PARTIAL = "partial"     # Week 14-16 (some picks locked)
    COMPLETE = "complete"   # After Week 17 (all picks locked)

def get_determination_level(through_week: int) -> str:
    """Determine draft order determination level."""
    if through_week < 14:
        return "none"
    elif through_week < 17:
        return "partial"
    else:
        return "complete"
```

### Week Progression Logic

```python
def update_week_config_after_results(nfl_week: int):
    """
    Update week configuration after new playoff results available.
    
    Called after fetching playoff matchup results for a week.
    """
    config = load_week_config()
    
    # Update playoff results tracking
    config["playoff_results"]["through_week"] = nfl_week
    config["playoff_results"]["weeks_available"].append(nfl_week)
    config["playoff_results"]["weeks_pending"].remove(nfl_week)
    
    # Update draft order state
    config["draft_order_state"]["determination_level"] = get_determination_level(nfl_week)
    config["draft_order_state"]["locked_picks"] = count_locked_picks(nfl_week)
    config["draft_order_state"]["uncertain_picks"] = 12 - count_locked_picks(nfl_week)
    
    # Save config
    save_week_config(config)

def count_locked_picks(through_week: int) -> int:
    """
    Count how many first-round picks are locked.
    
    Critical logic:
    - Middle picks (1.03-1.08) require knowing which 6 teams are "remaining"
    - "Remaining" = teams not in Championship, 3rd Place, or Toilet Bowl
    - This is only known AFTER Week 15 (when special game participants identified)
    """
    if through_week < 14:
        return 0  # Regular season not complete
    elif through_week == 14:
        return 0  # Know standings, but not special game participants yet
    elif through_week == 15:
        return 6  # Picks 1.03-1.08 now locked (special game participants identified)
    elif through_week == 16:
        return 8  # Middle picks + Toilet Bowl (1.01-1.02)
    elif through_week >= 17:
        return 12  # All picks finalized
    else:
        return 0
```

---

## 4. Draft Order Projection Dashboard

### Page Overview

**Route:** `/draft-order-projection`

**Purpose:** Show current and projected draft order with certainty indicators

**Use Cases:**
1. **During Playoffs (Weeks 15-16):** Show locked picks + possible scenarios
2. **After Week 17:** Show finalized draft order
3. **Trade Analysis:** Help managers evaluate pick trades during playoffs

### UI Mockup

```
┌─────────────────────────────────────────────────────────────────┐
│ 2026 Draft Order Projection                                     │
│                                                                   │
│ Status: 8 of 12 picks finalized (Week 16 complete)              │
│ Next Update: After Week 17 Championship (Jan 5, 2025)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ✅ FINALIZED PICKS (8)                                           │
│                                                                   │
│ Pick  Original Owner      Current Owner       Status             │
│ ────  ────────────────   ────────────────    ────────────       │
│ 1.01  TRIPS 🔥           TRIPS 🔥             ✅ LOCKED          │
│       (Toilet Bowl Winner)                                       │
│                                                                   │
│ 1.02  Spirit Halloween   Mommy Rainier        ✅ LOCKED (Traded)│
│       (Toilet Bowl Loser)                                        │
│                                                                   │
│ 1.03  On To 2026         On To 2026           ✅ LOCKED          │
│       (10th place)                                               │
│                                                                   │
│ 1.04  Mostly Washed      Mostly Washed        ✅ LOCKED          │
│       (9th place)                                                │
│                                                                   │
│ 1.05  Gaeta Spur FC      Paper Tigers         ✅ LOCKED (Traded)│
│       (8th place)                                                │
│                                                                   │
│ 1.06  Rashid Shaheed     Rashid Shaheed       ✅ LOCKED          │
│       (7th place)                                                │
│                                                                   │
│ 1.07  Paper Tigers       Gaeta Spur FC        ✅ LOCKED (Traded)│
│       (6th place)                                                │
│                                                                   │
│ 1.08  Mommy Rainier      Spirit Halloween     ✅ LOCKED (Traded)│
│       (5th place)                                                │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ ⏳ PENDING RESULTS - WEEK 17 CHAMPIONSHIP (4 picks)             │
│                                                                   │
│ Pick  Scenario A               Scenario B                        │
│ ────  ─────────────────────   ─────────────────────────         │
│ 1.09  🏆 208 Ferrari Way      🏆 Like a Good Naber             │
│       (if wins 3rd place)      (if wins 3rd place)              │
│       Current: 208 Ferrari     Current: Like a Good Naber       │
│                                                                   │
│ 1.10  💔 Like a Good Naber    💔 208 Ferrari Way                │
│       (if loses 3rd place)     (if loses 3rd place)             │
│       Current: Like a Good     Current: 208 Ferrari             │
│                                                                   │
│ 1.11  💔 Bucky's Depression   💔 2-Man Title Charge             │
│       (if loses championship)  (if loses championship)          │
│       Current: Bucky's Dep.    Current: 2-Man Title             │
│                                                                   │
│ 1.12  🏆 2-Man Title Charge   🏆 Bucky's Depression            │
│       (if wins championship)   (if wins championship)           │
│       Current: 2-Man Title     Current: Bucky's Depression      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Legend:
✅ LOCKED - Pick finalized, no changes possible
⏳ PENDING - Awaiting game result
🏆 Winner scenario
💔 Loser scenario
```

### Key Features

1. **Visual Certainty Indicators**
   - Green checkmark (✅) for locked picks
   - Clock icon (⏳) for pending picks
   - Color coding: Green (locked), Yellow (pending), Gray (unknown)

2. **Scenario Display**
   - For uncertain picks, show both possible outcomes
   - Clearly label which team currently owns each scenario
   - Include game context (e.g., "if wins 3rd place")

3. **Pick Value Context**
   - Show tier (Early/Mid/Late) for each pick
   - Include dynasty value when available
   - Highlight traded picks

4. **Timeline Indicator**
   - Show current status (e.g., "Week 16 complete")
   - Indicate when next update occurs (e.g., "After Week 17")
   - Progress bar: 8/12 picks finalized

5. **Filtering Options**
   - "Show All Picks" vs "Show Only My Picks"
   - "Show Only Uncertain" for quick scenario view
   - Sort by pick number, team, or certainty

---

## 5. Implementation Design

### 5.1 New Script: `calculate_progressive_draft_order.py`

**Location:** [`pipeline/scripts/calculate_progressive_draft_order.py`](../pipeline/scripts/calculate_progressive_draft_order.py)

**Purpose:** Calculate draft order with certainty tracking based on available playoff results

```python
#!/usr/bin/env python3
"""
Calculate progressive draft order with certainty tracking.

Determines which picks are locked vs uncertain based on 
playoff results available through current week.

Output: pipeline/draft_order_2026_progressive.json
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class PickCertainty(Enum):
    LOCKED = "locked"
    PENDING_RESULT = "pending"
    UNKNOWN = "unknown"

@dataclass
class PickScenario:
    """Possible outcome for an uncertain pick"""
    team_id: int
    team_name: str
    condition: str  # e.g., "if wins championship"
    probability: Optional[float] = None  # Future enhancement

@dataclass
class DraftPick:
    """Draft pick with certainty tracking"""
    pick_number: int
    pick_label: str
    tier: str
    certainty: PickCertainty
    
    # If LOCKED
    original_owner: Optional[Dict] = None
    current_owner: Optional[Dict] = None
    
    # If PENDING_RESULT or UNKNOWN
    scenarios: Optional[List[PickScenario]] = None
    pending_game: Optional[str] = None  # e.g., "Week 17 Championship"

def main():
    """Main execution"""
    # 1. Load week configuration
    week_config = load_week_config()
    through_week = week_config["playoff_results"]["through_week"]
    
    # 2. Load regular season standings
    standings = load_final_regular_season_standings()
    
    # 3. Load playoff results (through available weeks)
    playoff_results = load_playoff_results_through_week(through_week)
    
    # 4. Calculate progressive draft order
    draft_order = calculate_progressive_draft_order(
        standings, 
        playoff_results, 
        through_week
    )
    
    # 5. Load pick ownership
    ownership = load_pick_ownership()
    
    # 6. Merge with ownership (for locked picks)
    draft_order = merge_with_ownership(draft_order, ownership)
    
    # 7. Validate
    validate_progressive_draft_order(draft_order, through_week)
    
    # 8. Write output
    write_progressive_draft_order(draft_order, "pipeline/draft_order_2026_progressive.json")
    
    print(f"✅ Progressive draft order calculated (through Week {through_week})")
    print(f"   Locked: {count_locked(draft_order)} picks")
    print(f"   Uncertain: {count_uncertain(draft_order)} picks")

def calculate_progressive_draft_order(
    standings: List,
    playoff_results: Dict,
    through_week: int
) -> Dict:
    """
    Calculate draft order with certainty based on available data.
    
    Args:
        standings: Regular season final standings
        playoff_results: Playoff results through available weeks
        through_week: Last week with complete results
    
    Returns:
        Dict with pick assignments and certainty
    """
    picks = []
    
    # Determine what we know based on through_week
    if through_week >= 14:
        # Middle picks (1.03-1.08) are LOCKED
        picks.extend(calculate_middle_picks(standings, PickCertainty.LOCKED))
    
    if through_week >= 16:
        # Toilet Bowl complete - Picks 1.01-1.02 are LOCKED
        toilet_bowl = playoff_results.get('toilet_bowl')
        if toilet_bowl:
            picks.extend([
                create_locked_pick(1, "1.01", toilet_bowl['winner'], "Toilet Bowl Winner"),
                create_locked_pick(2, "1.02", toilet_bowl['loser'], "Toilet Bowl Loser")
            ])
    else:
        # Toilet Bowl pending - Picks 1.01-1.02 are PENDING or UNKNOWN
        if through_week >= 15:
            # We know WHO will play but not who wins
            toilet_bowl_participants = identify_toilet_bowl_participants(playoff_results)
            picks.extend(create_pending_picks(
                [1, 2], 
                ["1.01", "1.02"],
                toilet_bowl_participants,
                "Week 16 Toilet Bowl",
                PickCertainty.PENDING_RESULT
            ))
        else:
            # Don't even know who plays yet
            picks.extend(create_unknown_picks([1, 2], ["1.01", "1.02"]))
    
    if through_week >= 17:
        # Championship and 3rd place complete - Picks 1.09-1.12 are LOCKED
        championship = playoff_results.get('championship')
        third_place = playoff_results.get('third_place')
        
        if championship and third_place:
            picks.extend([
                create_locked_pick(9, "1.09", third_place['winner'], "3rd Place Winner"),
                create_locked_pick(10, "1.10", third_place['loser'], "3rd Place Loser"),
                create_locked_pick(11, "1.11", championship['loser'], "Championship Loser"),
                create_locked_pick(12, "1.12", championship['winner'], "Championship Winner")
            ])
    else:
        # Championship and 3rd place pending
        if through_week >= 16:
            # We know WHO will play
            championship_participants = playoff_results.get('championship_participants')
            third_place_participants = playoff_results.get('third_place_participants')
            
            # Picks 1.09-1.10 (3rd place game)
            picks.extend(create_pending_picks(
                [9, 10],
                ["1.09", "1.10"],
                third_place_participants,
                "Week 17 3rd Place Game",
                PickCertainty.PENDING_RESULT
            ))
            
            # Picks 1.11-1.12 (championship)
            picks.extend(create_pending_picks(
                [11, 12],
                ["1.11", "1.12"],
                championship_participants,
                "Week 17 Championship",
                PickCertainty.PENDING_RESULT
            ))
        else:
            # Don't know who plays yet
            picks.extend(create_unknown_picks([9, 10, 11, 12], ["1.09", "1.10", "1.11", "1.12"]))
    
    return {"round_1": picks}

def create_locked_pick(
    pick_num: int, 
    pick_label: str, 
    team: Dict, 
    description: str
) -> DraftPick:
    """Create a locked pick with finalized owner"""
    return DraftPick(
        pick_number=pick_num,
        pick_label=pick_label,
        tier=get_tier_for_pick(pick_num),
        certainty=PickCertainty.LOCKED,
        original_owner={
            "roster_id": team['roster_id'],
            "team_name": team['team_name'],
            "description": description
        }
    )

def create_pending_picks(
    pick_numbers: List[int],
    pick_labels: List[str],
    participants: List[Dict],
    game_name: str,
    certainty: PickCertainty
) -> List[DraftPick]:
    """Create pending picks with scenario outcomes"""
    picks = []
    
    # Assume 2 participants for winner/loser scenarios
    team_a, team_b = participants[0], participants[1]
    
    for i, (pick_num, pick_label) in enumerate(zip(pick_numbers, pick_labels)):
        if i == 0:
            # First pick goes to winner
            scenarios = [
                PickScenario(
                    team_id=team_a['roster_id'],
                    team_name=team_a['team_name'],
                    condition=f"if {team_a['team_name']} wins {game_name}"
                ),
                PickScenario(
                    team_id=team_b['roster_id'],
                    team_name=team_b['team_name'],
                    condition=f"if {team_b['team_name']} wins {game_name}"
                )
            ]
        else:
            # Second pick goes to loser
            scenarios = [
                PickScenario(
                    team_id=team_a['roster_id'],
                    team_name=team_a['team_name'],
                    condition=f"if {team_a['team_name']} loses {game_name}"
                ),
                PickScenario(
                    team_id=team_b['roster_id'],
                    team_name=team_b['team_name'],
                    condition=f"if {team_b['team_name']} loses {game_name}"
                )
            ]
        
        picks.append(DraftPick(
            pick_number=pick_num,
            pick_label=pick_label,
            tier=get_tier_for_pick(pick_num),
            certainty=certainty,
            scenarios=scenarios,
            pending_game=game_name
        ))
    
    return picks

def create_unknown_picks(
    pick_numbers: List[int],
    pick_labels: List[str]
) -> List[DraftPick]:
    """Create unknown picks (participants not yet determined)"""
    return [
        DraftPick(
            pick_number=pick_num,
            pick_label=pick_label,
            tier=get_tier_for_pick(pick_num),
            certainty=PickCertainty.UNKNOWN,
            scenarios=None,
            pending_game="Playoffs not complete"
        )
        for pick_num, pick_label in zip(pick_numbers, pick_labels)
    ]
```

### 5.2 Dashboard API Enhancement

**File:** [`pipeline/scripts/generate_dashboard_json.py`](../pipeline/scripts/generate_dashboard_json.py)

```python
def generate_dashboard_json():
    """Generate JSON data for dashboard frontend."""
    
    data = {
        # Existing data...
        "standings": load_standings(),
        "trades": load_trades(),
    }
    
    # Add progressive draft order
    progressive_file = "pipeline/draft_order_2026_progressive.json"
    if os.path.exists(progressive_file):
        data["draft_order_progressive"] = load_json(progressive_file)
        data["draft_order_available"] = True
        
        # Add summary stats
        progressive = data["draft_order_progressive"]
        data["draft_order_stats"] = {
            "total_picks": 12,
            "locked_picks": count_locked_picks(progressive),
            "uncertain_picks": count_uncertain_picks(progressive),
            "last_updated": progressive.get("last_updated"),
            "through_week": progressive.get("through_week")
        }
    else:
        data["draft_order_available"] = False
    
    write_json("dashboard/frontend/public/api-dashboard.json", data)
```

---

## 6. Data Structures

### Progressive Draft Order JSON

**File:** [`pipeline/draft_order_2026_progressive.json`](../pipeline/draft_order_2026_progressive.json)

```json
{
  "season": 2025,
  "draft_year": 2026,
  "through_week": 16,
  "determination_level": "partial",
  "last_updated": "2024-12-29T12:00:00Z",
  
  "summary": {
    "total_picks": 12,
    "locked_picks": 8,
    "uncertain_picks": 4
  },
  
  "draft_order": {
    "round_1": [
      {
        "pick_number": 1,
        "pick_label": "1.01",
        "tier": "Early",
        "certainty": "locked",
        "original_owner": {
          "roster_id": 8,
          "team_name": "TRIPS 🔥",
          "description": "Toilet Bowl Winner",
          "regular_season_rank": 11
        },
        "current_owner": {
          "roster_id": 8,
          "team_name": "TRIPS 🔥"
        },
        "traded": false
      },
      {
        "pick_number": 9,
        "pick_label": "1.09",
        "tier": "Late",
        "certainty": "pending",
        "pending_game": "Week 17 3rd Place Game",
        "scenarios": [
          {
            "team_id": 1,
            "team_name": "208 Ferrari Way",
            "condition": "if wins 3rd place game",
            "current_owner": {
              "roster_id": 1,
              "team_name": "208 Ferrari Way"
            }
          },
          {
            "team_id": 2,
            "team_name": "Like a Good Naber",
            "condition": "if wins 3rd place game",
            "current_owner": {
              "roster_id": 5,
              "team_name": "Mommy Rainier",
              "note": "Traded from Like a Good Naber"
            }
          }
        ]
      },
      {
        "pick_number": 12,
        "pick_label": "1.12",
        "tier": "Late",
        "certainty": "pending",
        "pending_game": "Week 17 Championship",
        "scenarios": [
          {
            "team_id": 7,
            "team_name": "2-Man Title Charge",
            "condition": "if wins championship",
            "current_owner": {
              "roster_id": 7,
              "team_name": "2-Man Title Charge"
            }
          },
          {
            "team_id": 3,
            "team_name": "Bucky's Depression",
            "condition": "if wins championship",
            "current_owner": {
              "roster_id": 3,
              "team_name": "Bucky's Depression"
            }
          }
        ]
      }
    ]
  }
}
```

### Frontend TypeScript Types

```typescript
// types/draft-order.ts

export type PickCertainty = 'locked' | 'pending' | 'unknown';

export interface PickScenario {
  team_id: number;
  team_name: string;
  condition: string;
  current_owner: {
    roster_id: number;
    team_name: string;
    note?: string;
  };
  probability?: number;
}

export interface LockedPick {
  pick_number: number;
  pick_label: string;
  tier: string;
  certainty: 'locked';
  original_owner: {
    roster_id: number;
    team_name: string;
    description: string;
    regular_season_rank: number;
  };
  current_owner: {
    roster_id: number;
    team_name: string;
  };
  traded: boolean;
}

export interface UncertainPick {
  pick_number: number;
  pick_label: string;
  tier: string;
  certainty: 'pending' | 'unknown';
  pending_game?: string;
  scenarios: PickScenario[];
}

export type DraftPick = LockedPick | UncertainPick;

export interface ProgressiveDraftOrder {
  season: number;
  draft_year: number;
  through_week: number;
  determination_level: 'none' | 'partial' | 'complete';
  last_updated: string;
  summary: {
    total_picks: number;
    locked_picks: number;
    uncertain_picks: number;
  };
  draft_order: {
    round_1: DraftPick[];
  };
}
```

---

## Summary

This progressive draft order system provides:

1. **Real-Time Tracking:** Updates as each playoff week completes
2. **Clear Communication:** Visual indicators for locked vs uncertain picks
3. **Scenario Visibility:** Shows all possible outcomes for pending picks
4. **Trade Integration:** Applies pick ownership to all scenarios
5. **Dashboard Feature:** Dedicated page for draft order projection

**Key Files:**
- [`pipeline/scripts/calculate_progressive_draft_order.py`](../pipeline/scripts/calculate_progressive_draft_order.py) - Progressive calculation
- [`pipeline/draft_order_2026_progressive.json`](../pipeline/draft_order_2026_progressive.json) - Output data
- [`pipeline/config/current_week.json`](../pipeline/config/current_week.json) - Week tracking with playoff state
- [`dashboard/frontend/src/pages/DraftOrderProjection.tsx`](../dashboard/frontend/src/pages/DraftOrderProjection.tsx) - Dashboard page

**Next Steps:**
1. Implement progressive calculation script
2. Add week tracking enhancements
3. Build dashboard page UI
4. Test with current Week 16 state
5. Validate after Week 17 completion
