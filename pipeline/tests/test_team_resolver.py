"""
Tests for team identity resolution system
"""

import pytest
import csv
import tempfile
from pathlib import Path
from utils.team_resolver import TeamResolver, TeamIdentityError, sync_team_identities


@pytest.fixture
def sample_mapping_file(tmp_path):
    """Create a sample team mapping CSV for testing"""
    mapping_file = tmp_path / "team_mapping.csv"
    
    with open(mapping_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['roster_id', 'sleeper_username', 'real_name', 'nickname', 
                        'current_team_name', 'week_7_team_name', 'historical_team_names', 'notes'])
        writer.writerow(['1', 'user1', 'Alice', 'Ali', 'Team Alice', 'Team Alice', 'Team Alice', 'Test user'])
        writer.writerow(['2', 'user2', 'Bob', 'Bob', 'Team Bob', 'Old Team Bob', 'Old Team Bob | Team Bob', 'Name changed'])
        writer.writerow(['3', 'user3', 'Charlie', 'Char', 'Team Charlie', 'Team Charlie', 'Team Charlie', 'Test user'])
    
    return str(mapping_file)


class TestTeamResolver:
    """Test TeamResolver class"""
    
    def test_initialization(self, sample_mapping_file):
        """Test resolver initializes correctly"""
        resolver = TeamResolver(sample_mapping_file)
        assert len(resolver.teams) == 3
        assert 1 in resolver.teams
        assert 2 in resolver.teams
        assert 3 in resolver.teams
    
    def test_missing_file_raises_error(self):
        """Test that missing mapping file raises TeamIdentityError"""
        with pytest.raises(TeamIdentityError):
            TeamResolver("nonexistent_file.csv")
    
    def test_get_by_roster_id(self, sample_mapping_file):
        """Test lookup by roster ID"""
        resolver = TeamResolver(sample_mapping_file)
        
        team = resolver.get_by_roster_id(1)
        assert team is not None
        assert team['real_name'] == 'Alice'
        assert team['current_team_name'] == 'Team Alice'
        
        # Non-existent roster
        assert resolver.get_by_roster_id(999) is None
    
    def test_get_by_username(self, sample_mapping_file):
        """Test lookup by Sleeper username"""
        resolver = TeamResolver(sample_mapping_file)
        
        team = resolver.get_by_username('user2')
        assert team is not None
        assert team['real_name'] == 'Bob'
        
        # Case insensitive
        team = resolver.get_by_username('USER2')
        assert team is not None
        
        # Non-existent user
        assert resolver.get_by_username('nonexistent') is None
    
    def test_get_by_real_name(self, sample_mapping_file):
        """Test lookup by real name"""
        resolver = TeamResolver(sample_mapping_file)
        
        team = resolver.get_by_real_name('Charlie')
        assert team is not None
        assert team['roster_id'] == '3'
        
        # Case insensitive
        team = resolver.get_by_real_name('charlie')
        assert team is not None
        
        # Non-existent name
        assert resolver.get_by_real_name('NonExistent') is None
    
    def test_get_by_current_team_name(self, sample_mapping_file):
        """Test lookup by current team name"""
        resolver = TeamResolver(sample_mapping_file)
        
        team = resolver.get_by_current_team_name('Team Bob')
        assert team is not None
        assert team['real_name'] == 'Bob'
        
        # Case insensitive
        team = resolver.get_by_current_team_name('team bob')
        assert team is not None
    
    def test_get_nickname(self, sample_mapping_file):
        """Test getting nickname"""
        resolver = TeamResolver(sample_mapping_file)
        
        assert resolver.get_nickname(1) == 'Ali'
        assert resolver.get_nickname(2) == 'Bob'
        assert 'Unknown' in resolver.get_nickname(999)
    
    def test_get_current_team_name(self, sample_mapping_file):
        """Test getting current team name"""
        resolver = TeamResolver(sample_mapping_file)
        
        assert resolver.get_current_team_name(1) == 'Team Alice'
        assert resolver.get_current_team_name(2) == 'Team Bob'
        assert 'Unknown' in resolver.get_current_team_name(999)
    
    def test_get_stable_identifier(self, sample_mapping_file):
        """Test getting stable identifier (real name)"""
        resolver = TeamResolver(sample_mapping_file)
        
        assert resolver.get_stable_identifier(1) == 'Alice'
        assert resolver.get_stable_identifier(3) == 'Charlie'
        assert 'Unknown' in resolver.get_stable_identifier(999)
    
    def test_list_all_teams(self, sample_mapping_file):
        """Test listing all teams"""
        resolver = TeamResolver(sample_mapping_file)
        
        teams = resolver.list_all_teams()
        assert len(teams) == 3
        assert teams[0]['roster_id'] == '1'  # Sorted by roster ID
        assert teams[1]['roster_id'] == '2'
        assert teams[2]['roster_id'] == '3'
    
    def test_update_team_name(self, sample_mapping_file):
        """Test updating team name"""
        resolver = TeamResolver(sample_mapping_file)
        
        # Update team name
        success = resolver.update_team_name(1, 'New Team Name')
        assert success is True
        
        # Verify update
        team = resolver.get_by_roster_id(1)
        assert team['current_team_name'] == 'New Team Name'
        
        # Verify historical names updated
        assert 'Team Alice' in team['historical_team_names']
        assert 'New Team Name' in team['historical_team_names']
        
        # Non-existent roster
        success = resolver.update_team_name(999, 'Some Name')
        assert success is False
    
    def test_update_team_name_no_change(self, sample_mapping_file):
        """Test updating to same name doesn't duplicate history"""
        resolver = TeamResolver(sample_mapping_file)
        
        original_history = resolver.teams[1]['historical_team_names']
        resolver.update_team_name(1, 'Team Alice')
        
        # History should not have duplicates
        assert resolver.teams[1]['historical_team_names'] == original_history
    
    def test_sync_with_sleeper_data(self, sample_mapping_file):
        """Test syncing with Sleeper API data"""
        resolver = TeamResolver(sample_mapping_file)
        
        # Mock Sleeper data
        rosters = [
            {'roster_id': 1, 'owner_id': 'owner1', 'metadata': {'team_name': 'Updated Team 1'}},
            {'roster_id': 2, 'owner_id': 'owner2', 'metadata': {'team_name': 'Team Bob'}},
            {'roster_id': 3, 'owner_id': 'owner3', 'metadata': {}},  # No team name
        ]
        
        users = [
            {'user_id': 'owner1', 'display_name': 'user1'},
            {'user_id': 'owner2', 'display_name': 'user2'},
            {'user_id': 'owner3', 'display_name': 'user3'},
        ]
        
        updates = resolver.sync_with_sleeper_data(rosters, users)
        
        # Should update roster 1 (name changed)
        assert updates >= 1
        assert resolver.get_current_team_name(1) == 'Updated Team 1'
    
    def test_validate_mapping(self, sample_mapping_file):
        """Test mapping validation"""
        resolver = TeamResolver(sample_mapping_file)
        
        # Should pass validation
        assert resolver.validate_mapping() is True


