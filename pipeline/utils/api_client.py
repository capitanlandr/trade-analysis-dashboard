"""
API Client with Enhanced Retry Logic and Error Handling
Provides robust API calls with exponential backoff and rate limit handling
"""

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import requests
import logging
from typing import Dict, Any, Optional
import time
import random

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded - requires exponential backoff"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TimeoutError(APIError):
    """Request timeout"""
    pass


def log_retry_attempt(retry_state):
    """Log retry attempts for debugging"""
    logger.warning(f"Retrying API call (attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}")


@retry(
    stop=stop_after_attempt(5),  # Increased from 3 to 5 attempts for rate limits
    wait=wait_exponential(multiplier=2, min=4, max=60),  # Enhanced backoff: 4s, 8s, 16s, 32s, 60s
    retry=retry_if_exception_type((requests.exceptions.RequestException, APIError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
def fetch_with_retry(url: str, timeout: int = 10, params: Optional[Dict] = None) -> Any:
    """
    Fetch JSON from URL with enhanced retry and exponential backoff.
    
    Enhanced retry strategy for rate limits:
    - 5 attempts total (up from 3)
    - Exponential backoff: 4s, 8s, 16s, 32s, 60s (capped)
    - Jitter added to prevent thundering herd
    - Special handling for 429 rate limit responses
    - Respects Retry-After headers when available
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        params: Optional query parameters
    
    Returns:
        JSON response as dict or list
    
    Raises:
        APIError: If all retries exhausted
        RateLimitError: If rate limited (429) - will be retried automatically
        TimeoutError: If request times out
    """
    try:
        logger.debug(f"Fetching: {url}")
        
        # Add jitter to prevent thundering herd effect
        jitter = random.uniform(0.1, 0.5)
        time.sleep(jitter)
        
        response = requests.get(url, timeout=timeout, params=params)
        
        if response.status_code == 429:
            # Extract retry-after header if available
            retry_after = response.headers.get('Retry-After')
            retry_after_seconds = None
            
            if retry_after:
                try:
                    retry_after_seconds = int(retry_after)
                    logger.warning(f"Rate limited on {url}, retry after {retry_after_seconds}s")
                except ValueError:
                    logger.warning(f"Rate limited on {url}, invalid retry-after header: {retry_after}")
            else:
                logger.warning(f"Rate limited on {url}, no retry-after header")
            
            # Sleep for the retry-after duration if specified and reasonable
            if retry_after_seconds and 1 <= retry_after_seconds <= 300:  # Max 5 minutes
                logger.info(f"Sleeping for {retry_after_seconds}s as requested by API")
                time.sleep(retry_after_seconds)
            
            raise RateLimitError(f"Rate limited: {url}", retry_after_seconds)
        
        if response.status_code == 404:
            logger.debug(f"Not found: {url}")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        raise TimeoutError(f"Timeout: {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url}", exc_info=True)
        raise APIError(f"Request failed: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=2, max=30),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=before_sleep_log(logger, logging.INFO),
    reraise=True
)
def fetch_with_rate_limit_retry(url: str, timeout: int = 10, params: Optional[Dict] = None) -> Any:
    """
    Specialized fetch function with aggressive rate limit handling.
    
    This function is designed specifically for endpoints known to have strict rate limits.
    Uses more conservative retry strategy with longer waits.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        params: Optional query parameters
    
    Returns:
        JSON response as dict or list
    
    Raises:
        APIError: If all retries exhausted
        RateLimitError: If rate limited after all retries
        TimeoutError: If request times out
    """
    try:
        logger.debug(f"Fetching with rate limit retry: {url}")
        
        # More conservative jitter for rate-limited endpoints
        jitter = random.uniform(0.5, 1.5)
        time.sleep(jitter)
        
        response = requests.get(url, timeout=timeout, params=params)
        
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '60')  # Default to 60s
            try:
                retry_after_seconds = int(retry_after)
                logger.warning(f"Rate limited on {url}, will wait {retry_after_seconds}s")
                
                # Sleep for the full retry-after duration
                if retry_after_seconds <= 300:  # Max 5 minutes
                    time.sleep(retry_after_seconds)
                else:
                    time.sleep(60)  # Fallback to 1 minute
                    
            except ValueError:
                time.sleep(60)  # Fallback wait
            
            raise RateLimitError(f"Rate limited: {url}", retry_after_seconds)
        
        if response.status_code == 404:
            logger.debug(f"Not found: {url}")
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
    
    Enhanced retry configuration for better rate limit handling:
    - Increased total retries to 5
    - Longer backoff factor for rate limits
    - Additional status codes for retry
    
    Returns:
        Configured requests.Session
    """
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    
    retry_strategy = Retry(
        total=5,  # Increased from 3
        backoff_factor=3,  # Increased from 2 for longer waits
        status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],  # Added Cloudflare errors
        allowed_methods=["GET", "POST"],
        raise_on_status=False  # Let us handle status codes manually
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