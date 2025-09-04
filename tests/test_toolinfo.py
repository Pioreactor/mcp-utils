"""Focused tests for ToolInfo and related results."""

from typing import Any

import msgspec

from mcp_utils.schema import ListToolsResult, ToolInfo


def test_tool_info_from_callable_builds_schema() -> None:
    """from_callable should populate name, description and a JSON schema."""

    def example_tool(name: str, count: int = 1) -> dict[str, Any]:
        """Echo tool for testing."""
        return {"name": name, "count": count}

    info = ToolInfo.from_callable(example_tool, name="example_tool")

    assert info.name == "example_tool"
    assert info.description == "Echo tool for testing."

    schema = info.inputSchema
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"
    assert "properties" in schema
    props = schema["properties"]
    assert "name" in props and props["name"].get("type") == "string"
    assert "count" in props and props["count"].get("type") in {"integer", "number"}
    # Required should include only arguments without defaults
    assert "required" in schema and "name" in schema["required"]


def test_tool_info_serialization_omits_defaults() -> None:
    """Default/None fields are omitted due to omit_defaults=True."""
    info = ToolInfo(
        name="no_desc",
        inputSchema={"type": "object", "properties": {}, "required": []},
        # description left as default None
    )

    payload = msgspec.json.decode(msgspec.json.encode(info))
    assert payload["name"] == "no_desc"
    assert payload["inputSchema"] == {"type": "object", "properties": {}, "required": []}
    # description is default None; it should be omitted
    assert "description" not in payload


def test_list_tools_result_parsing_roundtrip() -> None:
    """Parse a tools/list-like payload and round-trip via JSON."""
    data = {
        "tools": [
            {
                "name": "search",
                "description": "Search the index",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "summarize",
                "description": "Summarize text",
                "inputSchema": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}, "ratio": {"type": "number"}},
                    "required": ["text"],
                },
            },
        ],
        "nextCursor": "abc123",
    }

    result = msgspec.convert(data, ListToolsResult)
    assert isinstance(result, ListToolsResult)
    assert len(result.tools) == 2
    assert result.tools[0].name == "search"
    assert result.tools[1].name == "summarize"
    assert result.nextCursor == "abc123"

    roundtrip = msgspec.json.decode(msgspec.json.encode(result))
    assert roundtrip["tools"][0]["inputSchema"]["properties"]["query"]["type"] == "string"
    assert roundtrip["nextCursor"] == "abc123"

