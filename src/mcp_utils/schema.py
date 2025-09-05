"""msgspec models for MCP (Model Context Protocol) schema."""

from collections.abc import Callable
from enum import Enum
from typing import Any, Literal

import msgspec

from .utils import inspect_callable


def build_json_schema_for_msgspec_struct(struct_type: type[Any]) -> dict[str, Any]:
    """Return a clean JSON Schema dict for a msgspec Struct.
    """
    if struct_type is None:
        return {"type": "object", "properties": {}}

    (schemas,), components = msgspec.json.schema_components([struct_type])

    # Try direct component by the class name for stable selection
    name = getattr(struct_type, "__name__", None)
    if name and name in components:
        return components[name]
    else:
        raise ValueError()


class Role(str, Enum):
    """Role in the MCP protocol."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Annotations(msgspec.Struct):
    """Annotations for MCP objects."""

    audience: list[Role] | None = None
    # Range constraints will be added via msgspec.Meta in a later pass
    priority: float | None = None


class Annotated(msgspec.Struct):
    """Base for objects that include optional annotations for the client."""

    annotations: Annotations | None = None


class BlobResourceContents(msgspec.Struct):
    """Contents of a blob resource."""

    blob: str
    uri: str
    mime_type: str | None = msgspec.field(default=None, name="mimeType")


## Removed Pydantic RootModel helper


class TextContent(msgspec.Struct, tag="text", tag_field="type"):
    """Text content in MCP."""

    text: str

    @property
    def type(self) -> str:  # for test compatibility
        return "text"


class ImageContent(msgspec.Struct, tag="image", tag_field="type"):
    """Image content in MCP."""

    image: BlobResourceContents

    @property
    def type(self) -> str:  # for test compatibility
        return "image"


class EmbeddedResource(msgspec.Struct, tag="embedded-resource", tag_field="type"):
    """Embedded resource content in MCP."""

    resource: BlobResourceContents

    @property
    def type(self) -> str:  # for test compatibility
        return "embedded-resource"


class CallToolRequest(msgspec.Struct):
    """Request to invoke a tool provided by the server."""

    method: Literal["tools/call"]
    params: dict[str, Any]


class CallToolResult(msgspec.Struct, omit_defaults=True):
    """The server's response to a tool call."""

    content: list[TextContent | ImageContent | EmbeddedResource]
    is_error: bool = msgspec.field(default=False, name="isError")
    _meta: dict[str, Any] | None = None


class CancelledNotification(msgspec.Struct):
    """Notification for cancelling a previously-issued request."""

    method: Literal["notifications/cancelled"]
    params: dict[str, Any]


class ClientCapabilities(msgspec.Struct):
    """Capabilities a client may support."""

    experimental: dict[str, dict[str, Any]] | msgspec.UnsetType = msgspec.UNSET
    roots: dict[str, bool] | msgspec.UnsetType = msgspec.UNSET
    sampling: dict[str, Any] | msgspec.UnsetType  = msgspec.UNSET
    prompts: dict[str, bool] | msgspec.UnsetType = msgspec.UNSET
    resources: dict[str, bool] | msgspec.UnsetType = msgspec.UNSET
    tools: dict[str, bool] | msgspec.UnsetType = msgspec.UNSET
    logging: dict[str, bool] | msgspec.UnsetType = msgspec.UNSET


class CompleteRequestArgument(msgspec.Struct):
    """Argument information for completion request."""

    name: str
    value: str


class CompleteRequest(msgspec.Struct):
    """Request for completion options."""

    method: Literal["completion/complete"]
    params: dict[str, Any]


class CompletionValues(msgspec.Struct):
    """Completion values response."""

    values: list[str]
    has_more: bool | None = msgspec.field(default=None, name="hasMore")
    total: int | None = None


class CompleteResult(msgspec.Struct, omit_defaults=True):
    """Response to a completion request."""

    completion: CompletionValues
    _meta: dict[str, Any] | None = None


class ResourceReference(msgspec.Struct):
    """Reference to a resource."""

    id: str
    type: str = "resource"


class PromptReference(msgspec.Struct):
    """Reference to a prompt."""

    id: str
    type: str = "prompt"


class InitializeRequest(msgspec.Struct):
    """Request to initialize the MCP connection."""

    method: Literal["initialize"]
    params: dict[str, Any]


class ServerInfo(msgspec.Struct):
    """Information about the server."""

    name: str
    version: str


class InitializeResult(msgspec.Struct):
    """Result of initialization request."""

    protocolVersion: str
    capabilities: ClientCapabilities
    serverInfo: ServerInfo
    instructions: str | msgspec.UnsetType = msgspec.UNSET


class ListResourcesRequest(msgspec.Struct):
    """Request to list available resources."""

    method: Literal["resources/list"]
    params: dict[str, Any] | None = None


class ResourceInfo(msgspec.Struct):
    """Information about a resource."""

    uri: str
    name: str
    description: str = ""
    mime_type: str | None = None

    @classmethod
    def from_callable(cls, callable: Callable, path: str, name: str) -> "ResourceInfo":
        return cls(
            uri=path,
            name=name,
            description=callable.__doc__ or "",
            mime_type="application/json",
        )


class ListResourcesResult(msgspec.Struct):
    """Result of listing resources."""

    resources: list[ResourceInfo]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET


class ResourceTemplateInfo(msgspec.Struct):
    """Information about a resource template.

    https://spec.modelcontextprotocol.io/specification/2024-11-05/server/resources/#resource-templates
    """

    uriTemplate: str
    name: str
    description: str = ""
    mimeType: str = "application/json"

    @classmethod
    def from_callable(
        cls, path: str, callable: Callable, name: str
    ) -> "ResourceTemplateInfo":
        return cls(
            uriTemplate=path,
            name=name,
            description=callable.__doc__ or "",
            mimeType="application/json",
        )


