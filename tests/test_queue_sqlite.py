"""Tests for SQLiteResponseQueue implementation."""

import json
from typing import Any

import pytest

from mcp_utils.queue import SQLiteResponseQueue
from mcp_utils.schema import MCPResponse


@pytest.fixture()
def q(tmp_path) -> SQLiteResponseQueue:
    return SQLiteResponseQueue(db_path=str(tmp_path / "queue.db"))


def build_response(resp_id: str | int, result: dict[str, Any] | None = None) -> MCPResponse:
    return MCPResponse(jsonrpc="2.0", id=resp_id, result=result or {})


def test_push_and_pop_single(q: SQLiteResponseQueue) -> None:
    session = "s1"
    resp = build_response("1", {"x": 1})
    q.push_response(session, resp)

    data = q.wait_for_response(session, timeout=0)
    assert data is not None
    payload = json.loads(data)
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == "1"
    assert payload["result"] == {"x": 1}


def test_timeout_behavior(q: SQLiteResponseQueue) -> None:
    session = "s-timeout"
    assert q.wait_for_response(session, timeout=0) is None
    assert q.wait_for_response(session, timeout=0.1) is None


def test_clear_session(q: SQLiteResponseQueue) -> None:
    session = "s-clear"
    q.push_response(session, build_response("1"))
    q.push_response(session, build_response("2"))
    q.clear_session(session)
    assert q.wait_for_response(session, timeout=0) is None


def test_fifo_ordering(q: SQLiteResponseQueue) -> None:
    session = "s-fifo"
    q.push_response(session, build_response("1", {"n": 1}))
    q.push_response(session, build_response("2", {"n": 2}))

    d1 = json.loads(q.wait_for_response(session, timeout=0))
    d2 = json.loads(q.wait_for_response(session, timeout=0))
    assert d1["id"] == "1"
    assert d2["id"] == "2"


def test_isolation_between_sessions(q: SQLiteResponseQueue) -> None:
    s1, s2 = "s-a", "s-b"
    q.push_response(s1, build_response("a1"))
    q.push_response(s2, build_response("b1"))

    d1 = json.loads(q.wait_for_response(s1, timeout=0))
    assert d1["id"] == "a1"
    # s1 should be empty now
    assert q.wait_for_response(s1, timeout=0) is None

    d2 = json.loads(q.wait_for_response(s2, timeout=0))
    assert d2["id"] == "b1"

