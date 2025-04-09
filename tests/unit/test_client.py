import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from merge_mcp.client import MergeAPIClient, MergeClientError
from merge_mcp.types import CommonModelScope


def test_error_instantiation():
    """Test that MergeClientError can be instantiated with a message."""
    error = MergeClientError("Test error message")
    assert str(error) == "Test error message"


def test_singleton_pattern(mock_env_vars):
    """Test that MergeAPIClient follows the singleton pattern."""
    client1 = MergeAPIClient()
    client2 = MergeAPIClient()
        
    # Both instances should be the same object
    assert client1 is client2
        
    # Test get_instance class method
    client3 = MergeAPIClient.get_instance()
    assert client1 is client3
    
def test_initialization_with_env_vars(mock_env_vars):
    """Test client initialization with environment variables."""
    client = MergeAPIClient()
    
    assert client._api_key == "test_api_key"
    assert client._account_token == "test_account_token"
    assert client._tenant == "US"
    assert client._base_url == "https://api.merge.dev/"
    assert client._initialized is True

def test_initialization_with_explicit_params(monkeypatch):
    """Test client initialization with explicit parameters."""
    # Reset singleton for this test
    MergeAPIClient._instance = None
    
    # Set environment variables that should be overridden
    monkeypatch.setenv("MERGE_API_KEY", "env_api_key")
    monkeypatch.setenv("MERGE_ACCOUNT_TOKEN", "env_account_token")
    
    client = MergeAPIClient(
        api_key="explicit_api_key",
        account_token="explicit_account_token"
    )
    
    assert client._api_key == "explicit_api_key"
    assert client._account_token == "explicit_account_token"

def test_initialization_missing_api_key(monkeypatch):
    """Test that initialization fails when API key is missing."""
    # Reset singleton for this test
    MergeAPIClient._instance = None
    
    # Clear environment variables
    monkeypatch.delenv("MERGE_API_KEY", raising=False)
    monkeypatch.setenv("MERGE_ACCOUNT_TOKEN", "test_account_token")
    
    with pytest.raises(MergeClientError, match="Merge API key is required"):
        MergeAPIClient()

def test_initialization_missing_account_token(monkeypatch):
    """Test that initialization fails when account token is missing."""
    # Reset singleton for this test
    MergeAPIClient._instance = None
    
    # Clear environment variables
    monkeypatch.setenv("MERGE_API_KEY", "test_api_key")
    monkeypatch.delenv("MERGE_ACCOUNT_TOKEN", raising=False)
    
    with pytest.raises(MergeClientError, match="Merge account token is required"):
        MergeAPIClient()

def test_initialization_invalid_tenant(monkeypatch):
    """Test that initialization fails with invalid tenant."""
    # Reset singleton for this test
    MergeAPIClient._instance = None
    
    # Set environment variables
    monkeypatch.setenv("MERGE_API_KEY", "test_api_key")
    monkeypatch.setenv("MERGE_ACCOUNT_TOKEN", "test_account_token")
    monkeypatch.setenv("MERGE_TENANT", "INVALID")
    
    with pytest.raises(ValueError, match="Invalid tenant: INVALID"):
        MergeAPIClient()

def test_tenant_base_url_mapping(monkeypatch):
    """Test that different tenants map to the correct base URLs."""
    tenant_url_mapping = {
        "US": "https://api.merge.dev/",
        "EU": "https://api-eu.merge.dev/",
        "APAC": "https://api-ap.merge.dev/"
    }
    
    for tenant, expected_url in tenant_url_mapping.items():
        # Reset singleton for this test
        MergeAPIClient._instance = None
        
        # Set environment variables
        monkeypatch.setenv("MERGE_API_KEY", "test_api_key")
        monkeypatch.setenv("MERGE_ACCOUNT_TOKEN", "test_account_token")
        monkeypatch.setenv("MERGE_TENANT", tenant)
        
        client = MergeAPIClient()
        assert client._base_url == expected_url

