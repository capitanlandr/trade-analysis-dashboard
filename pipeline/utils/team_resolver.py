"""
Team Identity Resolution
Maps roster IDs to stable identities (real names, usernames, team names)
Handles team name changes and provides consistent lookups across the pipeline
"""

import csv
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime

from utils.logging_config import get_logger
from utils.validators import ValidationError

logger = get_logger(__name__)


class TeamIdentityError(Exception):
    """Raised when team identity operations fail"""
    pass


class TeamResolver:
    """
    Resolves team identities from roster IDs.
    
    Provides stable lookups even when team names change:
    - roster_id: Permanent identifier (never changes)
    - real_name: Stable person identifier
    - sleeper_username: Sleeper account name
    - current_team_name: Latest team name (updated automatically)
    - historical_team_names: Audit trail of all names used
    """
    
    def __init__(self, mapping_file: str = "team_identity_mapping.csv"):
        """
        Initialize resolver with team mapping file.
        
        Args:
            mapping_file: Path to team identity CSV
            
        Raises:
            TeamIdentityError: If mapping file doesn't exist or is invalid
        """
        self.mapping_file = Path(mapping_file)
        self.teams: Dict[int, Dict[str, str]] = {}
        self._load_mapping()
    
    def _load_mapping(self):
        """
        Load team mapping from CSV.
        
        Raises:
            TeamIdentityError: If file doesn't exist or is invalid
        """
        if not self.mapping_file.exists():
            raise TeamIdentityError(f"Team mapping file not found: {self.mapping_file}")
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        roster_id = int(row['roster_id'])
                        self.teams[roster_id] = row
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid row in team mapping: {e}")
                        continue
            
            logger.debug(f"Loaded {len(self.teams)} team identities from {self.mapping_file}")
            
        except Exception as e:
            raise TeamIdentityError(f"Failed to load team mapping: {e}")
    
    def get_by_roster_id(self, roster_id: int) -> Optional[Dict[str, str]]:
        """
        Get team info by roster ID (most reliable lookup).
        
        Args:
            roster_id: Sleeper roster ID
            
        Returns:
            Team info dict or None if not found
        """
        return self.teams.get(roster_id)
    
    def get_by_username(self, username: str) -> Optional[Dict[str, str]]:
        """
        Get team info by Sleeper username.
        
        Args:
            username: Sleeper username
            
        Returns:
            Team info dict or None if not found
        """
        for team in self.teams.values():
            if team['sleeper_username'].lower() == username.lower():
                return team
        return None
    
    def get_by_real_name(self, real_name: str) -> Optional[Dict[str, str]]:
        """
        Get team info by real name (stable identifier).
        
        Args:
            real_name: Person's real name
            
        Returns:
            Team info dict or None if not found
        """
        for team in self.teams.values():
            if team['real_name'].lower() == real_name.lower():
                return team
        return None
    
    def get_by_current_team_name(self, team_name: str) -> Optional[Dict[str, str]]:
        """
        Get team info by current team name.
        
        Args:
            team_name: Current team name
            
        Returns:
            Team info dict or None if not found
        """
        for team in self.teams.values():
            if team['current_team_name'].lower() == team_name.lower():
                return team
        return None
    
    def get_nickname(self, roster_id: int) -> str:
        """
        Get short nickname for roster ID.
        
        Args:
            roster_id: Sleeper roster ID
            
        Returns:
            Nickname or fallback identifier
        """
        team = self.get_by_roster_id(roster_id)
        return team['nickname'] if team else f"Unknown (roster {roster_id})"
    
    def get_current_team_name(self, roster_id: int) -> str:
        """
        Get current team name for roster ID.
        
        Args:
            roster_id: Sleeper roster ID
            
        Returns:
            Current team name or fallback identifier
        """
        team = self.get_by_roster_id(roster_id)
        return team['current_team_name'] if team else f"Unknown Team (roster {roster_id})"
    
    def get_stable_identifier(self, roster_id: int) -> str:
        """
        Get stable identifier (real name) for roster ID.
        Real names don't change, making them ideal for long-term references.
        
        Args:
            roster_id: Sleeper roster ID
            
        Returns:
            Real name or fallback identifier
        """
        team = self.get_by_roster_id(roster_id)
        return team['real_name'] if team else f"Unknown (roster {roster_id})"
    
    def list_all_teams(self) -> List[Dict[str, str]]:
        """
        Get list of all teams sorted by roster ID.
        
        Returns:
            List of team info dicts
        """
        return sorted(self.teams.values(), key=lambda x: int(x['roster_id']))
    
    def update_team_name(self, roster_id: int, new_team_name: str) -> bool:
        """
        Update current team name and track in historical names.
        
        Args:
            roster_id: Sleeper roster ID
            new_team_name: New team name
            
        Returns:
            True if updated, False if roster ID not found
        """
        if roster_id not in self.teams:
            logger.warning(f"Cannot update team name: roster_id {roster_id} not found")
            return False
        
        old_name = self.teams[roster_id]['current_team_name']
        
        # No change needed
        if old_name == new_team_name:
            logger.debug(f"Team name unchanged for roster {roster_id}: {new_team_name}")
            return True
        
        # Update current name
        self.teams[roster_id]['current_team_name'] = new_team_name
        
        # Update historical names if not already there
        historical = self.teams[roster_id]['historical_team_names']
        if old_name and old_name not in historical:
            self.teams[roster_id]['historical_team_names'] = f"{historical} | {old_name}".strip(' |')
        if new_team_name not in historical:
            self.teams[roster_id]['historical_team_names'] = f"{self.teams[roster_id]['historical_team_names']} | {new_team_name}".strip(' |')
        
        logger.info(f"Updated team name for roster {roster_id}: {old_name} → {new_team_name}")
        
        # Save updated mapping
        self._save_mapping()
        return True
    
    def sync_with_sleeper_data(self, rosters: List[Dict], users: List[Dict]) -> int:
        """
        Sync team names from Sleeper API data.
        Updates current_team_name for any changes detected.
        
        Checks both rosters and users endpoints for team names:
        - rosters[].metadata.team_name (less common)
        - users[].metadata.team_name (primary source)
        
        Args:
            rosters: List of roster dicts from Sleeper API
            users: List of user dicts from Sleeper API
            
        Returns:
            Number of team names updated
        """
        updates = 0
        
        # Create mapping of owner_id to user data for quick lookup
        user_map = {user['user_id']: user for user in users}
        
        for roster in rosters:
            roster_id = roster['roster_id']
            owner_id = roster.get('owner_id')
            
            # Try to get team name from multiple sources (in priority order)
            team_name = None
            
            # 1. Check roster metadata (less common but takes precedence if present)
            team_name = roster.get('metadata', {}).get('team_name')
            
            # 2. Check user metadata (primary source for team names)
            if not team_name and owner_id and owner_id in user_map:
                team_name = user_map[owner_id].get('metadata', {}).get('team_name')
            
            # Skip if no team name found
            if not team_name:
                continue
            
            # Check if this is actually a change
            current_name = self.get_current_team_name(roster_id)
            if current_name != team_name:
                if self.update_team_name(roster_id, team_name):
                    updates += 1
                    logger.info(f"Synced team name for roster {roster_id}: {current_name} → {team_name}")
        
        if updates > 0:
            logger.info(f"Synced {updates} team name changes from Sleeper data")
        else:
            logger.debug("No team name changes detected")
        
        return updates
    
    def _save_mapping(self):
        """
        Save updated mapping back to CSV.
        
        Raises:
            TeamIdentityError: If save fails
        """
        try:
            with open(self.mapping_file, 'w', encoding='utf-8', newline='') as f:
                fieldnames = ['roster_id', 'sleeper_username', 'real_name', 'nickname', 
                             'current_team_name', 'week_7_team_name', 'historical_team_names', 'notes']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for roster_id in sorted(self.teams.keys()):
                    writer.writerow(self.teams[roster_id])
            
            logger.debug(f"Saved team mapping to {self.mapping_file}")
            
        except Exception as e:
            raise TeamIdentityError(f"Failed to save team mapping: {e}")
    
    def validate_mapping(self) -> bool:
        """
        Validate team mapping for completeness and consistency.
        
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        if not self.teams:
            raise ValidationError("Team mapping is empty")
        
        # Check for required fields
        required_fields = ['roster_id', 'real_name', 'sleeper_username', 'current_team_name']
        for roster_id, team in self.teams.items():
            for field in required_fields:
                if not team.get(field):
                    raise ValidationError(f"Missing {field} for roster_id {roster_id}")
        
        # Check for duplicate roster IDs (should be impossible but validate anyway)
        if len(self.teams) != len(set(self.teams.keys())):
            raise ValidationError("Duplicate roster IDs found in team mapping")
        
        logger.debug("Team mapping validation passed")
        return True


def sync_team_identities(rosters: List[Dict], users: List[Dict], 
                         mapping_file: str = "team_identity_mapping.csv") -> int:
    """
    Convenience function to sync team identities from Sleeper data.
    Can be called from pipeline stages to keep mappings current.
    
    Args:
        rosters: List of roster dicts from Sleeper API
        users: List of user dicts from Sleeper API
        mapping_file: Path to team identity mapping CSV
        
    Returns:
        Number of team names updated
        
    Raises:
        TeamIdentityError: If sync fails
    """
    try:
        resolver = TeamResolver(mapping_file)
        updates = resolver.sync_with_sleeper_data(rosters, users)
        return updates
    except Exception as e:
        logger.error(f"Failed to sync team identities: {e}")
        raise TeamIdentityError(f"Team identity sync failed: {e}")