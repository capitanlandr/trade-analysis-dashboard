"""
Property-Based Tests for Season Configuration Management
Tests universal correctness properties for season configuration validation
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Any

from utils.season_config import SeasonConfiguration, SeasonInfo, PipelineConfig, ImmutabilityViolation


# Strategy for generating valid season statuses
season_status_strategy = st.sampled_from(['active', 'static', 'unavailable'])

# Strategy for generating valid league IDs (non-placeholder)
valid_league_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Nd',)), 
    min_size=10, 
    max_size=20
).filter(lambda x: not any(placeholder in x.lower() for placeholder in ['placeholder', 'todo', 'change_me', 'xxx']))

# Strategy for generating placeholder league IDs
placeholder_league_id_strategy = st.sampled_from([
    'placeholder_id',
    'TODO_UPDATE_THIS',
    'CHANGE_ME_123',
    'xxx_placeholder_xxx'
])

# Strategy for generating season names
season_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_'),
    min_size=3,
    max_size=15
).filter(lambda x: x and not x.startswith('_') and not x.endswith('_'))

# Strategy for generating years
year_strategy = st.integers(min_value=2020, max_value=2030)


@st.composite
def season_info_strategy(draw, status=None, require_valid_league_id=True):
    """Generate SeasonInfo instances"""
    status = status or draw(season_status_strategy)
    
    if require_valid_league_id:
        league_id = draw(valid_league_id_strategy)
    else:
        league_id = draw(st.one_of(valid_league_id_strategy, placeholder_league_id_strategy, st.just("")))
    
    year = draw(year_strategy)
    description = f"Season {year} - {status}"
    
    return SeasonInfo(
        status=status,
        league_id=league_id,
        year=year,
        description=description,
        backfill_completed=draw(st.booleans()) if status == 'static' else None,
        last_incremental_fetch=None
    )


@st.composite
def pipeline_config_strategy(draw, season_names: List[str]):
    """Generate PipelineConfig instances"""
    # Ensure we don't have empty season_names
    assume(len(season_names) > 0)
    
    # Generate active and static seasons as subsets of available seasons
    active_seasons = draw(st.lists(st.sampled_from(season_names), unique=True, max_size=len(season_names)))
    static_seasons = draw(st.lists(st.sampled_from(season_names), unique=True, max_size=len(season_names)))
    
    return PipelineConfig(
        active_seasons=active_seasons,
        static_seasons=static_seasons,
        allow_static_refetch=draw(st.booleans()),
        cumulative_files={'trades': 'trades.json', 'waiver_wire': 'waiver-wire.json'},
        backup_before_append=draw(st.booleans()),
        validation={
            'require_league_ids': draw(st.booleans()),
            'check_season_conflicts': draw(st.booleans()),
            'validate_transaction_ids': draw(st.booleans())
        }
    )


@st.composite
def season_configuration_strategy(draw, valid_config=True):
    """Generate SeasonConfiguration instances"""
    # Generate season names
    season_names = draw(st.lists(season_name_strategy, min_size=1, max_size=5, unique=True))
    
    # Generate seasons dict
    seasons = {}
    for season_name in season_names:
        if valid_config:
            # For valid configs, ensure active seasons have valid league IDs
            seasons[season_name] = draw(season_info_strategy(require_valid_league_id=True))
        else:
            # For invalid configs, allow placeholder league IDs
            seasons[season_name] = draw(season_info_strategy(require_valid_league_id=False))
    
    # Generate pipeline config
    pipeline = draw(pipeline_config_strategy(season_names))
    
    # For valid configs, ensure no conflicts between active and static
    if valid_config:
        active_set = set(pipeline.active_seasons)
        static_set = set(pipeline.static_seasons)
        
        # Remove conflicts by prioritizing active seasons
        conflicts = active_set.intersection(static_set)
        for conflict in conflicts:
            pipeline.static_seasons.remove(conflict)
        
        # Ensure active seasons have active status and valid league IDs
        for season_name in pipeline.active_seasons:
            seasons[season_name].status = 'active'
            if not seasons[season_name].league_id or any(p in seasons[season_name].league_id.lower() for p in ['placeholder', 'todo', 'change_me', 'xxx']):
                seasons[season_name].league_id = draw(valid_league_id_strategy)
        
        # Ensure static seasons have static status
        for season_name in pipeline.static_seasons:
            seasons[season_name].status = 'static'
    
    return SeasonConfiguration(
        seasons=seasons,
        pipeline=pipeline,
        schema_version="2.0.0",
        last_updated=None,
        created_date="2025-12-31",
        migration_notes="Property test generated configuration"
    )


class TestSeasonConfigurationProperties:
    """Property-based tests for season configuration validation"""
    
    @given(season_configuration_strategy(valid_config=True))
    @settings(max_examples=50, deadline=5000)
    def test_valid_configurations_pass_validation(self, config: SeasonConfiguration):
        """
        Property 10: Configuration Validation
        Valid configurations should always pass validation without raising exceptions
        """
        # This should not raise any exceptions
        config.validate()
        
        # Additional invariants that should hold for valid configs
        active_set = set(config.pipeline.active_seasons)
        static_set = set(config.pipeline.static_seasons)
        
        # No conflicts between active and static
        assert len(active_set.intersection(static_set)) == 0
        
        # All referenced seasons exist
        all_referenced = active_set.union(static_set)
        defined_seasons = set(config.seasons.keys())
        assert all_referenced.issubset(defined_seasons)
        
        # Active seasons have valid league IDs (if validation enabled)
        if config.pipeline.validation.get('require_league_ids', True):
            for season_name in config.pipeline.active_seasons:
                season = config.seasons[season_name]
                assert season.league_id and season.league_id.strip() != ""
                
                # No placeholder patterns
                placeholder_patterns = ['placeholder', 'todo', 'change_me', 'xxx']
                assert not any(pattern.lower() in season.league_id.lower() for pattern in placeholder_patterns)
    
    @given(season_name_strategy, season_name_strategy)
    @settings(max_examples=30)
    def test_active_static_conflict_detection(self, season1: str, season2: str):
        """
        Property 10: Configuration Validation - Conflict Detection
        Configurations with seasons in both active and static lists should be rejected
        """
        assume(season1 != season2)  # Ensure different season names
        
        # Create seasons
        seasons = {
            season1: SeasonInfo(status='active', league_id='1234567890123456789', year=2024, description='Test Season 1'),
            season2: SeasonInfo(status='static', league_id='9876543210987654321', year=2023, description='Test Season 2')
        }
        
        # Create conflicting pipeline config (season1 in both lists)
        pipeline = PipelineConfig(
            active_seasons=[season1],
            static_seasons=[season1],  # Conflict!
            allow_static_refetch=False,
            cumulative_files={'trades': 'trades.json'},
            backup_before_append=True,
            validation={'require_league_ids': True, 'check_season_conflicts': True, 'validate_transaction_ids': True}
        )
        
        config = SeasonConfiguration(
            seasons=seasons,
            pipeline=pipeline,
            schema_version="2.0.0",
            last_updated=None,
            created_date="2025-12-31",
            migration_notes="Conflict test"
        )
        
        # Should raise ValueError due to conflict
        with pytest.raises(ValueError, match="Seasons cannot be both active and static"):
            config.validate()
    
    @given(season_name_strategy)
    @settings(max_examples=30)
    def test_placeholder_league_id_detection(self, season_name: str):
        """
        Property 10: Configuration Validation - Placeholder Detection
        Active seasons with placeholder league IDs should be rejected
        """
        placeholder_id = 'placeholder_league_id_123'
        
        seasons = {
            season_name: SeasonInfo(
                status='active', 
                league_id=placeholder_id, 
                year=2024, 
                description='Test Season'
            )
        }
        
        pipeline = PipelineConfig(
            active_seasons=[season_name],
            static_seasons=[],
            allow_static_refetch=False,
            cumulative_files={'trades': 'trades.json'},
            backup_before_append=True,
            validation={'require_league_ids': True, 'check_season_conflicts': True, 'validate_transaction_ids': True}
        )
        
        config = SeasonConfiguration(
            seasons=seasons,
            pipeline=pipeline,
            schema_version="2.0.0",
            last_updated=None,
            created_date="2025-12-31",
            migration_notes="Placeholder test"
        )
        
        # Should raise ValueError due to placeholder league ID
        with pytest.raises(ValueError, match="has placeholder league_id"):
            config.validate()
    
    @given(season_name_strategy)
    @settings(max_examples=30)
    def test_missing_league_id_detection(self, season_name: str):
        """
        Property 10: Configuration Validation - Missing League ID Detection
        Active seasons with missing league IDs should be rejected when validation is enabled
        """
        seasons = {
            season_name: SeasonInfo(
                status='active', 
                league_id='',  # Empty league ID
                year=2024, 
                description='Test Season'
            )
        }
        
        pipeline = PipelineConfig(
            active_seasons=[season_name],
            static_seasons=[],
            allow_static_refetch=False,
            cumulative_files={'trades': 'trades.json'},
            backup_before_append=True,
            validation={'require_league_ids': True, 'check_season_conflicts': True, 'validate_transaction_ids': True}
        )
        
        config = SeasonConfiguration(
            seasons=seasons,
            pipeline=pipeline,
            schema_version="2.0.0",
            last_updated=None,
            created_date="2025-12-31",
            migration_notes="Missing league ID test"
        )
        
        # Should raise ValueError due to missing league ID
        with pytest.raises(ValueError, match="missing league_id"):
            config.validate()
    
    @given(season_name_strategy, st.sampled_from(['unavailable', 'invalid_status']))
    @settings(max_examples=30)
    def test_invalid_season_status_detection(self, season_name: str, invalid_status: str):
        """
        Property 10: Configuration Validation - Invalid Status Detection
        Seasons with invalid statuses should be rejected
        """
        assume(invalid_status not in ['active', 'static', 'unavailable'])
        
        seasons = {
            season_name: SeasonInfo(
                status=invalid_status, 
                league_id='1234567890123456789', 
                year=2024, 
                description='Test Season'
            )
        }
        
        pipeline = PipelineConfig(
            active_seasons=[],
            static_seasons=[],
            allow_static_refetch=False,
            cumulative_files={'trades': 'trades.json'},
            backup_before_append=True,
            validation={'require_league_ids': True, 'check_season_conflicts': True, 'validate_transaction_ids': True}
        )
        
        config = SeasonConfiguration(
            seasons=seasons,
            pipeline=pipeline,
            schema_version="2.0.0",
            last_updated=None,
            created_date="2025-12-31",
            migration_notes="Invalid status test"
        )
        
        # Should raise ValueError for invalid status (unless it's 'unavailable' which is valid)
        if invalid_status != 'unavailable':
            with pytest.raises(ValueError, match="Invalid status"):
                config.validate()
    
    @given(season_configuration_strategy(valid_config=True))
    @settings(max_examples=30)
    def test_configuration_roundtrip_consistency(self, config: SeasonConfiguration):
        """
        Property 10: Configuration Validation - Roundtrip Consistency
        Configurations should maintain consistency through save/load cycles
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save configuration
            config.save(temp_path)
            
            # Load configuration
            loaded_config = SeasonConfiguration.load(temp_path)
            
            # Validate loaded configuration
            loaded_config.validate()
            
            # Check key properties are preserved
            assert loaded_config.schema_version == config.schema_version
            assert loaded_config.created_date == config.created_date
            assert len(loaded_config.seasons) == len(config.seasons)
            assert loaded_config.pipeline.active_seasons == config.pipeline.active_seasons
            assert loaded_config.pipeline.static_seasons == config.pipeline.static_seasons
            
            # Check season details are preserved
            for season_name, original_season in config.seasons.items():
                loaded_season = loaded_config.seasons[season_name]
                assert loaded_season.status == original_season.status
                assert loaded_season.league_id == original_season.league_id
                assert loaded_season.year == original_season.year
                assert loaded_season.description == original_season.description
        
        finally:
            # Clean up
            Path(temp_path).unlink(missing_ok=True)
    
    @given(season_name_strategy)
    @settings(max_examples=30)
    def test_immutability_violation_detection(self, season_name: str):
        """
        Property 10: Configuration Validation - Immutability Protection
        Operations on static seasons should raise ImmutabilityViolation
        """
        from utils.season_config import validate_season_operation, ImmutabilityViolation
        
        # Create a config with a static season
        seasons = {
            season_name: SeasonInfo(
                status='static', 
                league_id='1234567890123456789', 
                year=2024, 
                description='Static Test Season'
            )
        }
        
        pipeline = PipelineConfig(
            active_seasons=[],
            static_seasons=[season_name],
            allow_static_refetch=False,
            cumulative_files={'trades': 'trades.json'},
            backup_before_append=True,
            validation={'require_league_ids': True, 'check_season_conflicts': True, 'validate_transaction_ids': True}
        )
        
        config = SeasonConfiguration(
            seasons=seasons,
            pipeline=pipeline,
            schema_version="2.0.0",
            last_updated=None,
            created_date="2025-12-31",
            migration_notes="Immutability test"
        )
        
        # Save config to temporary file and set up global config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save(temp_path)
            
            # Mock the global config by temporarily replacing the file path
            import utils.season_config
            original_get_config = utils.season_config.get_season_config
            
            def mock_get_config():
                return SeasonConfiguration.load(temp_path)
            
            utils.season_config.get_season_config = mock_get_config
            
            # Test that modifying operations raise ImmutabilityViolation
            prohibited_operations = ['modify', 'fetch', 'update', 'delete']
            
            for operation in prohibited_operations:
                with pytest.raises(ImmutabilityViolation, match="Cannot .* static season"):
                    validate_season_operation(season_name, operation)
            
            # Test that read operations are allowed (should not raise)
            validate_season_operation(season_name, 'read')
        
        finally:
            # Restore original function and clean up
            utils.season_config.get_season_config = original_get_config
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])