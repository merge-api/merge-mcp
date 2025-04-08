import re
from typing import Any, Dict, List, Optional

from merge_mcp.client import MergeAPIClient
from merge_mcp.constants import (
    IRREGULAR_TAG_MAP,
    READ_METHODS,
    READ_SCOPE,
    SINGULAR_TAGS,
    WRITE_METHODS,
    WRITE_SCOPE,
)
from merge_mcp.types import CommonModelScope

class SchemaIndex:
    """
    A class to index and manage an OpenAPI schema.

    Attributes:
        _merge_openapi: The OpenAPI schema.
        _index: The index of the OpenAPI schema.
            - The structure is { model: { method: [schema] } }
        _operation_id_to_schema_map: A map of operation IDs to schemas.
            - The structure is { operation_id: schema }
        _meta_schemas: A map of endpoint and method to meta schemas.
            - The structure is { endpoint_method: meta_schema }
    """

    def __init__(self, merge_openapi: dict, available_scopes: List[CommonModelScope]):
        self._merge_openapi = merge_openapi
        self._client = MergeAPIClient.get_instance()
        self._component_properties_map = self._build_component_properties_map(self._merge_openapi)
        self._tag_to_scope_availability = self._build_tag_to_scope_availability(available_scopes)
        self._index = self._build_index_for_available_scopes()
        self._operation_id_to_schema_map = self._build_operation_id_to_schema_map()

    def _build_index(self) -> dict:
        """Build a complete index of all schemas without fetching meta schemas.
        
        This is used when available_scopes is not provided.
        """
        paths = self._merge_openapi.get("paths", {})
        index = {}
        for endpoint, ops in paths.items():
            for method, schema in ops.items():
                tags = schema.get("tags", [])
                # First key is the model with a value of the method which is the key to a list of schemas
                for tag in tags:
                    if tag not in index:
                        index[tag] = {}
                    if method not in index[tag]:
                        index[tag][method] = []
                    index[tag][method].append({
                        **schema,
                        "endpoint": endpoint,
                        "method": method
                    })
        return index

    def _build_component_properties_map(self, openapi_schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        schema_component_keys = openapi_schema.get("components", {}).get("schemas", {}).keys()
        component_properties_map = {}
        for schema_component_key in schema_component_keys:
            component_properties_map[schema_component_key] = openapi_schema.get("components", {}).get("schemas", {}).get(schema_component_key)
        return component_properties_map

    def _build_tag_to_scope_availability(self, available_scopes: List[CommonModelScope]) -> Dict[str, Dict[str, bool]]:
        """
        Build a lookup dictionary of tags to scope availability from available scopes.

        Example:
            Input:
            [
                CommonModelScope(
                    model_name="Ticket",
                    is_read_enabled=True,
                    is_write_enabled=True
                ),
                CommonModelScope(
                    model_name="Comment",
                    is_read_enabled=True,
                    is_write_enabled=False
                )
            ]

            Output:
            {tickets: {read, write}, comments: {read}}

        Args:
            available_scopes: List of available scopes from the API

        Returns:
            A dictionary where keys are model names and values are dictionaries of read and write availability.
        """
        tag_to_scope_availability = {}
        for scope in available_scopes:
            model_tag = self._create_tag_from_model(scope.model_name)
            if model_tag:
                tag_to_scope_availability[model_tag] = {
                    READ_SCOPE: scope.is_read_enabled,
                    WRITE_SCOPE: scope.is_write_enabled
                }
        return tag_to_scope_availability


    def _create_tag_from_model(self, model: str) -> str:
        """
        Create a tag from a model name.

        The tag is the lowercase model name with an 's' appended. If the model name is in PascalCase,
        it converts the model name to kebab-case and then appends an 's'.

        Special cases for RemoteUser and tags that aren't pluralized.

        Args:
            model: The model name.
            
        Returns:
            The tag for the model.
        """
        if model in IRREGULAR_TAG_MAP:
            return IRREGULAR_TAG_MAP[model]
        
        # Insert an underscore before any uppercase letter that is not at the beginning,
        # then convert the entire string to lowercase and append an 's'
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '-', model).lower()
        if snake_case in SINGULAR_TAGS:
            return snake_case
        return snake_case + "s"

        
    def _build_index_for_available_scopes(self) -> dict:
        """
        Build an index filtered by available scopes
        
        Returns:
            The filtered index of the shape { tag: { method: [schema] } }.
        """
        paths = self._merge_openapi.get("paths", {})
        index = {}
        
        # Build index only for available models and operations
        for endpoint, ops in paths.items():
            for method, schema in ops.items():
                tags = schema.get("tags", [])
                # if all models aren't in available models, skip
                if not all(tag in self._tag_to_scope_availability for tag in tags):
                    continue

                # Skip if operation type doesn't match available permissions
                if method in READ_METHODS and not all(self._tag_to_scope_availability[tag][READ_SCOPE] for tag in tags):
                    continue
                if method in WRITE_METHODS and not all(self._tag_to_scope_availability[tag][WRITE_SCOPE] for tag in tags):
                    continue

                # Create schema entry
                schema_entry = {
                    **schema,
                    "endpoint": endpoint,
                    "method": method,
                }

                # Add to index
                for tag in tags:
                    if tag not in index:
                        index[tag] = {}
                    if method not in index[tag]:
                        index[tag][method] = []
                    index[tag][method].append(schema_entry)
        
        return index

    def _build_operation_id_to_schema_map(self) -> dict:
        # change this so we don't get the runtime error of dictionary changed size during iteration
        operation_id_to_schema_map = {}
        for _, methods in self._index.items():
            for _, schemas in methods.items():
                for schema in schemas:
                    operation_id_to_schema_map[schema.get("operationId")] = schema
        return operation_id_to_schema_map

    def get_all_operation_schemas(self) -> List[Dict[str, Any]]:
        return list(self._operation_id_to_schema_map.values())

    def update_schema_parameters_by_operation_id(self, operation_id: str, schema_parameters: List[Dict[str, Any]]) -> None:
        self._operation_id_to_schema_map[operation_id]["parameters"] = schema_parameters
    
    def get_by_operation_id(self, operation_id: str) -> Optional[Dict[str, Any]]:
        return self._operation_id_to_schema_map.get(operation_id)

    def get_schema_component_properties(self, component_name: str) -> Optional[Dict[str, Any]]:
        return self._component_properties_map.get(component_name)