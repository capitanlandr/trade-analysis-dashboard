# Waiver Wire Analytics - Component Design & Implementation Plan

## Executive Summary

This document outlines the design and implementation plan for 4 new UI components on the Waiver Wire Analysis page, implementing the metrics defined in `WAIVER_WIRE_METRICS.md`. These components will transform raw transaction data into actionable insights about manager performance and strategy.

**Target Metrics:**
1. **Waiver Wire Efficiency Score (WWES)** - Points per dollar spent
2. **Waiver Hit Rate (WHR)** - Decision quality with 3-tier classification  
3. **Roster Churn Index (RCI)** - Activity level and management style
4. **Waiver Timing Score (WTS)** - Proactive vs reactive strategy

**Estimated Total Effort:** 16-22 hours across 4 phases

---

## Component Architecture Overview

### Current State Analysis

**Existing Components:**
- `WaiverWireAnalysis.tsx` - Main page with transaction table
- `api-waiver-wire.json` - Data source with 482 transactions (291 waiver + 191 FA)

**Current Data Structure:**
```typescript
interface WaiverWireTransaction {
  transaction_id: string;
  type: 'waiver' | 'free_agent';
  action: 'add' | 'drop';
  status: 'complete' | 'failed';
  team_name: string;
  roster_id: number;
  player_name: string;
  player_id: string;
  waiver_bid: number;
  week: number;
  created_date: string;
  status_updated_date: string;
  notes: string;
  sequence: number | null;
  priority: number | null;
}
```

### Proposed Component Structure

```
WaiverWireAnalysis (page)
├── [Existing] All Transactions Table
└── [NEW] Waiver Wire Metrics Section
    ├── Component 1: EfficiencyScoreCard
    ├── Component 2: HitRateCard  
    ├── Component 3: ChurnIndexCard
    └── Component 4: TimingScoreCard
```

---

## Component 1: Efficiency Score Card (WWES)

### Visual Design

```
┌─────────────────────────────────────────────────────┐
│ 💰 Waiver Wire Efficiency Score                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│         ⭐ +1.8σ                                    │
│         Top 5% of League                            │
│                                                     │
│  Your Score: 3.27 pts/dollar                       │
│  League Avg: 1.80 pts/dollar                       │
│                                                     │
│  ┌─────────────────────────────────────┐          │
│  │ Points Gained:     144 pts          │          │
│  │ FAAB Spent:        $43              │          │
│  │ Free Agent Adds:   1                │          │
│  └─────────────────────────────────────┘          │
│                                                     │
│  📊 League Rankings                                │
│  1. Team A    3.45  (+2.1σ) █████████████         │
│  2. You       3.27  (+1.8σ) ████████████          │
│  3. Team C    2.92  (+1.4σ) ██████████            │
│  ...                                               │
└─────────────────────────────────────────────────────┘
```

### Data Requirements

**Frontend Calculations Needed:**
- Sum fantasy points scored by acquired players post-acquisition
- Sum total FAAB spent on waiver claims
- Count free agent pickups
- Calculate league mean and standard deviation
- Generate z-score normalization
- Rank all managers

**New Backend Data:**
```typescript
interface EfficiencyData {
  manager_metrics: {
    roster_id: number;
    team_name: string;
    total_points_from_adds: number;
    faab_spent: number;
    free_agent_count: number;
    raw_wwes: number;
    normalized_wwes: number;
    league_percentile: number;
  }[];
  league_stats: {
    mean_wwes: number;
    std_dev_wwes: number;
    median_wwes: number;
  };
}
```

**Implementation Phases:**
1. **Phase 1**: Display card with placeholder data
2. **Phase 2**: Add player stats scraping for points calculation
3. **Phase 3**: Add normalization and league comparison
4. **Phase 4**: Add interactive league rankings table

---

## Component 2: Hit Rate Card (WHR)

### Visual Design