@pytest.mark.asyncio
async def test_get_initialized_instance(mock_env_vars, mock_httpx_client):
    """Test get_initialized_instance class method."""
    client_instance, mock_response = mock_httpx_client
    
    # Mock the response for get_account_details
    mock_response.json.return_value = {"category": "hris"}
    
    # Reset singleton for this test
    MergeAPIClient._instance = None
    
    client = await MergeAPIClient.get_initialized_instance()
    
    # Verify that initialize_account_info was called
    assert client._category == "hris"
    assert client._account_info == {"category": "hris"}

@pytest.mark.asyncio
async def test_get_account_details(merge_client, mock_httpx_client, mock_account_details_response):
    """Test get_account_details method."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = mock_account_details_response
    
    result = await merge_client.get_account_details()
    
    # Verify the API call
    client_instance.request.assert_called_once()
    request_args = client_instance.request.call_args[1]
    assert request_args["method"] == "GET"
    assert "/api/hris/v1/account-details" in request_args["url"]
    
    # Verify the result
    assert result == {"category": "hris", "details": mock_account_details_response}

@pytest.mark.asyncio
async def test_get_account_details_error(merge_client, mock_httpx_client, mock_http_error):
    """Test get_account_details method when an error occurs."""
    client_instance, _ = mock_httpx_client
    client_instance.request.side_effect = mock_http_error
    
    with pytest.raises(MergeClientError, match="Failed to get account details"):
        await merge_client.get_account_details()

@pytest.mark.asyncio
async def test_initialize_account_info(merge_client, mock_httpx_client, mock_account_details_response):
    """Test initialize_account_info method."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = mock_account_details_response
    
    await merge_client.initialize_account_info()
    
    assert merge_client._account_info == mock_account_details_response
    assert merge_client._category == "hris"
    
    # Calling again should not make another API call
    client_instance.request.reset_mock()
    await merge_client.initialize_account_info()
    client_instance.request.assert_not_called()

def test_get_account_info(merge_client):
    """Test get_account_info method."""
    # When account info is not initialized
    assert merge_client.get_account_info() == {}
    
    # When account info is initialized
    merge_client._account_info = {"test": "data"}
    assert merge_client.get_account_info() == {"test": "data"}

@pytest.mark.asyncio
async def test_fetch_enabled_scopes(merge_client, mock_httpx_client, mock_enabled_scopes_response):
    """Test fetch_enabled_scopes method."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = mock_enabled_scopes_response
    
    result = await merge_client.fetch_enabled_scopes()
    
    # Verify the API call
    client_instance.request.assert_called_once()
    request_args = client_instance.request.call_args[1]
    assert request_args["method"] == "GET"
    assert "linked-account-scopes" in request_args["url"]
    
    # Verify the result
    assert len(result) == 2
    assert isinstance(result[0], CommonModelScope)
    assert result[0].model_name == "Employee"
    assert result[0].is_read_enabled is True
    assert result[0].is_write_enabled is False
    
    assert result[1].model_name == "Employment"
    assert result[1].is_read_enabled is True
    assert result[1].is_write_enabled is True

@pytest.mark.asyncio
async def test_fetch_enabled_scopes_error(merge_client, mock_httpx_client):
    """Test fetch_enabled_scopes method when an error occurs."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = {"error": "Invalid response"}  # Missing common_models
    
    with pytest.raises(MergeClientError, match="Failed to get enabled scopes"):
        await merge_client.fetch_enabled_scopes()

@pytest.mark.asyncio
async def test_get_openapi_schema(merge_client, mock_httpx_client, mock_openapi_schema_response):
    """Test get_openapi_schema method."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = mock_openapi_schema_response
    
    result = await merge_client.get_openapi_schema()
    
    # Verify the API call
    client_instance.request.assert_called_once()
    request_args = client_instance.request.call_args[1]
    assert request_args["method"] == "GET"
    assert "schema" in request_args["url"]
    assert request_args["headers"].get("Authorization") is None  # Should be unauthorized
    
    # Verify the result
    assert result == mock_openapi_schema_response

@pytest.mark.asyncio
async def test_call_associated_meta_endpoint(merge_client, mock_httpx_client):
    """Test call_associated_meta_endpoint method."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = {"meta": "data"}
    
    result = await merge_client.call_associated_meta_endpoint("/tickets", "get")
    
    # Verify the API call
    client_instance.request.assert_called_once()
    request_args = client_instance.request.call_args[1]
    assert request_args["method"] == "GET"
    assert "/tickets/meta/get" in request_args["url"]
    
    # Verify the result
    assert result == {"meta": "data"}

