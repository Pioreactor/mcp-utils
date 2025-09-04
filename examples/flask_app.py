"""
Example Flask application implementing an MCP server.

`pip install mcp-utils flask gunicorn`

This example also:

* Demonstrates logging setup
* Demonstrates session management
* Demonstrates SSE stream handling

Uses the built-in SQLite-backed response queue.
"""

import logging
import sys

from flask import Flask, jsonify, request
import msgspec
from gunicorn.app.base import BaseApplication

from mcp_utils.core import MCPServer
from mcp_utils.queue import SQLiteResponseQueue
from mcp_utils.schema import (
    CallToolResult,
    CompletionValues,
    GetPromptResult,
    Message,
    TextContent,
)

app = Flask(__name__)
mcp = MCPServer("weather", "1.0", response_queue=SQLiteResponseQueue("responses.db"))

logger = logging.getLogger("mcp_utils")
logger.setLevel(logging.DEBUG)


@mcp.tool()
def get_weather(city: str) -> str:
    return "sunny"


@mcp.prompt()
def get_forecast() -> GetPromptResult:
    return GetPromptResult(
        description="Weather forecast prompt",
        messages=[
            Message(
                role="user",
                content=TextContent(
                    text="What is the weather forecast like?",
                ),
            )
        ],
    )


@mcp.prompt()
def get_weather_prompt(city: str) -> GetPromptResult:
    return GetPromptResult(
        description="Weather prompt",
        messages=[
            Message(
                role="user",
                content=TextContent(
                    text=f"What is the weather like in {city}?",
                ),
            )
        ],
    )


@get_weather_prompt.completion("city")
def get_cities(city_name: str) -> CompletionValues:
    all_cities = ["New York", "London", "Tokyo", "Sydney", "Beijing"]
    # Filter cities that start with the given city
    return [city for city in all_cities if city.lower().startswith(city_name.lower())]


@app.route("/mcp", methods=["POST"])
def mcp_route():
    response = mcp.handle_message(request.get_json())
    # Convert msgspec Struct to builtin types for jsonify
    return jsonify(msgspec.to_builtins(response))


class FlaskApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    options = {
        "bind": "0.0.0.0:9000",
        "workers": 1,
        "worker_class": "gevent",
        "loglevel": "debug",
    }
    FlaskApplication(app, options).run()
