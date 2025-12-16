# Dashboard Data Files

This directory contains generated JSON files consumed by the frontend. These files are **build artifacts** created by the Python pipeline, not source code.

## Generating Data

Run the full pipeline to regenerate all JSON files:

```bash
python update_dashboard.py
```

Individual data updates:
```bash
# Trades and standings
python pipeline/scripts/generate_dashboard_json.py

# Waiver wire analysis
python pipeline/scripts/generate_waiver_wire_dashboard_json.py

# Playoff scenarios
python pipeline/scripts/calculate_playoff_scenarios.py
```

## File Descriptions

- `api-trades.json` - Trade analysis with valuations and win rates
- `api-teams.json` - Team rosters and metadata
- `api-standings.json` - Current standings with playoff scenarios
- `api-waiver-wire.json` - Waiver wire acquisition metrics
- `api-stats-summary.json` - League-wide statistics
- `playoff_scenarios_simulated.json` - Monte Carlo playoff simulations

## Important Notes

⚠️ **Do not manually edit these files** - changes will be overwritten on next pipeline run.

📝 **Do not commit these files** - they are excluded via .gitignore (except .example.json files).

🔄 **Regenerate after league data changes** - trades, waiver moves, weekly results.