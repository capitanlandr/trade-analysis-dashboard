#!/usr/bin/env python3
"""
Static Pick Origin Mapping for 2025 Draft
Since Sleeper API conflates roster_id (origin) vs owner_id (current owner),
we maintain a static mapping based on LINEAR draft order.

In a 12-team LINEAR draft (same order every round):
- Pick order 1-12 = Round 1 (roster 1→12)
- Pick order 13-24 = Round 2 (roster 1→12) SAME ORDER
- Pick order 25-36 = Round 3 (roster 1→12) SAME ORDER
- Pick order 37-48 = Round 4 (roster 1→12) SAME ORDER
"""

# Roster ID to owner name mapping
ROSTER_TO_OWNER = {
    1: 'lndahayo',
    2: 'brevinowens',
    3: 'cjsyregelas',
    4: 'gnewman4',
    5: 'zachlearningtogolf',
    6: 'thekylecasey',
    7: 'jwalters74',
    8: 'tylerpilgrim',
    9: 'mgaeta23',
    10: 'jakeduf',
    11: 'wkerwin',
    12: 'donewton'
}

OWNER_TO_ROSTER = {v: k for k, v in ROSTER_TO_OWNER.items()}

# EXPLICIT origin mapping from user-provided truth data
# Custom draft order (NOT based on roster IDs)
# Name mapping: tyler=tylerpilgrim, will=wkerwin, zach=zachlearningtogolf,
#               brevin=brevinowens, johnny=jwalters74, don=donewton,
#               landry=lndahayo, kyle=thekylecasey, gaeta=mgaeta23,
#               chris=cjsyregelas, jake=jakeduf, grant=gnewman4
EXPLICIT_ORIGINS = {
    # Round 1 (format: "origin (drafter)")
    (1, 1): 'tylerpilgrim',      # tyler (tyler)
    (1, 2): 'wkerwin',            # will (don)
    (1, 3): 'zachlearningtogolf', # zach (will)
    (1, 4): 'brevinowens',        # brevin (brevin)
    (1, 5): 'jwalters74',         # johnny (zach) ← jwalters74 origin
    (1, 6): 'donewton',           # don (zach)
    (1, 7): 'lndahayo',           # landry (johnny) ← lndahayo origin
    (1, 8): 'thekylecasey',       # kyle (will)
    (1, 9): 'mgaeta23',           # gaeta (brevin)
    (1, 10): 'cjsyregelas',       # chris (kyle)
    (1, 11): 'jakeduf',           # jake (will)
    (1, 12): 'gnewman4',          # grant (don)
}

# For rounds 2-4, replicate Round 1 order (linear draft)
for round_num in [2, 3, 4]:
    for pick in range(1, 13):
        EXPLICIT_ORIGINS[(round_num, pick)] = EXPLICIT_ORIGINS[(1, pick)]

def get_pick_origin_owner(round_num, pick_in_round):
    """
    Get the origin owner for a pick using explicit mapping
    
    Args:
        round_num: 1, 2, 3, or 4
        pick_in_round: 1-12
    
    Returns:
        owner name (string)
    """
    key = (round_num, pick_in_round)
    return EXPLICIT_ORIGINS.get(key, f'UNKNOWN_R{round_num}P{pick_in_round}')

def get_pick_origin_roster(round_num, pick_in_round):
    """Get the origin roster ID"""
    owner = get_pick_origin_owner(round_num, pick_in_round)
    return OWNER_TO_ROSTER.get(owner, 0)

# Pre-computed lookup for all 2025 picks
PICK_ORIGIN_MAP = {}

for round_num in [1, 2, 3, 4]:
    for pick_in_round in range(1, 13):
        key = (2025, round_num, pick_in_round)
        owner = get_pick_origin_owner(round_num, pick_in_round)
        roster = get_pick_origin_roster(round_num, pick_in_round)
        
        PICK_ORIGIN_MAP[key] = {
            'origin_owner': owner,
            'origin_roster': roster
        }

# Also create lookup by string notation
PICK_ORIGIN_BY_NOTATION = {}

for round_num in [1, 2, 3, 4]:
    for pick_in_round in range(1, 13):
        notation = f"2025 Round {round_num}"
        owner = get_pick_origin_owner(round_num, pick_in_round)
        
        if notation not in PICK_ORIGIN_BY_NOTATION:
            PICK_ORIGIN_BY_NOTATION[notation] = []
        
        PICK_ORIGIN_BY_NOTATION[notation].append(owner)

if __name__ == "__main__":
    print("="*80)
    print("2025 PICK ORIGIN MAPPING")
    print("="*80)
    
    print("\nRound 1 Origins:")
    for i in range(1, 13):
        owner = get_pick_origin_owner(1, i)
        print(f"  1.{i:02d}: {owner}")
    
    print("\nRound 2 Origins:")
    for i in range(1, 13):
        owner = get_pick_origin_owner(2, i)
        print(f"  2.{i:02d}: {owner}")
    
    print("\nRound 3 Origins:")
    for i in range(1, 13):
        owner = get_pick_origin_owner(3, i)
        print(f"  3.{i:02d}: {owner}")
    
    print("\nRound 4 Origins:")
    for i in range(1, 13):
        owner = get_pick_origin_owner(4, i)
        print(f"  4.{i:02d}: {owner}")