```
┌─────────────────────────────────────────────────────┐
│ 🎯 Waiver Hit Rate                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│         45.2% Success Rate                          │
│         Above Average (58th Percentile)             │
│                                                     │
│  ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░ 9 / 20 Adds                │
│                                                     │
│  Hit Breakdown:                                    │
│  ┌──────────────────────────────────┐             │
│  │ 🟢 Tier 1: Weekly Starters    18% │ (4 hits)   │
│  │ 🟡 Tier 2: Spot Starters      15% │ (3 hits)   │
│  │ 🟠 Tier 3: Bench Depth        12% │ (2 hits)   │
│  │ ⚪ Misses                      55% │ (11 adds)  │
│  └──────────────────────────────────┘             │
│                                                     │
│  Notable Hits:                                     │
│  • Puka Nacua (Tier 1) - 8/10 weeks started       │
│  • Tank Dell (Tier 2) - 3/8 weeks started         │
│  • Gus Edwards (Tier 3) - 1 week spike            │
└─────────────────────────────────────────────────────┘
```

### Data Requirements

**Frontend Calculations Needed:**
- Count total adds per manager
- Classify each add as Tier 1/2/3 hit or miss based on:
  - Weeks started post-acquisition
  - Single-week scoring spikes (≥10 pts)
  - Season-end positional rankings
- Calculate tier-specific percentages
- Generate visual breakdown

**New Backend Data:**
```typescript
interface HitRateData {
  manager_metrics: {
    roster_id: number;
    team_name: string;
    total_adds: number;
    tier1_hits: number;
    tier2_hits: number;
    tier3_hits: number;
    misses: number;
    overall_hit_rate: number;
    hit_details: {
      player_name: string;
      tier: 1 | 2 | 3 | null;
      weeks_started: number;
      total_weeks_available: number;
      best_week_score: number;
      acquisition_week: number;
    }[];
  }[];
  league_stats: {
    avg_hit_rate: number;
    median_hit_rate: number;
  };
}
```

**Implementation Phases:**
1. **Phase 1**: Mock data with tier visualization
2. **Phase 2**: Add roster/lineup data scraping from Sleeper API
3. **Phase 3**: Implement tier classification logic
4. **Phase 4**: Add notable hits section with player details

---

## Component 3: Churn Index Card (RCI)

### Visual Design

```
┌─────────────────────────────────────────────────────┐
│ 🔄 Roster Churn Index                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│         12.4% Weekly Churn                          │
│         Active Management Style                     │
│                                                     │
│  35 roster moves / 11 weeks / 25 spots             │
│                                                     │
│  Position Breakdown:                               │
│  ┌──────────────────────────────────┐             │
│  │ DST    ████████████░ 68.2%  (8)  │             │
│  │ RB     ██░░░░░░░░░░  10.9%  (6)  │             │
│  │ WR     ██░░░░░░░░░░   9.1%  (5)  │             │
│  │ TE     █░░░░░░░░░░░   5.5%  (3)  │             │
│  │ QB     █░░░░░░░░░░░   3.6%  (2)  │             │
│  └──────────────────────────────────┘             │
│                                                     │
│  💡 Strategy: Expected defense streaming           │
│     with moderate RB speculation                   │
└─────────────────────────────────────────────────────┘
```

### Data Requirements

**Frontend Calculations Needed:**
- Count total adds and drops per manager
- Calculate churn rate: (Adds + Drops) / (Weeks × Roster Size)
- Group by position for position-specific churn
- Categorize management style based on rate

**New Backend Data:**
```typescript
interface ChurnData {
  manager_metrics: {
    roster_id: number;
    team_name: string;
    total_adds: number;
    total_drops: number;
    overall_churn_rate: number;
    position_churn: {
      position: string;
      adds: number;
      drops: number;
      churn_rate: number;
      roster_slots: number;
    }[];
    management_style: 'extreme' | 'active' | 'moderate' | 'passive';
  }[];
  league_stats: {
    avg_churn_rate: number;
    median_churn_rate: number;
  };
  league_settings: {
    current_week: number;
    roster_size: number;
    position_limits: Record<string, number>;
  };
}
```

**Implementation Phases:**
1. **Phase 1**: Basic churn calculation and display
2. **Phase 2**: Position-specific breakdown with charts
3. **Phase 3**: Management style categorization
4. **Phase 4**: Add strategy insights and recommendations

---

## Component 4: Timing Score Card (WTS)

### Visual Design

