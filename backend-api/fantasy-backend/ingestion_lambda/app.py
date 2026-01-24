import json
import urllib.request
import urllib.error
import boto3
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'fantasy-dashboard-data')
table = dynamodb.Table(table_name)

SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

# Season configuration (embedded - matches pipeline/config/seasons.yaml)
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

PIPELINE_CONFIG = {
    'active_seasons': ['season_3'],
    'static_seasons': ['season_2']
}


def lambda_handler(event, context):
    """
    Multi-Season Ingestion Lambda
    
    Regular runs (hourly): Only update ACTIVE seasons
    Backfill mode: Update ALL seasons (including static/historical)
    
    Event params:
    - backfill: true/false (default: false)
    - seasons: ['season_2', 'season_3'] (default: active only)
    """
    
    print(f"Starting ingestion at {datetime.now(timezone.utc).isoformat()}")
    
    # Check if this is a backfill request
    backfill_mode = event.get('backfill', False)
    requested_seasons = event.get('seasons', None)
    
    # Determine which seasons to process
    if requested_seasons:
        seasons_to_process = requested_seasons
        mode = "CUSTOM"
    elif backfill_mode:
        seasons_to_process = list(SEASONS.keys())
        mode = "BACKFILL (all seasons)"
    else:
        seasons_to_process = PIPELINE_CONFIG.get('active_seasons', ['season_3'])
        mode = "INCREMENTAL (active only)"
    
    print(f"Mode: {mode}")
    print(f"Processing seasons: {seasons_to_process}")
    
    results = {
        'mode': mode,
        'seasons_processed': [],
        'total_trades': 0,
        'errors': []
    }
    
    # Process each season
    for season_id in seasons_to_process:
        try:
            season_info = SEASONS.get(season_id)
            if not season_info:
                print(f"⚠️ Season {season_id} not found in config, skipping")
                continue
            
            print(f"\n=== Processing {season_id} ===")
            season_result = ingest_season(season_id, season_info)
            results['seasons_processed'].append(season_id)
            results['total_trades'] += season_result['trades_ingested']
            
        except Exception as e:
            error_msg = f"Failed to process {season_id}: {str(e)}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
    
    print(f"\n✅ Ingestion complete: {json.dumps(results, default=str)}")
    return {
        'statusCode': 200 if not results['errors'] else 500,
        'body': json.dumps(results, default=str)
    }


def ingest_season(season_id: str, season_info: Dict) -> Dict:
    """
    Ingest data for a single season
    
    Returns:
        {trades_ingested, standings_updated, league_info_updated}
    """
    
    league_id = season_info['league_id']
    year = season_info['year']
    status = season_info['status']
    
    print(f"Season: {season_id}, League: {league_id}, Year: {year}, Status: {status}")
    
    result = {
        'trades_ingested': 0,
        'standings_updated': False,
        'league_info_updated': False
    }
    
    # 1. Ingest trades
    print("Fetching trades...")
    result['trades_ingested'] = ingest_trades(season_id, league_id)
    
    # 2. Ingest waiver transactions
    print("Fetching waivers...")
    result['waivers_ingested'] = ingest_waivers(season_id, league_id)
    
    # 3. Ingest matchups (weekly lineups and scores)
    print("Fetching matchups...")
    result['matchups_ingested'] = ingest_matchups(season_id, league_id)
    
    # 4. Ingest NFL player stats
    print("Fetching NFL stats...")
    result['nfl_stats_ingested'] = ingest_nfl_stats(season_id, year)
    
    # 5. Ingest standings
    print("Fetching standings...")
    ingest_standings(season_id, league_id)
    result['standings_updated'] = True
    
    # 6. Ingest league info
    print("Fetching league info...")
    ingest_league_info(season_id, league_id, year)
    result['league_info_updated'] = True
    
    print(f"✅ {season_id}: {result['trades_ingested']} trades, standings ✓, league info ✓")
    return result