class TestSyncTeamIdentities:
    """Test sync_team_identities convenience function"""
    
    def test_sync_team_identities_success(self, sample_mapping_file):
        """Test successful team identity sync"""
        rosters = [
            {'roster_id': 1, 'owner_id': 'owner1', 'metadata': {'team_name': 'Synced Team'}},
        ]
        users = [
            {'user_id': 'owner1', 'display_name': 'user1'},
        ]
        
        updates = sync_team_identities(rosters, users, sample_mapping_file)
        assert updates >= 0  # May be 0 if no changes or 1 if updated
    
    def test_sync_with_invalid_file_raises_error(self):
        """Test sync with invalid file raises TeamIdentityError"""
        rosters = []
        users = []
        
        with pytest.raises(TeamIdentityError):
            sync_team_identities(rosters, users, "nonexistent.csv")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_mapping_file(self, tmp_path):
        """Test with empty mapping file"""
        empty_file = tmp_path / "empty.csv"
        with open(empty_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['roster_id', 'sleeper_username', 'real_name', 'nickname', 
                           'current_team_name', 'week_7_team_name', 'historical_team_names', 'notes'])
        
        resolver = TeamResolver(str(empty_file))
        assert len(resolver.teams) == 0
    
    def test_malformed_roster_id(self, tmp_path):
        """Test handling of malformed roster IDs"""
        bad_file = tmp_path / "bad.csv"
        with open(bad_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['roster_id', 'sleeper_username', 'real_name', 'nickname', 
                           'current_team_name', 'week_7_team_name', 'historical_team_names', 'notes'])
            writer.writerow(['not_a_number', 'user1', 'Alice', 'Ali', 'Team', 'Team', 'Team', 'bad'])
            writer.writerow(['2', 'user2', 'Bob', 'Bob', 'Team Bob', 'Team Bob', 'Team Bob', 'good'])
        
        resolver = TeamResolver(str(bad_file))
        # Should skip bad row and load good one
        assert len(resolver.teams) == 1
        assert 2 in resolver.teams