```
┌─────────────────────────────────────────────────────┐
│ ⏰ Waiver Timing Score                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│         +18.2 Points                                │
│         75th Percentile (Proactive)                 │
│                                                     │
│  Early Week Advantage Over Late Week               │
│                                                     │
│  ┌────────────────┬────────────────┐              │
│  │ 🌅 Early Week  │ 🌙 Late Week   │              │
│  │ (Tue-Thu)      │ (Fri-Mon)      │              │
│  ├────────────────┼────────────────┤              │
│  │ 2 hits         │ 1 hit          │              │
│  │ 64.0 pts/hit   │ 42.0 pts/hit   │              │
│  │                │                │              │
│  │ Puka Nacua  72 │ Z.Charbonnet 42│              │
│  │ Tank Dell   56 │                │              │
│  └────────────────┴────────────────┘              │
│                                                     │
│  📊 Your Pattern: Proactive Researcher              │
│     Strong film study and trend identification      │
└─────────────────────────────────────────────────────┘
```

### Data Requirements

**Frontend Calculations Needed:**
- Parse transaction timestamps for day-of-week
- Classify adds as Early (Tue-Thu) or Late (Fri-Mon)
- Filter to only Tier 1/2 hits (requires WHR data)
- Calculate average points per hit for each window
- Compute differential score

**New Backend Data:**
```typescript
interface TimingData {
  manager_metrics: {
    roster_id: number;
    team_name: string;
    early_week_adds: number;
    late_week_adds: number;
    early_week_hits: number;
    late_week_hits: number;
    early_avg_points: number;
    late_avg_points: number;
    timing_score: number;
    timing_percentile: number;
    strategy_type: 'proactive' | 'balanced' | 'reactive';
    notable_hits: {
      player_name: string;
      timing: 'early' | 'late';
      points_scored: number;
      tier: 1 | 2;
    }[];
  }[];
  league_stats: {
    avg_timing_score: number;
    median_timing_score: number;
  };
}
```

**Implementation Phases:**
1. **Phase 1**: Day-of-week parsing and classification
2. **Phase 2**: Integration with WHR for hit filtering
3. **Phase 3**: Timing differential calculation
4. **Phase 4**: Strategy categorization and notable hits

---

## Comprehensive Implementation Plan

### Phase 1: Foundation & Easy Win (Week 1)
**Component: Roster Churn Index (RCI)**
- **Complexity**: EASY
- **Effort**: 1-2 hours
- **Dependencies**: None (uses existing data)

#### Tasks:
1. Create `ChurnIndexCard.tsx` component
2. Add basic churn calculation in `generate_waiver_wire_dashboard_json.py`
3. Update `WaiverWireData` type with churn metrics
4. Display overall churn rate and management style
5. Add position breakdown visualization

#### Deliverables:
- [ ] `dashboard/frontend/src/components/WaiverWire/ChurnIndexCard.tsx`
- [ ] Update `pipeline/scripts/generate_waiver_wire_dashboard_json.py` with churn calculations
- [ ] Update `dashboard/frontend/src/types/waiver-wire.ts` with ChurnData interface
- [ ] Integration into `WaiverWireAnalysis.tsx` page

---

### Phase 2: Value Metric (Week 2)
**Component: Waiver Wire Efficiency Score (WWES)**
- **Complexity**: MEDIUM
- **Effort**: 4-6 hours
- **Dependencies**: Requires player stats data

#### Tasks:
1. Create script to fetch player stats from Sleeper API
2. Implement points-after-acquisition calculation
3. Add FAAB tracking (already in transaction data)
4. Implement z-score normalization
5. Create `EfficiencyScoreCard.tsx` component
6. Add league rankings table

#### New Data Requirements:
- **Sleeper API**: `/stats/nfl/{season_type}/{season}`
- **Sleeper API**: `/league/{league_id}/rosters` (for roster tracking)
- Calculate points scored AFTER acquisition date

#### Deliverables:
- [ ] `pipeline/scripts/fetch_player_stats.py` (new script)
- [ ] `dashboard/frontend/src/components/WaiverWire/EfficiencyScoreCard.tsx`
- [ ] Update JSON generation with efficiency calculations
- [ ] Add efficiency data to API response
- [ ] League comparison table component

---

### Phase 3: Quality Metric (Week 3-4)
**Component: Waiver Hit Rate (WHR)**
- **Complexity**: HARD
- **Effort**: 8-10 hours
- **Dependencies**: Requires lineup data, player stats

