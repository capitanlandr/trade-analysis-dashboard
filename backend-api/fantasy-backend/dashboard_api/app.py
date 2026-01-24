import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List

# Your league configuration
LEAGUE_ID = "1312166810505719808"
SLEEPER_BASE_URL = "https://api.sleeper.app/v1"

def lambda_handler(event, context) -> Dict[str, Any]:
    """
    Monolithic Lambda handling all dashboard API endpoints
    
    Routes:
    - GET /api/trades      → Real-time trades from Sleeper
    - GET /api/standings   → Current standings
    - GET /api/waivers     → Waiver wire transactions
    - GET /api/league-info → League metadata
    
    Returns JSON with CORS headers for frontend access
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
            return handle_trades()
        elif path == '/api/standings':
            return handle_standings()
        elif path == '/api/waivers':
            return handle_waivers()
        elif path == '/api/league-info':
            return handle_league_info()
        elif path == '/api/health':
            return handle_health()
        else:
            return cors_response(404, {
                'error': 'Endpoint not found',
                'available_endpoints': [
                    '/api/trades',
                    '/api/standings',
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


def handle_trades() -> Dict[str, Any]:
    """
    Fetch ALL trades from Sleeper API (matches pipeline stage 1 raw fetch)
    Loops through all weeks to get complete trade history
    """
    try:
        # Step 1: Get league info to determine current week (like pipeline does)
        league_url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}"
        league = fetch_sleeper_api(league_url)
        current_week = league.get('settings', {}).get('leg', 1)
        season = league.get('season')
        league_name = league.get('name')
        
        print(f"League: {league_name}, Season: {season}, Current Week: {current_week}")
        
        # Step 2: Fetch users and rosters (like pipeline does)
        users_url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/users"
        rosters_url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/rosters"
        
        users = fetch_sleeper_api(users_url)
        rosters = fetch_sleeper_api(rosters_url)
        
        print(f"Fetched {len(users)} users and {len(rosters)} rosters")
        
        # Step 3: Loop through ALL weeks to fetch trades (MATCHING PIPELINE!)
        all_trades = []
        weeks_scanned = 0
        weeks_with_trades = 0
        
        for week in range(1, current_week + 6):
            try:
                url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/transactions/{week}"
                transactions = fetch_sleeper_api(url)
                weeks_scanned += 1
                
                if transactions:
                    # Filter to only trades
                    trades = [t for t in transactions if t.get('type') == 'trade']
                    if trades:
                        all_trades.extend(trades)
                        weeks_with_trades += 1
                        print(f"Week {week}: {len(trades)} trade(s)")
                        
            except Exception as e:
                # Week might not exist yet, continue
                print(f"Week {week}: No data (expected for future weeks)")
                continue
        
        # Sort by date (most recent first) - like pipeline does
        all_trades.sort(key=lambda t: t.get('created', 0), reverse=True)
        
        print(f"Total: {len(all_trades)} trades from {weeks_with_trades} weeks")
        
        return cors_response(200, {
            'success': True,
            'source': 'real-time-sleeper-api-all-weeks',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'metadata': {
                'league_id': LEAGUE_ID,
                'league_name': league_name,
                'season': season,
                'current_week': current_week,
                'weeks_scanned': weeks_scanned,
                'weeks_with_trades': weeks_with_trades
            },
            'users': users,
            'rosters': rosters,
            'trades': all_trades,
            'trade_count': len(all_trades),
            'message': f'Fetched {len(all_trades)} trades from {weeks_with_trades} weeks - MATCHES PIPELINE STAGE 1!'
        })
        
    except Exception as e:
        return cors_response(500, {
            'error': str(e),
            'endpoint': '/api/trades'
        })


def handle_standings() -> Dict[str, Any]:
    """Fetch current league standings"""
    try:
        # Fetch rosters
        rosters_url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/rosters"
        rosters = fetch_sleeper_api(rosters_url)
        
        # Fetch users for team names
        users_url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/users"
        users = fetch_sleeper_api(users_url)
        
        # Combine rosters with user info
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
                'points_for': settings.get('fpts', 0) + settings.get('fpts_decimal', 0) / 100,
                'points_against': settings.get('fpts_against', 0) + settings.get('fpts_against_decimal', 0) / 100,
            })
        
        # Sort by wins (descending)
        standings.sort(key=lambda x: (-x['wins'], -x['points_for']))
        
        return cors_response(200, {
            'success': True,
            'source': 'real-time-sleeper-api',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'standings': standings
        })
        
    except Exception as e:
        return cors_response(500, {
            'error': str(e),
            'endpoint': '/api/standings'
        })


def handle_waivers() -> Dict[str, Any]:
    """Fetch waiver wire transactions"""
    try:
        # Fetch transactions
        url = f"{SLEEPER_BASE_URL}/league/{LEAGUE_ID}/transactions/1"
        transactions = fetch_sleeper_api(url)
        
        # Filter to waiver/free agent adds
        waivers = [t for t in transactions if t.get('type') in ['waiver', 'free_agent']]
        
        return cors_response(200, {
            'success': True,
            'source': 'real-time-sleeper-api',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'waiver_count': len(waivers),
            'waivers': waivers
        })
        
    except Exception as e:
        return cors_response(500, {
            'error': str(e),
            'endpoint': '/api/waivers'
        })


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
            '/api/standings',
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
