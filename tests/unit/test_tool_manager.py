import pytest
from unittest.mock import patch, MagicMock

from mcp.types import TextContent, Tool

from merge_mcp.types import RequestMeta, CommonModelScope
from merge_mcp.tool_manager import ToolManager


@pytest.mark.asyncio
async def test_create(mock_schema_index, mock_client):
    """Test the create class method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=mock_client):
        with patch("merge_mcp.tool_manager.ScopeManager") as mock_scope_manager_class:
            # Setup mock scope manager
            mock_scope_manager = MagicMock()
            mock_scope_manager.get_available_scopes.return_value = [
                CommonModelScope(model_name="Ticket", is_read_enabled=True, is_write_enabled=True)
            ]
            mock_scope_manager_class.return_value = mock_scope_manager
            
            # Test with provided schema_index
            with patch.object(ToolManager, "async_init") as mock_async_init:
                tool_manager = await ToolManager.create(mock_schema_index, ["ticket.read"])
                    
                # Check that the tool manager was initialized correctly
                assert tool_manager._schema_index == mock_schema_index
                assert tool_manager._requested_scopes == ["ticket.read"]
                assert tool_manager._enabled_scopes == mock_client.fetch_enabled_scopes.return_value
                mock_async_init.assert_awaited_once()
            
            # Test without schema_index
            with patch("merge_mcp.tool_manager.SchemaIndex") as mock_schema_index_class:
                mock_schema_index_class.return_value = mock_schema_index
                with patch.object(ToolManager, "async_init") as mock_async_init:
                    tool_manager = await ToolManager.create(requested_scopes=["ticket.read"])
                    
                    # Check that the tool manager was initialized correctly
                    assert tool_manager._schema_index == mock_schema_index
                    assert tool_manager._requested_scopes == ["ticket.read"]
                    assert tool_manager._enabled_scopes == mock_client.fetch_enabled_scopes.return_value
                    mock_async_init.assert_awaited_once()
                    
                    # Check that SchemaIndex was created with the correct arguments
                    mock_schema_index_class.assert_called_once_with(
                        mock_client.get_openapi_schema.return_value,
                        mock_scope_manager.get_available_scopes.return_value
                    )


@pytest.mark.asyncio
async def test_async_init(mock_schema_index):
    """Test the async_init method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        
        with patch.object(tool_manager, "fetch_tools") as mock_fetch_tools:
            mock_fetch_tools.return_value = [MagicMock(), MagicMock()]
            
            await tool_manager.async_init()
            
            # Check that fetch_tools was called
            mock_fetch_tools.assert_awaited_once()
            
            # Check that tools were set
            assert tool_manager._tools == mock_fetch_tools.return_value


def test_list_tools(mock_schema_index):
    """Test the list_tools method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._tools = [MagicMock(), MagicMock()]
        
        tools = tool_manager.list_tools()
        
        # Check that the correct tools were returned
        assert tools == tool_manager._tools


@pytest.mark.asyncio
async def test_fetch_tools(mock_schema_index):
    """Test the fetch_tools method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        
        # Mock _convert_operation_schema_to_tools
        with patch.object(tool_manager, "_convert_operation_schema_to_tools") as mock_convert:
            mock_convert.side_effect = [
                [Tool(name="tool1", description="Tool 1", inputSchema={})],
                [],  # Empty list to test filtering
                [Tool(name="tool2", description="Tool 2", inputSchema={})]
            ]
            
            tools = await tool_manager.fetch_tools()
            
            # Check that _convert_operation_schema_to_tools was called for each schema
            assert mock_convert.call_count == len(mock_schema_index.get_all_operation_schemas())
            
            # Check that the correct tools were returned (filtered and flattened)
            assert len(tools) == 2
            assert tools[0].name == "tool1"
            assert tools[1].name == "tool2"


