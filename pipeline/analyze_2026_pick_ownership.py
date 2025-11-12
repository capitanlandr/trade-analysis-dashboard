#!/usr/bin/env python3
"""
Analyze 2026 draft pick ownership across all teams.

Provides metrics on:
- Total picks owned by each team
- Picks by round
- Net picks gained/lost through trades
- Pick value estimates using weekly projections
"""

import pandas as pd
import requests
from collections import defaultdict
import json

# League configuration
LEAGUE_ID = "1180814327660371968"

# Roster ID to username mapping (from Sleeper API)
ROSTER_TO_USER = {
    1: "lndahayo",
    2: "gnewman4", 
    3: "brevinowens",
    4: "cjsyregelas",
    5: "zachlearningtogolf",
    6: "thekylecasey",
    7: "jwalters74",
    8: "tylerpilgrim",
    9: "mgaeta23",
    10: "jakeduf",
    11: "wkerwin",
    12: "donewton"
}

def fetch_2026_picks_from_transactions():
    """
    Fetch 2026 pick ownership from asset_transactions.csv (source of truth).
    Sleeper API is unreliable for pick trades.
    """
    try:
        df = pd.read_csv('asset_transactions.csv')
    except FileNotFoundError:
        print("Error: asset_transactions.csv not found")
        return []
    
    # Filter for 2026 picks
    picks_2026 = df[df['asset_name'].str.contains('2026 Round', na=False)].copy()
    
    # Extract round number
    picks_2026['round'] = picks_2026['asset_name'].str.extract(r'2026 Round (\d+)')[0].astype(int)
    
    # Build list of trades
    trades = []
    for _, row in picks_2026.iterrows():
        trades.append({
            'origin_owner': row['origin_owner'],
            'round': row['round'],
            'current_owner': row['receiving_team'],
            'trade_date': row['trade_date']
        })
    
    return trades

def load_pick_values():
    """Load pick value projections from CSV."""
    try:
        df = pd.read_csv('weekly_2026_pick_projections_expanded.csv')
        return df
    except FileNotFoundError:
        print("Warning: weekly_2026_pick_projections_expanded.csv not found")
        return None

def calculate_ownership(traded_picks):
    """
    Calculate current ownership of all 2026 picks based on transaction log.
    Returns dict: {(origin_username, round): current_owner_username}
    """
    # Initialize: each team owns their own picks
    ownership = {}
    for username in ROSTER_TO_USER.values():
        for round_num in range(1, 5):
            ownership[(username, round_num)] = username
    
    # Apply trades in chronological order
    sorted_trades = sorted(traded_picks, key=lambda x: x['trade_date'])
    
    for trade in sorted_trades:
        origin = trade['origin_owner']
        round_num = trade['round']
        new_owner = trade['current_owner']
        
        key = (origin, round_num)
        ownership[key] = new_owner
    
    return ownership

def build_metrics(ownership, pick_values_df):
    """Build comprehensive metrics for each team."""
    metrics = []
    
    for owner_username in ROSTER_TO_USER.values():
        # Count picks owned by this team
        picks_owned = defaultdict(list)  # round -> list of origin usernames
        
        for (origin_username, round_num), current_owner in ownership.items():
            if current_owner == owner_username:
                picks_owned[round_num].append(origin_username)
        
        # Calculate totals
        total_picks = sum(len(picks) for picks in picks_owned.values())
        round_counts = {f"Round_{r}": len(picks_owned[r]) for r in range(1, 5)}
        
        # Calculate net picks (owned - original)
        net_picks = total_picks - 4  # Each team starts with 4 picks
        
        # Calculate estimated value if we have projections
        estimated_value = 0
        if pick_values_df is not None:
            # Use Week 9 values (most recent)
            for round_num, origin_usernames in picks_owned.items():
                for origin_username_pick in origin_usernames:
                    col_name = f"Week9_2026_{_round_suffix(round_num)}"
                    
                    if col_name in pick_values_df.columns:
                        team_row = pick_values_df[pick_values_df['Team'] == origin_username_pick]
                        if not team_row.empty:
                            estimated_value += team_row[col_name].values[0]
        
        # Build pick details
        pick_details = []
        for round_num in range(1, 5):
            for origin_username_pick in picks_owned[round_num]:
                pick_details.append({
                    'round': round_num,
                    'origin_team': origin_username_pick,
                    'is_own_pick': origin_username_pick == owner_username
                })
        
        metrics.append({
            'Team': owner_username,
            'Total_Picks': total_picks,
            **round_counts,
            'Net_Picks': net_picks,
            'Estimated_Value': round(estimated_value) if estimated_value > 0 else None,
            'Pick_Details': pick_details
        })
    
    return metrics

