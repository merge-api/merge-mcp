import logging
from typing import Any, Dict, Optional, Tuple

from merge_mcp.constants import EXCLUDED_PARAMETERS
from merge_mcp.schema_index import SchemaIndex

logger = logging.getLogger(__name__)

class SchemaParser:
    """
    A class responsible for parsing OpenAPI schemas and extracting structured information.
    This class handles the complex logic of parsing operation schemas, parameters, and
    request bodies to create standardized representations for tool creation.
    """

    def __init__(self):
        """Initialize the SchemaParser."""
        pass

    def extract_input_schema_and_update_parameters(self, operation_schema: Dict[str, Any], schema_index: SchemaIndex) -> Dict[str, Any]:
        """
        Extract the input schema properties and required fields from an operation schema.
        
        Args:
            operation_schema: The operation schema to extract from.
            schema_index: The schema index to use for resolving schema components.
            
        Returns:
            A dictionary containing the properties and required fields of the input schema.
        """
        input_schema_properties = {}
        input_schema_required_fields = []
        
        # Extract path and query parameters
        path_and_query_params = self.extract_path_and_query_parameters(operation_schema)
        input_schema_properties.update(path_and_query_params["properties"])
        input_schema_required_fields.extend(path_and_query_params["required"])
        
        # Extract request body if it exists, and update parameters
        body_properties = self.extract_request_body_properties_and_update_parameters(operation_schema, schema_index)
        if body_properties:
            input_schema_properties.update(body_properties.get("properties", {}))
            input_schema_required_fields.extend(body_properties.get("required", []))
            updated_parameters = operation_schema.get("parameters", [])
            for property, property_schema in body_properties.get("properties", {}).items():
                updated_parameters.append({
                    "name": property,
                    "in": "body",
                    "required": property in input_schema_required_fields,
                    "schema": property_schema
                })
            schema_index.update_schema_parameters_by_operation_id(operation_schema["operationId"], updated_parameters)
            
        return {
            "type": "object",
            "properties": input_schema_properties,
            "required": input_schema_required_fields
        }

    def extract_path_and_query_parameters(self, operation_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract path and query parameters from an operation schema.
        
        Args:
            operation_schema: The operation schema to extract from.
            
        Returns:
            A dictionary with properties and required fields.
        """
        result = {
            "properties": {},
            "required": []
        }
        
        if "parameters" not in operation_schema:
            return result
            
        for param in operation_schema["parameters"]:
            if param["name"] in EXCLUDED_PARAMETERS or param["in"] == "header":
                continue

            param_property, is_required = self.convert_parameter_to_property(param)
            result["properties"][param["name"]] = param_property
            if is_required:
                result["required"].append(param["name"])
                
        return result

    def extract_request_body_properties_and_update_parameters(self, operation_schema: Dict[str, Any], schema_index: SchemaIndex) -> Optional[Dict[str, Any]]:
        """
        Extract properties from the request body schema.
        
        Args:
            operation_schema: The operation schema containing the request body.
            schema_index: The schema index to use for resolving schema components.
            
        Returns:
            A dictionary with properties and required fields from the request body.
        """
        schema_component = operation_schema.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref", "").split("/")[-1]
        if schema_component:
            return schema_index.get_schema_component_properties(schema_component)
        return None

    def update_schema_with_body_properties(self, input_schema: Dict[str, Any], 
                                          body_properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update the input schema with properties from the request body.
        
        Args:
            input_schema: The existing input schema.
            body_properties: Properties extracted from the request body.
            
        Returns:
            The updated input schema.
        """
        # Add body properties to the input schema
        input_schema["properties"].update(body_properties["properties"])
        
        # Add required fields from the body
        input_schema["required"].extend(body_properties["required"])
        
        return input_schema

    def convert_parameter_to_property(self, parameter: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """
        Convert an OpenAPI parameter to a JSON Schema property.
        
        Args:
            parameter: The parameter to convert.
            
        Returns:
            A tuple containing the property schema and whether it's required.
        """
        property_schema = {
            "type": parameter["schema"]["type"],
            "description": parameter.get("description", ""),
            "in": parameter["in"]
        }
        
        # Copy relevant fields from the parameter schema
        if "schema" in parameter:
            schema = parameter["schema"]
            for key in ["type", "format", "enum", "minimum", "maximum", "default", "description", "example"]:
                if key in schema:
                    property_schema[key] = schema[key]
        
        # Determine if the parameter is required
        is_required = parameter.get("required", False)

        property = {
            parameter["name"]: property_schema
        }
        
        return property, is_required
