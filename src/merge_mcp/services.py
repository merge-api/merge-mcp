from typing import Tuple, Optional
from merge_mcp.constants import ALL_SCOPES
from collections import defaultdict
from typing import Dict, Set, List

def extract_model_name_and_scope_from_requested_scope(scope: str) -> Tuple[str, Optional[str]]:
    """
    Extract model name and scope from requested scope.

    Args:
        scope: The scope to extract from.
        
    Returns:
        A tuple containing the model name and scope.
    """
    # Remove category prefix if present
    model_name_and_scope = scope.split(".", 1)[1] if "." in scope else scope

    # Split model name and scope
    model_name, scope = model_name_and_scope.split(":", 1) if ":" in model_name_and_scope else (model_name_and_scope, None)
    model_name = model_name.lower()
    scope = scope.lower() if scope else None
    if scope and scope not in ALL_SCOPES:
        raise ValueError(f"Invalid scope: {scope}")
    return model_name, scope


def create_requested_scopes_lookup(requested_scopes: List[str]) -> Dict[str, Set[str]]:
    """
    Create a lookup dictionary from requested scopes.
    
    Args:
        requested_scopes: List of requested scopes from the user
        
    Returns:
        A dictionary where keys are model names and values are sets of operations.
    """
    lookup = defaultdict(set)
    for scope in requested_scopes:
        model_name, scope = extract_model_name_and_scope_from_requested_scope(scope)
        if scope and scope not in ALL_SCOPES:
            raise ValueError(f"Invalid scope: {scope}")
        lookup[model_name].update([scope] if scope else ALL_SCOPES)
    return lookup