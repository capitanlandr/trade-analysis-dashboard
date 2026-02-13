import json
import csv
import io
import time
import urllib.request
import urllib.error
import boto3
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'fantasy-dashboard-data')
table = dynamodb.Table(table_name)

# ---------------------------------------------------------------------------
# Throttle-safe DynamoDB helpers
# ---------------------------------------------------------------------------
# The table uses PROVISIONED billing at 25 WCU (free tier).  Large writes
# can exceed the burst bucket, so every write goes through a retry wrapper.
# ---------------------------------------------------------------------------

# Pause between heavy ingestion stages (seconds).  Gives the 25 WCU burst
# bucket time to refill between stages that each do dozens of writes.
INTER_STAGE_PAUSE_SECONDS = 2

# Maximum retries for a single DynamoDB write before giving up
MAX_RETRIES = 8

# Base delay for exponential backoff (seconds)
BASE_BACKOFF = 0.5


def throttle_safe_put_item(item: dict, retries: int = MAX_RETRIES) -> None:
    """put_item with exponential backoff on ProvisionedThroughputExceededException."""
    for attempt in range(retries):
        try:
            table.put_item(Item=item)
            return
        except ClientError as e:
            code = e.response['Error']['Code']
            if code in ('ProvisionedThroughputExceededException', 'ThrottlingException'):
                wait = BASE_BACKOFF * (2 ** attempt)
                print(f"    [throttle] put_item attempt {attempt + 1}/{retries} throttled, "
                      f"waiting {wait:.1f}s ...")
                time.sleep(wait)
            else:
                raise
    # Final attempt -- let the exception propagate if it fails
    table.put_item(Item=item)


def throttle_safe_batch_write(items: list, batch_size: int = 10,
                              inter_batch_pause: float = 0.5) -> None:
    """
    Write a list of items using batch_writer, with controlled batch sizes
    and pauses between batches to stay within 25 WCU.

    boto3 batch_writer handles UnprocessedItems internally, but it does NOT
    handle ProvisionedThroughputExceededException from the service.  We add:
      - Small batch sizes (default 10 items) so each flush is ~10-25 WCU
      - Pauses between flushes to let the WCU budget recover
      - Retry/backoff on throttle errors for each mini-batch
    """
    for i in range(0, len(items), batch_size):
        chunk = items[i:i + batch_size]
        _write_batch_chunk_with_retry(chunk)
        # Pause between batches to avoid sustained throughput spikes
        if i + batch_size < len(items):
            time.sleep(inter_batch_pause)


