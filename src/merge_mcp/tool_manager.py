import logging
from typing import Any, Dict, List, Sequence, Union

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from merge_mcp.client import MergeAPIClient
from merge_mcp.constants import EXCLUDED_PARAMETERS
from merge_mcp.types import RequestMeta
from merge_mcp.schema_index import SchemaIndex
from merge_mcp.schema_parser import SchemaParser
from merge_mcp.scope_manager import ScopeManager

DEFAULT_TOOL_CALL_HEADERS = {
    "Content-Type": "application/json",
}

class ToolManager:
    """
    A class to manage tools for a Merge API client.
    
    This class handles the complex logic of parsing operation schemas, parameters,
    and request bodies to create standardized representations for tool creation.

    Attributes:
        _client: The Merge API client.
        _schema_index: The index of the OpenAPI schema for lookups.
        _requested_scopes: The requested scopes from the user.
        _enabled_scopes: The enabled scopes from the API.
        _tools: The constructed list of tools to be returned via the MCP list_tools endpoint.
        _schema_parser: The schema parser to help extract information from the OpenAPI schema.
        _scope_manager: The scope manager to help manage scopes.
    """
    def __init__(self, schema_index: SchemaIndex, requested_scopes: List[str]):
        # Get the client singleton instance directly
        self._client = MergeAPIClient.get_instance()
        self._schema_index = schema_index
        self._requested_scopes = requested_scopes
        self._enabled_scopes = []
        self._tools: list[Tool] = []
        self._schema_parser = SchemaParser()
        self._scope_manager = None

    @classmethod
    async def create(cls, schema_index: SchemaIndex = None, requested_scopes: List[str] = None) -> 'ToolManager':
        # Default to empty list if requested_scopes is None
        requested_scopes = requested_scopes or []
        
        # Get the client singleton instance directly
        client = MergeAPIClient.get_instance()
        
        enabled_scopes = await client.fetch_enabled_scopes()
        scope_manager = None

        # If schema_index is not provided, create it with available scopes
        if schema_index is None:
            # Get available scopes based on requested and enabled scopes
            scope_manager = ScopeManager(enabled_scopes, requested_scopes)
            available_scopes = scope_manager.get_available_scopes()
            open_api_schema = await client.get_openapi_schema()
            schema_index = SchemaIndex(open_api_schema, available_scopes)
        
        instance = cls(schema_index, requested_scopes or [])
        instance._enabled_scopes = enabled_scopes
        instance._scope_manager = scope_manager
        await instance.async_init()
        return instance
    
    async def async_init(self) -> None:
        self._tools = await self.fetch_tools()

    def list_tools(self) -> list[Tool]:
        return self._tools

    async def fetch_tools(self) -> List[Tool]:
        """
        Fetch tools concurrently using asyncio.gather for improved performance.

        Returns:
            A list of tools.
        """
        import asyncio
        
        # Create a list of coroutines to execute concurrently
        coroutines = [
            self._convert_operation_schema_to_tools(schema)
            for schema in self._schema_index.get_all_operation_schemas()
        ]
        
        # Execute all coroutines concurrently
        results = await asyncio.gather(*coroutines)
        
        # Flatten the results and filter out empty lists
        tools = [tool for result in results if result for tool in result]
        
        return tools

    async def _convert_operation_schema_to_tools(self, operation_schema: Dict[str, Any], is_creating_meta_tool: bool = False) -> List[Tool]:
        """
        Convert an operation schema from the OpenAPI schema to a mcp tool.

        Args:
            operation_schema: The operation schema from the OpenAPI schema.
            is_creating_meta_tool: A flag indicating if the operation is a meta operation. Meta tools are ignored by default, unless this flag is set to True.
        
        Returns:
            The converted tool, or None if the operation is not valid.
        """
        tools_to_return = []

        name = operation_schema["operationId"]
        description = operation_schema["description"]

        if "meta" in name and not is_creating_meta_tool:
            # Meta operations are ignored by default
            return []

        input_schema = self._schema_parser.extract_input_schema_and_update_parameters(operation_schema, self._schema_index)

        if self._needs_model_schema(operation_schema, input_schema):
            if self._can_populate_model_schema_with_meta_call(input_schema):
                try:
                    await self._populate_model_schema_with_meta_call(operation_schema, input_schema)
                except Exception as e:
                    logging.error(f"Failed to populate model schema with meta call for {name}: {e}")
                    return []
            else:
                # add associated meta endpoint tool and make sure "model" gets added to input schema
                associated_meta_tool = await self._fetch_associated_meta_tool(operation_schema)
                if associated_meta_tool:
                    description = f"{description}\n\n{associated_meta_tool.name} should be called before calling {name}."
                    operation_schema["description"] = description
                    tools_to_return.append(associated_meta_tool)

        tools_to_return.append(Tool(
            name=name,
            description=description,
            inputSchema=input_schema
        ))
        return tools_to_return
    
    def _needs_model_schema(self, operation_schema: Dict[str, Any], input_schema: Dict[str, Any]) -> bool:
        """
        Determine if a model schema needs to be added. A model schema is added when the operation is a POST or PATCH and the input schema has a model property.

        Args:
            operation_schema: The operation schema from the OpenAPI schema.
            input_schema: The input schema.
            
        Returns:
            A boolean indicating if a model schema needs to be added.
        """
        return operation_schema.get("method") in ["post", "patch"] and "model" in input_schema["properties"]
    
    def _can_populate_model_schema_with_meta_call(self, input_schema: Dict[str, Any]) -> bool:
        """
        Determine if a model schema can be populated with a meta call. This is true when the input schema has no required fields other than "model".
        
        Args:
            input_schema: The input schema.
            
        Returns:
            A boolean indicating if a model schema can be populated with a meta call.
        """
        return len([field for field in input_schema["required"] if field != "model"]) == 0
    
    async def _populate_model_schema_with_meta_call(self, operation_schema: Dict[str, Any], input_schema: Dict[str, Any]) -> None:
        """
        Populate the model schema by calling the associated meta endpoint.

        Args:
            operation_schema: The operation schema from the OpenAPI schema.
            input_schema: The input schema to add the meta tool to.
            
        Returns:
            None
        """
        input_schema_properties = input_schema["properties"]
        meta_schema = await self._client.call_associated_meta_endpoint(operation_schema["endpoint"], operation_schema["method"])
        input_schema_properties.update(meta_schema.get("request_schema", {}).get("properties", {}))
        return None
    
    async def _fetch_associated_meta_tool(self, operation_schema: Dict[str, Any]) -> Tool:
        """
        Fetch the associated meta tool for a given operation schema.
        
        Args:
            operation_schema: The operation schema from the OpenAPI schema.
            
        Returns:
            The associated meta tool.
        """
        name = operation_schema["operationId"]
        split_name = name.split("_", 1)
        if len(split_name) != 2:
            raise ValueError(f"Invalid operation ID: {name}")

        associated_meta_operation_id = f"{split_name[0]}_meta_{operation_schema['method']}_retrieve"
        associated_meta_operation = self._schema_index.get_by_operation_id(associated_meta_operation_id)
        if not associated_meta_operation:
            raise ValueError(f"Associated meta operation not found: {associated_meta_operation_id}")
        
        # update the description to note that this should be called before the main operation
        associated_meta_operation["description"] = f"{associated_meta_operation['description']}\n\nThis operation should be called before {name}."
        
        associated_tools = await self._convert_operation_schema_to_tools(associated_meta_operation, is_creating_meta_tool=True)
        return associated_tools[0]

    def _build_request_from_schema_and_arguments(self, schema: Dict[str, Any], arguments: Dict[str, Any]) -> RequestMeta:
        """
        Build a request from schema and arguments.
        
        Args:
            schema: The operation schema.
            arguments: The arguments provided for the operation.
            
        Returns:
            A RequestMeta object containing the request details.
        """
        method = schema.get("method").upper()
        path = schema.get("endpoint")

        request_meta = RequestMeta(
            method=method,
            path=path
        )
        
        # Group parameters by their location
        for parameter in schema.get("parameters", []):
            # Skip headers and excluded parameters
            if parameter.get("in") == "header" or parameter.get("name") in EXCLUDED_PARAMETERS:
                continue

            param_location = parameter.get("in")
            if param_location in ["query", "body", "path"]:
                param_name = parameter["name"]
                param_value = arguments.get(param_name)
                
                if param_value is not None:
                    if param_location == "query":
                        request_meta.query_params[param_name] = param_value
                    elif param_location == "body":
                        request_meta.body_params[param_name] = param_value
                    elif param_location == "path":
                        request_meta.path = request_meta.path.replace(f"{{{param_name}}}", str(param_value))
        
        return request_meta

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Sequence[Union[TextContent, ImageContent, EmbeddedResource]]:
        """
        Call a tool by name with the given arguments.

        Args:
            name: The name of the tool to call.
            arguments: The arguments to pass to the tool.
        
        Returns:
            A sequence of responses from the tool.
        """
        # Find the tool with the given name
        schema = self._schema_index.get_by_operation_id(name)
        request = self._build_request_from_schema_and_arguments(schema, arguments)

        # take upper case method
        try:
            response = await self._client._make_request(request.method, request.path, params=request.query_params, data=request.body_params, headers=DEFAULT_TOOL_CALL_HEADERS, with_retry=True)
            return [TextContent(type="text", text=f"Successfully called {name}, response: {response}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to call {name} with request: {request}, used schema: {schema}, and arguments: {arguments}, error: {str(e)}")]