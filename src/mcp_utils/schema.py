"""msgspec models for MCP (Model Context Protocol) schema."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dc_field
from enum import Enum
from typing import Any, Literal

import msgspec
from msgspec import Meta, field

from .utils import inspect_callable

logger = logging.getLogger("mcp_utils")


class Role(str, Enum):
    """Role in the MCP protocol."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Annotations(msgspec.Struct):
    """Annotations for MCP objects."""

    audience: list[Role] | None = None
    priority: float | None = field(default=None, ge=0, le=1)


class Annotated(msgspec.Struct):
    """Base for objects that include optional annotations for the client."""

    annotations: Annotations | None = None


class BlobResourceContents(msgspec.Struct):
    """Contents of a blob resource."""

    blob: str
    mime_type: str | None = field(default=None, name="mimeType")
    uri: str


class ToolArguments(msgspec.Struct):
    """Arguments for a tool call."""

    root: dict[str, Any]


class TextContent(msgspec.Struct):
    """Text content in MCP."""

    text: str
    type: str = "text"


class ImageContent(msgspec.Struct):
    """Image content in MCP."""

    image: BlobResourceContents
    type: str = "image"


class EmbeddedResource(msgspec.Struct):
    """Embedded resource content in MCP."""

    resource: BlobResourceContents
    type: str = field(default="embedded-resource")


class CallToolRequest(msgspec.Struct):
    """Request to invoke a tool provided by the server."""

    method: Literal["tools/call"]
    params: dict[str, Any]


class CallToolResult(msgspec.Struct):
    """The server's response to a tool call."""

    _meta: dict[str, Any] | None = None
    content: list[TextContent | ImageContent | EmbeddedResource]
    is_error: bool = field(default=False, name="isError")


class CancelledNotification(msgspec.Struct):
    """Notification for cancelling a previously-issued request."""

    method: Literal["notifications/cancelled"]
    params: dict[str, Any]


class ClientCapabilities(msgspec.Struct):
    """Capabilities a client may support."""

    experimental: dict[str, dict[str, Any]] | None = None
    roots: dict[str, bool] | None = None
    sampling: dict[str, Any] | None = None
    prompts: dict[str, bool] | None = None
    resources: dict[str, bool] | None = None
    tools: dict[str, bool] | None = None
    logging: dict[str, bool] | None = None


class CompleteRequestArgument(msgspec.Struct):
    """Argument information for completion request."""

    name: str
    value: str


class CompleteRequest(msgspec.Struct):
    """Completion request."""

    method: Literal["completion/complete"]
    params: dict[str, Any]


class CompletionValues(msgspec.Struct):
    """Completion values response."""

    has_more: bool | None = field(default=None, name="hasMore")
    total: int | None = None
    values: list[str] = field(max_length=100)


class CompleteResult(msgspec.Struct):
    """Response to a completion request."""

    _meta: dict[str, Any] | None = None
    completion: CompletionValues


class ResourceReference(msgspec.Struct):
    """Reference to a resource."""

    type: str = "resource"
    id: str


class PromptReference(msgspec.Struct):
    """Reference to a prompt."""

    type: str = "prompt"
    id: str


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
    nextCursor: str | None = None


class ResourceTemplateInfo(msgspec.Struct):
    """Information about a resource template."""

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
    nextCursor: str | None = None


class ReadResourceRequest(msgspec.Struct):
    """Request to read a specific resource."""

    method: Literal["resources/read"]
    params: dict[str, Any]


class ReadResourceResult(msgspec.Struct):
    """Result of reading a resource."""

    _meta: dict[str, Any] | None = None
    resource: BlobResourceContents


class ListPromptsRequest(msgspec.Struct):
    """Request to list prompts."""

    method: Literal["prompts/list"]
    params: dict[str, Any] | None = None


class PromptInfo(msgspec.Struct):
    """Information about a prompt."""

    id: str
    name: str
    description: str = ""
    arguments: list[dict[str, Any]] | None = None

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "PromptInfo":
        metadata = inspect_callable(callable)
        arguments = []
        if metadata.arg_model:
            annotations = metadata.arg_model.__annotations__
            for field_name in annotations:
                required = not hasattr(metadata.arg_model, field_name)
                arguments.append(
                    {"name": field_name, "description": "", "required": required}
                )
        return cls(
            id=name, name=name, description=callable.__doc__ or "", arguments=arguments
        )


class ListPromptsResult(msgspec.Struct):
    """Result of listing prompts."""

    prompts: list[PromptInfo]
    nextCursor: str | None = None


class GetPromptRequest(msgspec.Struct):
    """Request to get a specific prompt."""

    method: Literal["prompts/get"]
    params: dict[str, Any]


class Message(msgspec.Struct):
    """Message in MCP."""

    role: Literal["system", "user", "assistant"]
    content: TextContent | ImageContent | EmbeddedResource


class GetPromptResult(msgspec.Struct):
    """Result of getting a prompt."""

    _meta: dict[str, Any] | None = None
    description: str
    messages: list[Message]


class ListToolsRequest(msgspec.Struct):
    """Request to list available tools."""

    method: Literal["tools/list"]
    params: dict[str, Any] | None = None


@dataclass
class ToolInfo:
    """Information about a tool."""

    name: str
    description: str | None = None
    inputSchema: dict[str, Any] = dc_field(default_factory=dict)
    arg_model: type[Any] | None = dc_field(default=None, metadata=Meta(omit=True))

    @classmethod
    def from_callable(cls, callable: Callable, name: str) -> "ToolInfo":
        metadata = inspect_callable(callable)
        return cls(
            name=name,
            description=callable.__doc__ or "",
            inputSchema={},
            arg_model=metadata.arg_model,
        )


class ListToolsResult(msgspec.Struct):
    """Result of listing tools."""

    tools: list[ToolInfo]
    nextCursor: str | None = None


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
    nextCursor: str | None = None


class ErrorResponse(msgspec.Struct):
    """Error response in MCP."""

    code: int | None = None
    message: str | None = None
    data: Any | None = None


class MCPResponse(msgspec.Struct):
    """Base response model for MCP responses."""

    jsonrpc: Literal["2.0"] = "2.0"
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

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None

