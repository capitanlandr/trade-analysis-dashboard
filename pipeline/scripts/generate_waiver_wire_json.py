#!/usr/bin/env python3
"""
Generate waiver wire JSON for dashboard consumption.

This script fetches waiver wire and free agent transactions from the Sleeper API
and generates a clean JSON file for the dashboard to consume.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import pandas as pd
import requests
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from utils.team_resolver import TeamResolver
from utils.backup import BackupManager


class WaiverWireGenerator:
    """Generate waiver wire JSON for dashboard."""
    
    def __init__(self, config_path: str = "config/default.yaml"):
        """Initialize the generator."""
        self.config = self._load_config(config_path)
        self.league_id = self.config['league']['id']
        self.api_base = self.config['api']['sleeper']['base_url']
        self.team_resolver = TeamResolver()
        
        # Setup logging
        log_level = getattr(logging, self.config['logging']['level'].upper(), logging.INFO)
        setup_logging("Waiver Wire JSON Generator", log_level)
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def _fetch_api_data(self, endpoint: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch data from Sleeper API with retry logic."""
        url = f"{self.api_base}{endpoint}"
        
        try:
            self.logger.info(f"Fetching data from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise
    
    def fetch_transactions(self) -> List[Dict[str, Any]]:
        """Fetch all waiver wire and free agent transactions."""
        self.logger.info("Fetching waiver wire transactions...")
        
        all_transactions = []
        
        # Fetch transactions for multiple weeks to get comprehensive data
        # Start from week 1 and go through current week + a few extra
        for week in range(1, 20):  # Covers regular season + playoffs
            try:
                endpoint = f"/league/{self.league_id}/transactions/{week}"
                week_transactions = self._fetch_api_data(endpoint)
                
                if week_transactions:
                    # Filter for waiver and free agent transactions only
                    waiver_transactions = [
                        t for t in week_transactions 
                        if t.get('type') in ['waiver', 'free_agent']
                    ]
                    all_transactions.extend(waiver_transactions)
                    self.logger.info(f"Week {week}: Found {len(waiver_transactions)} waiver/FA transactions")
                else:
                    self.logger.info(f"Week {week}: No transactions found")
                    
            except Exception as e:
                self.logger.warning(f"Failed to fetch week {week} transactions: {e}")
                continue
        
        self.logger.info(f"Total transactions fetched: {len(all_transactions)}")
        return all_transactions
    
    def fetch_players(self) -> Dict[str, str]:
        """Fetch player data for name resolution."""
        self.logger.info("Fetching player data...")
        
        try:
            endpoint = "/players/nfl"
            players_data = self._fetch_api_data(endpoint)
            
            if not players_data:
                self.logger.warning("No player data received")
                return {}
            
            # Convert to player_id -> name mapping
            players = {}
            for player_id, player_info in players_data.items():
                if isinstance(player_info, dict):
                    first_name = player_info.get('first_name', '')
                    last_name = player_info.get('last_name', '')
                    full_name = f"{first_name} {last_name}".strip()
                    if full_name:
                        players[player_id] = full_name
                    else:
                        players[player_id] = f"Player {player_id}"
            
            self.logger.info(f"Loaded {len(players)} player names")
            return players
            
        except Exception as e:
            self.logger.error(f"Failed to fetch player data: {e}")
            return {}
    
    def process_transactions(self, transactions: List[Dict[str, Any]], players: Dict[str, str]) -> List[Dict[str, Any]]:
        """Process and clean transaction data."""
        self.logger.info("Processing transactions...")
        
        processed = []
        
        for transaction in transactions:
            try:
                # Skip None transactions
                if transaction is None:
                    continue
                    
                # Extract basic transaction info
                transaction_id = transaction.get('transaction_id', '')
                transaction_type = transaction.get('type', 'unknown')
                status = transaction.get('status', 'unknown')
                created = transaction.get('created', 0)
                status_updated = transaction.get('status_updated', 0)
                week = transaction.get('leg', 0)
                
                # Handle settings safely
                settings = transaction.get('settings') or {}
                waiver_bid = settings.get('waiver_bid', 0) or 0
                
                # Convert timestamps to readable dates
                created_date = datetime.fromtimestamp(created / 1000).strftime('%Y-%m-%d %H:%M:%S')
                status_updated_date = datetime.fromtimestamp(status_updated / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                # Process adds and drops
                adds = transaction.get('adds') or {}
                drops = transaction.get('drops') or {}
                
                # Create entries for each add/drop
                for player_id, roster_id in adds.items():
                    if roster_id:  # Skip null roster_ids
                        team_name = self.team_resolver.get_current_team_name(roster_id)
                        player_name = players.get(player_id, f"Player {player_id}")
                        
                        processed.append({
                            'transaction_id': str(transaction_id),
                            'type': transaction_type,
                            'action': 'add',
                            'status': status,
                            'team_name': team_name,
                            'roster_id': roster_id,
                            'player_name': player_name,
                            'player_id': str(player_id),
                            'waiver_bid': waiver_bid,
                            'week': week,
                            'created_date': created_date,
                            'status_updated_date': status_updated_date,
                            'notes': f"{transaction_type.replace('_', ' ').title()} transaction",
                            'sequence': transaction.get('settings', {}).get('seq'),
                            'priority': None  # Not available in basic transaction data
                        })
                
                for player_id, roster_id in drops.items():
                    if roster_id:  # Skip null roster_ids
                        team_name = self.team_resolver.get_current_team_name(roster_id)
                        player_name = players.get(player_id, f"Player {player_id}")
                        
                        processed.append({
                            'transaction_id': str(transaction_id),
                            'type': transaction_type,
                            'action': 'drop',
                            'status': status,
                            'team_name': team_name,
                            'roster_id': roster_id,
                            'player_name': player_name,
                            'player_id': str(player_id),
                            'waiver_bid': 0,  # Drops don't have bids
                            'week': week,
                            'created_date': created_date,
                            'status_updated_date': status_updated_date,
                            'notes': f"{transaction_type.replace('_', ' ').title()} transaction",
                            'sequence': transaction.get('settings', {}).get('seq'),
                            'priority': None
                        })
                        
            except Exception as e:
                self.logger.warning(f"Failed to process transaction {transaction.get('transaction_id', 'unknown')}: {e}")
                continue
        
        # Sort by created date (most recent first)
        processed.sort(key=lambda x: x['created_date'], reverse=True)
        
        self.logger.info(f"Processed {len(processed)} transaction records")
        return processed
    
    def generate_json(self) -> Dict[str, Any]:
        """Generate the complete waiver wire JSON."""
        self.logger.info("Starting waiver wire JSON generation...")
        
        # Fetch data
        transactions = self.fetch_transactions()
        players = self.fetch_players()
        
        # Process transactions
        processed_transactions = self.process_transactions(transactions, players)
        
        # Create final JSON structure
        waiver_data = {
            'all_transactions': processed_transactions
        }
        
        self.logger.info("Waiver wire JSON generation completed")
        return waiver_data
    
    def save_json(self, data: Dict[str, Any], output_path: str) -> None:
        """Save JSON data to file."""
        try:
            # Create backup of existing file if it exists
            if Path(output_path).exists():
                backup_manager = BackupManager()
                backup_manager.backup_file(output_path, "waiver_wire_json")
            
            # Save new data
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Waiver wire JSON saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON: {e}")
            raise


def main():
    """Main execution function."""
    try:
        generator = WaiverWireGenerator()
        
        # Generate the JSON data
        waiver_data = generator.generate_json()
        
        # Save to dashboard public directory
        output_path = "../dashboard/frontend/public/api-waiver-wire.json"
        generator.save_json(waiver_data, output_path)
        
        print(f"✅ Waiver wire JSON generated successfully!")
        print(f"📁 Output: {output_path}")
        print(f"📊 Total transactions: {len(waiver_data['all_transactions'])}")
        
    except Exception as e:
        print(f"❌ Error generating waiver wire JSON: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()