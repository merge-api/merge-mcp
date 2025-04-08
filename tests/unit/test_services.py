import pytest
from merge_mcp.constants import ALL_SCOPES, READ_SCOPE, WRITE_SCOPE
from merge_mcp.services import (
    extract_model_name_and_scope_from_requested_scope,
    create_requested_scopes_lookup,
)


def test_with_category_prefix_and_scope():
    # Test with category prefix and scope
    result = extract_model_name_and_scope_from_requested_scope("category.model:read")
    assert result == ("model", "read")


def test_without_category_prefix_with_scope():
    # Test without category prefix but with scope
    result = extract_model_name_and_scope_from_requested_scope("model:write")
    assert result == ("model", "write")

def test_with_category_prefix_without_scope():
    # Test with category prefix but without scope
    result = extract_model_name_and_scope_from_requested_scope("category.model")
    assert result == ("model", None)

def test_without_category_prefix_without_scope():
    # Test without category prefix and without scope
    result = extract_model_name_and_scope_from_requested_scope("model")
    assert result == ("model", None)

def test_case_insensitivity():
    # Test case insensitivity
    result = extract_model_name_and_scope_from_requested_scope("CaTeGoRy.MoDeL:ReAd")
    assert result == ("model", "read")

def test_invalid_scope():
    # Test invalid scope
    with pytest.raises(ValueError, match="Invalid scope: invalid_scope"):
        extract_model_name_and_scope_from_requested_scope("model:invalid_scope")

def test_with_single_scope():
    # Test with a single scope
    result = create_requested_scopes_lookup(["model:read"])
    assert result == {"model": {READ_SCOPE}}

def test_with_multiple_scopes_same_model():
    # Test with multiple scopes for the same model
    result = create_requested_scopes_lookup(["model:read", "model:write"])
    assert result == {"model": {READ_SCOPE, WRITE_SCOPE}}

def test_with_multiple_models():
    # Test with multiple models
    result = create_requested_scopes_lookup(["model1:read", "model2:write"])
    assert result == {"model1": {READ_SCOPE}, "model2": {WRITE_SCOPE}}

def test_with_category_prefix():
    # Test with category prefix
    result = create_requested_scopes_lookup(["category.model:read"])
    assert result == {"model": {READ_SCOPE}}

def test_without_scope_defaults_to_all_scopes():
    # Test that when no scope is provided, it defaults to ALL_SCOPES
    result = create_requested_scopes_lookup(["model"])
    assert result == {"model": set(ALL_SCOPES)}

def test_mixed_scopes_and_no_scopes():
    # Test with a mix of scopes and no scopes
    result = create_requested_scopes_lookup(["model1:read", "model2"])
    assert result == {"model1": {READ_SCOPE}, "model2": set(ALL_SCOPES)}

def test_invalid_scope():
    # Test with invalid scope
    with pytest.raises(ValueError, match="Invalid scope: invalid_scope"):
        create_requested_scopes_lookup(["model:invalid_scope"])

def test_empty_list():
    # Test with empty list
    result = create_requested_scopes_lookup([])
    assert result == {}