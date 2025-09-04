"""
Queue implementation for MCP responses
"""

import logging
import sqlite3
import time
from typing import Protocol

import msgspec

from .schema import MCPResponse

logger = logging.getLogger("mcp_utils")


class ResponseQueueProtocol(Protocol):
    """Protocol defining the interface for response queues"""

    def push_response(
        self,
        session_id: str,
        response: MCPResponse,
    ) -> None: ...

    def wait_for_response(
        self, session_id: str, timeout: float | None = None
    ) -> str | None: ...

    def clear_session(self, session_id: str) -> None: ...


class RedisResponseQueue(ResponseQueueProtocol):
    """
    A Redis-backed queue implementation for MCP responses.
    Each session has its own Redis list.
    """

    def __init__(self, redis_client):
        """
        Initialize Redis queue

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def _get_queue_key(self, session_id: str) -> str:
        """Get Redis key for session queue"""
        return f"mcp:response_queue:{session_id}"

    def push_response(
        self,
        session_id: str,
        response: MCPResponse,
    ) -> None:
        """
        Push a response to the Redis queue for a specific session

        Args:
            session_id: The session ID
            response: The response to push
        """
        queue_key = self._get_queue_key(session_id)
        value = msgspec.json.encode(response).decode()
        logger.debug(f"Redis: Saving response for session: {session_id}: {value}")
        self.redis.rpush(queue_key, value)

    def wait_for_response(
        self, session_id: str, timeout: float | None = None
    ) -> MCPResponse | None:
        """
        Wait for a response from the Redis queue for a specific session

        Args:
            session_id: The session ID
            timeout: How long to wait for a response in seconds.
                    If None, wait indefinitely.
                    If 0, return immediately if no response is available.

        Returns:
            The next queued response or None if timeout occurs
        """
        queue_key = self._get_queue_key(session_id)
        if timeout == 0:
            # Non-blocking check
            data = self.redis.lpop(queue_key)
        else:
            # Blocking wait with timeout
            data = self.redis.blpop(
                queue_key, timeout=timeout if timeout is not None else 0
            )
            if data:
                # blpop returns (key, value) tuple
                data = data[1]

        if not data:
            return None
        elif isinstance(data, bytes):
            return data.decode("utf-8")
        return data

    def clear_session(self, session_id: str) -> None:
        """
        Clear all queued responses for a session

        Args:
            session_id: The session ID to clear
        """
        queue_key = self._get_queue_key(session_id)
        self.redis.delete(queue_key)
        logger.debug(f"Redis: Clearing session: {session_id}")


class SQLiteResponseQueue(ResponseQueueProtocol):
    """
    A SQLite-backed queue implementation for MCP responses.
    Each session is a logical queue keyed by `session_id`.

    Uses a simple table and transactional pop to ensure single-delivery.
    """

    def __init__(self, db_path: str = ":memory:"):
        """Initialize and create tables if needed.

        Args:
            db_path: Path to the SQLite database file. Defaults to in-memory.
        """
        # isolation_level=None -> autocommit mode so we can manage BEGIN/COMMIT explicitly
        self.conn = sqlite3.connect(
            db_path, timeout=30, check_same_thread=False, isolation_level=None
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS response_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL DEFAULT (strftime('%s','now'))
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_response_queue_session_id
            ON response_queue(session_id, id)
            """
        )

    def push_response(self, session_id: str, response: MCPResponse) -> None:
        """Insert a response payload for a session."""
        payload = msgspec.json.encode(response).decode()
        logger.debug(f"SQLite: Saving response for session: {session_id}: {payload}")
        self.conn.execute(
            "INSERT INTO response_queue (session_id, payload) VALUES (?, ?)",
            (session_id, payload),
        )

    def _pop_one(self, session_id: str) -> str | None:
        """Atomically pop the oldest payload for the session, if any."""
        try:
            cur = self.conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT id, payload FROM response_queue WHERE session_id = ? ORDER BY id LIMIT 1",
                (session_id,),
            ).fetchone()
            if not row:
                cur.execute("ROLLBACK")
                return None
            row_id, payload = row
            cur.execute("DELETE FROM response_queue WHERE id = ?", (row_id,))
            cur.execute("COMMIT")
            return payload
        except sqlite3.Error as e:
            logger.error(f"SQLite pop error: {e}")
            try:
                self.conn.execute("ROLLBACK")
            except Exception:
                pass
            return None

    def wait_for_response(self, session_id: str, timeout: float | None = None) -> str | None:
        """
        Wait for and pop the next response for a session.

        If timeout is None, waits indefinitely using polling.
        If timeout is 0, returns immediately if none available.
        """
        # Immediate, non-blocking attempt
        payload = self._pop_one(session_id)
        if payload is not None:
            return payload

        if timeout == 0:
            return None

        # Poll until available or timeout
        start = time.time()
        while True:
            payload = self._pop_one(session_id)
            if payload is not None:
                return payload
            if timeout is not None and (time.time() - start) >= timeout:
                return None
            time.sleep(0.1)

    def clear_session(self, session_id: str) -> None:
        """Remove all queued items for a session."""
        logger.debug(f"SQLite: Clearing session: {session_id}")
        self.conn.execute(
            "DELETE FROM response_queue WHERE session_id = ?",
            (session_id,),
        )