def test_construct_meta_endpoint(merge_client):
    """Test _construct_meta_endpoint method."""
    # Simple endpoint
    assert merge_client._construct_meta_endpoint("/tickets", "get") == "/tickets/meta/get"
    
    # Endpoint with ID
    assert merge_client._construct_meta_endpoint("/tickets/123", "get") == "/tickets/meta/get/123"
    
    # Complex endpoint
    assert merge_client._construct_meta_endpoint("/tickets/123/comments", "get") == "/tickets/meta/get/123/comments"

def test_get_headers(merge_client):
    """Test _get_headers method."""
    # Default headers
    headers = merge_client._get_headers()
    assert headers["Authorization"] == "Bearer test_api_key"
    assert headers["X-Account-Token"] == "test_account_token"
    assert "MCP-Session-ID" in headers
    assert headers["MCP-Session-ID"] == merge_client._session_id
    
    # Unauthorized headers
    headers = merge_client._get_headers(unauthorized=True)
    assert "Authorization" not in headers
    assert "X-Account-Token" not in headers
    assert "MCP-Session-ID" in headers
    assert headers["MCP-Session-ID"] == merge_client._session_id
    
    # Additional headers
    headers = merge_client._get_headers(additional_headers={"Custom-Header": "Value"})
    assert headers["Authorization"] == "Bearer test_api_key"
    assert headers["X-Account-Token"] == "test_account_token"
    assert headers["Custom-Header"] == "Value"
    assert "MCP-Session-ID" in headers
    assert headers["MCP-Session-ID"] == merge_client._session_id

def test_format_url(merge_client):
    """Test _format_url method."""
    # Full path
    merge_client._category = "hris"
    assert merge_client._format_url("/api/hris/v1/employees") == "https://api.merge.dev/api/hris/v1/employees"
    
    # Relative path with category
    assert merge_client._format_url("employees") == "https://api.merge.dev/api/hris/v1/employees"
    assert merge_client._format_url("/employees") == "https://api.merge.dev/api/hris/v1/employees"
    
    # Relative path without category
    merge_client._category = None
    assert merge_client._format_url("employees") == "https://api.merge.dev/employees"

def test_format_error_message(merge_client):
    """Test _format_error_message method."""
    error_msg = merge_client._format_error_message(
        "Error prefix",
        "Error suffix",
        1,
        3,
        "GET",
        "https://api.merge.dev/test",
        {"param": "value"},
        {"data": "value"}
    )
    
    assert "Error prefix" in error_msg
    assert "Error suffix" in error_msg
    assert "Attempt 1/3" in error_msg
    assert "GET request" in error_msg
    assert "https://api.merge.dev/test" in error_msg
    assert "param" in error_msg
    assert "data" in error_msg

