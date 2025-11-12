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