@pytest.mark.asyncio
async def test_convert_operation_schema_to_tools_basic(mock_schema_index, mock_schema_parser):
    """Test the _convert_operation_schema_to_tools method with a basic schema."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._schema_parser = mock_schema_parser
        
        # Test with a basic schema (no model, no meta)
        operation_schema = {
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
        }
        
        # Mock the extract_input_schema_and_update_parameters to return a specific value
        input_schema = {
            "type": "object",
            "properties": {"page": {"type": "integer"}},
            "required": []
        }
        mock_schema_parser.extract_input_schema_and_update_parameters.return_value = input_schema
        mock_schema_parser.extract_input_schema_and_update_parameters.side_effect = None
        
        with patch.object(tool_manager, "_needs_model_schema", return_value=False):
            tools = await tool_manager._convert_operation_schema_to_tools(operation_schema)
            
            # Check that the correct tool was returned
            assert len(tools) == 1
            assert tools[0].name == "tickets_list"
            assert tools[0].description == "List all tickets"
            assert tools[0].inputSchema == input_schema


@pytest.mark.asyncio
async def test_convert_operation_schema_to_tools_meta(mock_schema_index, mock_schema_parser):
    """Test the _convert_operation_schema_to_tools method with a meta schema."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._schema_parser = mock_schema_parser
        
        # Test with a meta schema
        operation_schema = {
            "operationId": "tickets_meta_post_retrieve",
            "description": "Get metadata for creating a ticket",
            "method": "get",
            "endpoint": "/tickets/meta/post",
            "parameters": []
        }
        
        # Test with is_creating_meta_tool=False (should be ignored)
        tools = await tool_manager._convert_operation_schema_to_tools(operation_schema, is_creating_meta_tool=False)
        assert len(tools) == 0
        
        # Test with is_creating_meta_tool=True (should be included)
        tools = await tool_manager._convert_operation_schema_to_tools(operation_schema, is_creating_meta_tool=True)
        assert len(tools) == 1
        assert tools[0].name == "tickets_meta_post_retrieve"


@pytest.mark.asyncio
async def test_convert_operation_schema_to_tools_with_model_schema(mock_schema_index, mock_schema_parser, mock_client):
    """Test the _convert_operation_schema_to_tools method with a schema that needs a model schema."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=mock_client):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._schema_parser = mock_schema_parser
        tool_manager._client = mock_client
        
        # Test with a schema that needs a model schema
        operation_schema = {
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
        }
        
        # Fix: Create a specific input schema for testing
        input_schema = {
            "type": "object",
            "properties": {"model": {"type": "string"}},
            "required": ["model"]
        }
        mock_schema_parser.extract_input_schema_and_update_parameters.return_value = input_schema
        mock_schema_parser.extract_input_schema_and_update_parameters.side_effect = None
        
        # Case 1: Can populate with meta call
        with patch.object(tool_manager, "_needs_model_schema", return_value=True):
            with patch.object(tool_manager, "_can_populate_model_schema_with_meta_call", return_value=True):
                with patch.object(tool_manager, "_populate_model_schema_with_meta_call") as mock_populate:
                    # Fix: Make the mock awaitable
                    mock_populate.return_value = None
                    
                    tools = await tool_manager._convert_operation_schema_to_tools(operation_schema)
                    
                    # Check that _populate_model_schema_with_meta_call was called
                    mock_populate.assert_called_once_with(operation_schema, input_schema)
                    
                    # Check that the correct tool was returned
                    assert len(tools) == 1
                    assert tools[0].name == "tickets_create"
        
        # Case 2: Cannot populate with meta call, need to fetch associated meta tool
        with patch.object(tool_manager, "_needs_model_schema", return_value=True):
            with patch.object(tool_manager, "_can_populate_model_schema_with_meta_call", return_value=False):
                with patch.object(tool_manager, "_fetch_associated_meta_tool") as mock_fetch:
                    meta_tool = Tool(name="tickets_meta_post_retrieve", description="Meta tool", inputSchema={})
                    mock_fetch.return_value = meta_tool
                    
                    tools = await tool_manager._convert_operation_schema_to_tools(operation_schema)
                    
                    # Check that _fetch_associated_meta_tool was called
                    mock_fetch.assert_awaited_once_with(operation_schema)
                    
                    # Check that both tools were returned (meta tool first)
                    assert len(tools) == 2
                    assert tools[0] == meta_tool
                    assert tools[1].name == "tickets_create"
                    
                    # Check that the description was updated
                    assert meta_tool.name in tools[1].description


def test_needs_model_schema(mock_schema_index):
    """Test the _needs_model_schema method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        
        # Test with POST method and model property
        operation_schema = {"method": "post"}
        input_schema = {"properties": {"model": {"type": "string"}}}
        assert tool_manager._needs_model_schema(operation_schema, input_schema) is True
        
        # Test with PATCH method and model property
        operation_schema = {"method": "patch"}
        input_schema = {"properties": {"model": {"type": "string"}}}
        assert tool_manager._needs_model_schema(operation_schema, input_schema) is True
        
        # Test with GET method and model property
        operation_schema = {"method": "get"}
        input_schema = {"properties": {"model": {"type": "string"}}}
        assert tool_manager._needs_model_schema(operation_schema, input_schema) is False
        
        # Test with POST method but no model property
        operation_schema = {"method": "post"}
        input_schema = {"properties": {}}
        assert tool_manager._needs_model_schema(operation_schema, input_schema) is False


