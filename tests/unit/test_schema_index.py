from unittest.mock import patch, MagicMock

from merge_mcp.constants import READ_SCOPE, WRITE_SCOPE, IRREGULAR_TAG_MAP, SINGULAR_TAGS
from merge_mcp.schema_index import SchemaIndex


def test_init(mock_openapi_schema, available_scopes):
    """Test initialization of SchemaIndex."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        
        # Check that the client was retrieved
        mock_client_class.get_instance.assert_called_once()
        
        # Check that the component properties map was built
        assert "Ticket" in schema_index._component_properties_map
        assert "Comment" in schema_index._component_properties_map
        
        # Check that the tag to scope availability map was built
        assert "tickets" in schema_index._tag_to_scope_availability
        assert "comments" in schema_index._tag_to_scope_availability
        assert "users" in schema_index._tag_to_scope_availability
        assert "time-off" in schema_index._tag_to_scope_availability
        
        # Check that the index was built
        assert "tickets" in schema_index._index
        assert "comments" in schema_index._index
        assert "users" in schema_index._index
        assert "time-off" in schema_index._index
        
        # Check that the operation ID to schema map was built
        assert "tickets_list" in schema_index._operation_id_to_schema_map
        assert "tickets_create" in schema_index._operation_id_to_schema_map
        assert "comments_list" in schema_index._operation_id_to_schema_map
        assert "users_list" in schema_index._operation_id_to_schema_map
        assert "time_off_list" in schema_index._operation_id_to_schema_map


def test_build_component_properties_map(mock_openapi_schema, available_scopes):
    """Test _build_component_properties_map method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        component_properties_map = schema_index._component_properties_map
        
        # Check that the component properties map was built correctly
        assert "Ticket" in component_properties_map
        assert "Comment" in component_properties_map
        assert component_properties_map["Ticket"]["properties"]["id"]["type"] == "string"
        assert component_properties_map["Ticket"]["properties"]["title"]["type"] == "string"
        assert component_properties_map["Comment"]["properties"]["id"]["type"] == "string"
        assert component_properties_map["Comment"]["properties"]["body"]["type"] == "string"


def test_build_tag_to_scope_availability(mock_openapi_schema, available_scopes):
    """Test _build_tag_to_scope_availability method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        tag_to_scope_availability = schema_index._tag_to_scope_availability
        
        # Check that the tag to scope availability map was built correctly
        assert tag_to_scope_availability["tickets"][READ_SCOPE] is True
        assert tag_to_scope_availability["tickets"][WRITE_SCOPE] is True
        assert tag_to_scope_availability["comments"][READ_SCOPE] is True
        assert tag_to_scope_availability["comments"][WRITE_SCOPE] is False
        assert tag_to_scope_availability["users"][READ_SCOPE] is True
        assert tag_to_scope_availability["users"][WRITE_SCOPE] is False
        assert tag_to_scope_availability["time-off"][READ_SCOPE] is True
        assert tag_to_scope_availability["time-off"][WRITE_SCOPE] is False


def test_create_tag_from_model():
    """Test _create_tag_from_model method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex({"paths": {}, "components": {"schemas": {}}}, [])
        
        # Test regular model names
        assert schema_index._create_tag_from_model("Ticket") == "tickets"
        assert schema_index._create_tag_from_model("Comment") == "comments"
        
        # Test PascalCase model names
        assert schema_index._create_tag_from_model("TimeOffRequest") == "time-off-requests"
        assert schema_index._create_tag_from_model("BankAccount") == "bank-accounts"
        
        # Test irregular model names
        for model, tag in IRREGULAR_TAG_MAP.items():
            assert schema_index._create_tag_from_model(model) == tag
        
        # Test singular tags
        for tag in SINGULAR_TAGS:
            model = "".join(word.capitalize() for word in tag.split("-"))
            assert schema_index._create_tag_from_model(model) == tag


