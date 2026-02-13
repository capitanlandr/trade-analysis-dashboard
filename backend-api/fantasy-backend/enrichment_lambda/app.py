"""
Enrichment Lambda - Task 2.1: The Centerpiece
Ports pipeline stages 2-5 into a single Lambda that:
1. Reads raw data from DynamoDB (trades, waivers, standings, matchups, valuations)
2. Reads reference data (team mapping, pick origins, draft order)
3. Runs enrichment logic (extract assets, cache values, analyze trades, waiver wire)
4. Writes 7 ENRICHED_*#LATEST items to DynamoDB

Schedule: Daily at 10 AM UTC (after ingestion)
Runtime: Python 3.11 + pandas/numpy Lambda Layer
"""

import json
import os
import io
import csv
import re
import time
import math
import random
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from functools import cmp_to_key

import boto3
import pandas as pd
import numpy as np
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get('TABLE_NAME', 'fantasy-dashboard-data')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

# Season configuration (matches ingestion_lambda/app.py)
SEASONS = {
    'season_2': {
        'status': 'static',
        'league_id': '1180814327660371968',
        'year': 2024,
        'description': 'Season 2 - Historical (2024)'
    },
    'season_3': {
        'status': 'active',
        'league_id': '1312166810505719808',
        'year': 2025,
        'description': 'Season 3 - Current (2025/2026)'
    }
}

# Pipeline constants (from pipeline/constants.py)
FAAB_VALUE_PER_DOLLAR = 1
DRAFT_COMPLETION_DATE = datetime(2025, 5, 5)
SEASON_START_DATE = datetime(2025, 9, 3)
ROUND_ORDINALS = {1: '1st', 2: '2nd', 3: '3rd', 4: '4th', 5: '5th'}

# API configuration
SLEEPER_API_BASE = "https://api.sleeper.app/v1"
DYNASTYPROCESS_CSV_URL = "https://github.com/dynastyprocess/data/raw/master/files/values.csv"
GITHUB_API_BASE = "https://api.github.com"
DYNASTYPROCESS_REPO = "dynastyprocess/data"
DYNASTYPROCESS_VALUES_PATH = "files/values.csv"
GIT_COMMIT_SEARCH_DAYS = 7

# Tier values (from config)
TIER_VALUES = {
    'early_first': 5430,
    'mid_first': 2558,
    'late_first': 1232,
}

# Lambda-local path for bundled CSVs
LAMBDA_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Throttle-safe DynamoDB helpers (same pattern as ingestion lambda)
# ---------------------------------------------------------------------------
MAX_RETRIES = 8
BASE_BACKOFF = 0.5


def throttle_safe_put_item(item: dict, retries: int = MAX_RETRIES) -> None:
    """put_item with exponential backoff on throttle."""
    for attempt in range(retries):
        try:
            table.put_item(Item=item)
            return
        except ClientError as e:
            code = e.response['Error']['Code']
            if code in ('ProvisionedThroughputExceededException', 'ThrottlingException'):
                wait = BASE_BACKOFF * (2 ** attempt)
                logger.warning(f"[throttle] put_item attempt {attempt+1}/{retries} throttled, "
                               f"waiting {wait:.1f}s")
                time.sleep(wait)
            else:
                raise
    table.put_item(Item=item)