@pytest.mark.asyncio
async def test_make_request_success(merge_client, mock_httpx_client):
    """Test _make_request method with successful response."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.return_value = {"success": True}
    
    result = await merge_client._make_request(
        "GET",
        "/api/hris/v1/employees",
        params={"param": "value"},
        data={"data": "value"},
        headers={"Custom-Header": "Value"}
    )
    
    # Verify the API call
    client_instance.request.assert_called_once()
    request_args = client_instance.request.call_args[1]
    assert request_args["method"] == "GET"
    assert "/api/hris/v1/employees" in request_args["url"]
    assert request_args["params"] == {"param": "value"}
    assert request_args["json"] == {"data": "value"}
    assert request_args["headers"]["Custom-Header"] == "Value"
    
    # Verify the result
    assert result == {"success": True}

@pytest.mark.asyncio
async def test_make_request_non_json_response(merge_client, mock_httpx_client):
    """Test _make_request method with non-JSON response."""
    client_instance, mock_response = mock_httpx_client
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
    mock_response.text = "Plain text response"
    
    result = await merge_client._make_request("GET", "/api/hris/v1/employees")
    
    # Verify the result
    assert result == "Plain text response"

@pytest.mark.asyncio
async def test_make_request_http_error(merge_client, mock_httpx_client, mock_http_error):
    """Test _make_request method with HTTP error."""
    client_instance, _ = mock_httpx_client
    client_instance.request.side_effect = mock_http_error
    
    with pytest.raises(MergeClientError, match="HTTP Error 400"):
        await merge_client._make_request("GET", "/api/hris/v1/employees")

@pytest.mark.asyncio
async def test_make_request_with_retry(merge_client, mock_httpx_client, mock_http_error):
    """Test _make_request method with retry on failure."""
    client_instance, mock_response = mock_httpx_client
    
    # First call fails, second succeeds
    client_instance.request.side_effect = [mock_http_error, mock_response]
    mock_response.json.return_value = {"success": True}
    
    # Mock asyncio.sleep to avoid actual delays
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        result = await merge_client._make_request(
            "GET",
            "/api/hris/v1/employees",
            with_retry=True,
            max_retries=2,
            backoff_factor=0.1
        )
    
    # Verify retry behavior
    assert client_instance.request.call_count == 2
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 0.1  # First backoff delay
    
    # Verify the result
    assert result == {"success": True}

@pytest.mark.asyncio
async def test_make_request_max_retries_exceeded(merge_client, mock_httpx_client, mock_http_error):
    """Test _make_request method when max retries are exceeded."""
    client_instance, _ = mock_httpx_client
    
    # All calls fail
    client_instance.request.side_effect = [mock_http_error, mock_http_error, mock_http_error]
    
    # Mock asyncio.sleep to avoid actual delays
    with patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(MergeClientError, match="HTTP Error 400"):
            await merge_client._make_request(
                "GET",
                "/api/hris/v1/employees",
                with_retry=True,
                max_retries=3,
                backoff_factor=0.1
            )
    
    # Verify retry behavior
    assert client_instance.request.call_count == 3

@pytest.mark.asyncio
async def test_make_request_unexpected_error(merge_client, mock_httpx_client):
    """Test _make_request method with unexpected error."""
    client_instance, _ = mock_httpx_client
    
    # Raise an unexpected error
    client_instance.request.side_effect = Exception("Unexpected error")
    
    # Mock asyncio.sleep to avoid actual delays
    with patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(MergeClientError, match="Unexpected error"):
            await merge_client._make_request(
                "GET",
                "/api/hris/v1/employees",
                with_retry=True,
                max_retries=2,
                backoff_factor=0.1
            )
    
    # Verify retry behavior
    assert client_instance.request.call_count == 2


@pytest.mark.asyncio
async def test_session_id(merge_client):
    """Test that session_id is properly initialized and used in headers."""
    # Reset singleton for this test
    MergeAPIClient._instance = None

    # Create a new client instance
    with patch.dict('os.environ', {
        'MERGE_API_KEY': 'test_api_key',
        'MERGE_ACCOUNT_TOKEN': 'test_account_token',
        'MERGE_TENANT': 'US'
    }), patch('httpx.AsyncClient') as mock_client:
        client = merge_client

        # Test that session_id is initialized as a UUID string
        assert client._session_id is not None
        assert isinstance(client._session_id, str)

        # UUID should be 36 characters in the format 8-4-4-4-12
        assert len(client._session_id) == 36

        # Store the session_id for later comparison
        session_id = client._session_id

        # Test that session_id is included in headers
        headers = client._get_headers()
        assert headers["MCP-Session-ID"] == session_id

        # Test that the same session_id is used for all requests
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = AsyncMock()
            mock_response.json = AsyncMock(return_value={"data": "test"})

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            await client._make_request("GET", "test-endpoint")

            # Verify the session_id was included in the request headers
            call_kwargs = mock_client.return_value.__aenter__.return_value.request.call_args[1]
            assert "headers" in call_kwargs
            assert "MCP-Session-ID" in call_kwargs["headers"]
            assert call_kwargs["headers"]["MCP-Session-ID"] == session_id
