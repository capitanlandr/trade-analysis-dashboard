# Waiver Wire Metrics - Detailed Implementation Plan

## Overview
This document provides step-by-step implementation instructions for the 4 new Waiver Wire Analytics components. Follow this plan sequentially to build each metric incrementally with working deliverables at each phase.

---

## PHASE 1: Roster Churn Index (RCI)
**Timeline**: Week 1 | **Effort**: 1-2 hours | **Complexity**: EASY

### Backend Tasks

#### Task 1.1: Add Churn Calculations to JSON Generator (30 min)
**File**: `pipeline/scripts/generate_waiver_wire_dashboard_json.py`

**Implementation**:
```python
def calculate_churn_metrics(df, current_week, roster_size=25):
    """Calculate roster churn index for each manager."""
    churn_data = []
    
    for roster_id in df['roster_id'].unique():
        manager_txns = df[df['roster_id'] == roster_id]
        team_name = manager_txns['team_name'].iloc[0]
        
        # Count adds and drops
        adds = len(manager_txns[manager_txns['action'] == 'add'])
        drops = len(manager_txns[manager_txns['action'] == 'drop'])
        
        # Calculate overall churn
        weeks_elapsed = current_week - 1
        overall_churn = ((adds + drops) / (weeks_elapsed * roster_size)) * 100
        
        # Position-specific churn (requires position data)
        # TODO: Add position breakdown once player position data available
        
        # Categorize management style
        if overall_churn > 20:
            style = 'extreme'
        elif overall_churn > 10:
            style = 'active'
        elif overall_churn > 5:
            style = 'moderate'
        else:
            style = 'passive'
        
        churn_data.append({
            'roster_id': roster_id,
            'team_name': team_name,
            'total_adds': adds,
            'total_drops': drops,
            'overall_churn_rate': round(overall_churn, 2),
            'management_style': style
        })
    
    return churn_data
```

**Integration Point**: Add to `generate_waiver_wire_dashboard_data()` function after line 95

**Output**: Add `churn_metrics` key to dashboard_data dictionary

#### Task 1.2: Update API Response Structure (15 min)
**File**: Update `dashboard_data` structure

```python
dashboard_data = {
    'metadata': { ... },
    'all_transactions': all_transactions,
    'churn_metrics': churn_data,  # NEW
    # ... existing keys
}
```

### Frontend Tasks

#### Task 1.3: Create TypeScript Interfaces (15 min)
**File**: `dashboard/frontend/src/types/waiver-wire.ts`

```typescript
export interface ChurnMetric {
  roster_id: number;
  team_name: string;
  total_adds: number;
  total_drops: number;
  overall_churn_rate: number;
  management_style: 'extreme' | 'active' | 'moderate' | 'passive';
  position_churn?: {
    position: string;
    churn_rate: number;
    total_moves: number;
  }[];
}

export interface WaiverWireData {
  all_transactions: WaiverWireTransaction[];
  churn_metrics?: ChurnMetric[];  // Add to existing interface
}
```

#### Task 1.4: Create ChurnIndexCard Component (45 min)
**File**: `dashboard/frontend/src/components/WaiverWire/ChurnIndexCard.tsx`

