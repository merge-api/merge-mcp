import logging
from typing import Dict, List, Set

from merge_mcp.constants import READ_SCOPE, WRITE_SCOPE
from merge_mcp.types import CommonModelScope

logger = logging.getLogger(__name__)

class ScopeManager:
    """
    A class to manage API scopes.
    
    This class handles the logic of filtering enabled scopes based on user requests
    and provides a clean interface for scope operations.
    """
    
    def __init__(self, enabled_scopes: List[CommonModelScope], requested_scopes: List[str]):
        """
        Initialize the ScopeManager.
        
        Args:
            enabled_scopes: List of enabled scopes from the API
            requested_scopes: List of requested scopes from the user
        """
        self.enabled_scopes = enabled_scopes
        self.requested_scopes = requested_scopes
        self.requested_scopes_lookup = self._create_requested_scopes_lookup()
        
    def _create_requested_scopes_lookup(self) -> Dict[str, Set[str]]:
        """
        Create a lookup dictionary from requested scopes.
        
        Returns:
            A dictionary where keys are model names and values are sets of operations.
        """
        from merge_mcp.services import create_requested_scopes_lookup
        return create_requested_scopes_lookup(self.requested_scopes)
    
    def get_available_scopes(self) -> List[CommonModelScope]:
        """
        Get available scopes based on enabled scopes and requested scopes.
        
        Returns:
            A list of available scopes.
        """
        if not self.requested_scopes:
            # If no scopes are requested, return all enabled scopes
            return self.enabled_scopes.copy()
            
        available_scopes = []
        
        for scope in self.enabled_scopes:
            model_name = scope.model_name.lower()
            
            # Skip if model not in requested scopes
            if model_name not in self.requested_scopes_lookup:
                continue
                
            # Get requested operations for this model
            requested_operations = self.requested_scopes_lookup[model_name]
            
            # Create filtered scope
            filtered_scope = CommonModelScope(
                model_name=scope.model_name,
                is_read_enabled=scope.is_read_enabled and (READ_SCOPE in requested_operations),
                is_write_enabled=scope.is_write_enabled and (WRITE_SCOPE in requested_operations)
            )
            
            # Add to available scopes if at least one operation is enabled
            if filtered_scope.is_read_enabled or filtered_scope.is_write_enabled:
                available_scopes.append(filtered_scope)
                logger.debug(f"Added scope: {filtered_scope.model_name} (read: {filtered_scope.is_read_enabled}, write: {filtered_scope.is_write_enabled})")
            
        return available_scopes