def _round_suffix(round_num):
    """Convert round number to suffix (1st, 2nd, 3rd, 4th)."""
    suffixes = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th'}
    return suffixes.get(round_num, f'{round_num}th')

def print_summary(metrics):
    """Print formatted summary of metrics."""
    print("\n" + "="*80)
    print("2026 DRAFT PICK OWNERSHIP ANALYSIS")
    print("="*80 + "\n")
    
    # Sort by total picks descending
    sorted_metrics = sorted(metrics, key=lambda x: x['Total_Picks'], reverse=True)
    
    # Summary table
    print("SUMMARY BY TEAM")
    print("-" * 80)
    print(f"{'Team':<25} {'Total':>6} {'1st':>5} {'2nd':>5} {'3rd':>5} {'4th':>5} {'Net':>5} {'Est Value':>10}")
    print("-" * 80)
    
    for m in sorted_metrics:
        value_str = f"{m['Estimated_Value']:,}" if m['Estimated_Value'] else "N/A"
        print(f"{m['Team']:<25} {m['Total_Picks']:>6} "
              f"{m['Round_1']:>5} {m['Round_2']:>5} {m['Round_3']:>5} {m['Round_4']:>5} "
              f"{m['Net_Picks']:>+5} {value_str:>10}")
    
    print("-" * 80)
    
    # League totals
    total_picks = sum(m['Total_Picks'] for m in metrics)
    print(f"{'LEAGUE TOTAL':<25} {total_picks:>6}")
    print()
    
    # Detailed breakdown
    print("\nDETAILED PICK OWNERSHIP")
    print("="*80 + "\n")
    
    for m in sorted_metrics:
        print(f"{m['Team']} ({m['Total_Picks']} picks, Net: {m['Net_Picks']:+d})")
        print("-" * 40)
        
        # Group by round
        for round_num in range(1, 5):
            round_picks = [p for p in m['Pick_Details'] if p['round'] == round_num]
            if round_picks:
                origins = [p['origin_team'] for p in round_picks]
                own_picks = sum(1 for p in round_picks if p['is_own_pick'])
                traded_picks = len(round_picks) - own_picks
                
                print(f"  Round {round_num}: {len(round_picks)} pick(s)")
                print(f"    Origins: {', '.join(origins)}")
                if traded_picks > 0:
                    print(f"    ({own_picks} own, {traded_picks} acquired)")
        print()

