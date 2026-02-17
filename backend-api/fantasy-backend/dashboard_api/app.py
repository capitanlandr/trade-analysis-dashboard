import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List

import boto3
from boto3.dynamodb.conditions import Key

# Your league configuration
LEAGUE_ID = "1312166810505719808"
SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

# DynamoDB setup
TABLE_NAME = os.environ.get('TABLE_NAME', 'fantasy-dashboard-data')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Dashboard API Lambda -- thin read layer over DynamoDB enriched data.

    Enriched endpoints (DynamoDB GetItem, <100ms):
    - GET /api/trades      -> ENRICHED_TRADES#LATEST       (Task 2.2)
    - GET /api/teams       -> ENRICHED_TEAMS#LATEST        (Task 2.3)
    - GET /api/stats       -> ENRICHED_STATS#LATEST        (Task 2.4)
    - GET /api/standings   -> ENRICHED_STANDINGS#LATEST     (Task 3.1)
    - GET /api/playoffs    -> ENRICHED_PLAYOFF#LATEST       (Task 3.2)
    - GET /api/draft-order -> ENRICHED_DRAFTORDER#LATEST    (Task 3.3)
    - GET /api/waivers     -> ENRICHED_WAIVERS#LATEST       (Task 3.4)

    Legacy endpoints (direct Sleeper API):
    - GET /api/league-info -> Sleeper API
    - GET /api/health      -> Health check

    Query params: ?season=all | season_2 | season_3 (default: all = combined view)
    Returns JSON with CORS headers for frontend access.
    """

    # Extract path and method
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')

    print(f"Request: {method} {path}")

    # Handle OPTIONS for CORS preflight
    if method == 'OPTIONS':
        return cors_response(200, {'message': 'OK'})

    # Route to appropriate handler
    try:
        if path == '/api/trades':
            return handle_trades(event)
        elif path == '/api/teams':
            return handle_teams(event)
        elif path == '/api/stats':
            return handle_stats(event)
        elif path == '/api/standings':
            return handle_standings(event)
        elif path == '/api/playoffs':
            return handle_playoffs(event)
        elif path == '/api/draft-order':
            return handle_draft_order(event)
        elif path == '/api/waivers':
            return handle_waivers(event)
        elif path == '/api/league-info':
            return handle_league_info()
        elif path == '/api/health':
            return handle_health()
        else:
            return cors_response(404, {
                'error': 'Endpoint not found',
                'available_endpoints': [
                    '/api/trades',
                    '/api/teams',
                    '/api/stats',
                    '/api/standings',
                    '/api/playoffs',
                    '/api/draft-order',
                    '/api/waivers',
                    '/api/league-info',
                    '/api/health'
                ]
            })

    except Exception as e:
        print(f"Error: {str(e)}")
        return cors_response(500, {
            'error': 'Internal server error',
            'message': str(e)
        })


def get_season_param(event: Dict[str, Any]) -> str:
    """Extract season from query string parameters, defaulting to 'all' (combined view)."""
    params = event.get('queryStringParameters') or {}
    return params.get('season', 'all')


def handle_trades(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 2.2: Trades endpoint -- single DynamoDB GetItem for ENRICHED_TRADES#LATEST.
    Returns enriched trade data matching api-trades.json schema.
    """
    season = get_season_param(event)
    print(f"handle_trades: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_TRADES#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched trade data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_teams(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 2.3: Teams endpoint -- single DynamoDB GetItem for ENRICHED_TEAMS#LATEST.
    Returns enriched team/manager data matching api-teams.json schema.
    """
    season = get_season_param(event)
    print(f"handle_teams: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_TEAMS#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched team data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_stats(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 2.4: Stats endpoint -- single DynamoDB GetItem for ENRICHED_STATS#LATEST.
    Returns enriched stats summary matching api-stats-summary.json schema.
    """
    season = get_season_param(event)
    print(f"handle_stats: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_STATS#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched stats data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_standings(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 3.1: Standings endpoint -- single DynamoDB GetItem for ENRICHED_STANDINGS#LATEST.
    Returns enriched standings data matching api-standings.json schema.
    """
    season = get_season_param(event)
    print(f"handle_standings: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_STANDINGS#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched standings data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_playoffs(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 3.2: Playoff scenarios endpoint -- single DynamoDB GetItem for ENRICHED_PLAYOFF#LATEST.
    Returns enriched playoff scenario data matching api-playoff-scenarios.json schema.
    """
    season = get_season_param(event)
    print(f"handle_playoffs: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_PLAYOFF#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched playoff data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_draft_order(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 3.3: Draft order endpoint -- single DynamoDB GetItem for ENRICHED_DRAFTORDER#LATEST.
    Returns enriched draft order data matching api-draft-order.json schema.
    """
    season = get_season_param(event)
    print(f"handle_draft_order: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_DRAFTORDER#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched draft order data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_waivers(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task 3.4: Waivers endpoint -- single DynamoDB GetItem for ENRICHED_WAIVERS#LATEST.
    Returns enriched waiver wire data matching waiver-wire-page.json schema.
    """
    season = get_season_param(event)
    print(f"handle_waivers: season={season}")

    result = table.get_item(Key={'PK': f'SEASON#{season}', 'SK': 'ENRICHED_WAIVERS#LATEST'})
    item = result.get('Item')
    if not item:
        return cors_response(404, {'error': 'No enriched waivers data found', 'season': season})
    return cors_response(200, json.loads(item['Data']))


def handle_league_info() -> Dict[str, Any]:
    """Fetch league metadata"""
    try:
        url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}"
        league = fetch_sleeper_api(url)
        
        return cors_response(200, {
            'success': True,
            'source': 'real-time-sleeper-api',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'league': {
                'name': league.get('name'),
                'season': league.get('season'),
                'status': league.get('status'),
                'total_rosters': league.get('total_rosters'),
                'league_id': LEAGUE_ID
            }
        })
        
    except Exception as e:
        return cors_response(500, {
            'error': str(e),
            'endpoint': '/api/league-info'
        })


def handle_health() -> Dict[str, Any]:
    """Health check endpoint"""
    return cors_response(200, {
        'status': 'healthy',
        'lambda': 'dashboard_api',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'league_id': LEAGUE_ID,
        'endpoints': [
            '/api/trades',
            '/api/teams',
            '/api/stats',
            '/api/standings',
            '/api/playoffs',
            '/api/draft-order',
            '/api/waivers',
            '/api/league-info',
            '/api/health'
        ]
    })


# Helper Functions

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


def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body, default=str)
    }