#### Tasks:
1. Fetch weekly lineup data from Sleeper API
2. Implement usage rate tracking (weeks started post-acquisition)
3. Add season-end positional ranking calculations
4. Implement 3-tier classification logic
5. Create `HitRateCard.tsx` component with tier visualization
6. Add "Notable Hits" section

#### New Data Requirements:
- **Sleeper API**: `/league/{league_id}/matchups/{week}` (for lineup data)
- **Calculation**: Weeks started / weeks available post-acquisition
- **Calculation**: Season-end positional rankings (top-36 RB/WR, top-12 QB/TE)
- **Logic**: Multi-criteria evaluation for tier assignment

#### Deliverables:
- [ ] `pipeline/scripts/fetch_matchup_data.py` (new script)
- [ ] `dashboard/frontend/src/components/WaiverWire/HitRateCard.tsx`
- [ ] Hit classification algorithm in backend
- [ ] Tier visualization component (progress bar)
- [ ] Notable hits list with player details

---

### Phase 4: Strategy Metric (Week 5)
**Component: Waiver Timing Score (WTS)**
- **Complexity**: MEDIUM
- **Effort**: 3-4 hours
- **Dependencies**: Requires WHR completion

#### Tasks:
1. Parse transaction timestamps for day-of-week
2. Implement early vs late week classification
3. Leverage WHR tier data for filtering
4. Calculate timing differential
5. Create `TimingScoreCard.tsx` component
6. Add strategy categorization

#### New Data Requirements:
- **Parsing**: Day-of-week from `created_date` timestamp
- **Classification**: Tuesday-Thursday vs Friday-Monday
- **Integration**: Tier 1/2 hits from WHR metric
- **Calculation**: Early avg - Late avg point differential

#### Deliverables:
- [ ] `dashboard/frontend/src/components/WaiverWire/TimingScoreCard.tsx`
- [ ] Day-of-week parsing utility
- [ ] Timing calculation in backend
- [ ] Strategy pattern analysis
- [ ] Notable early/late hits comparison

---

## Data Pipeline Updates

### New Backend Endpoints

**Option A: Single Comprehensive Endpoint**
```typescript
GET /api/waiver-wire/metrics

Response:
{
  efficiency: EfficiencyData,
  hit_rate: HitRateData,
  churn: ChurnData,
  timing: TimingData
}
```

**Option B: Separate Endpoints (Recommended)**
```typescript
GET /api/waiver-wire/efficiency
GET /api/waiver-wire/hit-rate  
GET /api/waiver-wire/churn
GET /api/waiver-wire/timing
```

**Recommendation**: Option B allows:
- Independent loading states
- Faster initial page load
- Easier debugging
- Progressive enhancement

### New Python Pipeline Scripts

**Required New Scripts:**
1. `pipeline/scripts/fetch_player_stats.py`
   - Fetch weekly fantasy points from Sleeper
   - Cache player stats by week
   - Output: `player_stats_weekly.json`

2. `pipeline/scripts/fetch_lineup_data.py`
   - Fetch weekly starting lineups
   - Track player usage rates
   - Output: `lineup_data_weekly.json`

3. `pipeline/scripts/calculate_waiver_metrics.py`
   - Import all required data sources
   - Calculate all 4 metrics
   - Output: `waiver_metrics.json`

4. `pipeline/scripts/generate_waiver_metrics_json.py`
   - Format for frontend consumption
   - Output: `dashboard/frontend/public/api-waiver-metrics.json`

### Updated Pipeline Flow

```
Stage 5: stage5_waiver_wire.py (EXISTING)
  ↓
  └─> waiver_wire_analysis.csv

[NEW] Stage 5a: fetch_player_stats.py
  ↓
  └─> player_stats_weekly.json

[NEW] Stage 5b: fetch_lineup_data.py  
  ↓
  └─> lineup_data_weekly.json

[NEW] Stage 5c: calculate_waiver_metrics.py
  ├─ Input: waiver_wire_analysis.csv
  ├─ Input: player_stats_weekly.json
  ├─ Input: lineup_data_weekly.json
  ↓
  └─> waiver_metrics.json

[NEW] Stage 5d: generate_waiver_metrics_json.py
  ↓
  └─> dashboard/frontend/public/api-waiver-metrics.json
```