def save_to_csv(metrics):
    """Save metrics to CSV file."""
    # Flatten for CSV
    rows = []
    for m in metrics:
        row = {
            'Team': m['Team'],
            'Total_Picks': m['Total_Picks'],
            'Round_1': m['Round_1'],
            'Round_2': m['Round_2'],
            'Round_3': m['Round_3'],
            'Round_4': m['Round_4'],
            'Net_Picks': m['Net_Picks'],
            'Estimated_Value': m['Estimated_Value']
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Total_Picks', ascending=False)
    
    output_file = '2026_pick_ownership_metrics.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Metrics saved to {output_file}")
    
    # Also save detailed JSON
    json_file = '2026_pick_ownership_detailed.json'
    with open(json_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"✓ Detailed data saved to {json_file}")

def save_to_markdown(metrics):
    """Save metrics to a formatted markdown file."""
    sorted_metrics = sorted(metrics, key=lambda x: x['Total_Picks'], reverse=True)
    
    md_lines = [
        "# 2026 Draft Pick Ownership Analysis",
        "",
        f"*Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "## Summary Table",
        "",
        "| Team | Total Picks | 1st | 2nd | 3rd | 4th | Net | Est. Value |",
        "|------|-------------|-----|-----|-----|-----|-----|------------|"
    ]
    
    for m in sorted_metrics:
        value_str = f"{m['Estimated_Value']:,}" if m['Estimated_Value'] else "N/A"
        net_str = f"+{m['Net_Picks']}" if m['Net_Picks'] > 0 else str(m['Net_Picks'])
        md_lines.append(
            f"| {m['Team']} | {m['Total_Picks']} | {m['Round_1']} | {m['Round_2']} | "
            f"{m['Round_3']} | {m['Round_4']} | {net_str} | {value_str} |"
        )
    
    # Add key insights
    md_lines.extend([
        "",
        "## Key Insights",
        ""
    ])
    
    # Most picks
    most_picks = sorted_metrics[0]
    md_lines.append(f"### Most Picks Owned")
    md_lines.append("")
    for i, m in enumerate(sorted_metrics[:3], 1):
        net_str = f"+{m['Net_Picks']}" if m['Net_Picks'] > 0 else str(m['Net_Picks'])
        md_lines.append(f"{i}. **{m['Team']}** - {m['Total_Picks']} picks ({net_str} net)")
    md_lines.append("")
    
    # Most valuable
    by_value = sorted([m for m in metrics if m['Estimated_Value']], 
                     key=lambda x: x['Estimated_Value'], reverse=True)
    md_lines.append(f"### Most Valuable Pick Portfolios")
    md_lines.append("")
    for i, m in enumerate(by_value[:3], 1):
        md_lines.append(f"{i}. **{m['Team']}** - {m['Estimated_Value']:,} value "
                       f"({m['Round_1']} first-rounders)")
    md_lines.append("")
    
    # Most first rounders
    by_firsts = sorted(metrics, key=lambda x: x['Round_1'], reverse=True)
    md_lines.append(f"### Most First-Round Picks")
    md_lines.append("")
    for i, m in enumerate(by_firsts[:3], 1):
        if m['Round_1'] > 0:
            md_lines.append(f"{i}. **{m['Team']}** - {m['Round_1']} first-round picks")
    md_lines.append("")
    
    # Detailed breakdown
    md_lines.extend([
        "## Detailed Pick Ownership",
        ""
    ])
    
    for m in sorted_metrics:
        net_str = f"+{m['Net_Picks']}" if m['Net_Picks'] > 0 else str(m['Net_Picks'])
        md_lines.append(f"### {m['Team']}")
        md_lines.append(f"**{m['Total_Picks']} total picks ({net_str} net)**")
        md_lines.append("")
        
        # Group by round
        for round_num in range(1, 5):
            round_picks = [p for p in m['Pick_Details'] if p['round'] == round_num]
            if round_picks:
                origins = [p['origin_team'] for p in round_picks]
                own_picks = sum(1 for p in round_picks if p['is_own_pick'])
                traded_picks = len(round_picks) - own_picks
                
                md_lines.append(f"**Round {round_num}:** {len(round_picks)} pick(s)")
                md_lines.append(f"- Origins: {', '.join(origins)}")
                if traded_picks > 0:
                    md_lines.append(f"- *({own_picks} own, {traded_picks} acquired)*")
                md_lines.append("")
        
        md_lines.append("")
    
    # League totals
    total_picks = sum(m['Total_Picks'] for m in metrics)
    total_value = sum(m['Estimated_Value'] for m in metrics if m['Estimated_Value'])
    
    md_lines.extend([
        "## League Totals",
        "",
        f"- **Total Picks:** {total_picks} (should be 48)",
        f"- **Total Estimated Value:** {total_value:,}",
        ""
    ])
    
    # Write to file
    output_file = '2026_pick_ownership_analysis.md'
    with open(output_file, 'w') as f:
        f.write('\n'.join(md_lines))
    
    print(f"✓ Markdown analysis saved to {output_file}")

def main():
    print("Loading 2026 draft picks from transaction log...")
    traded_picks = fetch_2026_picks_from_transactions()
    print(f"✓ Found {len(traded_picks)} pick trades")
    
    print("\nCalculating ownership...")
    ownership = calculate_ownership(traded_picks)
    
    print("Loading pick value projections...")
    pick_values_df = load_pick_values()
    
    print("Building metrics...")
    metrics = build_metrics(ownership, pick_values_df)
    
    print_summary(metrics)
    save_to_csv(metrics)
    save_to_markdown(metrics)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()
