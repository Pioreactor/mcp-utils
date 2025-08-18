"""Tests for MCP schema models."""

import json

import msgspec
import pytest

from mcp_utils.schema import (
    Annotations,
    BlobResourceContents,
    CallToolRequest,
    CallToolResult,
    ErrorResponse,
    ImageContent,
    InitializeRequest,
    MCPRequest,
    MCPResponse,
    Message,
    ResourceInfo,
    Role,
    ServerInfo,
    TextContent,
    ToolInfo,
)


def test_role_enum():
    """Test Role enum values and JSON serialization."""
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"
    assert Role.SYSTEM == "system"

    # Test JSON serialization
    assert json.loads(json.dumps({"role": Role.USER})) == {"role": "user"}


def test_annotations():
    """Test Annotations model."""
    # Test with valid data
    data = {
        "audience": ["user", "assistant"],
        "priority": 0.5,
    }
    annotations = Annotations(**data)
    assert annotations.audience == [Role.USER, Role.ASSISTANT]
    assert annotations.priority == 0.5

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(annotations)) == data

    # Test validation
    with pytest.raises(msgspec.ValidationError):
        Annotations(priority=1.5)  # priority must be <= 1


def test_blob_resource_contents():
    """Test BlobResourceContents model."""
    data = {
        "blob": "SGVsbG8gd29ybGQ=",  # base64 encoded "Hello world"
        "mimeType": "text/plain",
        "uri": "https://example.com/resource",
    }
    resource = BlobResourceContents(**data)
    assert resource.blob == "SGVsbG8gd29ybGQ="
    assert resource.mime_type == "text/plain"
    assert resource.uri == "https://example.com/resource"

    # Test JSON serialization with aliases
    json_data = json.loads(msgspec.json.encode(resource))
    assert json_data["mimeType"] == "text/plain"  # Check alias works
    assert json_data["uri"] == "https://example.com/resource"


def test_content_types():
    """Test different content type models."""
    # Test TextContent
    text = TextContent(text="Hello")
    assert text.type == "text"
    assert json.loads(msgspec.json.encode(text)) == {"text": "Hello", "type": "text"}

    # Test ImageContent
    image_data = {
        "image": {
            "blob": "SGVsbG8=",
            "mimeType": "image/png",
            "uri": "https://example.com/image",
        },
        "type": "image",
    }
    image = ImageContent(**image_data)
    assert image.type == "image"
    assert json.loads(msgspec.json.encode(image)) == image_data


def test_call_tool_request():
    """Test CallToolRequest model."""
    data = {
        "method": "tools/call",
        "params": {"name": "test_tool", "args": {"key": "value"}},
    }
    request = CallToolRequest(**data)
    assert request.method == "tools/call"
    assert request.params == {"name": "test_tool", "args": {"key": "value"}}

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(request)) == data


def test_call_tool_result():
    """Test CallToolResult model."""
    data = {
        "content": [{"text": "Hello", "type": "text"}],
        "isError": False,
    }
    result = CallToolResult(**data)
    assert result._meta is None
    assert isinstance(result.content[0], TextContent)
    assert not result.is_error

    # Test JSON serialization with aliases
    json_data = json.loads(msgspec.json.encode(result))
    assert json_data["isError"] is False  # Check alias works
    assert json_data["content"][0] == {"text": "Hello", "type": "text"}


def test_mcp_response():
    """Test MCPResponse model."""
    # Test successful response
    success_data = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {"key": "value"},
    }
    response = MCPResponse(**success_data)
    assert response.jsonrpc == "2.0"
    assert response.id == "1"
    assert response.result == {"key": "value"}
    assert not response.is_error()

    # Test error response
    error_data = {
        "jsonrpc": "2.0",
        "id": "1",
        "error": {
            "code": 100,
            "message": "Test error",
            "data": {"detail": "More info"},
        },
    }
    error_response = MCPResponse(**error_data)
    assert error_response.is_error()
    assert error_response.error.code == 100
    assert error_response.error.message == "Test error"

    # Test JSON serialization
    json_data = json.loads(msgspec.json.encode(error_response, skip_defaults=True))
    assert json_data == error_data

    # Test extra fields are forbidden
    with pytest.raises(TypeError):
        MCPResponse(**{**success_data, "extra": "field"})