**Component Structure**:
```tsx
import React from 'react';
import { RefreshCw } from 'lucide-react';
import { ChurnMetric } from '../../types/waiver-wire';

interface ChurnIndexCardProps {
  metrics: ChurnMetric[];
  currentTeamId: number;  // To highlight user's team
}

export const ChurnIndexCard: React.FC<ChurnIndexCardProps> = ({ 
  metrics, 
  currentTeamId 
}) => {
  const userMetric = metrics.find(m => m.roster_id === currentTeamId);
  
  // Style badge based on management style
  const getStyleBadge = (style: string) => {
    const styles = {
      'extreme': { bg: 'bg-red-100', text: 'text-red-800', label: 'Extreme Churn' },
      'active': { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Active' },
      'moderate': { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Moderate' },
      'passive': { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Passive' }
    };
    return styles[style] || styles.moderate;
  };
  
  const styleBadge = userMetric ? getStyleBadge(userMetric.management_style) : null;
  
  return (
    <div className="card">
      <div className="flex items-center mb-4">
        <RefreshCw className="h-5 w-5 text-orange-600 mr-2" />
        <h3 className="text-lg font-semibold">Roster Churn Index</h3>
      </div>
      
      {userMetric ? (
        <>
          <div className="text-center mb-4">
            <div className="text-4xl font-bold text-gray-900">
              {userMetric.overall_churn_rate}%
            </div>
            <div className="text-sm text-gray-600">Weekly Churn Rate</div>
          </div>
          
          {styleBadge && (
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${styleBadge.bg} ${styleBadge.text} mb-4`}>
              {styleBadge.label} Management Style
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-600">Total Adds</div>
              <div className="font-semibold">{userMetric.total_adds}</div>
            </div>
            <div>
              <div className="text-gray-600">Total Drops</div>
              <div className="font-semibold">{userMetric.total_drops}</div>
            </div>
          </div>
          
          {/* League Comparison */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-700 mb-2">League Rankings</h4>
            <div className="space-y-2">
              {metrics
                .sort((a, b) => b.overall_churn_rate - a.overall_churn_rate)
                .slice(0, 5)
                .map((m, idx) => (
                  <div 
                    key={m.roster_id}
                    className={`flex justify-between items-center text-sm ${
                      m.roster_id === currentTeamId ? 'bg-orange-50 px-2 py-1 rounded' : ''
                    }`}
                  >
                    <span className="text-gray-600">
                      {idx + 1}. {m.team_name}
                    </span>
                    <span className="font-medium">{m.overall_churn_rate}%</span>
                  </div>
                ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-8 text-gray-500">
          No churn data available
        </div>
      )}
    </div>
  );
};
```

#### Task 1.5: Integrate into WaiverWireAnalysis Page (30 min)
**File**: `dashboard/frontend/src/pages/WaiverWireAnalysis.tsx`

**Changes**:
1. Import ChurnIndexCard component
2. Add metrics section before transaction table
3. Pass churn_metrics data from API response

```tsx
// Add after line 433 (after header, before table)
{data?.churn_metrics && (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
    <ChurnIndexCard 
      metrics={data.churn_metrics} 
      currentTeamId={/* TODO: Get from user context */}
    />
    {/* Placeholder for other 3 cards */}
  </div>
)}
```

### Testing Phase 1
- [ ] Backend generates churn metrics correctly
- [ ] Frontend displays user's churn rate
- [ ] Management style categorization works
- [ ] League rankings display top 5
- [ ] Component is mobile responsive

---

## PHASE 2: Waiver Wire Efficiency Score (WWES)
**Timeline**: Week 2 | **Effort**: 4-6 hours | **Complexity**: MEDIUM

### Backend Tasks

#### Task 2.1: Create Player Stats Fetcher (2 hours)
**File**: `pipeline/scripts/fetch_player_stats.py` (NEW)

**Implementation**:
```python
#!/usr/bin/env python3
"""
Fetch weekly player stats from Sleeper API.
"""

import json
import sys
import os
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.api_client import fetch_with_retry
from utils.logging_config import setup_logging

logger = setup_logging(__name__)

def fetch_player_stats(season='2025', season_type='regular'):
    """
    Fetch all player stats for the season.
    
    Returns:
        Dict mapping player_id -> {week -> stats}
    """
    logger.info(f"Fetching player stats for {season} {season_type}...")
    
    try:
        url = f"https://api.sleeper.app/v1/stats/nfl/{season_type}/{season}"
        stats_data = fetch_with_retry(url)
        
        if not stats_data:
            logger.error("No stats data received")
            return {}
        
        # Reorganize by player and week
        player_weekly_stats = {}
        
        for week_str, week_data in stats_data.items():
            if not week_str.isdigit():
                continue
            
            week = int(week_str)
            
            for player_id, stats in week_data.items():
                if player_id not in player_weekly_stats:
                    player_weekly_stats[player_id] = {}
                
                player_weekly_stats[player_id][week] = {
                    'fantasy_points': stats.get('pts_ppr', 0),
                    'stats': stats
                }
        
        logger.info(f"Fetched stats for {len(player_weekly_stats)} players")
        
        # Save to file
        output_file = 'player_stats_weekly.json'
        with open(output_file, 'w') as f:
            json.dump(player_weekly_stats, f, indent=2)
        
        logger.info(f"Saved to {output_file}")
        return player_weekly_stats
        
    except Exception as e:
        logger.error(f"Failed to fetch player stats: {e}")
        raise