def ingest_trades(season_id: str, league_id: str) -> int:
    """Fetch trades for a season and store in DynamoDB"""
    
    # Get league info to determine weeks to scan
    league_url = f"{SLEEPER_BASE_URL}/league/{league_id}"
    league = fetch_sleeper_api(league_url)
    current_week = league.get('settings', {}).get('leg', 1)
    
    print(f"  Current week: {current_week}")
    
    # For historical seasons, scan more weeks (up to 18)
    max_week = current_week + 6 if current_week < 14 else 18
    
    # Fetch trades from all weeks
    all_trades = []
    for week in range(1, max_week + 1):
        try:
            url = f"{SLEEPER_BASE_URL}/league/{league_id}/transactions/{week}"
            transactions = fetch_sleeper_api(url)
            
            if transactions:
                trades = [t for t in transactions if t.get('type') == 'trade']
                if trades:
                    all_trades.extend(trades)
                    print(f"    Week {week}: {len(trades)} trades")
        except:
            continue  # Week doesn't exist
    
    if not all_trades:
        print(f"  No trades found for {season_id}")
        return 0
    
    print(f"  Total: {len(all_trades)} trades")
    
    # Write to DynamoDB
    timestamp = datetime.now(timezone.utc).isoformat()
    
    with table.batch_writer() as batch:
        for trade in all_trades:
            trade_id = trade.get('transaction_id', trade.get('id', ''))
            trade_created = trade.get('created', 0)
            trade_date = datetime.fromtimestamp(trade_created / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            
            item = {
                'PK': f'SEASON#{season_id}',
                'SK': f'TRADE#{trade_date}#{trade_id}',
                'EntityType': 'trade',
                'Season': season_id,
                'TradeId': trade_id,
                'TradeDate': trade_date,
                'TradeCreated': trade_created,
                'RawData': convert_floats_to_decimal(trade),
                'CreatedAt': trade_date,
                'UpdatedAt': timestamp,
                'GSI1PK': 'TRADE',
                'GSI1SK': f'{trade_date}#{season_id}'
            }
            
            batch.put_item(Item=item)
    
    print(f"  ✅ Wrote {len(all_trades)} trades to DynamoDB")
    return len(all_trades)


def ingest_waivers(season_id: str, league_id: str) -> int:
    """Fetch waiver and free agent transactions and store in DynamoDB"""
    
    # Get league info to determine weeks to scan
    league_url = f"{SLEEPER_BASE_URL}/league/{league_id}"
    league = fetch_sleeper_api(league_url)
    current_week = league.get('settings', {}).get('leg', 1)
    
    # For historical seasons, scan more weeks
    max_week = current_week + 6 if current_week < 14 else 18
    
    # Fetch waiver/free agent transactions from all weeks
    all_waivers = []
    for week in range(1, max_week + 1):
        try:
            url = f"{SLEEPER_BASE_URL}/league/{league_id}/transactions/{week}"
            transactions = fetch_sleeper_api(url)
            
            if transactions:
                waivers = [t for t in transactions if t.get('type') in ['waiver', 'free_agent']]
                if waivers:
                    all_waivers.extend(waivers)
                    print(f"    Week {week}: {len(waivers)} waiver/FA transactions")
        except:
            continue
    
    if not all_waivers:
        print(f"  No waiver transactions found for {season_id}")
        return 0
    
    print(f"  Total: {len(all_waivers)} waiver transactions")
    
    # Write to DynamoDB
    timestamp = datetime.now(timezone.utc).isoformat()
    
    with table.batch_writer() as batch:
        for waiver in all_waivers:
            waiver_id = waiver.get('transaction_id', waiver.get('id', ''))
            waiver_created = waiver.get('created', 0)
            waiver_date = datetime.fromtimestamp(waiver_created / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            
            item = {
                'PK': f'SEASON#{season_id}',
                'SK': f'WAIVER#{waiver_date}#{waiver_id}',
                'EntityType': 'waiver_transaction',
                'Season': season_id,
                'WaiverId': waiver_id,
                'WaiverDate': waiver_date,
                'WaiverCreated': waiver_created,
                'TransactionType': waiver.get('type'),
                'RawData': convert_floats_to_decimal(waiver),
                'CreatedAt': waiver_date,
                'UpdatedAt': timestamp,
                'GSI1PK': 'WAIVER',
                'GSI1SK': f'{waiver_date}#{season_id}'
            }
            
            batch.put_item(Item=item)
    
    print(f"  ✅ Wrote {len(all_waivers)} waiver transactions to DynamoDB")
    return len(all_waivers)


def ingest_matchups(season_id: str, league_id: str) -> int:
    """Fetch weekly matchups (lineups and scores) and store in DynamoDB"""
    
    # Get current week
    league_url = f"{SLEEPER_BASE_URL}/league/{league_id}"
    league = fetch_sleeper_api(league_url)
    current_week = league.get('settings', {}).get('leg', 1)
    
    # For historical seasons, fetch all weeks
    max_week = current_week if current_week > 1 else 18
    
    all_matchups = []
    for week in range(1, max_week + 1):
        try:
            url = f"{SLEEPER_BASE_URL}/league/{league_id}/matchups/{week}"
            matchups = fetch_sleeper_api(url)
            
            if matchups:
                print(f"    Week {week}: {len(matchups)} matchups")
                # Store each week's matchups as a single item
                timestamp = datetime.now(timezone.utc).isoformat()
                
                table.put_item(Item={
                    'PK': f'SEASON#{season_id}',
                    'SK': f'MATCHUPS#WEEK#{week:02d}',
                    'EntityType': 'matchups',
                    'Season': season_id,
                    'Week': week,
                    'Matchups': convert_floats_to_decimal(matchups),
                    'UpdatedAt': timestamp,
                    'GSI1PK': 'MATCHUPS',
                    'GSI1SK': f'{season_id}#WEEK#{week:02d}'
                })
                all_matchups.append(week)
        except:
            continue
    
    print(f"  ✅ Wrote matchups for {len(all_matchups)} weeks to DynamoDB")
    return len(all_matchups)


def ingest_nfl_stats(season_id: str, year: int) -> int:
    """Fetch NFL player stats and store in DynamoDB"""
    
    # Get current week to know which weeks to fetch
    season_type = 'regular'  # Could be 'regular' or 'post'
    
    # Fetch stats for each week (up to 18 weeks)
    all_weeks = []
    for week in range(1, 19):
        try:
            url = f"{SLEEPER_BASE_URL}/stats/nfl/{season_type}/{year}/{week}"
            stats = fetch_sleeper_api(url)
            
            if stats:
                # Stats is a dict with player_id as keys
                player_count = len(stats)
                print(f"    Week {week}: {player_count} players")
                
                timestamp = datetime.now(timezone.utc).isoformat()
                
                # Store week's stats
                table.put_item(Item={
                    'PK': f'NFL_STATS#{year}',
                    'SK': f'WEEK#{week:02d}',
                    'EntityType': 'nfl_stats',
                    'Season': season_id,
                    'Year': year,
                    'Week': week,
                    'SeasonType': season_type,
                    'PlayerStats': convert_floats_to_decimal(stats),
                    'PlayerCount': player_count,
                    'UpdatedAt': timestamp,
                    'GSI1PK': 'NFL_STATS',
                    'GSI1SK': f'{year}#WEEK#{week:02d}'
                })
                all_weeks.append(week)
        except:
            continue  # Week might not have data yet
    
    print(f"  ✅ Wrote NFL stats for {len(all_weeks)} weeks to DynamoDB")
    return len(all_weeks)


def ingest_standings(season_id: str, league_id: str) -> None:
    """Fetch standings and store in DynamoDB"""
    
    rosters_url = f"{SLEEPER_BASE_URL}/league/{league_id}/rosters"
    users_url = f"{SLEEPER_BASE_URL}/league/{league_id}/users"
    
    rosters = fetch_sleeper_api(rosters_url)
    users = fetch_sleeper_api(users_url)
    
    standings = []
    for roster in rosters:
        user = next((u for u in users if u['user_id'] == roster['owner_id']), None)
        settings = roster.get('settings', {})
        
        standings.append({
            'roster_id': roster['roster_id'],
            'username': user['display_name'] if user else 'Unknown',
            'wins': settings.get('wins', 0),
            'losses': settings.get('losses', 0),
            'ties': settings.get('ties', 0),
            'points_for': Decimal(str(settings.get('fpts', 0) + settings.get('fpts_decimal', 0) / 100)),
            'points_against': Decimal(str(settings.get('fpts_against', 0) + settings.get('fpts_against_decimal', 0) / 100))
        })
    
    standings.sort(key=lambda x: (-x['wins'], -float(x['points_for'])))
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    table.put_item(Item={
        'PK': f'SEASON#{season_id}',
        'SK': 'STANDINGS#CURRENT',
        'EntityType': 'standings',
        'Season': season_id,
        'Standings': standings,
        'UpdatedAt': timestamp
    })
    
    print(f"  ✅ Wrote standings for {len(standings)} teams")


def ingest_league_info(season_id: str, league_id: str, year: int) -> None:
    """Fetch league metadata and store in DynamoDB"""
    
    league_url = f"{SLEEPER_BASE_URL}/league/{league_id}"
    league = fetch_sleeper_api(league_url)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    table.put_item(Item={
        'PK': f'SEASON#{season_id}',
        'SK': 'METADATA',
        'EntityType': 'league_info',
        'Season': season_id,
        'LeagueId': league_id,
        'LeagueName': league.get('name', 'Unknown'),
        'Year': year,
        'TotalRosters': league.get('total_rosters', 0),
        'Status': league.get('status', 'unknown'),
        'UpdatedAt': timestamp
    })
    
    print(f"  ✅ Wrote league info")


def fetch_sleeper_api(url: str, timeout: int = 10) -> Any:
    """Fetch data from Sleeper API with error handling"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        raise Exception(f"Sleeper API HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Sleeper API connection error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON from Sleeper API: {str(e)}")


def convert_floats_to_decimal(obj):
    """Recursively convert floats to Decimal for DynamoDB compatibility"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


# For local testing
if __name__ == "__main__":
    # Test with backfill mode
    result = lambda_handler({'backfill': True}, None)
    print(json.dumps(result, indent=2, default=str))
