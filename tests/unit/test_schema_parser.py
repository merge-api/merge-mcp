from unittest.mock import patch, MagicMock

from merge_mcp.schema_parser import SchemaParser


def test_init():
    """Test initialization of SchemaParser."""
    parser = SchemaParser()
    assert isinstance(parser, SchemaParser)


def test_extract_path_and_query_parameters_empty():
    """Test extract_path_and_query_parameters with no parameters."""
    parser = SchemaParser()
    operation_schema = {}
    
    result = parser.extract_path_and_query_parameters(operation_schema)
    
    assert result == {"properties": {}, "required": []}


def test_extract_path_and_query_parameters():
    """Test extract_path_and_query_parameters with parameters."""
    parser = SchemaParser()
    operation_schema = {
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            },
            {
                "name": "filter",
                "in": "query",
                "required": False,
                "schema": {"type": "string", "enum": ["active", "inactive"]}
            },
            {
                "name": "include_deleted_data",  # This is in EXCLUDED_PARAMETERS
                "in": "query",
                "required": False,
                "schema": {"type": "boolean"}
            },
            {
                "name": "Authorization",
                "in": "header",  # Headers should be excluded
                "required": True,
                "schema": {"type": "string"}
            }
        ]
    }
    
    result = parser.extract_path_and_query_parameters(operation_schema)
    
    # Check that only id and filter are included, and id is required
    assert "id" in result["properties"]
    assert "filter" in result["properties"]
    assert "include_deleted_data" not in result["properties"]
    assert "Authorization" not in result["properties"]
    assert result["required"] == ["id"]


def test_convert_parameter_to_property():
    """Test convert_parameter_to_property."""
    parser = SchemaParser()
    
    # Test with a simple parameter
    parameter = {
        "name": "id",
        "in": "path",
        "required": True,
        "schema": {"type": "string"}
    }
    
    property_dict, is_required = parser.convert_parameter_to_property(parameter)
    
    assert "id" in property_dict
    assert property_dict["id"]["type"] == "string"
    assert property_dict["id"]["in"] == "path"
    assert is_required is True
    
    # Test with a parameter that has additional schema properties
    parameter = {
        "name": "limit",
        "in": "query",
        "required": False,
        "description": "Maximum number of results",
        "schema": {
            "type": "integer",
            "format": "int32",
            "minimum": 1,
            "maximum": 100,
            "default": 10,
            "example": 20
        }
    }
    
    property_dict, is_required = parser.convert_parameter_to_property(parameter)
    
    assert "limit" in property_dict
    assert property_dict["limit"]["type"] == "integer"
    assert property_dict["limit"]["format"] == "int32"
    assert property_dict["limit"]["minimum"] == 1
    assert property_dict["limit"]["maximum"] == 100
    assert property_dict["limit"]["default"] == 10
    assert property_dict["limit"]["example"] == 20
    assert property_dict["limit"]["description"] == "Maximum number of results"
    assert property_dict["limit"]["in"] == "query"
    assert is_required is False


def test_extract_request_body_properties_and_update_parameters(mock_openapi_schema):
    """Test extract_request_body_properties_and_update_parameters."""
    parser = SchemaParser()
    
    # Create a mock schema index
    schema_index = MagicMock()
    schema_index.get_schema_component_properties.return_value = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["name"]
    }
    
    # Create an operation schema with a request body
    operation_schema = {
        "operationId": "create_item",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/Item"
                    }
                }
            }
        }
    }
    
    result = parser.extract_request_body_properties_and_update_parameters(operation_schema, schema_index)
    
    # Check that the schema index was called with the correct component name
    schema_index.get_schema_component_properties.assert_called_once_with("Item")
    
    # Check that the result contains the expected properties
    assert result["properties"]["name"]["type"] == "string"
    assert result["properties"]["description"]["type"] == "string"
    assert result["required"] == ["name"]
    
    # Test with no request body
    operation_schema = {"operationId": "get_item"}
    result = parser.extract_request_body_properties_and_update_parameters(operation_schema, schema_index)
    assert result is None


def test_update_schema_with_body_properties():
    """Test update_schema_with_body_properties."""
    parser = SchemaParser()
    
    # Create an input schema with some properties and required fields
    input_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "in": "path"}
        },
        "required": ["id"]
    }
    
    # Create body properties to add
    body_properties = {
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"}
        },
        "required": ["name"]
    }
    
    result = parser.update_schema_with_body_properties(input_schema, body_properties)
    
    # Check that the properties were merged
    assert "id" in result["properties"]
    assert "name" in result["properties"]
    assert "description" in result["properties"]
    
    # Check that the required fields were merged
    assert "id" in result["required"]
    assert "name" in result["required"]


def test_extract_input_schema_and_update_parameters():
    """Test extract_input_schema_and_update_parameters."""
    parser = SchemaParser()
    
    # Test with both parameters and request body
    operation_schema_with_body = {
        "operationId": "create_item",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            }
        ],
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/Item"
                    }
                }
            }
        }
    }
    
    # Create a mock schema index for the first test
    schema_index1 = MagicMock()
    
    # Patch the extract methods to use controlled return values
    with patch.object(parser, "extract_path_and_query_parameters") as mock_extract_params:
        mock_extract_params.return_value = {
            "properties": {"id": {"type": "string", "in": "path"}},
            "required": ["id"]
        }
        
        with patch.object(parser, "extract_request_body_properties_and_update_parameters") as mock_extract_body:
            mock_extract_body.return_value = {
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"}
                },
                "required": ["name"]
            }
            
            result = parser.extract_input_schema_and_update_parameters(operation_schema_with_body, schema_index1)
            
            # Check that the extract methods were called
            mock_extract_params.assert_called_once_with(operation_schema_with_body)
            mock_extract_body.assert_called_once_with(operation_schema_with_body, schema_index1)
            
            # Check that the schema index was called to update parameters
            schema_index1.update_schema_parameters_by_operation_id.assert_called_once()
            
            # Check that the result contains all properties and required fields
            assert "id" in result["properties"]
            assert "name" in result["properties"]
            assert "description" in result["properties"]
            assert "id" in result["required"]
            assert "name" in result["required"]


def test_extract_input_schema_without_request_body():
    """Test extract_input_schema_and_update_parameters with no request body."""
    parser = SchemaParser()
    
    # Test with no request body
    operation_schema_no_body = {
        "operationId": "get_item",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string"}
            }
        ]
    }
    
    # Create a fresh mock schema index for the second test
    schema_index2 = MagicMock()
    
    with patch.object(parser, "extract_path_and_query_parameters") as mock_extract_params:
        mock_extract_params.return_value = {
            "properties": {"id": {"type": "string", "in": "path"}},
            "required": ["id"]
        }
        
        with patch.object(parser, "extract_request_body_properties_and_update_parameters") as mock_extract_body:
            mock_extract_body.return_value = None
            
            result = parser.extract_input_schema_and_update_parameters(operation_schema_no_body, schema_index2)
            
            # Check that the extract methods were called
            mock_extract_params.assert_called_once_with(operation_schema_no_body)
            mock_extract_body.assert_called_once_with(operation_schema_no_body, schema_index2)
            
            # Check that the schema index was not called to update parameters
            schema_index2.update_schema_parameters_by_operation_id.assert_not_called()
            
            # Check that the result contains only the path parameters
            assert "id" in result["properties"]
            assert "id" in result["required"]
            assert len(result["properties"]) == 1
            assert len(result["required"]) == 1