if __name__ == "__main__":
    fetch_player_stats()
```

#### Task 2.2: Calculate Efficiency Metrics (2 hours)
**File**: `pipeline/scripts/generate_waiver_wire_dashboard_json.py`

**Add Function**:
```python
def calculate_efficiency_metrics(df, player_stats):
    """Calculate WWES for each manager."""
    efficiency_data = []
    
    for roster_id in df['roster_id'].unique():
        manager_txns = df[df['roster_id'] == roster_id]
        team_name = manager_txns['team_name'].iloc[0]
        
        # Filter to successful adds only
        adds = manager_txns[
            (manager_txns['action'] == 'add') & 
            (manager_txns['status'] == 'complete')
        ]
        
        total_points = 0
        for _, add in adds.iterrows():
            player_id = str(add['player_id'])
            acq_week = add['week']
            
            # Sum points scored AFTER acquisition
            if player_id in player_stats:
                for week, stats in player_stats[player_id].items():
                    if week > acq_week:
                        total_points += stats['fantasy_points']
        
        # Calculate WWES
        faab_spent = adds[adds['type'] == 'waiver']['waiver_bid'].sum()
        fa_count = len(adds[adds['type'] == 'free_agent'])
        
        denominator = faab_spent + fa_count
        raw_wwes = total_points / denominator if denominator > 0 else 0
        
        efficiency_data.append({
            'roster_id': roster_id,
            'team_name': team_name,
            'total_points_from_adds': round(total_points, 2),
            'faab_spent': int(faab_spent),
            'free_agent_count': fa_count,
            'raw_wwes': round(raw_wwes, 2)
        })
    
    # Calculate league stats for normalization
    wwes_values = [m['raw_wwes'] for m in efficiency_data if m['raw_wwes'] > 0]
    mean_wwes = sum(wwes_values) / len(wwes_values) if wwes_values else 0
    
    # Calculate std dev
    if len(wwes_values) > 1:
        variance = sum((x - mean_wwes) ** 2 for x in wwes_values) / len(wwes_values)
        std_dev = variance ** 0.5
    else:
        std_dev = 1
    
    # Add normalized scores
    for metric in efficiency_data:
        if std_dev > 0:
            metric['normalized_wwes'] = round(
                (metric['raw_wwes'] - mean_wwes) / std_dev, 2
            )
        else:
            metric['normalized_wwes'] = 0
        
        # Calculate percentile
        metric['league_percentile'] = sum(
            1 for m in efficiency_data if m['raw_wwes'] < metric['raw_wwes']
        ) / len(efficiency_data) * 100 if efficiency_data else 50
    
    return {
        'manager_metrics': efficiency_data,
        'league_stats': {
            'mean_wwes': round(mean_wwes, 2),
            'std_dev_wwes': round(std_dev, 2),
            'median_wwes': round(sorted(wwes_values)[len(wwes_values)//2], 2) if wwes_values else 0
        }
    }
```

### Frontend Tasks

#### Task 1.6: Create ChurnIndexCard Component (1 hour)
**File**: `dashboard/frontend/src/components/WaiverWire/ChurnIndexCard.tsx`
- See implementation in design doc above
- Focus on clean, simple display
- Mobile-first responsive design

#### Task 1.7: Add to Page Layout (15 min)
**File**: `dashboard/frontend/src/pages/WaiverWireAnalysis.tsx`
- Import component
- Add metrics grid section
- Handle loading/error states

### Phase 1 Acceptance Criteria
✅ Churn rate calculates correctly for all managers
✅ Management style categorization accurate
✅ Component displays on waiver wire page
✅ Mobile responsive (stacks on small screens)
✅ Shows top 5 league rankings

---

## PHASE 2: Waiver Wire Efficiency Score (WWES)
**Timeline**: Week 2 | **Effort**: 4-6 hours | **Complexity**: MEDIUM

### Backend Tasks

#### Task 2.1: Create fetch_player_stats.py Script (2 hours)
- See implementation above (Task 2.1 from backend section)
- Add error handling for API failures
- Implement caching to avoid re-fetching
- Add to `update_dashboard.py` as Stage 5a

#### Task 2.2: Integrate Stats into Efficiency Calculation (1 hour)
- Modify `calculate_efficiency_metrics()` to load player_stats_weekly.json
- Implement points-after-acquisition logic
- Handle missing stats gracefully (player not found, future weeks, etc.)

#### Task 2.3: Update update_dashboard.py (15 min)
**File**: `update_dashboard.py`

**Add Stage 5a**:
```python
PIPELINE_STAGES = [
    # ... existing stages
    ("Stage 5: Waiver Wire Analysis", "python3 stage5_waiver_wire.py"),
    ("Stage 5a: Fetch Player Stats", "python3 scripts/fetch_player_stats.py"),  # NEW
    ("Stage 6: Analyze 2026 Pick Ownership", "python3 analyze_2026_pick_ownership.py"),
    # ... rest of stages
]
```

### Frontend Tasks

#### Task 2.4: Create EfficiencyScoreCard Component (2 hours)
**File**: `dashboard/frontend/src/components/WaiverWire/EfficiencyScoreCard.tsx`

**Features**:
- Large prominent score display
- Z-score badge (⭐ for +2.0, ✓ for +1.0, etc.)
- Breakdown of contributing factors
- League percentile indicator
- Expandable rankings table

**Component Template**:
```tsx
export const EfficiencyScoreCard: React.FC<Props> = ({ data, currentTeamId }) => {
  const userMetric = data.manager_metrics.find(m => m.roster_id === currentTeamId);
  
  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center mb-4">
        <DollarSign className="h-5 w-5 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold">Waiver Wire Efficiency</h3>
      </div>
      
      {/* Main Score Display */}
      {userMetric && (
        <>
          <div className="text-center mb-4">
            <div className="text-5xl font-bold text-blue-600">
              {getScoreBadge(userMetric.normalized_wwes)}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              {getPercentileLabel(userMetric.league_percentile)}
            </div>
          </div>
          
          {/* Breakdown */}
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-600">Your Score</div>
                <div className="font-bold text-lg">{userMetric.raw_wwes}</div>
                <div className="text-xs text-gray-500">pts/dollar</div>
              </div>
              <div>
                <div className="text-gray-600">League Avg</div>
                <div className="font-bold text-lg">{data.league_stats.mean_wwes}</div>
                <div className="text-xs text-gray-500">pts/dollar</div>
              </div>
            </div>
          </div>
          
          {/* Contributing Factors */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Points from Adds:</span>
              <span className="font-medium">{userMetric.total_points_from_adds} pts</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">FAAB Spent:</span>
              <span className="font-medium">${userMetric.faab_spent}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Free Agent Adds:</span>
              <span className="font-medium">{userMetric.free_agent_count}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
```

#### Task 2.5: Add Helper Functions (30 min)
**File**: `dashboard/frontend/src/utils/waiverMetrics.ts` (NEW)

```typescript
export const getScoreBadge = (zScore: number): string => {
  if (zScore >= 2.0) return '⭐ +' + zScore.toFixed(1) + 'σ';
  if (zScore >= 1.0) return '✓ +' + zScore.toFixed(1) + 'σ';
  if (zScore >= 0) return '+' + zScore.toFixed(1) + 'σ';
  if (zScore >= -1.0) return zScore.toFixed(1) + 'σ';
  return '✗ ' + zScore.toFixed(1) + 'σ';
};

export const getPercentileLabel = (percentile: number): string => {
  if (percentile >= 95) return 'Elite (Top 5%)';
  if (percentile >= 75) return 'Above Average (Top 25%)';
  if (percentile >= 50) return 'Above Average';
  if (percentile >= 25) return 'Below Average';
  return 'Needs Improvement';
};
```

### Phase 2 Acceptance Criteria
✅ Player stats fetch from Sleeper API successfully
✅ Points-after-acquisition calculation accurate
✅ Z-score normalization correct
✅ Efficiency card displays with proper styling
✅ League rankings sortable and interactive

---

## PHASE 3: Waiver Hit Rate (WHR)
**Timeline**: Week 3-4 | **Effort**: 8-10 hours | **Complexity**: HARD

### Backend Tasks

#### Task 3.1: Create Lineup Data Fetcher (3 hours)
**File**: `pipeline/scripts/fetch_lineup_data.py` (NEW)

**Purpose**: Fetch weekly starting lineups to track player usage

```python
def fetch_weekly_lineups(league_id, current_week):
    """
    Fetch lineup data for all weeks to determine player usage.
    
    Returns:
        Dict: {roster_id: {week: {starters: [player_ids]}}}
    """
    lineup_data = {}
    
    for week in range(1, current_week + 1):
        try:
            url = f"https://api.sleeper.app/v1/league/{league_id}/matchups/{week}"
            matchups = fetch_with_retry(url)
            
            for matchup in matchups:
                roster_id = matchup['roster_id']
                starters = matchup.get('starters', [])
                
                if roster_id not in lineup_data:
                    lineup_data[roster_id] = {}
                
                lineup_data[roster_id][week] = {
                    'starters': starters,
                    'points': matchup.get('points', 0)
                }
        
        except Exception as e:
            logger.warning(f"Failed to fetch week {week} lineups: {e}")
    
    return lineup_data
```

#### Task 3.2: Implement Hit Classification (3 hours)
**File**: `pipeline/scripts/calculate_waiver_metrics.py` (NEW)

**Logic**:
```python
def classify_add_as_hit(player_id, acq_week, lineup_data, player_stats, roster_id):
    """
    Classify waiver add as Tier 1, 2, 3 hit or miss.
    
    Criteria:
    - Tier 1: Started ≥50% of weeks post-acquisition
    - Tier 2: Started 25-49% of weeks post-acquisition  
    - Tier 3: Scored ≥10 pts in any single week
    - Miss: None of above
    """
    weeks_after_acq = []
    weeks_started = 0
    max_single_week_score = 0
    
    for week, lineup in lineup_data.get(roster_id, {}).items():
        if week > acq_week:
            weeks_after_acq.append(week)
            
            if player_id in lineup.get('starters', []):
                weeks_started += 1
            
            # Check scoring
            if player_id in player_stats:
                week_score = player_stats[player_id].get(week, {}).get('fantasy_points', 0)
                max_single_week_score = max(max_single_week_score, week_score)
    
    # Calculate usage rate
    usage_rate = (weeks_started / len(weeks_after_acq)) if weeks_after_acq else 0
    
    # Classify
    if usage_rate >= 0.5:
        return 1, weeks_started, len(weeks_after_acq)
    elif usage_rate >= 0.25:
        return 2, weeks_started, len(weeks_after_acq)
    elif max_single_week_score >= 10:
        return 3, weeks_started, len(weeks_after_acq)
    else:
        return None, weeks_started, len(weeks_after_acq)
```

#### Task 3.3: Generate Hit Rate Data (2 hours)
**File**: Integrate into `generate_waiver_wire_dashboard_json.py`

```python
def calculate_hit_rate_metrics(df, lineup_data, player_stats):
    """Calculate WHR for each manager."""
    hit_rate_data = []
    
    for roster_id in df['roster_id'].unique():
        manager_adds = df[
            (df['roster_id'] == roster_id) & 
            (df['action'] == 'add') &
            (df['status'] == 'complete')
        ]
        
        tier1_hits = []
        tier2_hits = []
        tier3_hits = []
        misses = []
        
        for _, add in manager_adds.iterrows():
            tier, weeks_started, weeks_avail = classify_add_as_hit(
                add['player_id'],
                add['week'],
                lineup_data,
                player_stats,
                roster_id
            )
            
            hit_detail = {
                'player_name': add['player_name'],
                'player_id': add['player_id'],
                'acquisition_week': add['week'],
                'weeks_started': weeks_started,
                'weeks_available': weeks_avail,
                'tier': tier
            }
            
            if tier == 1:
                tier1_hits.append(hit_detail)
            elif tier == 2:
                tier2_hits.append(hit_detail)
            elif tier == 3:
                tier3_hits.append(hit_detail)
            else:
                misses.append(hit_detail)
        
        total_adds = len(manager_adds)
        total_hits = len(tier1_hits) + len(tier2_hits) + len(tier3_hits)
        
        hit_rate_data.append({
            'roster_id': roster_id,
            'team_name': manager_adds['team_name'].iloc[0],
            'total_adds': total_adds,
            'tier1_hits': len(tier1_hits),
            'tier2_hits': len(tier2_hits),
            'tier3_hits': len(tier3_hits),
            'misses': len(misses),
            'overall_hit_rate': round((total_hits / total_adds * 100), 1) if total_adds > 0 else 0,
            'notable_hits': tier1_hits[:3]  # Top 3 Tier 1 hits
        })
    
    return hit_rate_data
```

### Frontend Tasks

#### Task 3.4: Create HitRateCard Component (2 hours)
**File**: `dashboard/frontend/src/components/WaiverWire/HitRateCard.tsx`

**Features**:
- Hit rate percentage (large display)
- Visual tier breakdown (stacked progress bar)
- Tier-specific counts and percentages
- Notable hits list
- League comparison

**Key Visual Elements**:
```tsx
// Tier Progress Bar Component
const TierProgressBar: React.FC<{tiers}> = ({ tiers }) => (
  <div className="w-full h-6 flex rounded-lg overflow-hidden">
    <div className="bg-green-500" style={{width: `${tiers.tier1}%`}} title="Tier 1" />
    <div className="bg-yellow-500" style={{width: `${tiers.tier2}%`}} title="Tier 2" />
    <div className="bg-orange-500" style={{width: `${tiers.tier3}%`}} title="Tier 3" />
    <div className="bg-gray-300" style={{width: `${tiers.misses}%`}} title="Misses" />
  </div>
);
```

### Phase 3 Acceptance Criteria
✅ Lineup data fetched for all weeks
✅ Tier classification logic accurate
✅ Hit rate percentages correct
✅ Notable hits display properly
✅ Tier progress bar renders correctly

---

## PHASE 4: Waiver Timing Score (WTS)
**Timeline**: Week 5 | **Effort**: 3-4 hours | **Complexity**: MEDIUM

### Backend Tasks

#### Task 4.1: Add Day-of-Week Parsing (1 hour)
**File**: `pipeline/scripts/calculate_waiver_metrics.py`

```python
from datetime import datetime

def parse_day_of_week(timestamp_str):
    """
    Parse transaction timestamp and return day classification.
    
    Returns:
        'early' for Tue-Thu, 'late' for Fri-Mon
    """
    dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    day = dt.weekday()  # 0=Mon, 1=Tue, ..., 6=Sun
    
    # Tue(1), Wed(2), Thu(3) = early
    # Fri(4), Sat(5), Sun(6), Mon(0) = late
    if day in [1, 2, 3]:
        return 'early'
    else:
        return 'late'
```

#### Task 4.2: Calculate Timing Score (2 hours)
**File**: Add function to `calculate_waiver_metrics.py`

```python
def calculate_timing_metrics(df, hit_rate_data, player_stats):
    """Calculate WTS for each manager."""
    timing_data = []
    
    for manager in hit_rate_data:
        roster_id = manager['roster_id']
        
        # Get all Tier 1/2 hits for this manager
        tier12_hits = [
            h for h in manager.get('hit_details', [])
            if h['tier'] in [1, 2]
        ]
        
        early_hits = []
        late_hits = []
        
        for hit in tier12_hits:
            # Get transaction for this player
            txn = df[
                (df['roster_id'] == roster_id) &
                (df['player_id'] == hit['player_id']) &
                (df['action'] == 'add')
            ].iloc[0]
            
            timing = parse_day_of_week(txn['created_date'])
            
            # Calculate points scored post-acquisition
            points = calculate_points_after_week(
                hit['player_id'],
                hit['acquisition_week'],
                player_stats
            )
            
            hit_data = {
                'player_name': hit['player_name'],
                'points': points,
                'tier': hit['tier']
            }
            
            if timing == 'early':
                early_hits.append(hit_data)
            else:
                late_hits.append(hit_data)
        
        # Calculate averages
        early_avg = (sum(h['points'] for h in early_hits) / len(early_hits)) if early_hits else 0
        late_avg = (sum(h['points'] for h in late_hits) / len(late_hits)) if late_hits else 0
        
        timing_score = early_avg - late_avg
        
        # Classify strategy
        if timing_score > 5:
            strategy = 'proactive'
        elif timing_score < -5:
            strategy = 'reactive'
        else:
            strategy = 'balanced'
        
        timing_data.append({
            'roster_id': roster_id,
            'team_name': manager['team_name'],
            'early_week_hits': len(early_hits),
            'late_week_hits': len(late_hits),
            'early_avg_points': round(early_avg, 1),
            'late_avg_points': round(late_avg, 1),
            'timing_score': round(timing_score, 1),
            'strategy_type': strategy,
            'notable_early_hits': sorted(early_hits, key=lambda x: x['points'], reverse=True)[:2],
            'notable_late_hits': sorted(late_hits, key=lambda x: x['points'], reverse=True)[:2]
        })
    
    return timing_data
```

### Frontend Tasks

#### Task 4.3: Create TimingScoreCard Component (1-2 hours)
**File**: `dashboard/frontend/src/components/WaiverWire/TimingScoreCard.tsx`

**Features**:
- Timing differential score (large display)
- Strategy badge (Proactive/Balanced/Reactive)
- Side-by-side early vs late comparison
- Notable hits from each timing window

### Phase 4 Acceptance Criteria
✅ Day-of-week parsing accurate
✅ Timing differential calculated correctly
✅ Strategy categorization logical
✅ Component displays comparison clearly
✅ Notable hits list helpful

---

## Integration & Polish

### Final Integration Tasks

#### Task 5.1: Create Container Component (1 hour)
**File**: `dashboard/frontend/src/components/WaiverWire/MetricsDashboard.tsx`

```tsx
export const MetricsDashboard: React.FC<{data}> = ({ data }) => {
  return (
    <div className="space-y-6 mb-8">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          Waiver Wire Performance Metrics
        </h2>
        <button className="text-sm text-gray-600 hover:text-gray-900">
          What do these mean?
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {data.efficiency && <EfficiencyScoreCard data={data.efficiency} />}
        {data.hit_rate && <HitRateCard data={data.hit_rate} />}
        {data.churn && <ChurnIndexCard metrics={data.churn.manager_metrics} />}
        {data.timing && <TimingScoreCard data={data.timing} />}
      </div>
    </div>
  );
};
```

#### Task 5.2: Add Loading States (30 min)
- Skeleton loaders for each card
- Error boundaries for each component
- Graceful degradation if metrics unavailable

#### Task 5.3: Add Help/Info Modal (1 hour)
**File**: `dashboard/frontend/src/components/WaiverWire/MetricsHelpModal.tsx`

**Content**:
- Explain each metric in plain language
- Show example calculations
- Link to full documentation
- Interpretation guide

### Polish Tasks

#### Task 5.4: Mobile Optimization
- Test all cards on 320px, 375px, 414px screens
- Ensure readable text sizes
- Stack cards vertically on mobile
- Optimize spacing and padding

#### Task 5.5: Accessibility
- Add ARIA labels to progress bars
- Ensure keyboard navigation works
- Test with screen reader
- Verify color contrast ratios

#### Task 5.6: Performance
- Lazy load components
- Memoize expensive calculations
- Implement virtual scrolling for rankings tables
- Add loading indicators

---

## Deployment Checklist

### Pre-Deployment
- [ ] All unit tests pass
- [ ] Visual regression tests pass
- [ ] Mobile testing complete
- [ ] Accessibility audit complete
- [ ] Performance benchmarks met (<3s load time)

### Deployment Steps
1. Merge all backend changes to main
2. Run full pipeline to generate metrics data
3. Deploy frontend components
4. Monitor Vercel deployment
5. Test production environment
6. Announce new features to league

### Post-Deployment
- [ ] Monitor error logs for 48 hours
- [ ] Gather user feedback
- [ ] Track engagement metrics
- [ ] Plan V2 enhancements based on usage

---

## Success Metrics

### User Engagement
- **Target**: 80% of managers view metrics within first week
- **Measure**: Page view analytics

### Accuracy
- **Target**: <5% calculation errors
- **Measure**: Spot-check 10 random managers

### Performance
- **Target**: Page load < 3 seconds
- **Measure**: Lighthouse score

### Satisfaction
- **Target**: Positive feedback from ≥75% of users
- **Measure**: Informal league polls

---

## Maintenance Plan

### Weekly Tasks
- Run pipeline to update metrics with new transaction data
- Monitor for API changes
- Check calculation accuracy

### Monthly Tasks
- Review metric thresholds (adjust if league meta changes)
- Gather feature requests
- Plan V2 enhancements

### Season Tasks
- Archive season data for historical comparison
- Reset metrics for new season
- Retrospective analysis and improvements

---

**Plan Version**: 1.0
**Created**: 2025-12-13
**Status**: Ready for Development