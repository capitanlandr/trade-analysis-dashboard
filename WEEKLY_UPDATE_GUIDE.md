# Weekly Dashboard Update Guide

## Quick Update (Recommended)

Just run this one command from the project root:

```bash
python3 update_dashboard.py
```

This automatically:
- ✅ Detects current week from Sleeper API
- ✅ Fetches latest trades and standings
- ✅ Runs waiver wire analysis
- ✅ Simulates 10,000 playoff scenarios
- ✅ Calculates progressive draft order
- ✅ Generates all 7 dashboard JSON files
- ✅ Commits and pushes to GitHub
- ✅ Triggers Vercel deployment

**Time:** 2-3 minutes  
**Result:** Dashboard updates automatically on Vercel

---

## Manual Step-by-Step (For Debugging)

If you need to run individual stages:

### 1. Detect Current Week
```bash
cd pipeline
python3 scripts/detect_current_week.py
```
Verifies: `pipeline/config/current_week.json` updated

### 2. Fetch and Process Trades
```bash
python3 stage1_fetch_trades.py
python3 stage2_extract_assets.py
python3 stage3_cache_values.py
python3 stage4_final.py
```
Verifies: `pipeline/league_trades_analysis_pipeline.csv` updated

### 3. Waiver Wire Analysis
```bash
python3 stage5_waiver_wire.py
```
Verifies: `pipeline/waiver_wire_stats.json` created

### 4. Standings and Playoff Scenarios
```bash
python3 scripts/fetch_standings.py
python3 scripts/simulate_playoff_scenarios.py
```
Verifies: `pipeline/standings_data.json` and `pipeline/playoff_scenarios_simulated.json` created

### 5. Draft Order Projection
```bash
python3 analyze_2026_pick_ownership.py
python3 scripts/calculate_progressive_draft_order.py
```
Verifies: `pipeline/draft_order_2026_progressive.json` created

### 6. Generate Dashboard JSON Files
```bash
python3 scripts/generate_dashboard_json.py
python3 scripts/generate_waiver_wire_dashboard_json.py
```
Verifies: 7 JSON files created in `dashboard/frontend/public/`

### 7. Deploy
```bash
cd ..
git add dashboard/frontend/public/*.json
git commit -m "data: update dashboard data"
git push origin main
```
Verifies: Vercel deployment triggered

---

## Weekly Checklist

### Before Running Update

- [ ] Verify current week is correct (check Sleeper app)
- [ ] Confirm all recent trades are processed in Sleeper
- [ ] Check if waiver period has cleared
- [ ] Note any roster changes you want to track

### After Running Update

- [ ] Visit dashboard URL (dynasuiiiianalytics.vercel.app)
- [ ] Check **Overview** page loads with latest trades
- [ ] Verify **Standings** shows correct week number
- [ ] Review **Playoff Scenarios** for updated probabilities
- [ ] Check **Draft Order** progression is accurate
- [ ] Confirm **Waiver Wire** metrics are current
- [ ] Test **Archive** page if you use it

### Data Quality Checks

- [ ] Current week number matches Sleeper app
- [ ] Trade count matches league history
- [ ] Standings W-L records are correct
- [ ] Points For/Against are accurate
- [ ] Playoff probabilities add up to 100%

---

## When Things Go Wrong

### Dashboard shows wrong week
```bash
# Manually update week in pipeline/config/current_week.json
# Then regenerate data
python3 update_dashboard.py
```

### Missing recent trades
```bash
# Re-fetch trades
cd pipeline
python3 stage1_fetch_trades.py
python3 stage2_extract_assets.py
python3 stage3_cache_values.py
python3 stage4_final.py
cd ..
python3 update_dashboard.py
```

### Playoff scenarios not updating
```bash
# Check current week is correct first
cat pipeline/config/current_week.json

# Then regenerate
cd pipeline
python3 scripts/fetch_standings.py
python3 scripts/simulate_playoff_scenarios.py
python3 scripts/generate_dashboard_json.py
```

### Draft order looks wrong
```bash
cd pipeline
python3 analyze_2026_pick_ownership.py
python3 scripts/calculate_progressive_draft_order.py
python3 scripts/generate_dashboard_json.py
```

---

## Automation Options

### Option 1: GitHub Actions (Recommended)

Already configured! Pipeline runs automatically every day at 9 AM EST.

**Manual trigger:**
1. Go to GitHub repo → Actions tab
2. Click "Update Dashboard Data"
3. Click "Run workflow"

### Option 2: Cron Job (Local Server)

Add to your crontab:
```bash
# Run every day at 9 AM
0 9 * * * cd /path/to/trade-analysis-dashboard-clean && /usr/bin/python3 update_dashboard.py >> update.log 2>&1
```

### Option 3: Manual Updates

Just run `python3 update_dashboard.py` whenever you want to update.

---

## Best Practices

### Timing
- **Best time to update**: After waivers clear (usually Wednesday morning)
- **Avoid updating**: During live games (data may be incomplete)
- **Playoff weeks**: Update immediately after Monday night to capture all results

### Frequency
- **Regular season**: Once per week (after waivers)
- **Playoff weeks**: 2-3 times per week for fresh scenarios
- **After big trades**: Immediately to see impact

### Data Validation
- Always check the dashboard after updating
- Compare standings to Sleeper app
- Verify playoff probabilities make sense
- Check that recent trades appear

---

## Quick Reference Commands

```bash
# Full update (recommended)
python3 update_dashboard.py

# Dry run (see what would happen)
python3 update_dashboard.py --dry-run

# Update without deploying
python3 update_dashboard.py --skip-git

# Check current week
cat pipeline/config/current_week.json

# View pipeline output files
ls -lh pipeline/*.json pipeline/*.csv

# Validate dashboard JSON files
cd dashboard/frontend/public && for f in api-*.json; do echo "=== $f ===" && jq . "$f" > /dev/null && echo "✓ Valid" || echo "✗ Invalid"; done
```

---

## Troubleshooting

See [README.md](README.md#-troubleshooting) for comprehensive troubleshooting guide.

**Quick fixes:**
- Wrong week → Edit `pipeline/config/current_week.json`
- Missing data → Run `python3 update_dashboard.py`
- Deployment failed → Check Vercel logs
- JSON invalid → Re-run generation scripts
