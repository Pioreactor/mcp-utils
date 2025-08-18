"""Pydantic models for MCP (Model Context Protocol) schema."""

import logging
from collections.abc import Callable
from dataclasses import MISSING
from enum import Enum
from typing import Annotated, Any, Literal

from msgspec import Meta, Struct, field

from .utils import inspect_callable

logger = logging.getLogger("mcp_utils")


class Role(str, Enum):
    """Role in the MCP protocol."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Annotations(Struct):
    """Annotations for MCP objects."""

    audience: list[Role] | None = None
    priority: Annotated[float, Meta(ge=0, le=1)] | None = None


class Annotated(Struct):
    """Base for objects that include optional annotations for the client."""

    annotations: Annotations | None = None


class BlobResourceContents(Struct):
    """Contents of a blob resource."""

    blob: str
    mime_type: str | None = field(default=None, name="mimeType")
    uri: str


class ToolArguments(Struct):
    """Arguments for a tool call."""

    root: dict[str, Any]


class TextContent(Struct):
    """Text content in MCP."""

    text: str
    type: str = field(default="text")


class ImageContent(Struct):
    """Image content in MCP."""

    image: BlobResourceContents
    type: str = field(default="image")


class EmbeddedResource(Struct):
    """Embedded resource content in MCP."""

    resource: BlobResourceContents
    type: str = field(default="embedded-resource")


class CallToolRequest(Struct):
    """Request to invoke a tool provided by the server."""

    method: Literal["tools/call"]
    params: dict[str, Any]


class CallToolResult(Struct):
    """The server's response to a tool call."""

    _meta: dict[str, Any] | None = None
    content: list[TextContent | ImageContent | EmbeddedResource]
    is_error: bool = field(default=False, name="isError")


class CancelledNotification(Struct):
    """Notification for cancelling a previously-issued request."""

    method: Literal["notifications/cancelled"]
    params: dict[str, Any]


class ClientCapabilities(Struct):
    """Capabilities a client may support."""

    experimental: dict[str, dict[str, Any]] | None = None
    roots: dict[str, bool] | None = None
    sampling: dict[str, Any] | None = None
    prompts: dict[str, bool] | None = None
    resources: dict[str, bool] | None = None
    tools: dict[str, bool] | None = None
    logging: dict[str, bool] | None = None


class CompleteRequestArgument(Struct):
    """Argument information for completion request."""

    name: str
    value: str


class CompleteRequest(Struct):
    """Request for completion options."""

    method: Literal["completion/complete"]
    params: dict[str, Any]


class CompletionValues(Struct):
    """Completion values response."""

    has_more: bool | None = field(default=None, name="hasMore")
    total: int | None = None
    values: list[str]


class CompleteResult(Struct):
    """Response to a completion request."""

    _meta: dict[str, Any] | None = None
    completion: CompletionValues


class ResourceReference(Struct):
    """Reference to a resource."""

    type: str = field(default="resource")
    id: str


class PromptReference(Struct):
    """Reference to a prompt."""

    type: str = field(default="prompt")
    id: str


class InitializeRequest(Struct):
    """Request to initialize the MCP connection."""

    method: Literal["initialize"]
    params: dict[str, Any]


class ServerInfo(Struct):
    """Information about the server."""

    name: str
    version: str


class InitializeResult(Struct):
    """Result of initialization request."""

    protocolVersion: str
    capabilities: ClientCapabilities
    serverInfo: ServerInfo


class ListResourcesRequest(Struct):
    """Request to list available resources."""

    method: Literal["resources/list"]
    params: dict[str, Any] | None = None


class ResourceInfo(Struct):
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


class ListResourcesResult(Struct):
    """Result of listing resources."""

    resources: list[ResourceInfo]
    nextCursor: str | None = None


class ResourceTemplateInfo(Struct):
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


class ListResourceTemplateResult(Struct):
    """Result of listing resource templates."""

    resourceTemplates: list[ResourceTemplateInfo]
    nextCursor: str | None = None


class ReadResourceRequest(Struct):
    """Request to read a specific resource."""

    method: Literal["resources/read"]
    params: dict[str, Any]


class ReadResourceResult(Struct):
    """Result of reading a resource."""

    _meta: dict[str, Any] | None = None
    resource: BlobResourceContents


class ListPromptsRequest(Struct):
    """Request to list available prompts."""

    method: Literal["prompts/list"]
    params: dict[str, Any] | None = None