def convert_for_dynamo(obj):
    """Convert Python objects to DynamoDB-compatible types."""
    if isinstance(obj, list):
        return [convert_for_dynamo(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_for_dynamo(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return 0
        return Decimal(str(round(obj, 6)))
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return 0
        return Decimal(str(round(val, 6)))
    elif isinstance(obj, np.bool_):
        return bool(obj)
    else:
        return obj


def clean_nan(obj):
    """Recursively replace NaN/None with safe defaults for JSON."""
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(item) for item in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return 0
    elif obj is None:
        return None
    else:
        return obj


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def fetch_url(url: str, timeout: int = 30, headers: dict = None) -> Any:
    """Fetch JSON from a URL with optional auth headers."""
    req_headers = {'User-Agent': 'DynasuiiiiEnrichment/2.0'}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode())


def fetch_csv_as_dataframe(url: str, timeout: int = 30) -> pd.DataFrame:
    """Fetch a CSV from URL and return as DataFrame."""
    req = urllib.request.Request(url, headers={'User-Agent': 'DynasuiiiiEnrichment/2.0'})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        csv_text = response.read().decode('utf-8')
    return pd.read_csv(io.StringIO(csv_text))


# ---------------------------------------------------------------------------
# DynamoDB readers
# ---------------------------------------------------------------------------
def query_items(pk: str, sk_prefix: str) -> List[Dict]:
    """Query DynamoDB for items matching PK and SK prefix."""
    items = []
    params = {
        'KeyConditionExpression': boto3.dynamodb.conditions.Key('PK').eq(pk) &
                                  boto3.dynamodb.conditions.Key('SK').begins_with(sk_prefix)
    }
    # Need to import Key
    from boto3.dynamodb.conditions import Key
    params = {
        'KeyConditionExpression': Key('PK').eq(pk) & Key('SK').begins_with(sk_prefix)
    }

    while True:
        response = table.query(**params)
        items.extend(response.get('Items', []))
        if 'LastEvaluatedKey' not in response:
            break
        params['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return items


def get_item(pk: str, sk: str) -> Optional[Dict]:
    """Get a single item from DynamoDB."""
    response = table.get_item(Key={'PK': pk, 'SK': sk})
    return response.get('Item')


def read_raw_trades(season_id: str) -> List[Dict]:
    """Read raw trade items from DynamoDB."""
    items = query_items(f'SEASON#{season_id}', 'TRADE#')
    trades = []
    for item in items:
        raw = item.get('RawData', {})
        if raw:
            raw = json_safe(raw)
            raw['season'] = season_id
            trades.append(raw)
    logger.info(f"  Read {len(trades)} raw trades for {season_id}")
    return trades


def read_raw_waivers(season_id: str) -> List[Dict]:
    """Read raw waiver items from DynamoDB."""
    items = query_items(f'SEASON#{season_id}', 'WAIVER#')
    waivers = []
    for item in items:
        raw = item.get('RawData', {})
        if raw:
            raw = json_safe(raw)
            raw['season'] = season_id
            waivers.append(raw)
    logger.info(f"  Read {len(waivers)} raw waivers for {season_id}")
    return waivers


def read_standings(season_id: str) -> Optional[Dict]:
    """Read standings from DynamoDB."""
    item = get_item(f'SEASON#{season_id}', 'STANDINGS#CURRENT')
    if item:
        return json_safe(item)
    return None


def read_valuations(season_id: str) -> Optional[List[Dict]]:
    """Read DynastyProcess valuations from DynamoDB."""
    item = get_item(f'SEASON#{season_id}', 'VALUATIONS#LATEST')
    if item:
        players_json = item.get('Players', '[]')
        if isinstance(players_json, str):
            return json.loads(players_json)
        return json_safe(players_json)
    return None


def read_team_mapping() -> List[Dict]:
    """Read team identity mapping from DynamoDB."""
    item = get_item('REFERENCE', 'TEAM_IDENTITY_MAPPING')
    if item:
        return json_safe(item.get('Teams', []))
    return []


def read_pick_origins() -> List[Dict]:
    """Read pick origin mapping from DynamoDB."""
    item = get_item('REFERENCE', 'PICK_ORIGIN_MAPPING_2025')
    if item:
        return json_safe(item.get('PickOrigins', []))
    return []


def read_draft_order_2026() -> Optional[Dict]:
    """Read 2026 draft order from DynamoDB."""
    item = get_item('REFERENCE', 'DRAFT_ORDER_2026')
    if item:
        draft_json = item.get('DraftOrder', '{}')
        if isinstance(draft_json, str):
            return json.loads(draft_json)
        return json_safe(draft_json)
    return None


def json_safe(obj):
    """Convert Decimal types from DynamoDB to native Python types."""
    if isinstance(obj, list):
        return [json_safe(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    else:
        return obj


# ---------------------------------------------------------------------------
# STAGE 2: Extract Assets from Trades
# Ported from pipeline/stage2_extract_assets.py
# ---------------------------------------------------------------------------
def fetch_sleeper_players() -> Dict:
    """Fetch NFL player data from Sleeper API for name resolution."""
    try:
        logger.info("Fetching Sleeper /players/nfl (~10MB)...")
        players = fetch_url(f"{SLEEPER_API_BASE}/players/nfl", timeout=60)
        logger.info(f"  Loaded {len(players)} players from Sleeper API")
        return players
    except Exception as e:
        logger.error(f"Failed to fetch Sleeper players: {e}")
        return {}


def build_roster_to_username(team_mapping: List[Dict]) -> Dict[int, str]:
    """Build roster_id -> sleeper_username mapping from team identity data."""
    mapping = {}
    for team in team_mapping:
        roster_id = team.get('roster_id')
        username = team.get('sleeper_username', '')
        if roster_id is not None:
            mapping[int(roster_id)] = username
    return mapping


def build_team_info_map(team_mapping: List[Dict]) -> Dict[int, Dict]:
    """Build roster_id -> full team info mapping."""
    mapping = {}
    for team in team_mapping:
        roster_id = team.get('roster_id')
        if roster_id is not None:
            mapping[int(roster_id)] = team
    return mapping


def extract_assets_from_trades(
    all_trades: List[Dict],
    roster_to_username: Dict[int, str],
    players: Dict
) -> List[Dict]:
    """
    Extract individual asset transactions from raw trades.
    Ported from pipeline/stage2_extract_assets.py::extract_assets_from_trades()
    """
    asset_transactions = []

    for trade in all_trades:
        trade_id = trade.get('transaction_id', trade.get('id', ''))
        trade_created = trade.get('created', 0)
        trade_date = datetime.fromtimestamp(trade_created / 1000).strftime('%Y-%m-%d') if trade_created else ''
        status = trade.get('status', 'unknown')
        roster_ids = trade.get('roster_ids', [])
        season = trade.get('season', '')

        trade_type = '2-team' if len(roster_ids) == 2 else f'{len(roster_ids)}-team'

        if len(roster_ids) == 2:
            roster_a, roster_b = roster_ids[0], roster_ids[1]
            team_a = roster_to_username.get(roster_a, f"Team{roster_a}")
            team_b = roster_to_username.get(roster_b, f"Team{roster_b}")
        else:
            team_a = f"{len(roster_ids)}-team trade"
            team_b = ""

        # Process player adds
        adds = trade.get('adds') or {}
        for player_id, to_roster in adds.items():
            player_info = players.get(str(player_id), {})
            player_name = player_info.get('full_name', f'Player_{player_id}') if isinstance(player_info, dict) else f'Player_{player_id}'

            receiving_team = roster_to_username.get(to_roster, f'Team{to_roster}')
            if len(roster_ids) == 2:
                giving_team = team_b if to_roster == roster_a else team_a
            else:
                giving_team = f'{len(roster_ids)}-team'

            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': str(trade_id),
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': 'player',
                'asset_name': player_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': None,
                'roster_a': team_a,
                'roster_b': team_b,
                'season': season,
            })

        # Process draft picks
        draft_picks = trade.get('draft_picks') or []
        for pick in draft_picks:
            pick_season = pick.get('season')
            round_num = pick.get('round')
            new_roster_id = pick.get('owner_id')
            original_roster_id = pick.get('roster_id')

            pick_name = f"{pick_season} Round {round_num}"
            origin_owner = roster_to_username.get(original_roster_id, f'Team{original_roster_id}')
            receiving_team = roster_to_username.get(new_roster_id, f'Team{new_roster_id}')

            if len(roster_ids) == 2:
                giving_team = team_b if new_roster_id == roster_a else team_a
            else:
                giving_team = f'{len(roster_ids)}-team'

            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': str(trade_id),
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': 'pick',
                'asset_name': pick_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': origin_owner,
                'roster_a': team_a,
                'roster_b': team_b,
                'season': season,
            })

        # Process FAAB
        waiver_budget = trade.get('waiver_budget') or []
        for faab in waiver_budget:
            amount = faab.get('amount', 0)
            receiver = faab.get('receiver')

            faab_name = f"${amount} FAAB"
            receiving_team = roster_to_username.get(receiver, f'Team{receiver}')

            if len(roster_ids) == 2:
                giving_team = team_b if receiver == roster_a else team_a
            else:
                giving_team = f'{len(roster_ids)}-team'

            asset_transactions.append({
                'trade_date': trade_date,
                'trade_id': str(trade_id),
                'trade_status': status,
                'trade_type': trade_type,
                'asset_type': 'faab',
                'asset_name': faab_name,
                'receiving_team': receiving_team,
                'giving_team': giving_team,
                'origin_owner': None,
                'roster_a': team_a,
                'roster_b': team_b,
                'season': season,
            })

    logger.info(f"  Extracted {len(asset_transactions)} asset transactions")
    return asset_transactions


# ---------------------------------------------------------------------------
# STAGE 3: Cache Asset Values
# Ported from pipeline/stage3_cache_values.py
# ---------------------------------------------------------------------------
def load_bundled_csvs() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load static CSVs bundled with Lambda code."""
    draft_csv = LAMBDA_DIR / 'sleeper_rookie_draft_2025.csv'
    proj_csv = LAMBDA_DIR / 'weekly_2026_pick_projections_expanded.csv'

    draft_results = pd.read_csv(draft_csv)
    pick_projections = pd.read_csv(proj_csv)

    logger.info(f"  Loaded {len(draft_results)} draft results, {len(pick_projections)} projection rows")
    return draft_results, pick_projections


def build_pick_lineage(draft_results: pd.DataFrame, pick_origins: List[Dict]) -> Dict:
    """Build PICK_LINEAGE mapping from draft results and pick origins."""
    # Build (round, pick) -> origin_owner mapping from DynamoDB pick origins
    origin_map = {}
    for po in pick_origins:
        r = po.get('round')
        p = po.get('pick')
        owner = po.get('origin_owner', '')
        if r and p:
            origin_map[(int(r), int(p))] = owner

    lineage = {}
    for _, row in draft_results.iterrows():
        round_num = int(row['Round'])
        pick_in_round = int(row['Pick in Round'])
        player = row['Player']
        overall_pick = int(row['Pick'])
        final_owner = row['Owner']

        origin_owner = origin_map.get((round_num, pick_in_round), f'Unknown_R{round_num}P{pick_in_round}')
        key = (origin_owner, round_num)

        if key not in lineage:
            lineage[key] = []
        lineage[key].append({
            'final_owner': final_owner,
            'pick_in_round': pick_in_round,
            'player': player,
            'overall_pick': overall_pick,
        })

    logger.info(f"  Built pick lineage: {sum(len(v) for v in lineage.values())} picks, "
                f"{len(lineage)} (origin, round) combos")
    return lineage


def build_draft_order_2026_map(
    draft_order_data: Optional[Dict],
    roster_to_username: Dict[int, str]
) -> Dict:
    """Build (username, round) -> pick_label mapping for 2026 picks."""
    mapping = {}
    if not draft_order_data:
        return mapping

    draft_order = draft_order_data.get('draft_order', {})
    for round_name, picks in draft_order.items():
        round_num = int(round_name.split('_')[1])
        for pick in picks:
            original_roster_id = pick['original_owner']['roster_id']
            pick_label = pick['pick_label']
            username = roster_to_username.get(int(original_roster_id), f"roster_{original_roster_id}")
            mapping[(username, round_num)] = pick_label

    logger.info(f"  Built 2026 draft order map: {len(mapping)} pick positions")
    return mapping


def get_github_headers() -> Dict:
    """Get GitHub API headers with optional auth token."""
    headers = {'User-Agent': 'DynasuiiiiEnrichment/2.0'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers


def get_all_commits_since(since_date: datetime) -> Dict[str, str]:
    """Fetch Git commits for historical values."""
    url = (f"{GITHUB_API_BASE}/repos/{DYNASTYPROCESS_REPO}/commits"
           f"?path={DYNASTYPROCESS_VALUES_PATH}"
           f"&since={since_date.strftime('%Y-%m-%dT00:00:00Z')}"
           f"&per_page=100")
    try:
        commits = fetch_url(url, timeout=15, headers=get_github_headers())
        if commits and isinstance(commits, list):
            commit_map = {c['commit']['committer']['date'][:10]: c['sha'] for c in commits}
            logger.info(f"  Fetched {len(commit_map)} Git commits since {since_date.strftime('%Y-%m-%d')}")
            return commit_map
        return {}
    except Exception as e:
        logger.warning(f"  Failed to fetch Git commits: {e}")
        return {}


def get_values_from_commit(commit_sha: str, cache: Dict) -> Optional[pd.DataFrame]:
    """Fetch values CSV from a specific Git commit."""
    if commit_sha in cache:
        return cache[commit_sha]

    url = f"https://raw.githubusercontent.com/{DYNASTYPROCESS_REPO}/{commit_sha}/{DYNASTYPROCESS_VALUES_PATH}"
    try:
        df = fetch_csv_as_dataframe(url, timeout=15)
        cache[commit_sha] = df
        return df
    except Exception as e:
        logger.warning(f"  Failed to load values from commit {commit_sha[:7]}: {e}")
        return None


def get_pick_tier_value(pick_in_round: int) -> int:
    """Get tier value for 1st round picks based on position."""
    if pick_in_round <= 4:
        return TIER_VALUES['early_first']
    elif pick_in_round <= 8:
        return TIER_VALUES['mid_first']
    else:
        return TIER_VALUES['late_first']


def get_pick_tier_name(pick_in_round: int) -> str:
    """Get tier name for reporting."""
    if pick_in_round <= 4:
        return "Early"
    elif pick_in_round <= 8:
        return "Mid"
    else:
        return "Late"


def get_2025_pick_value(
    pick_name: str,
    origin_owner: str,
    trade_date: str,
    df_values: pd.DataFrame,
    is_current: bool,
    pick_lineage: Dict
) -> Tuple[float, str, Optional[Dict]]:
    """Get value for 2025 picks using exact Git pick values."""
    try:
        round_num = int(pick_name.split('Round')[1].strip())
    except:
        return 0, "Parse error", None

    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    key = (origin_owner, round_num)
    lineage_list = pick_lineage.get(key, [])

    if not lineage_list:
        return 0, "No lineage", None

    lineage = lineage_list[0]
    player = lineage['player']
    pick_in_round = lineage['pick_in_round']

    if trade_dt < DRAFT_COMPLETION_DATE:
        if is_current:
            matches = df_values[df_values['player'].str.contains(player, case=False, na=False)]
            if not matches.empty:
                value = float(matches.iloc[0]['value_2qb'])
                return value, f"Player:{player}", {'player': player, 'pick_position': f"{round_num}.{pick_in_round:02d}"}
            return 0, f"Player not found:{player}", None
        else:
            exact_pick = f"2025 Pick {round_num}.{pick_in_round:02d}"
            matches = df_values[df_values['player'].str.contains(exact_pick, case=False, na=False)]
            if not matches.empty:
                value = float(matches.iloc[0]['value_2qb'])
                return value, f"Git:{exact_pick}", {'pick_exact': exact_pick}
            if round_num == 1:
                tier_value = get_pick_tier_value(pick_in_round)
                tier_name = get_pick_tier_name(pick_in_round)
                return tier_value, f"Tier:{tier_name} 1st", {'tier': tier_name}
            ordinal = ROUND_ORDINALS.get(round_num, f'{round_num}th')
            search = f"2026 {ordinal}"
            matches = df_values[df_values['player'].str.contains(search, case=False, na=False)]
            if not matches.empty:
                return float(matches.iloc[0]['value_2qb']), f"Fallback:Generic {ordinal}", None
            return 0, "Not found", None
    else:
        matches = df_values[df_values['player'].str.contains(player, case=False, na=False)]
        if not matches.empty:
            value = float(matches.iloc[0]['value_2qb'])
            return value, f"Player:{player} (post-draft)", {'player': player}
        return 0, f"Player not found:{player}", None


def get_available_weeks(team_row: pd.DataFrame, round_name: str) -> List[int]:
    """Get all available week numbers for team/round combo."""
    available = []
    pattern = f'Week(\\d+)_2026_{round_name}'
    for col in team_row.columns:
        match = re.match(pattern, col)
        if match:
            available.append(int(match.group(1)))
    return sorted(available)


def get_best_week_column(team_row: pd.DataFrame, round_name: str, target_week: int) -> Tuple[str, int]:
    """Select best available week column for target week."""
    available_weeks = get_available_weeks(team_row, round_name)
    if not available_weeks:
        raise ValueError(f"No weekly columns found for {round_name}")

    if target_week in available_weeks:
        selected_week = target_week
    elif any(w <= target_week for w in available_weeks):
        selected_week = max(w for w in available_weeks if w <= target_week)
    else:
        selected_week = min(available_weeks)

    return f'Week{selected_week}_2026_{round_name}', selected_week


def get_latest_week_column(team_row: pd.DataFrame, round_name: str) -> Tuple[str, int]:
    """Get the latest available week column."""
    available_weeks = get_available_weeks(team_row, round_name)
    if not available_weeks:
        raise ValueError(f"No weekly columns found for {round_name}")
    latest = max(available_weeks)
    return f'Week{latest}_2026_{round_name}', latest


def get_2026_plus_pick_value(
    pick_name: str,
    origin_owner: str,
    trade_date: str,
    df_values: pd.DataFrame,
    draft_order_2026: Dict,
    pick_projections: pd.DataFrame
) -> Tuple[float, str, Optional[Dict]]:
    """Get value for 2026+ picks."""
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    parts = pick_name.split()
    if len(parts) >= 3 and parts[1] == 'Round':
        year = parts[0]
        round_num = int(parts[2])
    else:
        return 0, "Parse error", None

    # 2026 picks - use DynastyProcess EXACT values
    if '2026' in pick_name and origin_owner:
        key = (origin_owner, round_num)
        pick_label = draft_order_2026.get(key)

        if pick_label:
            exact_pick_name = f"2026 Pick {pick_label}"
            matches = df_values[df_values['player'] == exact_pick_name]
            if not matches.empty:
                value = float(matches.iloc[0]['value_2qb'])
                return value, f"DynastyProcess:{exact_pick_name}", {
                    'origin': origin_owner, 'round': round_num,
                    'pick_label': pick_label, 'dynastyprocess_name': exact_pick_name
                }

        # Fallback to team projection
        round_name = ROUND_ORDINALS.get(round_num)
        if round_name:
            team_row = pick_projections[pick_projections['Team'] == origin_owner]
            if not team_row.empty:
                try:
                    days = (trade_dt - SEASON_START_DATE).days
                    week = max(2, (days // 7) + 1)
                    col, sel_week = get_best_week_column(team_row, round_name, week)
                    value = float(team_row.iloc[0][col])
                    return value, f"Fallback:Projection:Week{sel_week}_{round_name}", {
                        'week': sel_week, 'origin': origin_owner, 'fallback': 'team_projection'
                    }
                except (ValueError, KeyError):
                    pass

    # 2027/2028+ picks
    if ('2027' in pick_name or '2028' in pick_name) and origin_owner:
        round_name = ROUND_ORDINALS.get(round_num)
        if round_name:
            team_row = pick_projections[pick_projections['Team'] == origin_owner]
            if not team_row.empty:
                try:
                    col, latest_week = get_latest_week_column(team_row, round_name)
                    proj_value = float(team_row.iloc[0][col])

                    if round_num == 1:
                        tier = "Early" if proj_value > 3000 else ("Mid" if proj_value > 1500 else "Late")
                    else:
                        tier = "Early" if proj_value > 400 else ("Mid" if proj_value > 200 else "Late")

                    dp_name = f"{year} {tier} {round_name}"
                    matches = df_values[df_values['player'] == dp_name]
                    if not matches.empty:
                        value = float(matches.iloc[0]['value_2qb'])
                        return value, f"DynastyProcess:{dp_name}", {
                            'origin': origin_owner, 'tier': tier, 'dynastyprocess_name': dp_name
                        }
                    return proj_value, f"Projection:Week{latest_week}_2026_{round_name}", {
                        'origin': origin_owner, 'fallback': 'projection_as_proxy'
                    }
                except (ValueError, KeyError):
                    pass

    # Final fallback - generic value
    ordinal = ROUND_ORDINALS.get(round_num, f'{round_num}th')
    search = f"{year} {ordinal}"
    matches = df_values[df_values['player'] == search]
    if not matches.empty:
        return float(matches.iloc[0]['value_2qb']), f"Fallback:Generic:{search}", None

    return 0, "Not found", None


def cache_asset_values(
    asset_transactions: List[Dict],
    dynamo_valuations: Optional[List[Dict]],
    pick_lineage: Dict,
    draft_order_2026: Dict,
    pick_projections: pd.DataFrame
) -> List[Dict]:
    """
    Cache values for all assets. Ported from pipeline/stage3_cache_values.py.
    Uses DynastyProcess current values (from DynamoDB or live fetch) and
    Git history for historical values.
    """
    # Load current values - try DynamoDB first, then live fetch
    df_current = None
    if dynamo_valuations:
        df_current = pd.DataFrame(dynamo_valuations)
        logger.info(f"  Using DynamoDB valuations: {len(df_current)} players")

    if df_current is None or df_current.empty or 'value_2qb' not in df_current.columns:
        logger.info("  Fetching current DynastyProcess values from GitHub...")
        try:
            df_current = fetch_csv_as_dataframe(DYNASTYPROCESS_CSV_URL, timeout=30)
            logger.info(f"  Loaded {len(df_current)} current values from DynastyProcess")
        except Exception as e:
            logger.error(f"  Failed to load DynastyProcess values: {e}")
            df_current = pd.DataFrame(columns=['player', 'value_2qb', 'pos'])

    # Ensure value_2qb is numeric
    if 'value_2qb' in df_current.columns:
        df_current['value_2qb'] = pd.to_numeric(df_current['value_2qb'], errors='coerce').fillna(0)

    # Get earliest trade date for Git history
    trade_dates = [a['trade_date'] for a in asset_transactions if a.get('trade_date')]
    if trade_dates:
        earliest_date = min(datetime.strptime(d, '%Y-%m-%d') for d in trade_dates)
    else:
        earliest_date = datetime.now() - timedelta(days=365)

    commit_cache = get_all_commits_since(earliest_date - timedelta(days=GIT_COMMIT_SEARCH_DAYS))
    git_df_cache = {}

    cached_values = []

    for idx, row in enumerate(asset_transactions):
        asset_name = row['asset_name']
        asset_type = row['asset_type']
        trade_date = row['trade_date']
        origin_owner = row.get('origin_owner')

        if (idx + 1) % 100 == 0:
            logger.info(f"  Processed {idx + 1}/{len(asset_transactions)} assets...")

        # FAAB
        if asset_type == 'faab':
            try:
                amount = int(asset_name.replace('$', '').replace(' FAAB', ''))
            except ValueError:
                amount = 0
            value = amount * FAAB_VALUE_PER_DOLLAR
            cached_values.append({
                **row,
                'value_at_trade': value,
                'value_current': value,
                'value_source_at_trade': 'FAAB',
                'value_source_current': 'FAAB',
            })
            continue

        # Find closest Git commit for historical value
        commit_sha = commit_cache.get(trade_date)
        if not commit_sha and trade_date:
            trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
            for delta in range(1, GIT_COMMIT_SEARCH_DAYS + 1):
                before = (trade_dt - timedelta(days=delta)).strftime('%Y-%m-%d')
                if before in commit_cache:
                    commit_sha = commit_cache[before]
                    break
            if not commit_sha:
                for delta in range(1, GIT_COMMIT_SEARCH_DAYS + 1):
                    after = (trade_dt + timedelta(days=delta)).strftime('%Y-%m-%d')
                    if after in commit_cache:
                        commit_sha = commit_cache[after]
                        break

        df_hist = get_values_from_commit(commit_sha, git_df_cache) if commit_sha else None

        if asset_type == 'pick':
            if '2025 Round' in asset_name and origin_owner:
                df_for_trade = df_hist if df_hist is not None else df_current
                value_at_trade, src_trade, _ = get_2025_pick_value(
                    asset_name, origin_owner, trade_date, df_for_trade, False, pick_lineage)
                value_current, src_current, meta = get_2025_pick_value(
                    asset_name, origin_owner, trade_date, df_current, True, pick_lineage)
            elif ('2026' in asset_name or '2027' in asset_name or '2028' in asset_name) and origin_owner:
                df_for_trade = df_hist if df_hist is not None else df_current
                value_at_trade, src_trade, _ = get_2026_plus_pick_value(
                    asset_name, origin_owner, trade_date, df_for_trade,
                    draft_order_2026, pick_projections)
                value_current, src_current, meta = get_2026_plus_pick_value(
                    asset_name, origin_owner, trade_date, df_current,
                    draft_order_2026, pick_projections)
            else:
                value_at_trade = 0
                value_current = 0
                src_trade = "Unknown pick"
                src_current = "Unknown pick"
                meta = None
        else:
            # Players
            if df_hist is not None and 'value_2qb' in df_hist.columns:
                matches = df_hist[df_hist['player'].str.contains(asset_name, case=False, na=False)]
                value_at_trade = float(matches.iloc[0]['value_2qb']) if not matches.empty else 0
                src_trade = f"Git:{commit_sha[:7]}" if not matches.empty else "Not found"
            else:
                value_at_trade = 0
                src_trade = "No Git commit"

            if 'value_2qb' in df_current.columns:
                matches = df_current[df_current['player'].str.contains(asset_name, case=False, na=False)]
                value_current = float(matches.iloc[0]['value_2qb']) if not matches.empty else 0
                src_current = "DynastyProcess" if not matches.empty else "Not found"
            else:
                value_current = 0
                src_current = "No values"
            meta = None

        cached_values.append({
            **row,
            'value_at_trade': value_at_trade,
            'value_current': value_current,
            'value_source_at_trade': src_trade,
            'value_source_current': src_current,
            'metadata': str(meta or ''),
        })

    logger.info(f"  Cached values for {len(cached_values)} assets")
    return cached_values


# ---------------------------------------------------------------------------
# STAGE 4: Analyze Trades
# Ported from pipeline/stage4_final.py
# ---------------------------------------------------------------------------
def analyze_2team_trades(cached_values: List[Dict]) -> List[Dict]:
    """Analyze 2-team trades by aggregating values."""
    two_team = [v for v in cached_values if v.get('trade_type') == '2-team']
    trades = {}

    for row in two_team:
        trade_id = row['trade_id']
        if trade_id not in trades:
            trades[trade_id] = {
                'trade_date': row['trade_date'],
                'season': row.get('season', ''),
                'roster_a': None,
                'roster_b': None,
                'team_a_assets': [],
                'team_a_value_then': 0,
                'team_a_value_now': 0,
                'team_b_assets': [],
                'team_b_value_then': 0,
                'team_b_value_now': 0,
            }

        trade = trades[trade_id]
        if trade['roster_a'] is None:
            trade['roster_a'] = row['receiving_team']
            trade['roster_b'] = row['giving_team']

        if row['receiving_team'] == trade['roster_a']:
            trade['team_a_assets'].append(row)
            trade['team_a_value_then'] += row['value_at_trade']
            trade['team_a_value_now'] += row['value_current']
        else:
            trade['team_b_assets'].append(row)
            trade['team_b_value_then'] += row['value_at_trade']
            trade['team_b_value_now'] += row['value_current']

    results = []
    for trade_id, t in trades.items():
        winner_then = t['roster_a'] if t['team_a_value_then'] > t['team_b_value_then'] else t['roster_b']
        winner_now = t['roster_a'] if t['team_a_value_now'] > t['team_b_value_now'] else t['roster_b']

        if t['team_a_value_then'] > t['team_b_value_then']:
            margin_swing = ((t['team_a_value_now'] - t['team_b_value_now']) -
                            (t['team_a_value_then'] - t['team_b_value_then']))
        else:
            margin_swing = ((t['team_b_value_now'] - t['team_a_value_now']) -
                            (t['team_b_value_then'] - t['team_a_value_then']))

        results.append({
            'trade_id': trade_id,
            'trade_date': t['trade_date'],
            'season': t['season'],
            'team_a': t['roster_a'],
            'team_a_assets': t['team_a_assets'],
            'team_a_value_then': t['team_a_value_then'],
            'team_a_value_now': t['team_a_value_now'],
            'team_a_value_change': t['team_a_value_now'] - t['team_a_value_then'],
            'team_b': t['roster_b'],
            'team_b_assets': t['team_b_assets'],
            'team_b_value_then': t['team_b_value_then'],
            'team_b_value_now': t['team_b_value_now'],
            'team_b_value_change': t['team_b_value_now'] - t['team_b_value_then'],
            'winner_at_trade': winner_then,
            'winner_current': winner_now,
            'margin_at_trade': abs(t['team_a_value_then'] - t['team_b_value_then']),
            'margin_current': abs(t['team_a_value_now'] - t['team_b_value_now']),
            'swing_winner': winner_now if margin_swing != 0 else 'Tie',
            'swing_margin': abs(margin_swing),
        })

    results.sort(key=lambda x: x['swing_margin'], reverse=True)
    logger.info(f"  Analyzed {len(results)} 2-team trades")
    return results


# ---------------------------------------------------------------------------
# Dashboard JSON Generators
# Matches the exact schemas of the static JSON files
# ---------------------------------------------------------------------------
def generate_enriched_trades(analyzed_trades: List[Dict], team_info_map: Dict) -> Dict:
    """Generate api-trades.json equivalent."""
    trades_list = []

    for t in analyzed_trades:
        # Build asset detail lists
        team_a_asset_names = [a['asset_name'] for a in t['team_a_assets']]
        team_b_asset_names = [a['asset_name'] for a in t['team_b_assets']]

        def build_asset_details(assets):
            details = []
            for a in assets:
                # Map internal asset_type to static JSON type names
                asset_type = a['asset_type']
                if asset_type == 'pick':
                    asset_type = 'draft_pick'
                detail = {
                    'name': a['asset_name'],
                    'type': asset_type,
                    'value_then': a['value_at_trade'],
                    'value_now': a['value_current'],
                }
                # Add pick_label from metadata if present
                meta_str = a.get('metadata', '')
                if meta_str and 'pick_label' in str(meta_str):
                    try:
                        import ast
                        meta = ast.literal_eval(meta_str)
                        if isinstance(meta, dict) and 'pick_label' in meta:
                            detail['pick_label'] = meta['pick_label']
                    except:
                        pass
                details.append(detail)
            return details

        trade_entry = {
            'tradeId': str(t['trade_id']),
            'transactionId': str(t['trade_id']),
            'tradeDate': t['trade_date'],
            'season': t.get('season', ''),
            'teamA': t['team_a'],
            'teamAReceived': team_a_asset_names,
            'teamAAssets': build_asset_details(t['team_a_assets']),
            'teamAValueThen': t['team_a_value_then'],
            'teamAValueNow': t['team_a_value_now'],
            'teamAValueChange': t['team_a_value_change'],
            'teamB': t['team_b'],
            'teamBReceived': team_b_asset_names,
            'teamBAssets': build_asset_details(t['team_b_assets']),
            'teamBValueThen': t['team_b_value_then'],
            'teamBValueNow': t['team_b_value_now'],
            'teamBValueChange': t['team_b_value_change'],
            'winnerAtTrade': t['winner_at_trade'],
            'winnerCurrent': t['winner_current'],
            'marginAtTrade': t['margin_at_trade'],
            'marginCurrent': t['margin_current'],
            'swingWinner': t['swing_winner'],
            'swingMargin': t['swing_margin'],
        }
        trades_list.append(trade_entry)

    # Build metadata matching api-trades.json schema
    trade_dates = [t['tradeDate'] for t in trades_list if t.get('tradeDate')]
    seasons_in_data = list(set(t['season'] for t in trades_list if t.get('season')))
    trades_by_season = {}
    for t in trades_list:
        s = t.get('season', 'unknown')
        trades_by_season[s] = trades_by_season.get(s, 0) + 1

    metadata = {
        'lastUpdated': datetime.now(timezone.utc).isoformat(),
        'totalTrades': len(trades_list),
        'dateRange': {
            'earliest': min(trade_dates) if trade_dates else '',
            'latest': max(trade_dates) if trade_dates else '',
        },
        'seasonsIncluded': sorted(seasons_in_data),
        'tradesBySeason': trades_by_season,
        'schemaVersion': '2.0.0',
        'source': 'enrichment_lambda',
    }

    return {
        'success': True,
        'data': {
            'metadata': metadata,
            'trades': trades_list
        }
    }


def generate_enriched_teams(
    analyzed_trades: List[Dict],
    team_mapping: List[Dict]
) -> Dict:
    """Generate api-teams.json equivalent."""
    # Calculate per-team stats from analyzed trades
    team_stats = {}

    for t in analyzed_trades:
        for side, team_key in [('a', t['team_a']), ('b', t['team_b'])]:
            if team_key not in team_stats:
                team_stats[team_key] = {
                    'trade_count': 0,
                    'wins': 0,
                    'total_margin': 0,
                    'total_value_gained': 0,
                }
            stats = team_stats[team_key]
            stats['trade_count'] += 1

            if side == 'a':
                my_value_now = t['team_a_value_now']
                opp_value_now = t['team_b_value_now']
                stats['total_value_gained'] += t['team_a_value_change']
            else:
                my_value_now = t['team_b_value_now']
                opp_value_now = t['team_a_value_now']
                stats['total_value_gained'] += t['team_b_value_change']

            if my_value_now > opp_value_now:
                stats['wins'] += 1

            stats['total_margin'] += abs(my_value_now - opp_value_now)

    teams_list = []
    for team in team_mapping:
        username = team.get('sleeper_username', '')
        roster_id = team.get('roster_id', 0)
        stats = team_stats.get(username, {
            'trade_count': 0, 'wins': 0, 'total_margin': 0, 'total_value_gained': 0
        })

        trade_count = stats['trade_count']
        win_rate = (stats['wins'] / trade_count * 100) if trade_count > 0 else 0
        avg_margin = stats['total_margin'] / trade_count if trade_count > 0 else 0

        teams_list.append({
            'rosterId': int(roster_id),
            'teamName': team.get('current_team_name', ''),
            'realName': team.get('real_name', ''),
            'sleeperUsername': username,
            'nickname': team.get('nickname', team.get('real_name', '')),
            'tradeCount': trade_count,
            'winRate': win_rate,
            'avgMargin': avg_margin,
            'totalValueGained': stats['total_value_gained'],
        })

    return {
        'success': True,
        'data': {
            'teams': teams_list,
            'summary': {
                'totalTeams': len(teams_list),
                'totalTrades': len(analyzed_trades),
                'seasonsIncluded': list(set(t.get('season', '') for t in analyzed_trades if t.get('season')))
            }
        }
    }


def generate_enriched_stats(
    analyzed_trades: List[Dict],
    teams_data: Dict
) -> Dict:
    """Generate api-stats-summary.json equivalent."""
    teams_list = teams_data.get('data', {}).get('teams', [])

    total_trades = len(analyzed_trades)
    total_value = sum(t['team_a_value_now'] + t['team_b_value_now'] for t in analyzed_trades)
    avg_margin = (sum(t['margin_current'] for t in analyzed_trades) / total_trades) if total_trades > 0 else 0
    blockbuster_count = sum(1 for t in analyzed_trades if t['margin_current'] > 2000)

    # Find most active, biggest winner
    most_active = max(teams_list, key=lambda x: x['tradeCount'], default={})
    biggest_winner = max(teams_list, key=lambda x: x['totalValueGained'], default={})

    trade_dates = [t['trade_date'] for t in analyzed_trades if t.get('trade_date')]
    date_range = {
        'earliest': min(trade_dates) if trade_dates else '',
        'latest': max(trade_dates) if trade_dates else '',
    }

    # Team rankings (3 sorted views)
    by_value = sorted(teams_list, key=lambda x: x['totalValueGained'], reverse=True)
    by_win_rate = sorted(teams_list, key=lambda x: x['winRate'], reverse=True)
    by_trade_count = sorted(teams_list, key=lambda x: x['tradeCount'], reverse=True)

    # Recent activity (last 10 trades)
    recent = []
    sorted_trades = sorted(analyzed_trades, key=lambda x: x.get('trade_date', ''), reverse=True)
    for t in sorted_trades[:10]:
        recent.append({
            'tradeId': str(t['trade_id']),
            'tradeDate': t['trade_date'],
            'teamA': t['team_a'],
            'teamB': t['team_b'],
            'marginCurrent': t['margin_current'],
            'winnerCurrent': t['winner_current'],
        })

    # Build multiSeasonData matching api-stats-summary.json schema
    seasons_in_data = list(set(t.get('season', 'unknown') for t in analyzed_trades))
    trades_by_season = {}
    for t in analyzed_trades:
        s = t.get('season', 'unknown')
        trades_by_season[s] = trades_by_season.get(s, 0) + 1

    return {
        'success': True,
        'data': {
            'overview': {
                'totalTrades': total_trades,
                'totalTradeValue': total_value,
                'avgTradeMargin': avg_margin,
                'mostActiveTrader': most_active.get('nickname', most_active.get('realName', '')),
                'biggestWinner': biggest_winner.get('nickname', biggest_winner.get('realName', '')),
                'blockbusterCount': blockbuster_count,
                'dateRange': date_range,
            },
            'teamRankings': {
                'byValueGained': by_value,
                'byWinRate': by_win_rate,
                'byTradeCount': by_trade_count,
            },
            'recentActivity': recent,
            'multiSeasonData': {
                'seasonsIncluded': sorted(seasons_in_data),
                'tradesBySeason': trades_by_season,
            },
        }
    }


def fetch_standings_from_sleeper(
    league_id: str,
    team_mapping: List[Dict],
    current_week: int = 14,
) -> Dict:
    """
    Fetch full standings from Sleeper API and build the complete
    {divisions, metadata} structure that matches api-standings.json.
    Ported from pipeline/scripts/fetch_standings.py.
    """
    REGULAR_SEASON_WEEKS = 14

    # ---- helpers ----
    def _fetch(url):
        req = urllib.request.Request(url, headers={'User-Agent': 'DynasuiiiiEnrichment/2.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def _median(scores):
        s = sorted(scores)
        n = len(s)
        if n == 0:
            return 0.0
        if n % 2 == 0:
            return (s[n // 2 - 1] + s[n // 2]) / 2
        return s[n // 2]

    # ---- fetch league info, rosters, users ----
    logger.info("  [standings] Fetching league info, rosters, users from Sleeper...")
    league_info = _fetch(f"{SLEEPER_API_BASE}/league/{league_id}")
    rosters = _fetch(f"{SLEEPER_API_BASE}/league/{league_id}/rosters")
    users = _fetch(f"{SLEEPER_API_BASE}/league/{league_id}/users")
    user_map = {u['user_id']: u for u in users}

    # Build roster_id -> team_name / owner_name from team_mapping
    team_info_lookup = {}
    for tm in team_mapping:
        rid = tm.get('roster_id')
        if rid is not None:
            team_info_lookup[int(rid)] = {
                'team_name': tm.get('current_team_name', ''),
                'real_name': tm.get('real_name', ''),
            }

    # Determine current_week from league_info if possible
    nfl_state_week = league_info.get('settings', {}).get('leg', current_week)
    # Use min of detected week and REGULAR_SEASON_WEEKS
    effective_week = min(nfl_state_week if nfl_state_week else current_week, REGULAR_SEASON_WEEKS)
    logger.info(f"  [standings] effective_week={effective_week}")

    # ---- build schedules ----
    division_lookup = {r['roster_id']: r.get('settings', {}).get('division', 0) for r in rosters}
    schedules = {r['roster_id']: [] for r in rosters}

    for week in range(1, REGULAR_SEASON_WEEKS + 1):
        try:
            matchups = _fetch(f"{SLEEPER_API_BASE}/league/{league_id}/matchups/{week}")
            scores = [m.get('points', 0) or 0 for m in matchups if m.get('points') is not None]
            median_score = _median(scores)
            matchup_lookup = {m['roster_id']: m for m in matchups}

            for m in matchups:
                rid = m['roster_id']
                mid = m.get('matchup_id')
                opp_id = None
                for m2 in matchups:
                    if m2.get('matchup_id') == mid and m2['roster_id'] != rid:
                        opp_id = m2['roster_id']
                        break

                pf = m.get('points', 0) or 0
                pa = matchup_lookup.get(opp_id, {}).get('points', 0) or 0 if opp_id else 0

                if week <= effective_week:
                    result = 'W' if pf > pa else ('L' if pf < pa else 'T')
                    beat_median = pf > median_score
                else:
                    result = 'UPCOMING'
                    beat_median = None

                opp_info = team_info_lookup.get(opp_id, {})
                opp_name = opp_info.get('team_name', f'Team {opp_id}') if opp_id else 'BYE'

                schedules[rid].append({
                    'week': week,
                    'opponent_id': opp_id,
                    'points_for': pf,
                    'points_against': pa,
                    'result': result,
                    'beat_median': beat_median,
                    'median_score': median_score,
                    'opponent_name': opp_name,
                })
        except Exception as e:
            logger.warning(f"  [standings] Week {week} fetch failed: {e}")
            for rid in schedules:
                schedules[rid].append({
                    'week': week,
                    'opponent_id': None,
                    'points_for': 0,
                    'points_against': 0,
                    'result': 'UPCOMING',
                    'beat_median': None,
                    'median_score': 0,
                    'opponent_name': 'BYE',
                })

    # ---- calculate records ----
    records = {}
    for rid, schedule in schedules.items():
        wins = losses = ties = 0
        median_wins = median_losses = 0
        div_wins = div_losses = div_ties = 0
        pf_total = pa_total = 0.0

        for g in schedule:
            if g['result'] == 'UPCOMING':
                continue
            if g['result'] == 'W':
                wins += 1
            elif g['result'] == 'L':
                losses += 1
            else:
                ties += 1
            if g['beat_median'] is True:
                median_wins += 1
            elif g['beat_median'] is False:
                median_losses += 1
            opp_id = g['opponent_id']
            if opp_id and division_lookup.get(rid) == division_lookup.get(opp_id):
                if g['result'] == 'W':
                    div_wins += 1
                elif g['result'] == 'L':
                    div_losses += 1
                else:
                    div_ties += 1
            pf_total += g['points_for']
            pa_total += g['points_against']

        combined_wins = wins + median_wins
        combined_losses = losses + median_losses

        records[rid] = {
            'record': {'wins': combined_wins, 'losses': combined_losses, 'ties': ties},
            'matchup_record': {'wins': wins, 'losses': losses, 'ties': ties},
            'median_record': {'wins': median_wins, 'losses': median_losses},
            'division_record': {'wins': div_wins, 'losses': div_losses, 'ties': div_ties},
            'points_for': round(pf_total, 2),
            'points_against': round(pa_total, 2),
        }

    # ---- tiebreaker sort ----
    def _compare(r1, r2):
        rid1, rid2 = r1['roster_id'], r2['roster_id']
        rec1, rec2 = records[rid1], records[rid2]
        # 1. combined wins
        if rec1['record']['wins'] != rec2['record']['wins']:
            return -1 if rec1['record']['wins'] > rec2['record']['wins'] else 1
        # 2. H2H
        h2h1 = sum(1 for g in schedules[rid1] if g['opponent_id'] == rid2 and g['result'] == 'W')
        h2h2 = sum(1 for g in schedules[rid2] if g['opponent_id'] == rid1 and g['result'] == 'W')
        if h2h1 != h2h2:
            return -1 if h2h1 > h2h2 else 1
        # 3. division record
        if rec1['division_record']['wins'] != rec2['division_record']['wins']:
            return -1 if rec1['division_record']['wins'] > rec2['division_record']['wins'] else 1
        # 4. PF
        if abs(rec1['points_for'] - rec2['points_for']) > 0.01:
            return -1 if rec1['points_for'] > rec2['points_for'] else 1
        # 5. PA (lower better)
        if abs(rec1['points_against'] - rec2['points_against']) > 0.01:
            return -1 if rec1['points_against'] < rec2['points_against'] else 1
        return 0

    # ---- organize by division ----
    metadata = league_info.get('metadata', {})
    division_names = {
        1: metadata.get('division_1', 'Division 1'),
        2: metadata.get('division_2', 'Division 2'),
        3: metadata.get('division_3', 'Division 3'),
    }

    divisions_map = {}
    for roster in rosters:
        div_id = roster.get('settings', {}).get('division', 0)
        divisions_map.setdefault(div_id, []).append(roster)

    division_data = []
    for div_id in sorted(divisions_map.keys()):
        div_rosters = divisions_map[div_id]
        div_rosters.sort(key=cmp_to_key(_compare))

        teams = []
        for rank, roster in enumerate(div_rosters, 1):
            rid = roster['roster_id']
            owner_id = roster.get('owner_id')
            user = user_map.get(owner_id, {})
            tinfo = team_info_lookup.get(rid, {})
            team_name = tinfo.get('team_name') or user.get('display_name', f'Team {rid}')
            owner_name = tinfo.get('real_name') or user.get('display_name', 'Unknown')

            teams.append({
                'roster_id': rid,
                'team_name': team_name,
                'owner_name': owner_name,
                'rank': rank,
                **records[rid],
                'schedule': schedules[rid],
            })

        division_data.append({
            'division_id': div_id,
            'division_name': division_names.get(div_id, f'Division {div_id}'),
            'teams': teams,
        })

    logger.info(f"  [standings] Built {len(division_data)} divisions, "
                f"{sum(len(d['teams']) for d in division_data)} teams")

    return {
        'divisions': division_data,
        'metadata': {
            'current_week': effective_week,
            'total_weeks': REGULAR_SEASON_WEEKS,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'season': 2025,
        },
    }


def read_existing_enriched_standings() -> Optional[Dict]:
    """Read previously-written enriched standings from DynamoDB, if any."""
    try:
        item = get_item('SEASON#season_3', 'ENRICHED_STANDINGS#LATEST')
        if item and item.get('Data'):
            data = json.loads(item['Data']) if isinstance(item['Data'], str) else item['Data']
            if isinstance(data, dict) and 'divisions' in data and data['divisions']:
                logger.info("  [standings] Found existing enriched standings in DynamoDB, reusing")
                return data
    except Exception as e:
        logger.warning(f"  [standings] Failed to read existing enriched standings: {e}")
    return None


def generate_enriched_standings(
    standings_data: Optional[Dict],
    league_id: str,
    team_mapping: List[Dict],
) -> Dict:
    """
    Generate api-standings.json equivalent.
    Fetches full standings from Sleeper API to build the complete
    {divisions: Division[], metadata: StandingsMetadata} structure.

    Fallback chain:
    1. Fetch from Sleeper API (works during active season)
    2. If API returns empty matchups (offseason/pre_draft), reuse existing
       enriched standings from DynamoDB
    3. Return schema-compatible empty structure
    """
    try:
        result = fetch_standings_from_sleeper(league_id, team_mapping)
        # Check if the result has actual data (non-empty schedules)
        has_data = False
        for div in result.get('divisions', []):
            for team in div.get('teams', []):
                if team.get('schedule') and any(g.get('result') != 'UPCOMING' for g in team['schedule']):
                    has_data = True
                    break
            if has_data:
                break

        if has_data:
            return result

        logger.info("  [standings] Sleeper API returned no scored matchups (offseason?), checking existing data...")
    except Exception as e:
        logger.error(f"  [standings] Failed to build standings from Sleeper API: {e}")

    # Fallback: reuse existing enriched standings from DynamoDB
    existing = read_existing_enriched_standings()
    if existing:
        return existing

    # Final fallback: empty but schema-compatible
    return {
        'divisions': [],
        'metadata': {
            'current_week': 0,
            'total_weeks': 14,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'season': 2025,
        },
    }


def read_existing_enriched_playoff() -> Optional[Dict]:
    """Read previously-written enriched playoff data from DynamoDB, if any."""
    try:
        item = get_item('SEASON#season_3', 'ENRICHED_PLAYOFF#LATEST')
        if item and item.get('Data'):
            data = json.loads(item['Data']) if isinstance(item['Data'], str) else item['Data']
            if isinstance(data, dict) and data.get('results'):
                logger.info("  [playoff] Found existing enriched playoff data in DynamoDB, reusing")
                return data
    except Exception as e:
        logger.warning(f"  [playoff] Failed to read existing enriched playoff: {e}")
    return None


def generate_enriched_playoff(enriched_standings: Dict) -> Dict:
    """
    Generate api-playoff-scenarios.json equivalent.

    When the season is complete (week >= 14) all playoff positions are
    deterministic so we produce a single "simulation" with 100% probabilities
    derived directly from the standings.  This avoids needing a full Monte
    Carlo engine in the Lambda while still matching the frontend's expected
    PlayoffScenariosData schema.
    """
    divisions = enriched_standings.get('divisions', [])
    meta = enriched_standings.get('metadata', {})
    current_week = meta.get('current_week', 0)

    if not divisions:
        # Try to reuse existing enriched playoff data from DynamoDB
        existing = read_existing_enriched_playoff()
        if existing:
            return existing
        return {
            'metadata': {
                'current_week': current_week,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'season': 2025,
            },
            'num_simulations': 0,
            'results': [],
        }

    # Collect all teams with their division info
    all_teams = []
    for div in divisions:
        div_name = div.get('division_name', '')
        for team in div.get('teams', []):
            record = team.get('record', {})
            wins = record.get('wins', 0)
            losses = record.get('losses', 0)
            all_teams.append({
                'team_name': team.get('team_name', ''),
                'division': div_name,
                'roster_id': team.get('roster_id'),
                'rank_in_division': team.get('rank', 99),
                'wins': wins,
                'losses': losses,
                'points_for': team.get('points_for', 0),
            })

    # Determine division winners (rank 1 in each division)
    division_winners = [t for t in all_teams if t['rank_in_division'] == 1]
    # Sort division winners by record for seeding (best record = seed 1)
    division_winners.sort(key=lambda t: (-t['wins'], -t['points_for']))

    # Wild cards: best non-division-winners
    non_winners = [t for t in all_teams if t['rank_in_division'] != 1]
    non_winners.sort(key=lambda t: (-t['wins'], -t['points_for']))

    NUM_PLAYOFF_SPOTS = 6
    NUM_BYE_SPOTS = 2  # top 2 seeds get byes

    # Build seeded playoff teams
    seeded = []
    for t in division_winners:
        seeded.append(t)
    for t in non_winners:
        if len(seeded) >= NUM_PLAYOFF_SPOTS:
            break
        seeded.append(t)

    # Assign seeds
    seed_map = {}  # roster_id -> seed
    for idx, t in enumerate(seeded):
        seed_map[t['roster_id']] = idx + 1

    # Build results
    results = []
    playoff_roster_ids = set(seed_map.keys())
    num_sims = 20000 if current_week >= 14 else 0

    for t in all_teams:
        rid = t['roster_id']
        seed = seed_map.get(rid)
        in_playoffs = rid in playoff_roster_ids
        is_div_winner = t['rank_in_division'] == 1
        has_bye = seed is not None and seed <= NUM_BYE_SPOTS

        result = {
            'team_name': t['team_name'],
            'division': t['division'],
            'current_record': f"{t['wins']}-{t['losses']}",
            'playoff_probability': 100.0 if in_playoffs else 0.0,
            'division_winner_probability': 100.0 if is_div_winner else 0.0,
            'bye_week_probability': 100.0 if has_bye else 0.0,
            'seed_probabilities': {str(seed): 100.0} if seed else {},
            'playoff_count': num_sims if in_playoffs else 0,
            'division_winner_count': num_sims if is_div_winner else 0,
            'bye_week_count': num_sims if has_bye else 0,
            'clinched_playoff': in_playoffs and current_week >= 14,
            'clinched_division': is_div_winner and current_week >= 14,
            'clinched_bye': has_bye and current_week >= 14,
            'eliminated': not in_playoffs and current_week >= 14,
            'current_seed': seed,
            'most_likely_seed': seed,
            'projected_seed': seed,
        }
        results.append(result)

    return {
        'metadata': {
            'current_week': current_week,
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'season': 2025,
        },
        'num_simulations': num_sims,
        'results': results,
    }


def generate_enriched_draft_order(draft_order_data: Optional[Dict]) -> Dict:
    """Generate api-draft-order.json equivalent. Pass through from DynamoDB."""
    if draft_order_data:
        # Add timestamp
        draft_order_data['last_updated'] = datetime.now(timezone.utc).isoformat() + 'Z'
        return draft_order_data
    return {
        'season': 2025,
        'draft_year': 2026,
        'through_week': 0,
        'determination_level': 'unknown',
        'summary': {'total_picks': 0, 'locked_picks': 0, 'uncertain_picks': 0},
        'draft_order': {},
    }


def generate_enriched_waivers(
    all_waivers: List[Dict],
    roster_to_username: Dict[int, str],
    players: Dict
) -> Dict:
    """Generate waiver-wire-page.json equivalent."""

    def get_player_name(player_id):
        if not player_id or player_id == 'None':
            return 'Unknown Player'
        info = players.get(str(player_id), {})
        if isinstance(info, dict):
            first = info.get('first_name', '')
            last = info.get('last_name', '')
            if first and last:
                return f"{first} {last}"
            return first or last or f"Player {player_id}"
        return f"Player {player_id}"

    # Process raw waiver transactions
    all_transactions = []
    manager_stats = defaultdict(lambda: {
        'total_claims': 0, 'successful_claims': 0,
        'total_bid': 0, 'max_bid': 0, 'bids': [],
        'adds': 0, 'drops': 0
    })

    for raw_txn in all_waivers:
        txn_id = raw_txn.get('transaction_id', '')
        txn_type = raw_txn.get('type', 'free_agent')
        status = raw_txn.get('status', 'complete')
        created_ts = raw_txn.get('created', 0)
        status_updated_ts = raw_txn.get('status_updated', created_ts)
        leg = raw_txn.get('leg', 1)
        season = raw_txn.get('season', 'unknown')

        created_dt = datetime.fromtimestamp(created_ts / 1000).strftime('%Y-%m-%d %H:%M:%S') if created_ts else None
        status_updated_dt = datetime.fromtimestamp(status_updated_ts / 1000).strftime('%Y-%m-%d %H:%M:%S') if status_updated_ts else created_dt

        settings = raw_txn.get('settings', {}) or {}
        waiver_bid = settings.get('waiver_bid', 0) or 0
        seq = settings.get('seq', None)
        priority = settings.get('waiver_priority', None)

        # Derive year from season string (e.g. 'season_3' -> 2026, 'season_2' -> 2025)
        season_num = int(season.split('_')[1]) if '_' in season else 0
        year = 2023 + season_num  # season_2=2025, season_3=2026

        adds = raw_txn.get('adds') or {}
        drops = raw_txn.get('drops') or {}
        roster_ids = raw_txn.get('roster_ids', [])

        for player_id, to_roster in adds.items():
            team_name = roster_to_username.get(int(to_roster), f"Team {to_roster}")
            player_name = get_player_name(player_id)

            all_transactions.append({
                'transaction_id': str(txn_id),
                'type': txn_type,
                'action': 'add',
                'status': status,
                'team_name': team_name,
                'roster_id': int(to_roster),
                'player_name': player_name,
                'player_id': str(player_id),
                'player_value': None,
                'waiver_bid': waiver_bid,
                'week': leg,
                'created_date': created_dt,
                'status_updated_date': status_updated_dt,
                'notes': '',
                'sequence': seq,
                'priority': priority,
                'season': season,
                'year': year,
            })

            # Track manager stats
            ms = manager_stats[int(to_roster)]
            ms['adds'] += 1
            if txn_type == 'waiver':
                ms['total_claims'] += 1
                if status == 'complete':
                    ms['successful_claims'] += 1
                ms['total_bid'] += waiver_bid
                ms['max_bid'] = max(ms['max_bid'], waiver_bid)
                ms['bids'].append(waiver_bid)

        for player_id, from_roster in drops.items():
            team_name = roster_to_username.get(int(from_roster), f"Team {from_roster}")
            player_name = get_player_name(player_id)

            all_transactions.append({
                'transaction_id': str(txn_id),
                'type': txn_type,
                'action': 'drop',
                'status': status,
                'team_name': team_name,
                'roster_id': int(from_roster),
                'player_name': player_name,
                'player_id': str(player_id),
                'player_value': None,
                'waiver_bid': 0,
                'week': leg,
                'created_date': created_dt,
                'status_updated_date': status_updated_dt,
                'notes': '',
                'sequence': seq,
                'priority': priority,
                'season': season,
                'year': year,
            })

            manager_stats[int(from_roster)]['drops'] += 1

    # Sort by date descending
    all_transactions.sort(key=lambda x: x.get('created_date', '') or '', reverse=True)

    # Build manager activity
    manager_activity = []
    for roster_id, stats in manager_stats.items():
        team_name = roster_to_username.get(roster_id, f"Team {roster_id}")
        total_claims = stats['total_claims']
        success_rate = (stats['successful_claims'] / total_claims * 100) if total_claims > 0 else 0
        avg_bid = (stats['total_bid'] / total_claims) if total_claims > 0 else 0

        manager_activity.append({
            'roster_id': roster_id,
            'team_name': team_name,
            'total_claims': total_claims,
            'successful_claims': stats['successful_claims'],
            'success_rate': round(success_rate, 1),
            'total_bid': stats['total_bid'],
            'avg_bid': round(avg_bid, 1),
            'max_bid': stats['max_bid'],
        })

    # Build churn metrics per manager
    churn_metrics = []
    for roster_id, stats in manager_stats.items():
        team_name = roster_to_username.get(roster_id, f"Team {roster_id}")
        total_moves = stats['adds'] + stats['drops']
        # churn_rate as percentage of roster size (assume ~35 roster spots)
        churn_rate = round(total_moves / 35 * 100, 2) if total_moves > 0 else 0

        if churn_rate > 25:
            style = 'extreme'
        elif churn_rate > 12:
            style = 'active'
        elif churn_rate > 5:
            style = 'moderate'
        else:
            style = 'passive'

        churn_metrics.append({
            'roster_id': roster_id,
            'team_name': team_name,
            'total_adds': stats['adds'],
            'total_drops': stats['drops'],
            'overall_churn_rate': churn_rate,
            'management_style': style,
        })

    # Build bidding patterns
    all_bids = []
    for stats in manager_stats.values():
        all_bids.extend(stats['bids'])

    # Distribution buckets
    distribution = {}
    for bid in all_bids:
        if bid == 0:
            bucket = '0'
        elif bid <= 5:
            bucket = '1-5'
        elif bid <= 10:
            bucket = '6-10'
        elif bid <= 25:
            bucket = '11-25'
        elif bid <= 50:
            bucket = '26-50'
        else:
            bucket = '51+'
        distribution[bucket] = distribution.get(bucket, 0) + 1

    # Highest bids
    waiver_adds = [t for t in all_transactions if t['type'] == 'waiver' and t['action'] == 'add' and t['waiver_bid'] > 0]
    waiver_adds_sorted = sorted(waiver_adds, key=lambda x: x['waiver_bid'], reverse=True)
    highest_bids = []
    for t in waiver_adds_sorted[:25]:
        highest_bids.append({
            'player_id': t['player_id'],
            'player_name': t['player_name'],
            'waiver_bid': t['waiver_bid'],
            'team_name': t['team_name'],
            'status': t['status'],
        })

    # Zero-bid success rate
    zero_bids = [t for t in all_transactions if t['type'] == 'waiver' and t['waiver_bid'] == 0]
    zero_bid_success = [t for t in zero_bids if t['status'] == 'complete']
    zero_bid_success_rate = round(len(zero_bid_success) / len(zero_bids) * 100, 1) if zero_bids else 0

    # Build weekly activity
    weekly_activity_map = defaultdict(lambda: {'waiver': 0, 'free_agent': 0})
    for t in all_transactions:
        w = t.get('week', 0)
        weekly_activity_map[w][t['type']] = weekly_activity_map[w].get(t['type'], 0) + 1
    weekly_activity = []
    for w in sorted(weekly_activity_map.keys()):
        counts = weekly_activity_map[w]
        weekly_activity.append({
            'week': w,
            'waiver_count': counts.get('waiver', 0),
            'free_agent_count': counts.get('free_agent', 0),
            'total': counts.get('waiver', 0) + counts.get('free_agent', 0),
        })

    # Build contested players (players with multiple claims)
    player_claims = defaultdict(list)
    for t in all_transactions:
        if t['type'] == 'waiver' and t['action'] == 'add':
            player_claims[t['player_id']].append(t)
    contested_players = []
    for pid, claims in player_claims.items():
        if len(claims) >= 2:
            contested_players.append({
                'player_id': pid,
                'player_name': claims[0]['player_name'],
                'num_claims': len(claims),
                'winning_team': next((c['team_name'] for c in claims if c['status'] == 'complete'), None),
                'highest_bid': max(c['waiver_bid'] for c in claims),
            })
    contested_players.sort(key=lambda x: x['num_claims'], reverse=True)

    # Summary statistics
    waiver_txns = [t for t in all_transactions if t['type'] == 'waiver']
    fa_txns = [t for t in all_transactions if t['type'] == 'free_agent']
    successful = [t for t in waiver_txns if t['status'] == 'complete']
    total_bids = sum(t['waiver_bid'] for t in waiver_txns)

    return {
        'metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_waiver_transactions': len(waiver_txns),
            'total_free_agent_transactions': len(fa_txns),
            'successful_waivers': len(successful),
            'failed_waivers': len(waiver_txns) - len(successful),
            'success_rate': round(len(successful) / len(waiver_txns) * 100, 1) if waiver_txns else 0,
            'total_waiver_bids': total_bids,
            'average_waiver_bid': round(total_bids / len(waiver_txns), 1) if waiver_txns else 0,
            'source': 'enrichment_lambda',
        },
        'manager_activity': manager_activity,
        'churn_metrics': churn_metrics,
        'all_transactions': all_transactions,
        'recent_activity': all_transactions[:50],
        'weekly_activity': weekly_activity,
        'contested_players': contested_players,
        'bidding_patterns': {
            'distribution': distribution,
            'highest_bids': highest_bids,
            'zero_bid_success_rate': zero_bid_success_rate,
        },
        # These require player stats data not available in enrichment lambda.
        # Match static file: null when not computed.
        'efficiency_metrics': None,
        'hit_rate_metrics': None,
        'timing_metrics': None,
    }


# ---------------------------------------------------------------------------
# MAIN HANDLER
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """
    Enrichment Lambda handler - Task 2.1
    Reads raw data from DynamoDB, runs pipeline enrichment, writes 7 enriched items.
    """
    start_time = time.time()
    logger.info("=" * 80)
    logger.info("ENRICHMENT LAMBDA STARTED")
    logger.info(f"Table: {TABLE_NAME}")
    logger.info(f"Event: {json.dumps(event)}")
    logger.info("=" * 80)

    # Determine which seasons to process (default: all for enrichment)
    requested_seasons = event.get('seasons', list(SEASONS.keys()))

    results = {
        'status': 'success',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'seasons_processed': [],
        'enriched_items_written': [],
        'errors': [],
    }

    try:
        # ===================================================================
        # STEP 1: Read reference data (shared across seasons)
        # ===================================================================
        logger.info("STEP 1: Reading reference data...")
        team_mapping = read_team_mapping()
        if not team_mapping:
            raise RuntimeError("No team identity mapping found in DynamoDB. Run ingestion first.")
        logger.info(f"  Team mapping: {len(team_mapping)} teams")

        roster_to_username = build_roster_to_username(team_mapping)
        team_info_map = build_team_info_map(team_mapping)

        pick_origins = read_pick_origins()
        logger.info(f"  Pick origins: {len(pick_origins)} picks")

        draft_order_data = read_draft_order_2026()
        logger.info(f"  Draft order 2026: {'loaded' if draft_order_data else 'not found'}")

        draft_order_2026_map = build_draft_order_2026_map(draft_order_data, roster_to_username)

        # Load bundled CSVs
        draft_results, pick_projections = load_bundled_csvs()
        pick_lineage = build_pick_lineage(draft_results, pick_origins)

        # Fetch Sleeper players (shared across all seasons)
        players = fetch_sleeper_players()

        # ===================================================================
        # STEP 2: Read and process each season
        # ===================================================================
        all_trades_all_seasons = []
        all_waivers_all_seasons = []
        all_cached_values = []
        all_analyzed_trades = []
        standings_data = None

        for season_id in requested_seasons:
            season_info = SEASONS.get(season_id)
            if not season_info:
                logger.warning(f"Unknown season: {season_id}, skipping")
                continue

            logger.info(f"\n{'='*60}")
            logger.info(f"PROCESSING {season_id} ({season_info['description']})")
            logger.info(f"{'='*60}")

            # Read raw trades
            raw_trades = read_raw_trades(season_id)
            all_trades_all_seasons.extend(raw_trades)

            # Read raw waivers
            raw_waivers = read_raw_waivers(season_id)
            all_waivers_all_seasons.extend(raw_waivers)

            # Read standings (use active season's standings)
            if season_info['status'] == 'active':
                standings_data = read_standings(season_id)
                logger.info(f"  Standings: {'loaded' if standings_data else 'not found'}")

            # Read valuations
            valuations = read_valuations(season_id)
            logger.info(f"  Valuations: {len(valuations) if valuations else 0} players")

            # STAGE 2: Extract assets
            logger.info(f"  STAGE 2: Extracting assets from {len(raw_trades)} trades...")
            asset_txns = extract_assets_from_trades(raw_trades, roster_to_username, players)

            # STAGE 3: Cache values
            logger.info(f"  STAGE 3: Caching values for {len(asset_txns)} assets...")
            cached = cache_asset_values(
                asset_txns, valuations, pick_lineage,
                draft_order_2026_map, pick_projections
            )
            all_cached_values.extend(cached)

            # STAGE 4: Analyze trades
            logger.info(f"  STAGE 4: Analyzing trades...")
            analyzed = analyze_2team_trades(cached)
            all_analyzed_trades.extend(analyzed)

            results['seasons_processed'].append(season_id)

        # ===================================================================
        # STEP 3: Generate enriched outputs (all seasons combined)
        # ===================================================================
        logger.info(f"\n{'='*60}")
        logger.info(f"GENERATING ENRICHED OUTPUTS")
        logger.info(f"  Total trades analyzed: {len(all_analyzed_trades)}")
        logger.info(f"  Total waivers: {len(all_waivers_all_seasons)}")
        logger.info(f"{'='*60}")

        # Sort analyzed trades by swing margin descending (matching existing output)
        all_analyzed_trades.sort(key=lambda x: x['swing_margin'], reverse=True)

        # Generate all 7 enriched items
        enriched_trades = generate_enriched_trades(all_analyzed_trades, team_info_map)
        enriched_teams = generate_enriched_teams(all_analyzed_trades, team_mapping)
        enriched_stats = generate_enriched_stats(all_analyzed_trades, enriched_teams)
        # Use active season's league_id for live Sleeper API standings
        active_league_id = SEASONS.get('season_3', {}).get('league_id', '')
        enriched_standings = generate_enriched_standings(standings_data, active_league_id, team_mapping)
        enriched_playoff = generate_enriched_playoff(enriched_standings)
        enriched_draft_order = generate_enriched_draft_order(draft_order_data)
        enriched_waivers = generate_enriched_waivers(
            all_waivers_all_seasons, roster_to_username, players)

        logger.info(f"  Enriched trades: {len(enriched_trades['data']['trades'])} trades")
        logger.info(f"  Enriched teams: {len(enriched_teams['data']['teams'])} teams")
        logger.info(f"  Enriched waivers: {len(enriched_waivers.get('all_transactions', []))} transactions")

        # ===================================================================
        # STEP 4: Write enriched items to DynamoDB
        # ===================================================================
        logger.info("\nSTEP 4: Writing enriched items to DynamoDB...")

        # Use active season PK for enriched data
        active_season = 'season_3'
        pk = f'SEASON#{active_season}'
        timestamp = datetime.now(timezone.utc).isoformat()

        items_to_write = [
            ('ENRICHED_TRADES#LATEST', enriched_trades),
            ('ENRICHED_TEAMS#LATEST', enriched_teams),
            ('ENRICHED_STATS#LATEST', enriched_stats),
            ('ENRICHED_STANDINGS#LATEST', enriched_standings),
            ('ENRICHED_PLAYOFF#LATEST', enriched_playoff),
            ('ENRICHED_DRAFTORDER#LATEST', enriched_draft_order),
            ('ENRICHED_WAIVERS#LATEST', enriched_waivers),
        ]

        for sk, data in items_to_write:
            try:
                cleaned = clean_nan(data)
                json_str = json.dumps(cleaned, default=str)
                size_kb = len(json_str) / 1024

                logger.info(f"  Writing {sk} ({size_kb:.1f} KB)...")

                # DynamoDB has a 400KB item size limit.
                # JSON-serialize the data attribute to stay within limits.
                throttle_safe_put_item({
                    'PK': pk,
                    'SK': sk,
                    'EntityType': 'enriched_data',
                    'Season': active_season,
                    'Data': json_str,
                    'DataSizeKB': int(size_kb),
                    'UpdatedAt': timestamp,
                })

                results['enriched_items_written'].append(sk)
                logger.info(f"    Written successfully")

                # Pause between writes to stay within 25 WCU
                time.sleep(1)

            except Exception as e:
                error_msg = f"Failed to write {sk}: {str(e)}"
                logger.error(f"    {error_msg}")
                results['errors'].append(error_msg)

        # ===================================================================
        # STEP 5: Summary
        # ===================================================================
        duration = time.time() - start_time
        results['duration_seconds'] = round(duration, 1)
        results['trade_count'] = len(all_analyzed_trades)
        results['waiver_count'] = len(all_waivers_all_seasons)

        logger.info(f"\n{'='*80}")
        logger.info(f"ENRICHMENT COMPLETE")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Seasons: {results['seasons_processed']}")
        logger.info(f"  Items written: {len(results['enriched_items_written'])}/7")
        logger.info(f"  Errors: {len(results['errors'])}")
        logger.info(f"{'='*80}")

    except Exception as e:
        duration = time.time() - start_time
        results['status'] = 'error'
        results['error'] = str(e)
        results['duration_seconds'] = round(duration, 1)
        logger.error(f"Enrichment failed after {duration:.1f}s: {e}", exc_info=True)

    status_code = 200 if results['status'] == 'success' and not results['errors'] else 500
    return {
        'statusCode': status_code,
        'body': json.dumps(results, default=str)
    }
