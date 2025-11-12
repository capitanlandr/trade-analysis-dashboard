"""
Pytest Configuration and Shared Fixtures
Provides mock data and utilities for testing pipeline stages
"""

import pytest
import pandas as pd
from pathlib import Path
import json
from datetime import datetime


@pytest.fixture
def mock_trades_data():
    """Mock trade data for testing Stage 1 and Stage 2"""
    return {
        'metadata': {
            'league_id': 'test_league_123',
            'league_name': 'Test Dynasty League',
            'season': '2025',
            'current_week': 7,
            'fetch_timestamp': '2025-10-24T00:00:00',
            'total_trades': 2
        },
        'trades': [
            {
                'transaction_id': 'trade_001',
                'type': 'trade',
                'status': 'complete',
                'created': 1704067200000,  # 2024-01-01
                'roster_ids': [1, 2],
                'adds': {'9999': 1},  # Player to roster 1
                'draft_picks': [
                    {
                        'season': 2025,
                        'round': 1,
                        'owner_id': 1,
                        'roster_id': 2  # Originally roster 2's pick
                    }
                ],
                'waiver_budget': []
            },
            {
                'transaction_id': 'trade_002',
                'type': 'trade',
                'status': 'complete',
                'created': 1709251200000,  # 2024-03-01
                'roster_ids': [1, 2],
                'adds': {'8888': 2},
                'draft_picks': [
                    {
                        'season': 2026,
                        'round': 1,
                        'owner_id': 2,
                        'roster_id': 1
                    }
                ],
                'waiver_budget': [
                    {
                        'amount': 50,
                        'sender': 1,
                        'receiver': 2
                    }
                ]
            }
        ],
        'users': [
            {'user_id': 'user1', 'display_name': 'Manager A', 'username': 'managerA'},
            {'user_id': 'user2', 'display_name': 'Manager B', 'username': 'managerB'}
        ],
        'rosters': [
            {'roster_id': 1, 'owner_id': 'user1'},
            {'roster_id': 2, 'owner_id': 'user2'}
        ]
    }


@pytest.fixture
def mock_dynasty_values():
    """Mock DynastyProcess values for testing"""
    return pd.DataFrame({
        'player': [
            'Patrick Mahomes',
            'Josh Allen',
            'Justin Jefferson',
            '2025 Pick 1.01',
            '2025 Pick 1.05',
            '2025 Pick 1.10',
            '2026 1st',
            'Brock Bowers'  # Rookie from 2025 draft
        ],
        'value_2qb': [10000, 9500, 8000, 5430, 2558, 1232, 2500, 3500],
        'scrape_date': ['2025-10-24'] * 8
    })


@pytest.fixture
def mock_asset_transactions():
    """Mock asset transactions for testing Stage 3 and Stage 4"""
    return pd.DataFrame([
        {
            'trade_date': '2024-01-01',
            'trade_id': 'trade_001',
            'trade_status': 'complete',
            'trade_type': '2-team',
            'asset_type': 'player',
            'asset_name': 'Justin Jefferson',
            'receiving_team': 'Manager A',
            'giving_team': 'Manager B',
            'origin_owner': None,
            'roster_a': 'Manager A',
            'roster_b': 'Manager B'
        },
        {
            'trade_date': '2024-01-01',
            'trade_id': 'trade_001',
            'trade_status': 'complete',
            'trade_type': '2-team',
            'asset_type': 'pick',
            'asset_name': '2025 Round 1',
            'receiving_team': 'Manager B',
            'giving_team': 'Manager A',
            'origin_owner': 'Manager B',
            'roster_a': 'Manager A',
            'roster_b': 'Manager B'
        }
    ])