def test_build_index_for_available_scopes(mock_openapi_schema, available_scopes):
    """Test _build_index_for_available_scopes method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        index = schema_index._index
        
        # Check that the index was built correctly
        assert "tickets" in index
        assert "comments" in index
        assert "users" in index
        assert "time-off" in index
        
        # Check that the methods were filtered correctly
        assert "get" in index["tickets"]
        assert "post" in index["tickets"]
        assert "get" in index["comments"]
        assert "post" not in index["comments"]  # Comment write is not enabled
        
        # Check that the schemas were added correctly
        assert len(index["tickets"]["get"]) == 2  # tickets_list and multi_tag_list
        assert len(index["tickets"]["post"]) == 1  # tickets_create
        assert len(index["comments"]["get"]) == 2  # comments_list and multi_tag_list
        assert index["tickets"]["get"][0]["operationId"] in ["tickets_list", "multi_tag_list"]
        assert index["tickets"]["post"][0]["operationId"] == "tickets_create"
        assert index["comments"]["get"][0]["operationId"] in ["comments_list", "multi_tag_list"]


def test_build_operation_id_to_schema_map(mock_openapi_schema, available_scopes):
    """Test _build_operation_id_to_schema_map method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        operation_id_to_schema_map = schema_index._operation_id_to_schema_map
        
        # Check that the operation ID to schema map was built correctly
        assert "tickets_list" in operation_id_to_schema_map
        assert "tickets_create" in operation_id_to_schema_map
        assert "comments_list" in operation_id_to_schema_map
        assert "users_list" in operation_id_to_schema_map
        assert "time_off_list" in operation_id_to_schema_map
        assert "multi_tag_list" in operation_id_to_schema_map
        
        # Check that the schemas were added correctly
        assert operation_id_to_schema_map["tickets_list"]["operationId"] == "tickets_list"
        assert operation_id_to_schema_map["tickets_create"]["operationId"] == "tickets_create"
        assert operation_id_to_schema_map["comments_list"]["operationId"] == "comments_list"
        assert operation_id_to_schema_map["users_list"]["operationId"] == "users_list"
        assert operation_id_to_schema_map["time_off_list"]["operationId"] == "time_off_list"
        assert operation_id_to_schema_map["multi_tag_list"]["operationId"] == "multi_tag_list"


def test_get_all_operation_schemas(mock_openapi_schema, available_scopes):
    """Test get_all_operation_schemas method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        operation_schemas = schema_index.get_all_operation_schemas()
        
        # Check that all operation schemas were returned
        assert len(operation_schemas) == 6
        operation_ids = [schema["operationId"] for schema in operation_schemas]
        assert "tickets_list" in operation_ids
        assert "tickets_create" in operation_ids
        assert "comments_list" in operation_ids
        assert "users_list" in operation_ids
        assert "time_off_list" in operation_ids
        assert "multi_tag_list" in operation_ids


def test_update_schema_parameters_by_operation_id(mock_openapi_schema, available_scopes):
    """Test update_schema_parameters_by_operation_id method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        
        # Update parameters for tickets_list
        new_parameters = [{"name": "new_param", "in": "query"}]
        schema_index.update_schema_parameters_by_operation_id("tickets_list", new_parameters)
        
        # Check that the parameters were updated
        updated_schema = schema_index.get_by_operation_id("tickets_list")
        assert updated_schema["parameters"] == new_parameters


def test_get_by_operation_id(mock_openapi_schema, available_scopes):
    """Test get_by_operation_id method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        
        # Get schema for tickets_list
        schema = schema_index.get_by_operation_id("tickets_list")
        
        # Check that the schema was returned
        assert schema["operationId"] == "tickets_list"
        assert schema["tags"] == ["tickets"]
        assert schema["parameters"][0]["name"] == "param1"
        
        # Get schema for non-existent operation ID
        schema = schema_index.get_by_operation_id("non_existent")
        
        # Check that None was returned
        assert schema is None


def test_get_schema_component_properties(mock_openapi_schema, available_scopes):
    """Test get_schema_component_properties method."""
    with patch("merge_mcp.schema_index.MergeAPIClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.get_instance.return_value = mock_client
        
        schema_index = SchemaIndex(mock_openapi_schema, available_scopes)
        
        # Get component properties for Ticket
        component_properties = schema_index.get_schema_component_properties("Ticket")
        
        # Check that the component properties were returned
        assert component_properties["type"] == "object"
        assert component_properties["properties"]["id"]["type"] == "string"
        assert component_properties["properties"]["title"]["type"] == "string"
        
        # Get component properties for non-existent component
        component_properties = schema_index.get_schema_component_properties("NonExistent")
        
        # Check that None was returned
        assert component_properties is None