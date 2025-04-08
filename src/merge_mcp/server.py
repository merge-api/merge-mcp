from typing import List, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from merge_mcp.client import MergeAPIClient
from merge_mcp.tool_manager import ToolManager


async def serve(scopes: List[str] | None = None) -> None:
    server = Server("merge-mcp")
    await MergeAPIClient.get_initialized_instance()
    tool_manager = await ToolManager.create(requested_scopes=scopes)

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available MCP tools."""
        return tool_manager.list_tools()

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for MCP tools."""
        return await tool_manager.call_tool(name, arguments)

    options = server.create_initialization_options()
    print("Starting server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)