def test_can_populate_model_schema_with_meta_call(mock_schema_index):
    """Test the _can_populate_model_schema_with_meta_call method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        
        # Test with only model required
        input_schema = {"required": ["model"]}
        assert tool_manager._can_populate_model_schema_with_meta_call(input_schema) is True
        
        # Test with model and other fields required
        input_schema = {"required": ["model", "title"]}
        assert tool_manager._can_populate_model_schema_with_meta_call(input_schema) is False
        
        # Test with no model required
        input_schema = {"required": ["title"]}
        assert tool_manager._can_populate_model_schema_with_meta_call(input_schema) is False
        
        # Test with no required fields
        input_schema = {"required": []}
        assert tool_manager._can_populate_model_schema_with_meta_call(input_schema) is True


@pytest.mark.asyncio
async def test_populate_model_schema_with_meta_call(mock_schema_index, mock_client):
    """Test the _populate_model_schema_with_meta_call method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=mock_client):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._client = mock_client
        
        operation_schema = {
            "endpoint": "/tickets",
            "method": "post"
        }
        
        input_schema = {
            "properties": {
                "model": {"type": "string"}
            }
        }
        
        await tool_manager._populate_model_schema_with_meta_call(operation_schema, input_schema)
        
        # Check that call_associated_meta_endpoint was called
        mock_client.call_associated_meta_endpoint.assert_awaited_once_with("/tickets", "post")
        
        # Check that the input schema was updated
        assert "title" in input_schema["properties"]
        assert "description" in input_schema["properties"]