class PromptInfo(Struct):
    """Information about a prompt.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/prompts/#listing-prompts
    """

    id: str
    name: str
    description: str | None = None
    arguments: list[dict[str, Any]]

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "PromptInfo":
        """Create a PromptInfo from a callable."""
        metadata = inspect_callable(callable)
        arguments = []
        if metadata.arg_model:
            annotations = metadata.arg_model.__annotations__
            for field_name in annotations:
                default = getattr(metadata.arg_model, field_name, MISSING)
                arguments.append(
                    {
                        "name": field_name,
                        "description": "",
                        "required": default is MISSING,
                    }
                )
        return cls(
            id=name, name=name, description=callable.__doc__ or "", arguments=arguments
        )


class ListPromptsResult(Struct):
    """Result of listing prompts."""

    prompts: list[PromptInfo]
    nextCursor: str | None = None


class GetPromptRequest(Struct):
    """Request to get a specific prompt."""

    method: Literal["prompts/get"]
    params: dict[str, Any]


class Message(Struct):
    """Message in MCP."""

    role: Literal["system", "user", "assistant"]
    content: TextContent | ImageContent | EmbeddedResource


class GetPromptResult(Struct):
    """Result of getting a prompt."""

    _meta: dict[str, Any] | None = None
    description: str
    messages: list[Message]


class ListToolsRequest(Struct):
    """Request to list available tools."""

    method: Literal["tools/list"]
    params: dict[str, Any] | None = None


class ToolInfo(Struct):
    """Information about a tool.

    See: https://spec.modelcontextprotocol.io/specification/2024-11-05/server/tools/#listing-tools
    """

    name: str
    description: str | None = None
    inputSchema: dict[str, Any]
    arg_model: type | None = field(default=None, omit=True)

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "ToolInfo":
        """Create a ToolInfo from a callable."""
        metadata = inspect_callable(callable)
        return cls(
            name=name,
            description=callable.__doc__ or "",
            inputSchema={},
            arg_model=metadata.arg_model,
        )


class ListToolsResult(Struct):
    """Result of listing tools."""

    tools: list[ToolInfo]
    nextCursor: str | None = None


class SubscribeRequest(Struct):
    """Request to subscribe to a resource."""

    method: Literal["resources/subscribe"]
    params: dict[str, Any]


class UnsubscribeRequest(Struct):
    """Request to unsubscribe from a resource."""

    method: Literal["resources/unsubscribe"]
    params: dict[str, Any]


class SetLevelRequest(Struct):
    """Request to set the level of a resource."""

    method: Literal["resources/setLevel"]
    params: dict[str, Any]


class PingRequest(Struct):
    """Request to ping the server."""

    method: Literal["ping"]
    params: dict[str, Any] | None = None


class PingResult(Struct):
    """Result of ping request."""

    _meta: dict[str, Any] | None = None


class InitializedNotification(Struct):
    """Notification that initialization is complete."""

    method: Literal["notifications/initialized"]
    params: dict[str, Any] | None = None


class ProgressNotification(Struct):
    """Notification of progress."""

    method: Literal["notifications/progress"]
    params: dict[str, Any]


class RootsListChangedNotification(Struct):
    """Notification that the roots list has changed."""

    method: Literal["notifications/rootsListChanged"]
    params: dict[str, Any] | None = None


class CreateMessageRequest(Struct):
    """Request to create a message."""

    method: Literal["messages/create"]
    params: dict[str, Any]


class CreateMessageResult(Struct):
    """Result of creating a message."""

    message: dict[str, Any]


class ListRootsRequest(Struct):
    """Request to list roots."""

    method: Literal["roots/list"]
    params: dict[str, Any] | None = None


class RootInfo(Struct):
    """Information about a root."""

    id: str
    name: str
    description: str | None = None


class ListRootsResult(Struct):
    """Result of listing roots."""

    roots: list[RootInfo]
    nextCursor: str | None = None


class ErrorResponse(Struct):
    """Error response in MCP."""

    code: int | None = None
    message: str | None = None
    data: Any | None = None


class MCPResponse(Struct):
    """Base response model for MCP responses."""

    jsonrpc: Literal["2.0"] = field(default="2.0")
    id: str | int | None = None
    result: Any | None = None
    error: ErrorResponse | None = None

    def is_error(self) -> bool:
        """Check if the response contains an error."""
        return self.error is not None


class Result(Struct):
    """Generic result type."""

    _meta: dict[str, Any] | None = None


class MCPRequest(Struct):
    """Base request model for MCP requests."""

    jsonrpc: Literal["2.0"] = field(default="2.0")
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None