class ListResourceTemplateResult(msgspec.Struct):
    """Result of listing resource templates."""

    resourceTemplates: list[ResourceTemplateInfo]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET


class ReadResourceRequest(msgspec.Struct):
    """Request to read a specific resource."""

    method: Literal["resources/read"]
    params: dict[str, Any]


class ReadResourceResult(msgspec.Struct, omit_defaults=True):
    """Result of reading a resource."""

    resource: BlobResourceContents
    _meta: dict[str, Any] | None = None


class ListPromptsRequest(msgspec.Struct):
    """Request to list available prompts."""

    method: Literal["prompts/list"]
    params: dict[str, Any] | None = None


class PromptInfo(msgspec.Struct):
    """Information about a prompt.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/prompts/#listing-prompts
    """

    id: str
    name: str
    arguments: list[dict[str, Any]]
    description: str | None = None

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "PromptInfo":
        """Create a PromptInfo from a callable."""
        metadata = inspect_callable(callable)
        arguments = []
        if metadata.arg_model:
            for field in msgspec.structs.fields(metadata.arg_model):
                arguments.append(
                    {
                        "name": field.name,
                        "description": "",
                        "required": field.default is msgspec.UNSET,
                    }
                )
        return cls(
            id=name, name=name, description=callable.__doc__ or "", arguments=arguments
        )


class ListPromptsResult(msgspec.Struct):
    """Result of listing prompts."""

    prompts: list[PromptInfo]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET


class GetPromptRequest(msgspec.Struct):
    """Request to get a specific prompt."""

    method: Literal["prompts/get"]
    params: dict[str, Any]


class Message(msgspec.Struct):
    """Message in MCP."""

    role: Literal["system", "user", "assistant"]
    content: TextContent | ImageContent | EmbeddedResource


class GetPromptResult(msgspec.Struct, omit_defaults=True):
    """Result of getting a prompt."""

    description: str
    messages: list[Message]
    _meta: dict[str, Any] | None = None


class ListToolsRequest(msgspec.Struct):
    """Request to list available tools."""

    method: Literal["tools/list"]
    params: dict[str, Any] | None = None


class ToolInfo(msgspec.Struct, omit_defaults=True):
    """Information about a tool.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/tools/#listing-tools
    """

    name: str
    inputSchema: dict[str, Any]
    description: str | None = None
    arg_model: type[msgspec.Struct] | msgspec.UnsetType = msgspec.UNSET

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "ToolInfo":
        """Create a ToolInfo from a callable."""
        metadata = inspect_callable(callable)

        return cls(
            name=name,
            description=callable.__doc__ or "",
            inputSchema=build_json_schema_for_msgspec_struct(metadata.arg_model),
        )


class ListToolsResult(msgspec.Struct):
    """Result of listing tools."""

    tools: list[ToolInfo]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class SubscribeRequest(msgspec.Struct):
    """Request to subscribe to a resource."""

    method: Literal["resources/subscribe"]
    params: dict[str, Any]


class UnsubscribeRequest(msgspec.Struct):
    """Request to unsubscribe from a resource."""

    method: Literal["resources/unsubscribe"]
    params: dict[str, Any]


class SetLevelRequest(msgspec.Struct):
    """Request to set the level of a resource."""

    method: Literal["resources/setLevel"]
    params: dict[str, Any]


class PingRequest(msgspec.Struct):
    """Request to ping the server."""

    method: Literal["ping"]
    params: dict[str, Any] | None = None


class PingResult(msgspec.Struct):
    """Result of ping request."""

    _meta: dict[str, Any] | None = None


class InitializedNotification(msgspec.Struct):
    """Notification that initialization is complete."""

    method: Literal["notifications/initialized"]
    params: dict[str, Any] | None = None


class ProgressNotification(msgspec.Struct):
    """Notification of progress."""

    method: Literal["notifications/progress"]
    params: dict[str, Any]


class RootsListChangedNotification(msgspec.Struct):
    """Notification that the roots list has changed."""

    method: Literal["notifications/rootsListChanged"]
    params: dict[str, Any] | None = None


class CreateMessageRequest(msgspec.Struct):
    """Request to create a message."""

    method: Literal["messages/create"]
    params: dict[str, Any]


class CreateMessageResult(msgspec.Struct):
    """Result of creating a message."""

    message: dict[str, Any]


class ListRootsRequest(msgspec.Struct):
    """Request to list roots."""

    method: Literal["roots/list"]
    params: dict[str, Any] | None = None


class RootInfo(msgspec.Struct):
    """Information about a root."""

    id: str
    name: str
    description: str | None = None


class ListRootsResult(msgspec.Struct):
    """Result of listing roots."""

    roots: list[RootInfo]
    nextCursor: str | msgspec.UnsetType = msgspec.UNSET

class ErrorResponse(msgspec.Struct):
    """Error response in MCP."""

    code: int | None = None
    message: str | None = None
    data: Any | None = None


class MCPResponse(msgspec.Struct, omit_defaults=True):
    """Base response model for MCP responses."""

    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    result: Any | None = None
    error: ErrorResponse | None = None

    def is_error(self) -> bool:
        """Check if the response contains an error."""
        return self.error is not None


class Result(msgspec.Struct):
    """Generic result type."""

    _meta: dict[str, Any] | None = None


class MCPRequest(msgspec.Struct):
    """Base request model for MCP requests."""

    method: str
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    params: dict[str, Any] | None = None