@pytest.mark.asyncio
async def test_fetch_associated_meta_tool(mock_schema_index, mock_schema_parser):
    """Test the _fetch_associated_meta_tool method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._schema_parser = mock_schema_parser
        
        operation_schema = {
            "operationId": "tickets_create",
            "method": "post"
        }
        
        # Fix: Make sure the mock returns the expected meta operation
        meta_operation = {
            "operationId": "tickets_meta_post_retrieve",
            "description": "Get metadata for creating a ticket",
            "method": "get",
            "endpoint": "/tickets/meta/post"
        }
        mock_schema_index.get_by_operation_id.return_value = meta_operation
        mock_schema_index.get_by_operation_id.side_effect = None
        
        # Mock _convert_operation_schema_to_tools to return a tool
        with patch.object(tool_manager, "_convert_operation_schema_to_tools") as mock_convert:
            meta_tool = Tool(name="tickets_meta_post_retrieve", description="Meta tool", inputSchema={})
            mock_convert.return_value = [meta_tool]
            # Fix: Make the mock awaitable
            mock_convert.side_effect = lambda *args, **kwargs: [meta_tool]
            
            result = await tool_manager._fetch_associated_meta_tool(operation_schema)
            
            # Check that get_by_operation_id was called with the correct ID
            mock_schema_index.get_by_operation_id.assert_called_with("tickets_meta_post_retrieve")
            
            # Fix: Check that _convert_operation_schema_to_tools was called correctly
            mock_convert.assert_called_once_with(meta_operation, is_creating_meta_tool=True)
            
            # Check that the correct meta tool was returned
            assert result.name == "tickets_meta_post_retrieve"


def test_build_request_from_schema_and_arguments(mock_schema_index):
    """Test the _build_request_from_schema_and_arguments method."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=MagicMock()):
        tool_manager = ToolManager(mock_schema_index, [])
        
        # Test with query, body, and path parameters
        schema = {
            "method": "get",
            "endpoint": "/tickets/{ticket_id}",
            "parameters": [
                {
                    "name": "ticket_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                },
                {
                    "name": "include_details",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "boolean"}
                },
                {
                    "name": "data",
                    "in": "body",
                    "required": False,
                    "schema": {"type": "object"}
                },
                {
                    "name": "Authorization",
                    "in": "header",
                    "required": True,
                    "schema": {"type": "string"}
                },
                {
                    "name": "include_deleted_data",  # This is in EXCLUDED_PARAMETERS
                    "in": "query",
                    "required": False,
                    "schema": {"type": "boolean"}
                }
            ]
        }
        
        arguments = {
            "ticket_id": "123",
            "include_details": True,
            "data": {"comment": "Test"},
            "Authorization": "Bearer token",  # This should be ignored (header)
            "include_deleted_data": True  # This should be ignored (excluded)
        }
        
        request_meta = tool_manager._build_request_from_schema_and_arguments(schema, arguments)
        
        # Check that the request was built correctly
        assert request_meta.method == "GET"
        assert request_meta.path == "/tickets/123"
        assert request_meta.query_params == {"include_details": True}
        assert request_meta.body_params == {"data": {"comment": "Test"}}
        assert "Authorization" not in request_meta.query_params
        assert "Authorization" not in request_meta.body_params
        assert "include_deleted_data" not in request_meta.query_params


@pytest.mark.asyncio
async def test_call_tool_success(mock_schema_index, mock_client):
    """Test the call_tool method with a successful call."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=mock_client):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._client = mock_client
        tool_manager._schema_index = mock_schema_index
        
        # Fix: Set up the schema that will be returned by get_by_operation_id
        operation_schema = {
            "operationId": "tickets_list",
            "description": "List all tickets",
            "method": "get",
            "endpoint": "/tickets",
            "parameters": []
        }
        mock_schema_index.get_by_operation_id.return_value = operation_schema
        mock_schema_index.get_by_operation_id.side_effect = None
        
        # Mock _build_request_from_schema_and_arguments
        with patch.object(tool_manager, "_build_request_from_schema_and_arguments") as mock_build:
            request_meta = RequestMeta(
                method="GET",
                path="/tickets",
                query_params={"page": 1},
                body_params={}
            )
            mock_build.return_value = request_meta
            
            result = await tool_manager.call_tool("tickets_list", {"page": 1})
            
            # Check that get_by_operation_id was called
            mock_schema_index.get_by_operation_id.assert_called_with("tickets_list")
            
            # Check that _build_request_from_schema_and_arguments was called
            mock_build.assert_called_once_with(operation_schema, {"page": 1})
            
            # Check that _make_request was called
            mock_client._make_request.assert_called_once_with(
                "GET", "/tickets", params={"page": 1}, data={},
                headers={"Content-Type": "application/json"}, with_retry=True
            )
            
            # Check that the correct result was returned
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Successfully called tickets_list" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_error(mock_schema_index, mock_client):
    """Test the call_tool method with an error."""
    with patch("merge_mcp.tool_manager.MergeAPIClient.get_instance", return_value=mock_client):
        tool_manager = ToolManager(mock_schema_index, [])
        tool_manager._client = mock_client
        tool_manager._schema_index = mock_schema_index
        
        # Mock _make_request to raise an exception
        mock_client._make_request.side_effect = Exception("API error")
        
        # Mock _build_request_from_schema_and_arguments
        with patch.object(tool_manager, "_build_request_from_schema_and_arguments") as mock_build:
            mock_build.return_value = RequestMeta(
                method="GET",
                path="/tickets",
                query_params={"page": 1},
                body_params={}
            )
            
            result = await tool_manager.call_tool("tickets_list", {"page": 1})
            
            # Check that the correct result was returned
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Failed to call tickets_list" in result[0].text
            assert "API error" in result[0].text