---

## UI/UX Design Specifications

### Layout Integration

**Current Page Layout:**
```
WaiverWireAnalysis
└── All Transactions Table (full width)
```

**Proposed Layout:**
```
WaiverWireAnalysis
├── Metrics Dashboard (new section above table)
│   ├── Row 1: [Efficiency Card] [Hit Rate Card]
│   └── Row 2: [Churn Card] [Timing Card]
└── All Transactions Table
```

**Responsive Breakpoints:**
- **Mobile (< 640px)**: Stack cards vertically
- **Tablet (640-1024px)**: 2 cards per row
- **Desktop (> 1024px)**: All 4 cards in 2×2 grid

### Color Scheme & Visual Hierarchy

**Card Colors (Consistent with existing dashboard):**
- Efficiency: Blue theme (💰 primary-600)
- Hit Rate: Green theme (🎯 green-600)
- Churn: Orange theme (🔄 orange-600)
- Timing: Purple theme (⏰ purple-600)

**Status Indicators:**
- **Elite**: Gold badge with sparkle icon ⭐
- **Above Average**: Green checkmark ✓
- **Average**: Gray neutral circle
- **Below Average**: Yellow warning triangle ⚠️
- **Poor**: Red X ✗

### Interactive Features

**All Cards:**
- Hover for detailed tooltips
- Click for expanded view (modal with full breakdown)
- Export data button (CSV download)

**League Comparison:**
- Sortable tables
- Visual progress bars
- Highlight current user's row
- Percentile indicators

---

## Implementation Checklist

### Backend Changes

**New Files to Create:**
- [ ] `pipeline/scripts/fetch_player_stats.py`
- [ ] `pipeline/scripts/fetch_lineup_data.py`
- [ ] `pipeline/scripts/calculate_waiver_metrics.py`
- [ ] `pipeline/scripts/generate_waiver_metrics_json.py`

**Files to Update:**
- [ ] `update_dashboard.py` - Add new stages 5a-5d
- [ ] `pipeline/stage5_waiver_wire.py` - Ensure compatibility

**New Data Files:**
- [ ] `pipeline/player_stats_weekly.json`
- [ ] `pipeline/lineup_data_weekly.json`
- [ ] `pipeline/waiver_metrics.json`
- [ ] `dashboard/frontend/public/api-waiver-metrics.json`

### Frontend Changes

**New Components to Create:**
- [ ] `dashboard/frontend/src/components/WaiverWire/EfficiencyScoreCard.tsx`
- [ ] `dashboard/frontend/src/components/WaiverWire/HitRateCard.tsx`
- [ ] `dashboard/frontend/src/components/WaiverWire/ChurnIndexCard.tsx`
- [ ] `dashboard/frontend/src/components/WaiverWire/TimingScoreCard.tsx`
- [ ] `dashboard/frontend/src/components/WaiverWire/MetricsDashboard.tsx` (container)

**Files to Update:**
- [ ] `dashboard/frontend/src/pages/WaiverWireAnalysis.tsx` - Integrate metrics section
- [ ] `dashboard/frontend/src/types/waiver-wire.ts` - Add metric interfaces
- [ ] `dashboard/frontend/src/services/api.ts` - Add metrics endpoints

**New Utilities:**
- [ ] `dashboard/frontend/src/utils/waiverMetrics.ts` - Calculation helpers
- [ ] `dashboard/frontend/src/utils/chartHelpers.ts` - Visualization utilities

---

## Testing Strategy

### Unit Tests
- [ ] Churn rate calculation accuracy
- [ ] Z-score normalization correctness
- [ ] Tier classification logic
- [ ] Day-of-week parsing edge cases

### Integration Tests
- [ ] End-to-end metric calculation pipeline
- [ ] API endpoint responses
- [ ] Component rendering with various data states

### Visual Testing
- [ ] Mobile responsiveness (320px - 768px)
- [ ] Tablet layout (768px - 1024px)
- [ ] Desktop layout (> 1024px)
- [ ] Color contrast accessibility

---

## Risk Mitigation

### Data Quality Risks

