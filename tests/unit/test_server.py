"""Unit tests for the server module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from merge_mcp.server import serve
from merge_mcp.client import MergeAPIClient


@pytest.mark.asyncio
async def test_serve_initializes_server():
    """Test that serve initializes the server with the correct name."""
    with patch("merge_mcp.server.Server") as mock_server_class, patch(
        "merge_mcp.server.stdio_server"
    ) as mock_stdio_server, patch(
        "merge_mcp.server.MergeAPIClient.get_initialized_instance"
    ) as mock_get_initialized_instance, patch(
        "merge_mcp.server.ToolManager.create"
    ) as mock_tool_manager_create:
        # Setup mocks for Server
        mock_server = MagicMock()
        # Replace the async 'run' method with an AsyncMock so that when it's called,
        # the returned coroutine is awaitable.
        mock_server.run = AsyncMock()
        mock_server_class.return_value = mock_server

        # Mock create_initialization_options
        mock_initialization_options = MagicMock()
        mock_server.create_initialization_options.return_value = (
            mock_initialization_options
        )

        # Setup mock for MergeAPIClient.get_initialized_instance
        mock_api_client = MagicMock()
        mock_get_initialized_instance.return_value = mock_api_client

        # Setup mock for ToolManager.create
        mock_tool_manager = MagicMock()
        mock_tool_manager.list_tools.return_value = []
        mock_tool_manager.call_tool = AsyncMock()
        mock_tool_manager_create.return_value = mock_tool_manager

        # Setup for stdio_server
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_stdio_context = MagicMock()
        # Ensure __aenter__ is treated as async:
        mock_stdio_context.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )
        mock_stdio_server.return_value = mock_stdio_context

        # Call function under test
        await serve()

        # Verify server was initialized correctly
        mock_server_class.assert_called_once_with("merge-mcp")
        mock_get_initialized_instance.assert_called_once()
        mock_tool_manager_create.assert_called_once_with(requested_scopes=None)
        mock_server.run.assert_called_once_with(
            mock_read_stream, mock_write_stream, mock_initialization_options
        )
