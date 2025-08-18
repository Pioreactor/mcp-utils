"""Utility functions for MCP server implementation."""

from collections.abc import Callable
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any, get_type_hints

import msgspec


@dataclass
class CallableMetadata:
    """Metadata about a callable's signature."""

    arg_model: type[Any]  # msgspec Struct for arguments
    return_type: type[Any]  # Return type of the callable


def inspect_callable(
    func: Callable,
    *,
    skip_names: list[str] = None,
) -> CallableMetadata:
    """Inspect a callable and return its type information.

    Args:
        func: The callable to inspect
        skip_names: List of argument names to skip

    Returns:
        CallableMetadata containing arg_model (Pydantic model for args) and return type
    """
    skip_names = skip_names or []
    sig = signature(func)
    type_hints = get_type_hints(func)

    # Build annotations and defaults for a dynamic Struct
    annotations: dict[str, type[Any]] = {}
    namespace: dict[str, Any] = {"__annotations__": annotations}

    for name, param in sig.parameters.items():
        if name in skip_names:
            continue

        param_type = type_hints.get(name, Any)
        annotations[name] = param_type
        if param.default is not Parameter.empty:
            namespace[name] = param.default

    arg_model = type(f"{func.__name__}Args", (msgspec.Struct,), namespace)

    return CallableMetadata(
        arg_model=arg_model, return_type=type_hints.get("return", Any)
    )
