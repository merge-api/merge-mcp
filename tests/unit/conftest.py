from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from merge_mcp.client import MergeAPIClient
from merge_mcp.types import CommonModelScope


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("MERGE_API_KEY", "test_api_key")
    monkeypatch.setenv("MERGE_ACCOUNT_TOKEN", "test_account_token")
    monkeypatch.setenv("MERGE_TENANT", "US")
    
    # Clean up after test
    yield
    
    # Reset the singleton instance between tests
    MergeAPIClient._instance = None


@pytest.fixture
def mock_httpx_client():
    """Mock the httpx.AsyncClient for testing API requests."""
    with patch("httpx.AsyncClient") as mock_client:
        # Create a mock response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        # Set up the mock client to return the mock response
        client_instance = mock_client.return_value.__aenter__.return_value
        client_instance.request = AsyncMock(return_value=mock_response)
        
        yield client_instance, mock_response


@pytest.fixture
def merge_client(mock_env_vars):
    """Return a MergeAPIClient instance with mock environment variables."""
    return MergeAPIClient.get_instance()


@pytest.fixture
def mock_account_details_response() -> Dict[str, Any]:
    """Mock response for account details endpoint."""
    return {
        "category": "hris",
        "status": "active",
        "id": "test-account-id",
        "integration": {
            "name": "Test Integration",
            "category": "hris"
        }
    }


@pytest.fixture
def mock_enabled_scopes_response() -> Dict[str, Any]:
    """Mock response for enabled scopes endpoint."""
    return {
        "common_models": [
            {
                "model_name": "Employee",
                "model_permissions": {
                    "READ": {"is_enabled": True},
                    "WRITE": {"is_enabled": False}
                }
            },
            {
                "model_name": "Employment",
                "model_permissions": {
                    "READ": {"is_enabled": True},
                    "WRITE": {"is_enabled": True}
                }
            }
        ]
    }


@pytest.fixture
def mock_openapi_schema_response() -> Dict[str, Any]:
    """Mock response for OpenAPI schema endpoint."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Merge HRIS API",
            "version": "1.0.0"
        },
        "paths": {
            "/employees": {
                "get": {
                    "summary": "List Employees",
                    "operationId": "list_employees"
                }
            }
        }
    }


@pytest.fixture
def mock_http_error():
    """Mock an HTTP error response."""
    error_response = AsyncMock()
    error_response.status_code = 400
    error_response.text = '{"error": "Bad Request"}'
    
    http_error = httpx.HTTPStatusError(
        "400 Bad Request",
        request=AsyncMock(),
        response=error_response
    )
    http_error.response = error_response
    
    return http_error


@pytest.fixture
def enabled_scopes():
    """Fixture for enabled scopes."""
    return [
        CommonModelScope(model_name="Model1", is_read_enabled=True, is_write_enabled=True),
        CommonModelScope(model_name="Model2", is_read_enabled=True, is_write_enabled=False),
        CommonModelScope(model_name="Model3", is_read_enabled=False, is_write_enabled=True),
    ]

@pytest.fixture
def available_scopes():
    """Fixture for available scopes."""
    return [
        CommonModelScope(model_name="Ticket", is_read_enabled=True, is_write_enabled=True),
        CommonModelScope(model_name="Comment", is_read_enabled=True, is_write_enabled=False),
        CommonModelScope(model_name="RemoteUser", is_read_enabled=True, is_write_enabled=False),
        CommonModelScope(model_name="TimeOff", is_read_enabled=True, is_write_enabled=False),
    ]

@pytest.fixture
def mock_openapi_schema():
    """Fixture for a mock OpenAPI schema."""
    return {
        "paths": {
            "/tickets": {
                "get": {
                    "operationId": "tickets_list",
                    "tags": ["tickets"],
                    "parameters": [{"name": "param1", "in": "query"}]
                },
                "post": {
                    "operationId": "tickets_create",
                    "tags": ["tickets"],
                    "parameters": [{"name": "param2", "in": "body"}]
                }
            },
            "/comments": {
                "get": {
                    "operationId": "comments_list",
                    "tags": ["comments"],
                    "parameters": [{"name": "param3", "in": "query"}]
                }
            },
            "/users": {
                "get": {
                    "operationId": "users_list",
                    "tags": ["users"],
                    "parameters": [{"name": "param4", "in": "query"}]
                }
            },
            "/time-off": {
                "get": {
                    "operationId": "time_off_list",
                    "tags": ["time-off"],
                    "parameters": [{"name": "param5", "in": "query"}]
                }
            },
            "/multi-tag": {
                "get": {
                    "operationId": "multi_tag_list",
                    "tags": ["tickets", "comments"],
                    "parameters": [{"name": "param6", "in": "query"}]
                }
            }
        },
        "components": {
            "schemas": {
                "Ticket": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"}
                    }
                },
                "Comment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "body": {"type": "string"}
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_schema_index():
    """Fixture for a mock schema index."""
    schema_index = MagicMock()
    
    # Mock get_all_operation_schemas
    schema_index.get_all_operation_schemas.return_value = [
        {
            "operationId": "tickets_list",
            "description": "List all tickets",
            "method": "get",
            "endpoint": "/tickets",
            "parameters": [
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"}
                }
            ]
        },
        {
            "operationId": "tickets_create",
            "description": "Create a ticket",
            "method": "post",
            "endpoint": "/tickets",
            "parameters": [
                {
                    "name": "model",
                    "in": "body",
                    "required": True,
                    "schema": {"type": "string"}
                }
            ]
        },
        {
            "operationId": "tickets_meta_post_retrieve",
            "description": "Get metadata for creating a ticket",
            "method": "get",
            "endpoint": "/tickets/meta/post",
            "parameters": []
        }
    ]
    
    # Mock get_by_operation_id
    schema_index.get_by_operation_id.side_effect = lambda op_id: next(
        (schema for schema in schema_index.get_all_operation_schemas() if schema["operationId"] == op_id),
        None
    )
    
    return schema_index


@pytest.fixture
def mock_schema_parser():
    """Fixture for a mock schema parser."""
    parser = MagicMock()
    
    # Mock extract_input_schema_and_update_parameters
    parser.extract_input_schema_and_update_parameters.side_effect = lambda op_schema, _: {
        "type": "object",
        "properties": {
            "model": {"type": "string"} if "model" in [p["name"] for p in op_schema.get("parameters", [])]
            else {},
            "page": {"type": "integer"} if "page" in [p["name"] for p in op_schema.get("parameters", [])]
            else {}
        },
        "required": [p["name"] for p in op_schema.get("parameters", []) if p.get("required", False)]
    }
    
    return parser


@pytest.fixture
def mock_client():
    """Fixture for a mock MergeAPIClient."""
    client = AsyncMock()
    
    # Mock fetch_enabled_scopes
    client.fetch_enabled_scopes.return_value = [
        CommonModelScope(model_name="Ticket", is_read_enabled=True, is_write_enabled=True),
        CommonModelScope(model_name="User", is_read_enabled=True, is_write_enabled=False)
    ]
    
    # Mock get_openapi_schema
    client.get_openapi_schema.return_value = {"paths": {}}
    
    # Mock call_associated_meta_endpoint
    client.call_associated_meta_endpoint.return_value = {
        "request_schema": {
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"}
            }
        }
    }
    
    # Mock _make_request
    client._make_request.return_value = {"id": "123", "title": "Test Ticket"}
    
    return client