def test_mcp_request():
    """Test MCPRequest model."""
    data = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "test_method",
        "params": {"key": "value"},
    }
    request = MCPRequest(**data)
    assert request.jsonrpc == "2.0"
    assert request.id == "1"
    assert request.method == "test_method"
    assert request.params == {"key": "value"}

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(request)) == data


def test_message():
    """Test Message model."""
    # Test with text content
    text_msg = Message(
        role="user",
        content=TextContent(text="Hello"),
    )
    assert text_msg.role == Role.USER
    assert isinstance(text_msg.content, TextContent)

    # Test with image content
    image_msg = Message(
        role="assistant",
        content=ImageContent(
            image=BlobResourceContents(
                blob="SGVsbG8=",
                mimeType="image/png",
                uri="https://example.com/image",
            )
        ),
    )
    assert image_msg.role == Role.ASSISTANT
    assert isinstance(image_msg.content, ImageContent)

    # Test JSON serialization
    json_data = json.loads(msgspec.json.encode(image_msg))
    assert json_data["role"] == "assistant"
    assert json_data["content"]["type"] == "image"
    assert json_data["content"]["image"]["mimeType"] == "image/png"


def test_resource_info():
    """Test ResourceInfo model."""
    data = {
        "uri": "https://example.com/resource",
        "name": "Test Resource",
        "description": "A test resource",
        "mime_type": "text/plain",
    }
    resource = ResourceInfo(**data)
    assert resource.uri == "https://example.com/resource"
    assert resource.name == "Test Resource"
    assert resource.description == "A test resource"
    assert resource.mime_type == "text/plain"

    # Test JSON serialization
    json_data = json.loads(msgspec.json.encode(resource))
    assert json_data["mime_type"] == "text/plain"  # No alias for this field


def test_tool_info():
    """Test ToolInfo model."""
    data = {
        "name": "test_tool",
        "description": "A test tool",
        "inputSchema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
        },
    }
    tool = ToolInfo(**data)
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.inputSchema == {
        "type": "object",
        "properties": {"key": {"type": "string"}},
    }

    # Test JSON serialization
    json_data = json.loads(msgspec.json.encode(tool))
    assert "arg_model" not in json_data  # Should be excluded
    assert json_data["inputSchema"] == data["inputSchema"]


def test_error_response():
    """Test ErrorResponse model."""
    data = {
        "code": 100,
        "message": "Test error",
        "data": {"detail": "More info"},
    }
    error = ErrorResponse(**data)
    assert error.code == 100
    assert error.message == "Test error"
    assert error.data == {"detail": "More info"}

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(error, skip_defaults=True)) == data


def test_server_info():
    """Test ServerInfo model."""
    data = {
        "name": "Test Server",
        "version": "1.0.0",
    }
    server = ServerInfo(**data)
    assert server.name == "Test Server"
    assert server.version == "1.0.0"

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(server)) == data


def test_initialize_request():
    """Test InitializeRequest model."""
    data = {
        "method": "initialize",
        "params": {"clientInfo": {"name": "test-client", "version": "1.0.0"}},
    }
    request = InitializeRequest(**data)
    assert request.method == "initialize"
    assert request.params["clientInfo"]["name"] == "test-client"

    # Test JSON serialization
    assert json.loads(msgspec.json.encode(request)) == data


def test_nested_model_serialization():
    """Test nested model serialization."""
    # Create a complex nested structure
    data = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {
            "content": [
                {"text": "Hello", "type": "text"},
                {
                    "image": {
                        "blob": "SGVsbG8=",
                        "mimeType": "image/png",
                        "uri": "https://example.com/image",
                    },
                    "type": "image",
                },
            ],
            "isError": False,
        },
    }

    # Create response with nested models
    response = MCPResponse(**data)
    result = CallToolResult(**data["result"])
    response.result = result

    # Test JSON serialization of the entire structure
    json_data = json.loads(msgspec.json.encode(response, skip_defaults=True))
    assert json_data == data  # Should match the original structure exactly