**Risk**: Player stats data incomplete or unavailable
- **Mitigation**: Graceful degradation with "Data Unavailable" messages
- **Fallback**: Show transaction counts only without points calculation

**Risk**: Lineup data not accessible
- **Mitigation**: Use simplified WHR based on single-week scoring only
- **Fallback**: Display "Tier classification pending" status

### Performance Risks

**Risk**: Too many API calls slow page load
- **Mitigation**: Implement proper caching strategy
- **Solution**: Pre-calculate all metrics in pipeline, serve static JSON

**Risk**: Large dataset calculations timeout
- **Mitigation**: Process incrementally, save checkpoints
- **Solution**: Implement progressive loading with skeleton states

### UX Risks

**Risk**: Metrics too complex for casual users
- **Mitigation**: Add "What does this mean?" tooltips
- **Solution**: Provide interpretation text with each score

**Risk**: Mobile layout cramped
- **Mitigation**: Stack cards vertically on mobile
- **Solution**: Simplified mobile view with essential data only

---

## Success Criteria

### Functional Requirements
✅ All 4 metrics display correctly for each manager
✅ Calculations match documented formulas
✅ League comparisons rank managers accurately
✅ Data updates when new transactions added

### UX Requirements
✅ Mobile-responsive (works on 320px screens)
✅ Load time < 3 seconds
✅ Clear interpretation guidance for each metric
✅ Accessible color contrast (WCAG AA)

### Business Requirements
✅ Differentiate skilled vs lucky managers
✅ Provide actionable insights
✅ Engage users to check dashboard regularly
✅ Support strategy discussions in league

---

## Rollout Plan

### Week 1: MVP (RCI Only)
- Deploy simplest metric first
- Validate infrastructure
- Gather user feedback on presentation

### Week 2: Value Add (RCI + WWES)
- Add high-value efficiency metric
- Demonstrate ROI calculations
- Build user confidence in metrics

### Week 3-4: Core Metric (RCI + WWES + WHR)
- Release most anticipated metric
- Complete tier classification system
- Enable full quality analysis

### Week 5: Strategic Layer (All 4 Metrics)
- Add timing analysis
- Complete metric suite
- Provide comprehensive manager profiles

---

## Future Enhancements (Post-Launch)

### V2 Features
1. Historical trending (week-over-week metric changes)
2. Position-specific WWES breakdowns
3. Weighted WHR (Tier 1 = 3x, Tier 2 = 2x, Tier 3 = 1x)
4. Injury-adjusted metrics
5. Streaming success rates (DST/K separate tracking)

### Advanced Analytics
6. Predictive modeling (predict which adds will hit)
7. Trade-waiver cross-analysis
8. Draft-waiver efficiency comparison
9. Playoff performance correlation

### Social Features
10. League-wide metric leaderboards
11. Weekly metric change notifications
12. Manager strategy badges (e.g., "Proactive Researcher", "Streaming Specialist")

---

## Appendix A: Component File Structure

```
dashboard/frontend/src/components/WaiverWire/
├── ChurnIndexCard.tsx           (Phase 1)
├── EfficiencyScoreCard.tsx      (Phase 2)
├── HitRateCard.tsx              (Phase 3)
├── TimingScoreCard.tsx          (Phase 4)
├── MetricsDashboard.tsx         (Container)
└── shared/
    ├── MetricCard.tsx           (Base component)
    ├── TierProgressBar.tsx      (Reusable viz)
    ├── LeagueRankingsTable.tsx  (Reusable table)
    └── MetricTooltip.tsx        (Help text)
```

## Appendix B: API Response Schema

```typescript
// dashboard/frontend/public/api-waiver-metrics.json
{
  "metadata": {
    "generated_at": "2025-12-13T17:00:00Z",
    "current_week": 15,
    "season_year": 2025
  },
  "efficiency": { /* EfficiencyData */ },
  "hit_rate": { /* HitRateData */ },
  "churn": { /* ChurnData */ },
  "timing": { /* TimingData */ }
}
```

## Appendix C: Calculation Examples

See WAIVER_WIRE_METRICS.md for detailed calculation examples for each metric.

---

**Document Version**: 1.0
**Created**: 2025-12-13
**Last Updated**: 2025-12-13
**Status**: Ready for Implementation