def _write_batch_chunk_with_retry(chunk: list, retries: int = MAX_RETRIES) -> None:
    """Write a small chunk of items via batch_writer, retrying on throttle."""
    for attempt in range(retries):
        try:
            with table.batch_writer(overwrite_by_pkeys=['PK', 'SK']) as batch:
                for item in chunk:
                    batch.put_item(Item=item)
            return
        except ClientError as e:
            code = e.response['Error']['Code']
            if code in ('ProvisionedThroughputExceededException', 'ThrottlingException'):
                wait = BASE_BACKOFF * (2 ** attempt)
                print(f"    [throttle] batch chunk attempt {attempt + 1}/{retries} "
                      f"throttled ({len(chunk)} items), waiting {wait:.1f}s ...")
                time.sleep(wait)
            else:
                raise
    # Final attempt
    with table.batch_writer(overwrite_by_pkeys=['PK', 'SK']) as batch:
        for item in chunk:
            batch.put_item(Item=item)

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
    
    # Ingest reference data (Tasks 1.4 and 1.5)
    # These are not season-specific -- write once per invocation
    try:
        print("\n=== Ingesting Reference Data ===")
        team_mapping_result = ingest_team_mappings()
        results['team_mappings'] = team_mapping_result
        print(f"  Team mappings: {team_mapping_result['team_count']} teams")
    except Exception as e:
        error_msg = f"Failed to ingest team mappings: {str(e)}"
        print(f"  {error_msg}")
        results['errors'].append(error_msg)

    try:
        pick_mapping_result = ingest_pick_mappings()
        results['pick_mappings'] = pick_mapping_result
        print(f"  Pick mappings: {pick_mapping_result['pick_origin_count']} origins, {pick_mapping_result['draft_order_picks']} draft picks")
    except Exception as e:
        error_msg = f"Failed to ingest pick mappings: {str(e)}"
        print(f"  {error_msg}")
        results['errors'].append(error_msg)

    print(f"\nIngestion complete: {json.dumps(results, default=str)}")
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
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 2. Ingest waiver transactions
    print("Fetching waivers...")
    result['waivers_ingested'] = ingest_waivers(season_id, league_id)
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 3. Ingest matchups (weekly lineups and scores)
    print("Fetching matchups...")
    result['matchups_ingested'] = ingest_matchups(season_id, league_id)
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 4. Ingest NFL player stats
    print("Fetching NFL stats...")
    result['nfl_stats_ingested'] = ingest_nfl_stats(season_id, year)
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 5. Ingest standings
    print("Fetching standings...")
    ingest_standings(season_id, league_id)
    result['standings_updated'] = True
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 6. Ingest league info
    print("Fetching league info...")
    ingest_league_info(season_id, league_id, year)
    result['league_info_updated'] = True
    time.sleep(INTER_STAGE_PAUSE_SECONDS)

    # 7. Ingest DynastyProcess valuations (Task 1.3)
    print("Fetching DynastyProcess valuations...")
    try:
        valuation_result = ingest_valuations(season_id)
        result['valuations_ingested'] = valuation_result['player_count']
        result['valuation_date'] = valuation_result['valuation_date']
    except Exception as e:
        print(f"  Warning: Valuation ingestion failed: {str(e)}")
        result['valuations_ingested'] = 0

    print(f"  {season_id}: {result['trades_ingested']} trades, standings done, league info done, {result.get('valuations_ingested', 0)} valuations")
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
    
    # Write to DynamoDB using throttle-safe batch writer
    timestamp = datetime.now(timezone.utc).isoformat()

    items = []
    for trade in all_trades:
        trade_id = trade.get('transaction_id', trade.get('id', ''))
        trade_created = trade.get('created', 0)
        trade_date = datetime.fromtimestamp(trade_created / 1000, tz=timezone.utc).strftime('%Y-%m-%d')

        items.append({
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
        })

    throttle_safe_batch_write(items)
    print(f"  Wrote {len(all_trades)} trades to DynamoDB")
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
    
    # Write to DynamoDB using throttle-safe batch writer
    timestamp = datetime.now(timezone.utc).isoformat()

    items = []
    for waiver in all_waivers:
        waiver_id = waiver.get('transaction_id', waiver.get('id', ''))
        waiver_created = waiver.get('created', 0)
        waiver_date = datetime.fromtimestamp(waiver_created / 1000, tz=timezone.utc).strftime('%Y-%m-%d')

        items.append({
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
        })

    throttle_safe_batch_write(items)
    print(f"  Wrote {len(all_waivers)} waiver transactions to DynamoDB")
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
                timestamp = datetime.now(timezone.utc).isoformat()

                throttle_safe_put_item({
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
                # Pace writes -- each matchup item can be several KB
                time.sleep(0.3)
        except Exception:
            continue

    print(f"  Wrote matchups for {len(all_matchups)} weeks to DynamoDB")
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
                player_count = len(stats)
                print(f"    Week {week}: {player_count} players")

                timestamp = datetime.now(timezone.utc).isoformat()

                # NFL stats items can be very large (hundreds of KB).
                # Use throttle-safe put with retries.
                throttle_safe_put_item({
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
                # NFL stats items are large -- pause to let WCU recover
                time.sleep(0.5)
        except Exception:
            continue  # Week might not have data yet

    print(f"  Wrote NFL stats for {len(all_weeks)} weeks to DynamoDB")
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
    
    throttle_safe_put_item({
        'PK': f'SEASON#{season_id}',
        'SK': 'STANDINGS#CURRENT',
        'EntityType': 'standings',
        'Season': season_id,
        'Standings': standings,
        'UpdatedAt': timestamp
    })

    print(f"  Wrote standings for {len(standings)} teams")


def ingest_league_info(season_id: str, league_id: str, year: int) -> None:
    """Fetch league metadata and store in DynamoDB"""
    
    league_url = f"{SLEEPER_BASE_URL}/league/{league_id}"
    league = fetch_sleeper_api(league_url)
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    throttle_safe_put_item({
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

    print(f"  Wrote league info")


def ingest_valuations(season_id: str) -> Dict:
    """
    Task 1.3: Fetch DynastyProcess player valuations CSV and store in DynamoDB.

    Fetches the values.csv from DynastyProcess GitHub, parses player name,
    position, value_2qb, and scrape_date, then writes the full player list
    as a JSON-serialized attribute to DynamoDB.

    DynamoDB item: PK=SEASON#{season_id}, SK=VALUATIONS#LATEST
    """

    DYNASTYPROCESS_CSV_URL = "https://github.com/dynastyprocess/data/raw/master/files/values.csv"

    print(f"  Fetching DynastyProcess valuations from {DYNASTYPROCESS_CSV_URL}...")

    try:
        req = urllib.request.Request(
            DYNASTYPROCESS_CSV_URL,
            headers={'User-Agent': 'DynasuiiiiIngestion/1.0'}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            csv_text = response.read().decode('utf-8')
    except Exception as e:
        raise Exception(f"Failed to fetch DynastyProcess CSV: {str(e)}")

    # Parse CSV
    reader = csv.DictReader(io.StringIO(csv_text))

    players = []
    scrape_date = None

    for row in reader:
        # Extract the fields we need
        player_name = row.get('player', '').strip()
        position = row.get('pos', '').strip()
        value_2qb_raw = row.get('value_2qb', '0').strip()
        row_scrape_date = row.get('scrape_date', '').strip()

        # Parse value_2qb as integer (it can be empty or non-numeric)
        try:
            value_2qb = int(float(value_2qb_raw)) if value_2qb_raw else 0
        except (ValueError, TypeError):
            value_2qb = 0

        # Skip rows with no player name
        if not player_name:
            continue

        players.append({
            'player': player_name,
            'position': position,
            'value_2qb': value_2qb
        })

        # Capture scrape_date from first non-empty row
        if scrape_date is None and row_scrape_date:
            scrape_date = row_scrape_date

    if not players:
        raise Exception("DynastyProcess CSV parsed but contained no player records")

    print(f"  Parsed {len(players)} players, scrape_date={scrape_date}")

    # Write to DynamoDB as a single item.
    # The players list is JSON-serialized to stay within DynamoDB 400KB item limit.
    # At ~70 bytes per player * 2000+ players, the item is ~150-200KB which
    # consumes 150-200 WCUs in a single write against our 25 WCU provisioned
    # table.  The throttle_safe_put_item wrapper handles the resulting throttle
    # via exponential backoff (DynamoDB will accept it once burst budget refills).
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"  Writing valuations item (~{len(json.dumps(players)) // 1024}KB) "
          f"with throttle-safe retries ...")

    throttle_safe_put_item({
        'PK': f'SEASON#{season_id}',
        'SK': 'VALUATIONS#LATEST',
        'EntityType': 'valuations',
        'Season': season_id,
        'Players': json.dumps(players),  # JSON-serialized string
        'ValuationDate': scrape_date or 'unknown',
        'PlayerCount': len(players),
        'Source': 'dynastyprocess',
        'SourceUrl': DYNASTYPROCESS_CSV_URL,
        'UpdatedAt': timestamp
    })

    print(f"  Wrote valuations to DynamoDB: PK=SEASON#{season_id}, SK=VALUATIONS#LATEST ({len(players)} players)")

    return {
        'player_count': len(players),
        'valuation_date': scrape_date
    }


def ingest_team_mappings() -> Dict:
    """
    Task 1.4: Upload team identity mapping to DynamoDB as reference data.

    Hardcodes the 12-team identity mapping from team_identity_mapping.csv.
    This data rarely changes (only when a manager changes their Sleeper display name).

    DynamoDB item: PK=REFERENCE, SK=TEAM_IDENTITY_MAPPING
    """

    print("  Writing team identity mapping to DynamoDB...")

    # Hardcoded from /team_identity_mapping.csv (12 teams)
    teams = [
        {'roster_id': 1, 'sleeper_username': 'lndahayo', 'real_name': 'Landry', 'nickname': 'Landry', 'current_team_name': '208 Ferrari Way'},
        {'roster_id': 2, 'sleeper_username': 'gnewman4', 'real_name': 'Grant', 'nickname': 'Grant', 'current_team_name': 'Like a Good Naber'},
        {'roster_id': 3, 'sleeper_username': 'brevinowens', 'real_name': 'Brevin', 'nickname': 'Brevin', 'current_team_name': "Bucky's Depression"},
        {'roster_id': 4, 'sleeper_username': 'thekylecasey', 'real_name': 'Kyle', 'nickname': 'Kyle', 'current_team_name': 'Spirit Halloween'},
        {'roster_id': 5, 'sleeper_username': 'zachlearningtogolf', 'real_name': 'Zach', 'nickname': 'Zach', 'current_team_name': 'Mommy Rainier '},
        {'roster_id': 6, 'sleeper_username': 'cjsyregelas', 'real_name': 'Chris', 'nickname': 'Chris', 'current_team_name': 'Mostly Washed'},
        {'roster_id': 7, 'sleeper_username': 'jwalters74', 'real_name': 'Johnny', 'nickname': 'Johnny', 'current_team_name': '2-Man Title Charge'},
        {'roster_id': 8, 'sleeper_username': 'tylerpilgrim', 'real_name': 'Tyler', 'nickname': 'Tyler', 'current_team_name': 'TRIPS'},
        {'roster_id': 9, 'sleeper_username': 'mgaeta23', 'real_name': 'Matt', 'nickname': 'Gaeta', 'current_team_name': 'Gaeta Spur FC'},
        {'roster_id': 10, 'sleeper_username': 'jakeduf', 'real_name': 'Jake', 'nickname': 'Jake', 'current_team_name': 'Rashid Shaheed Truthers'},
        {'roster_id': 11, 'sleeper_username': 'wkerwin', 'real_name': 'Will', 'nickname': 'Will', 'current_team_name': 'On To 2026'},
        {'roster_id': 12, 'sleeper_username': 'donewton', 'real_name': 'Don', 'nickname': 'Don', 'current_team_name': 'Paper Tigers'},
    ]

    timestamp = datetime.now(timezone.utc).isoformat()

    throttle_safe_put_item({
        'PK': 'REFERENCE',
        'SK': 'TEAM_IDENTITY_MAPPING',
        'EntityType': 'team_identity_mapping',
        'Teams': teams,
        'TeamCount': len(teams),
        'UpdatedAt': timestamp
    })

    print(f"  Wrote team identity mapping to DynamoDB: PK=REFERENCE, SK=TEAM_IDENTITY_MAPPING ({len(teams)} teams)")

    return {
        'team_count': len(teams)
    }


def ingest_pick_mappings() -> Dict:
    """
    Task 1.5: Upload pick origin mapping and 2026 draft order to DynamoDB.

    Writes two reference items:
    1. PK=REFERENCE, SK=PICK_ORIGIN_MAPPING_2025 - the 48-pick origin mapping
    2. PK=REFERENCE, SK=DRAFT_ORDER_2026 - the full 2026 draft order JSON
    """

    print("  Writing pick origin mapping and draft order to DynamoDB...")

    # === Pick Origin Mapping (from pipeline/pick_origin_mapping.py) ===
    # Round 1 explicit origins (linear draft: same order every round)
    round_1_origins = {
        1: 'tylerpilgrim',
        2: 'wkerwin',
        3: 'zachlearningtogolf',
        4: 'brevinowens',
        5: 'jwalters74',
        6: 'donewton',
        7: 'lndahayo',
        8: 'thekylecasey',
        9: 'mgaeta23',
        10: 'cjsyregelas',
        11: 'jakeduf',
        12: 'gnewman4',
    }

    # Build all 48 picks (4 rounds x 12 picks, linear draft = same order each round)
    pick_origins = []
    for round_num in range(1, 5):
        for pick in range(1, 13):
            pick_origins.append({
                'round': round_num,
                'pick': pick,
                'pick_label': f'{round_num}.{pick:02d}',
                'origin_owner': round_1_origins[pick]
            })

    timestamp = datetime.now(timezone.utc).isoformat()

    # Write pick origin mapping
    throttle_safe_put_item({
        'PK': 'REFERENCE',
        'SK': 'PICK_ORIGIN_MAPPING_2025',
        'EntityType': 'pick_origin_mapping',
        'DraftYear': 2025,
        'PickOrigins': pick_origins,
        'PickCount': len(pick_origins),
        'UpdatedAt': timestamp
    })

    print(f"  Wrote pick origin mapping: PK=REFERENCE, SK=PICK_ORIGIN_MAPPING_2025 ({len(pick_origins)} picks)")

    # === Draft Order 2026 (from pipeline/draft_order_2026_progressive.json) ===
    # Hardcoded from the JSON file - full 48-pick draft order with ownership data
    draft_order_data = {
        "season": 2025,
        "draft_year": 2026,
        "through_week": 17,
        "determination_level": "complete",
        "summary": {
            "total_picks": 48,
            "locked_picks": 48,
            "uncertain_picks": 0,
            "round_1_locked": 12,
            "round_1_uncertain": 0
        },
        "draft_order": {
            "round_1": [
                {"pick_number": 1, "pick_label": "1.01", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 11, "team_name": "On To 2026", "description": "Toilet Bowl Winner"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": False},
                {"pick_number": 2, "pick_label": "1.02", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 5, "team_name": "Mommy Rainier ", "description": "Toilet Bowl Loser"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": True},
                {"pick_number": 3, "pick_label": "1.03", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 4, "team_name": "Spirit Halloween", "regular_season_rank": 12, "description": "12th place (remaining team)"}, "current_owner": {"roster_id": 4, "team_name": "Spirit Halloween"}, "traded": False},
                {"pick_number": 4, "pick_label": "1.04", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 8, "team_name": "TRIPS", "regular_season_rank": 11, "description": "11th place (remaining team)"}, "current_owner": {"roster_id": 4, "team_name": "Spirit Halloween"}, "traded": True},
                {"pick_number": 5, "pick_label": "1.05", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 6, "team_name": "Mostly Washed", "regular_season_rank": 9, "description": "9th place (remaining team)"}, "current_owner": {"roster_id": 8, "team_name": "TRIPS"}, "traded": True},
                {"pick_number": 6, "pick_label": "1.06", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers", "regular_season_rank": 7, "description": "7th place (remaining team)"}, "current_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers"}, "traded": False},
                {"pick_number": 7, "pick_label": "1.07", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC", "regular_season_rank": 6, "description": "6th place (remaining team)"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": False},
                {"pick_number": 8, "pick_label": "1.08", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 12, "team_name": "Paper Tigers", "regular_season_rank": 5, "description": "5th place (remaining team)"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": True},
                {"pick_number": 9, "pick_label": "1.09", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 2, "team_name": "Like a Good Naber", "description": "3rd Place Winner"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": True},
                {"pick_number": 10, "pick_label": "1.10", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 1, "team_name": "208 Ferrari Way", "description": "3rd Place Loser"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": True},
                {"pick_number": 11, "pick_label": "1.11", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 3, "team_name": "Bucky's Depression", "description": "Championship Loser"}, "current_owner": {"roster_id": 3, "team_name": "Bucky's Depression"}, "traded": False},
                {"pick_number": 12, "pick_label": "1.12", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 7, "team_name": "2-Man Title Charge", "description": "Championship Winner"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": True},
            ],
            "round_2": [
                {"pick_number": 1, "pick_label": "2.01", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 11, "team_name": "On To 2026", "description": "Toilet Bowl Winner"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": False},
                {"pick_number": 2, "pick_label": "2.02", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 5, "team_name": "Mommy Rainier ", "description": "Toilet Bowl Loser"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": True},
                {"pick_number": 3, "pick_label": "2.03", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 4, "team_name": "Spirit Halloween", "regular_season_rank": 12, "description": "12th place (remaining team)"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": True},
                {"pick_number": 4, "pick_label": "2.04", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 8, "team_name": "TRIPS", "regular_season_rank": 11, "description": "11th place (remaining team)"}, "current_owner": {"roster_id": 4, "team_name": "Spirit Halloween"}, "traded": True},
                {"pick_number": 5, "pick_label": "2.05", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 6, "team_name": "Mostly Washed", "regular_season_rank": 9, "description": "9th place (remaining team)"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 6, "pick_label": "2.06", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers", "regular_season_rank": 7, "description": "7th place (remaining team)"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 7, "pick_label": "2.07", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC", "regular_season_rank": 6, "description": "6th place (remaining team)"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": False},
                {"pick_number": 8, "pick_label": "2.08", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 12, "team_name": "Paper Tigers", "regular_season_rank": 5, "description": "5th place (remaining team)"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": True},
                {"pick_number": 9, "pick_label": "2.09", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 2, "team_name": "Like a Good Naber", "description": "3rd Place Winner"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 10, "pick_label": "2.10", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 1, "team_name": "208 Ferrari Way", "description": "3rd Place Loser"}, "current_owner": {"roster_id": 6, "team_name": "Mostly Washed"}, "traded": True},
                {"pick_number": 11, "pick_label": "2.11", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 3, "team_name": "Bucky's Depression", "description": "Championship Loser"}, "current_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC"}, "traded": True},
                {"pick_number": 12, "pick_label": "2.12", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 7, "team_name": "2-Man Title Charge", "description": "Championship Winner"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
            ],
            "round_3": [
                {"pick_number": 1, "pick_label": "3.01", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 11, "team_name": "On To 2026", "description": "Toilet Bowl Winner"}, "current_owner": {"roster_id": 11, "team_name": "On To 2026"}, "traded": False},
                {"pick_number": 2, "pick_label": "3.02", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 5, "team_name": "Mommy Rainier ", "description": "Toilet Bowl Loser"}, "current_owner": {"roster_id": 1, "team_name": "208 Ferrari Way"}, "traded": True},
                {"pick_number": 3, "pick_label": "3.03", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 4, "team_name": "Spirit Halloween", "regular_season_rank": 12, "description": "12th place (remaining team)"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 4, "pick_label": "3.04", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 8, "team_name": "TRIPS", "regular_season_rank": 11, "description": "11th place (remaining team)"}, "current_owner": {"roster_id": 8, "team_name": "TRIPS"}, "traded": False},
                {"pick_number": 5, "pick_label": "3.05", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 6, "team_name": "Mostly Washed", "regular_season_rank": 9, "description": "9th place (remaining team)"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 6, "pick_label": "3.06", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers", "regular_season_rank": 7, "description": "7th place (remaining team)"}, "current_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers"}, "traded": False},
                {"pick_number": 7, "pick_label": "3.07", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC", "regular_season_rank": 6, "description": "6th place (remaining team)"}, "current_owner": {"roster_id": 8, "team_name": "TRIPS"}, "traded": True},
                {"pick_number": 8, "pick_label": "3.08", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 12, "team_name": "Paper Tigers", "regular_season_rank": 5, "description": "5th place (remaining team)"}, "current_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers"}, "traded": True},
                {"pick_number": 9, "pick_label": "3.09", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 2, "team_name": "Like a Good Naber", "description": "3rd Place Winner"}, "current_owner": {"roster_id": 2, "team_name": "Like a Good Naber"}, "traded": False},
                {"pick_number": 10, "pick_label": "3.10", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 1, "team_name": "208 Ferrari Way", "description": "3rd Place Loser"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
                {"pick_number": 11, "pick_label": "3.11", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 3, "team_name": "Bucky's Depression", "description": "Championship Loser"}, "current_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers"}, "traded": True},
                {"pick_number": 12, "pick_label": "3.12", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 7, "team_name": "2-Man Title Charge", "description": "Championship Winner"}, "current_owner": {"roster_id": 5, "team_name": "Mommy Rainier "}, "traded": True},
            ],
            "round_4": [
                {"pick_number": 1, "pick_label": "4.01", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 11, "team_name": "On To 2026", "description": "Toilet Bowl Winner"}, "current_owner": {"roster_id": 1, "team_name": "208 Ferrari Way"}, "traded": True},
                {"pick_number": 2, "pick_label": "4.02", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 5, "team_name": "Mommy Rainier ", "description": "Toilet Bowl Loser"}, "current_owner": {"roster_id": 4, "team_name": "Spirit Halloween"}, "traded": True},
                {"pick_number": 3, "pick_label": "4.03", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 4, "team_name": "Spirit Halloween", "regular_season_rank": 12, "description": "12th place (remaining team)"}, "current_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers"}, "traded": True},
                {"pick_number": 4, "pick_label": "4.04", "tier": "Early", "certainty": "locked", "original_owner": {"roster_id": 8, "team_name": "TRIPS", "regular_season_rank": 11, "description": "11th place (remaining team)"}, "current_owner": {"roster_id": 8, "team_name": "TRIPS"}, "traded": False},
                {"pick_number": 5, "pick_label": "4.05", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 6, "team_name": "Mostly Washed", "regular_season_rank": 9, "description": "9th place (remaining team)"}, "current_owner": {"roster_id": 12, "team_name": "Paper Tigers"}, "traded": True},
                {"pick_number": 6, "pick_label": "4.06", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 10, "team_name": "Rashid Shaheed Truthers", "regular_season_rank": 7, "description": "7th place (remaining team)"}, "current_owner": {"roster_id": 12, "team_name": "Paper Tigers"}, "traded": True},
                {"pick_number": 7, "pick_label": "4.07", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 9, "team_name": "Gaeta Spur FC", "regular_season_rank": 6, "description": "6th place (remaining team)"}, "current_owner": {"roster_id": 2, "team_name": "Like a Good Naber"}, "traded": True},
                {"pick_number": 8, "pick_label": "4.08", "tier": "Mid", "certainty": "locked", "original_owner": {"roster_id": 12, "team_name": "Paper Tigers", "regular_season_rank": 5, "description": "5th place (remaining team)"}, "current_owner": {"roster_id": 6, "team_name": "Mostly Washed"}, "traded": True},
                {"pick_number": 9, "pick_label": "4.09", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 2, "team_name": "Like a Good Naber", "description": "3rd Place Winner"}, "current_owner": {"roster_id": 7, "team_name": "2-Man Title Charge"}, "traded": True},
                {"pick_number": 10, "pick_label": "4.10", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 1, "team_name": "208 Ferrari Way", "description": "3rd Place Loser"}, "current_owner": {"roster_id": 7, "team_name": "2-Man Title Charge"}, "traded": True},
                {"pick_number": 11, "pick_label": "4.11", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 3, "team_name": "Bucky's Depression", "description": "Championship Loser"}, "current_owner": {"roster_id": 3, "team_name": "Bucky's Depression"}, "traded": False},
                {"pick_number": 12, "pick_label": "4.12", "tier": "Late", "certainty": "locked", "original_owner": {"roster_id": 7, "team_name": "2-Man Title Charge", "description": "Championship Winner"}, "current_owner": {"roster_id": 2, "team_name": "Like a Good Naber"}, "traded": True},
            ]
        }
    }

    # Write draft order to DynamoDB
    # JSON-serialize the draft_order data to avoid DynamoDB nested map/list depth limits
    throttle_safe_put_item({
        'PK': 'REFERENCE',
        'SK': 'DRAFT_ORDER_2026',
        'EntityType': 'draft_order',
        'DraftYear': 2026,
        'Season': 2025,
        'DraftOrder': json.dumps(draft_order_data),
        'ThroughWeek': draft_order_data['through_week'],
        'DeterminationLevel': draft_order_data['determination_level'],
        'TotalPicks': draft_order_data['summary']['total_picks'],
        'UpdatedAt': timestamp
    })

    print(f"  Wrote draft order: PK=REFERENCE, SK=DRAFT_ORDER_2026 ({draft_order_data['summary']['total_picks']} picks)")

    return {
        'pick_origin_count': len(pick_origins),
        'draft_order_picks': draft_order_data['summary']['total_picks']
    }


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
