from unittest.mock import patch

from merge_mcp.constants import READ_SCOPE, WRITE_SCOPE
from merge_mcp.scope_manager import ScopeManager


def test_init(enabled_scopes):
    """Test initialization of ScopeManager."""
    requested_scopes = ["model1:read", "model2:write"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        mock_create_lookup.return_value = {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        
        assert manager.enabled_scopes == enabled_scopes
        assert manager.requested_scopes == requested_scopes
        assert manager.requested_scopes_lookup == {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}
        mock_create_lookup.assert_called_once_with(requested_scopes)


def test_create_requested_scopes_lookup():
    """Test _create_requested_scopes_lookup method."""
    enabled_scopes = []
    requested_scopes = ["model1:read", "model2:write"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        mock_create_lookup.return_value = {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        
        assert manager.requested_scopes_lookup == {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}
        mock_create_lookup.assert_called_once_with(requested_scopes)


def test_get_available_scopes_no_requested_scopes(enabled_scopes):
    """Test get_available_scopes when no scopes are requested."""
    requested_scopes = []
    
    manager = ScopeManager(enabled_scopes, requested_scopes)
    result = manager.get_available_scopes()
    
    # Should return all enabled scopes
    assert result == enabled_scopes
    assert result is not enabled_scopes  # Should be a copy


def test_get_available_scopes_with_requested_scopes(enabled_scopes):
    """Test get_available_scopes with requested scopes."""
    requested_scopes = ["model1:read", "model2:write"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        # Model1 has read requested, Model2 has write requested
        mock_create_lookup.return_value = {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        result = manager.get_available_scopes()
        
        # Expected results:
        # - Model1: read enabled (both requested and enabled), write disabled (not requested)
        # - Model2: read disabled (requested but not enabled), write disabled (requested but not enabled)
        # - Model3: not included (not requested)
        assert len(result) == 1
        assert result[0].model_name == "Model1"
        assert result[0].is_read_enabled is True
        assert result[0].is_write_enabled is False


def test_get_available_scopes_with_all_operations(enabled_scopes):
    """Test get_available_scopes with all operations requested."""
    requested_scopes = ["model1"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        # Model1 has all scopes requested
        mock_create_lookup.return_value = {"model1": {READ_SCOPE, WRITE_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        result = manager.get_available_scopes()
        
        # Expected results:
        # - Model1: both read and write enabled (both requested and enabled)
        # - Model2, Model3: not included (not requested)
        assert len(result) == 1
        assert result[0].model_name == "Model1"
        assert result[0].is_read_enabled is True
        assert result[0].is_write_enabled is True


def test_get_available_scopes_case_insensitivity(enabled_scopes):
    """Test get_available_scopes with case insensitivity."""
    requested_scopes = ["MODEL1:read"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        # Model1 has read requested (case insensitive)
        mock_create_lookup.return_value = {"model1": {READ_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        result = manager.get_available_scopes()
        
        assert len(result) == 1
        assert result[0].model_name == "Model1"
        assert result[0].is_read_enabled is True
        assert result[0].is_write_enabled is False


def test_get_available_scopes_no_matching_scopes(enabled_scopes):
    """Test get_available_scopes when no scopes match."""
    requested_scopes = ["model4:read"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        mock_create_lookup.return_value = {"model4": {READ_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        result = manager.get_available_scopes()
        
        # No scopes should match
        assert len(result) == 0


def test_get_available_scopes_with_logging(enabled_scopes, caplog):
    """Test that logging works correctly in get_available_scopes."""
    requested_scopes = ["model1:read"]
    
    with patch("merge_mcp.services.create_requested_scopes_lookup") as mock_create_lookup:
        mock_create_lookup.return_value = {"model1": {READ_SCOPE}}
        
        manager = ScopeManager(enabled_scopes, requested_scopes)
        
        with caplog.at_level("DEBUG"):
            result = manager.get_available_scopes()
            
            # Check that logging occurred
            assert "Added scope: Model1" in caplog.text
            assert "read: True" in caplog.text
            assert "write: False" in caplog.text