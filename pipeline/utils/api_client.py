"""
API Client with Retry Logic and Error Handling
Provides robust API calls with exponential backoff
"""

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded"""
    pass


class TimeoutError(APIError):
    """Request timeout"""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException, APIError)),
    reraise=True
)
def fetch_with_retry(url: str, timeout: int = 10, params: Optional[Dict] = None) -> Any:
    """
    Fetch JSON from URL with automatic retry and exponential backoff.
    
    Retries up to 3 times with exponential backoff:
    - 1st retry: 4 seconds
    - 2nd retry: 8 seconds  
    - 3rd retry: 10 seconds (capped)
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        params: Optional query parameters
    
    Returns:
        JSON response as dict or list
    
    Raises:
        APIError: If all retries exhausted
        RateLimitError: If rate limited (429)
        TimeoutError: If request times out
    """
    try:
        logger.debug(f"Fetching: {url}")
        response = requests.get(url, timeout=timeout, params=params)
        
        if response.status_code == 429:
            logger.warning(f"Rate limited on {url}")
            raise RateLimitError(f"Rate limited: {url}")
        
        if response.status_code == 404:
            logger.warning(f"Not found: {url}")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        raise TimeoutError(f"Timeout: {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url}", exc_info=True)
        raise APIError(f"Request failed: {str(e)}")


def create_session_with_retries() -> requests.Session:
    """
    Create requests Session with automatic retry on failures.
    
    Automatically retries on:
    - 429 (Rate Limit)
    - 500, 502, 503, 504 (Server Errors)
    
    Returns:
        Configured requests.Session
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


# Sleeper API Base URL
SLEEPER_API_BASE = "https://api.sleeper.app/v1"


def fetch_bracket_data(league_id: str) -> Dict[str, Any]:
    """
    Fetch both winners and losers bracket data from Sleeper.
    
    Args:
        league_id: Sleeper league ID
        
    Returns:
        Dict with 'winners_bracket' and 'losers_bracket' arrays
    """
    winners_url = f"{SLEEPER_API_BASE}/league/{league_id}/winners_bracket"
    losers_url = f"{SLEEPER_API_BASE}/league/{league_id}/losers_bracket"
    
    logger.info(f"Fetching bracket data for league {league_id}")
    
    winners = fetch_with_retry(winners_url)
    losers = fetch_with_retry(losers_url)
    
    return {
        'winners_bracket': winners or [],
        'losers_bracket': losers or []
    }


def identify_special_games(winners_bracket: list, losers_bracket: list) -> Dict[str, Any]:
    """
    Identify Championship, 3rd Place, and Toilet Bowl games using placement field.
    
    From Sleeper API:
    - Placement field (p):
      * Winners bracket: 1=Championship, 3=3rd Place
      * Losers bracket: 5=Toilet Bowl (11th place), 1=Consolation Championship (7th place)
    - Round field (r): 1=Wild Card, 2=Semifinals, 3=Finals
    - Winner field (w): null if game pending, roster_id if complete
    
    Args:
        winners_bracket: Winners bracket from Sleeper
        losers_bracket: Losers bracket from Sleeper
        
    Returns:
        Dict with championship, third_place, and toilet_bowl game info
    """
    # Championship: winners bracket, round 3, placement 1
    championship = next(
        (m for m in winners_bracket if m.get('r') == 3 and m.get('p') == 1),
        None
    )
    
    # 3rd Place: winners bracket, round 3, placement 3
    third_place = next(
        (m for m in winners_bracket if m.get('r') == 3 and m.get('p') == 3),
        None
    )
    
    # Toilet Bowl (11th place game): losers bracket, round 2, placement 5
    # This happens in Week 16 (semifinals of consolation bracket)
    toilet_bowl = next(
        (m for m in losers_bracket if m.get('r') == 2 and m.get('p') == 5),
        None
    )
    
    def format_game(matchup):
        """Format matchup data consistently"""
        if not matchup:
            return None
        return {
            'teams': [matchup.get('t1'), matchup.get('t2')],
            'winner': matchup.get('w'),
            'loser': matchup.get('l'),
            'complete': matchup.get('w') is not None,
            'matchup_id': matchup.get('m'),
            'round': matchup.get('r')
        }
    
    return {
        'championship': format_game(championship),
        'third_place': format_game(third_place),
        'toilet_bowl': format_game(toilet_bowl)
    }


def get_special_game_participants(special_games: Dict[str, Any]) -> set:
    """
    Extract all roster IDs participating in special games.
    
    Args:
        special_games: Output from identify_special_games()
        
    Returns:
        Set of roster_ids in Championship, 3rd Place, or Toilet Bowl
    """
    participants = set()
    
    for game_name in ['championship', 'third_place', 'toilet_bowl']:
        game = special_games.get(game_name)
        if game and game.get('teams'):
            participants.update(game['teams'])
    
    return participants