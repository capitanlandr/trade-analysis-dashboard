#!/usr/bin/env python3
"""
Stage 8a: Generate Trade Metrics JSON

Calculates advanced trade metrics (Sharpe Ratio, Significance Test,
Opponent-Adjusted Performance) from the trade analysis CSV and writes
api-trade-metrics.json to the dashboard public directory.

Input: league_trades_analysis_pipeline.csv, team_identity_mapping.csv
Output: dashboard/frontend/public/api-trade-metrics.json
"""

import csv
import json
import math
import sys
import os
from collections import defaultdict
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.logging_config import get_logger

logger = get_logger(__name__)

SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR.parent
REPO_ROOT = PIPELINE_DIR.parent

TRADES_CSV = PIPELINE_DIR / 'league_trades_analysis_pipeline.csv'
TEAMS_CSV = PIPELINE_DIR / 'team_identity_mapping.csv'
OUTPUT_FILE = REPO_ROOT / 'dashboard' / 'frontend' / 'public' / 'api-trade-metrics.json'


def binomial_pmf(n, k, p=0.5):
    comb = math.factorial(n) / (math.factorial(k) * math.factorial(n - k))
    return comb * (p ** k) * ((1 - p) ** (n - k))


def binomial_p_value_high(n, k):
    return sum(binomial_pmf(n, i) for i in range(k, n + 1))


def binomial_p_value_low(n, k):
    return sum(binomial_pmf(n, i) for i in range(0, k + 1))


def load_team_names():
    team_names = {}
    if not TEAMS_CSV.exists():
        logger.warning(f"Team identity CSV not found: {TEAMS_CSV}")
        return team_names

    with open(TEAMS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            team_names[row['sleeper_username']] = row['real_name']
    return team_names


def load_trades():
    trades = []
    if not TRADES_CSV.exists():
        logger.error(f"Trades analysis CSV not found: {TRADES_CSV}")
        return trades

    with open(TRADES_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    return trades


def generate_trade_metrics():
    logger.info("=" * 60)
    logger.info("STAGE 8a: GENERATE TRADE METRICS")
    logger.info("=" * 60)

    team_names = load_team_names()
    trades = load_trades()

    if not trades:
        logger.error("No trades found. Skipping trade metrics generation.")
        return

    logger.info(f"Loaded {len(trades)} trades, {len(team_names)} team mappings")

    manager_trades = defaultdict(list)
    manager_opponents = defaultdict(lambda: defaultdict(list))

    for t in trades:
        ta, tb = t['team_a'], t['team_b']
        ta_now = float(t['team_a_value_now'])
        tb_now = float(t['team_b_value_now'])
        advantage_a = ta_now - tb_now

        manager_trades[ta].append({'advantage': advantage_a, 'opponent': tb, 'date': t['trade_date']})
        manager_trades[tb].append({'advantage': -advantage_a, 'opponent': ta, 'date': t['trade_date']})

        manager_opponents[ta][tb].append(advantage_a)
        manager_opponents[tb][ta].append(-advantage_a)

    output = {
        'metadata': {
            'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_trades': len(trades),
            'description': 'Advanced trade metrics: Sharpe Ratio, Significance Test, Opponent-Adjusted Performance'
        },
        'managers': []
    }

    for manager, mtrades in manager_trades.items():
        advs = [t['advantage'] for t in mtrades]
        n = len(advs)
        mean = sum(advs) / n
        variance = sum((a - mean) ** 2 for a in advs) / n
        std_dev = variance ** 0.5
        sharpe = mean / std_dev if std_dev > 0 else 0

        wins = sum(1 for a in advs if a > 0)
        win_rate = wins / n * 100

        if wins >= n / 2:
            p_val = binomial_p_value_high(n, wins)
            direction = 'winning'
        else:
            p_val = binomial_p_value_low(n, wins)
            direction = 'losing'

        if p_val < 0.05:
            sig_verdict = 'significant'
        elif p_val < 0.10:
            sig_verdict = 'approaching'
        else:
            sig_verdict = 'not_significant'

        if n < 5:
            sharpe_verdict = 'insufficient_data'
        elif sharpe > 0.5 and n >= 10:
            sharpe_verdict = 'elite'
        elif sharpe > 0.3 and n >= 10:
            sharpe_verdict = 'skilled'
        elif sharpe > 0:
            sharpe_verdict = 'positive_noisy'
        else:
            sharpe_verdict = 'losing'

        opp_data = []
        for opp, opp_advs in manager_opponents[manager].items():
            opp_total = sum(opp_advs)
            opp_count = len(opp_advs)
            opp_data.append({
                'opponent': opp,
                'opponent_name': team_names.get(opp, opp),
                'net_advantage': round(opp_total, 1),
                'trade_count': opp_count,
                'avg_per_trade': round(opp_total / opp_count, 1)
            })
        opp_data.sort(key=lambda x: x['net_advantage'], reverse=True)

        unique_opps = len(opp_data)
        positive_opps = sum(1 for o in opp_data if o['net_advantage'] > 0)

        total_advantage = sum(advs)
        if opp_data and total_advantage != 0:
            top_opp_pct = round(opp_data[0]['net_advantage'] / total_advantage * 100, 1)
        else:
            top_opp_pct = 0

        mgr_entry = {
            'username': manager,
            'real_name': team_names.get(manager, manager),
            'trades': n,
            'net_advantage': round(total_advantage, 1),
            'sharpe': {
                'value': round(sharpe, 3),
                'mean': round(mean, 1),
                'std_dev': round(std_dev, 1),
                'verdict': sharpe_verdict
            },
            'significance': {
                'wins': wins,
                'win_rate': round(win_rate, 1),
                'p_value': round(p_val, 4),
                'direction': direction,
                'verdict': sig_verdict
            },
            'opponent_adjusted': {
                'unique_opponents': unique_opps,
                'positive_matchups': positive_opps,
                'top_opponent_concentration_pct': top_opp_pct,
                'opponents': opp_data
            }
        }
        output['managers'].append(mgr_entry)

    output['managers'].sort(key=lambda x: x['net_advantage'], reverse=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f"Generated {OUTPUT_FILE} with {len(output['managers'])} managers")
    logger.info("=" * 60)
    logger.info("STAGE 8a COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        generate_trade_metrics()
        print("Trade metrics generated successfully.")
    except Exception as e:
        logger.error(f"Stage 8a failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