@pytest.fixture
def mock_cached_values():
    """
    Mock cached values for testing Stage 4.
    
    IMPORTANT: Creates DataFrame the same way production does (from dict)
    so it includes numpy types (int64, float64) that must be JSON serializable.
    """
    data = [
        {
            'asset_name': 'Justin Jefferson',
            'asset_type': 'player',
            'trade_date': '2024-01-01',
            'trade_id': 1001,  # Will become numpy.int64
            'trade_type': '2-team',
            'receiving_team': 'Manager A',
            'giving_team': 'Manager B',
            'origin_owner': None,
            'value_at_trade': 7500,  # Will become numpy.int64
            'value_current': 8000,   # Will become numpy.int64
            'value_source_at_trade': 'Git:abc1234',
            'value_source_current': 'DynastyProcess',
            'metadata': ''
        },
        {
            'asset_name': '2025 Round 1',
            'asset_type': 'pick',
            'trade_date': '2024-01-01',
            'trade_id': 1001,  # Will become numpy.int64
            'trade_type': '2-team',
            'receiving_team': 'Manager B',
            'giving_team': 'Manager A',
            'origin_owner': 'Manager B',
            'value_at_trade': 5430,  # Will become numpy.int64
            'value_current': 3500,   # Will become numpy.int64
            'value_source_at_trade': 'Tier:Early 1st',
            'value_source_current': 'Player:Brock Bowers',
            'metadata': "{'tier': 'Early'}"
        }
    ]
    return pd.DataFrame(data)


@pytest.fixture
def mock_multiteam_cached_values():
    """
    Mock cached values for a 3-team trade.
    
    Simulates production data with numpy types from pandas DataFrames.
    """
    data = [
        {
            'asset_name': 'Amon-Ra St. Brown',
            'asset_type': 'player',
            'trade_date': '2024-03-15',
            'trade_id': 2001,
            'trade_type': '3-team',
            'receiving_team': 'Manager A',
            'giving_team': 'Manager B',
            'origin_owner': None,
            'value_at_trade': 9000,
            'value_current': 9500,
            'value_source_at_trade': 'DynastyProcess',
            'value_source_current': 'DynastyProcess',
            'metadata': ''
        },
        {
            'asset_name': 'Rome Odunze',
            'asset_type': 'player',
            'trade_date': '2024-03-15',
            'trade_id': 2001,
            'trade_type': '3-team',
            'receiving_team': 'Manager B',
            'giving_team': 'Manager C',
            'origin_owner': None,
            'value_at_trade': 7000,
            'value_current': 7500,
            'value_source_at_trade': 'DynastyProcess',
            'value_source_current': 'DynastyProcess',
            'metadata': ''
        },
        {
            'asset_name': 'Rashee Rice',
            'asset_type': 'player',
            'trade_date': '2024-03-15',
            'trade_id': 2001,
            'trade_type': '3-team',
            'receiving_team': 'Manager C',
            'giving_team': 'Manager A',
            'origin_owner': None,
            'value_at_trade': 6000,
            'value_current': 8000,
            'value_source_at_trade': 'DynastyProcess',
            'value_source_current': 'DynastyProcess',
            'metadata': ''
        }
    ]
    return pd.DataFrame(data)


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for tests"""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def mock_pick_projections():
    """Mock 2026 pick projections"""
    return pd.DataFrame({
        'Team': ['Manager A', 'Manager B'],
        'Week2_2026_1st': [3500, 4500],
        'Week7_2026_1st': [2800, 5200],
        'Week7_2026_2nd': [800, 1200],
        'Week7_2026_3rd': [300, 450],
        'Week7_2026_4th': [100, 150]
    })


@pytest.fixture
def mock_draft_results():
    """Mock 2025 draft results"""
    return pd.DataFrame([
        {'Pick': 1, 'Round': 1, 'Pick in Round': 1, 'Owner': 'Manager A', 'Player': 'Caleb Williams'},
        {'Pick': 2, 'Round': 1, 'Pick in Round': 2, 'Owner': 'Manager B', 'Player': 'Marvin Harrison Jr'},
        {'Pick': 5, 'Round': 1, 'Pick in Round': 5, 'Owner': 'Manager A', 'Player': 'Brock Bowers'}
    ])