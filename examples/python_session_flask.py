"""
Flask-based MCP server exposing a single `python_session` tool.

Install deps:

    pip install mcp-utils flask

Usage:

    python examples/python_session_flask.py

Notes:
- Keeps a persistent Python execution context across calls (shared state).
- Returns captured stdout/stderr and the value of the final expression, if any.
"""

from __future__ import annotations

import ast
import io
import logging
import sys
from contextlib import redirect_stdout, redirect_stderr

from flask import Flask, jsonify, request
import msgspec

from mcp_utils.core import MCPServer
from mcp_utils.queue import SQLiteResponseQueue
from mcp_utils.schema import CallToolResult, TextContent


app = Flask(__name__)
mcp = MCPServer("python-session", "1.0", response_queue=SQLiteResponseQueue("responses.db"))

logger = logging.getLogger("mcp_utils")
logger.setLevel(logging.DEBUG)


# A single, persistent execution context shared across requests
_EXEC_CONTEXT: dict[str, object] = {}


def _run_code_in_persistent_context(code: str, context: dict[str, object]) -> tuple[str, bool]:
    """Execute code in a persistent context and return (output, is_error).

    - Captures stdout and stderr
    - If the last statement is an expression, evaluates and appends its repr
    """
    stdout = io.StringIO()
    result_text = ""
    is_error = False

    try:
        module = ast.parse(code, mode="exec")
        body = module.body
        with redirect_stdout(stdout), redirect_stderr(stdout):
            if body and isinstance(body[-1], ast.Expr):
                # Execute all but last, then eval last expression and show its repr
                exec(compile(ast.Module(body=body[:-1], type_ignores=[]), "<session>", "exec"), context, context)
                last_expr = ast.Expression(body[-1].value)
                value = eval(compile(last_expr, "<session>", "eval"), context, context)
                if value is not None:
                    print(repr(value))
            else:
                exec(compile(module, "<session>", "exec"), context, context)
    except Exception as e:  # noqa: BLE001 - return error text to client
        is_error = True
        # Include exception type and message; details in stdout if any
        result_text = f"{e.__class__.__name__}: {e}"

    output = stdout.getvalue()
    if result_text:
        output = (output + ("\n" if output and not output.endswith("\n") else "") + result_text).rstrip()
    return (output if output else ("" if not is_error else result_text)), is_error


@mcp.tool()
def execute_code(code: str) -> CallToolResult:
    """Execute Python code in a session.

    Code executes in a persistent, shared context across calls.
    """
    output, is_error = _run_code_in_persistent_context(code, _EXEC_CONTEXT)
    # Always return a string content payload with error flag as appropriate
    return CallToolResult(content=[TextContent(text=output or "")], is_error=is_error)


@app.route("/mcp", methods=["POST"])
def mcp_route():
    response = mcp.handle_message(request.get_json())
    return jsonify(msgspec.to_builtins(response))


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # Run with Flask's built-in dev server locally
    app.run(host="127.0.0.1", port=9005, debug=True)
