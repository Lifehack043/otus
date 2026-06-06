"""
Store module for key-value storage communication with Redis.

Supports reconnection with retries and timeouts.
"""

import redis
from typing import Any, Optional


class Store:
    """Redis-based key-value store with reconnection and timeout support."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        retry_times: int = 3,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.retry_times = retry_times
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self._client: Optional[redis.Redis] = None

    def _get_client(self) -> redis.Redis:
        """Get or create a Redis client connection."""
        if self._client is None:
            self._connect()
        return self._client

    def _connect(self):
        """Establish connection to Redis."""
        self._client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            decode_responses=True,
        )

    def _execute_with_retry(self, operation, *args, **kwargs):
        """Execute a Redis operation with retry logic."""
        last_exception = None
        for attempt in range(self.retry_times):
            try:
                client = self._get_client()
                return operation(client, *args, **kwargs)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_exception = e
                # Reset client to force reconnection on next attempt
                self._client = None
        raise last_exception

    # --- Cache methods (for get_score - should not fail) ---

    def cache_get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache. Returns None if key not found or store is unavailable.
        """
        try:
            def _get(client, k):
                return client.get(k)
            return self._execute_with_retry(_get, key)
        except (redis.ConnectionError, redis.TimeoutError):
            return None

    def cache_set(self, key: str, value: Any, ttl: int = 0) -> None:
        """
        Set a value in cache with optional TTL in seconds.
        Does not raise if store is unavailable.
        """
        try:
            def _set(client, k, v, t):
                if t > 0:
                    client.setex(k, t, v)
                else:
                    client.set(k, v)
            self._execute_with_retry(_set, key, str(value), ttl)
        except (redis.ConnectionError, redis.TimeoutError):
            pass

    # --- Persistent storage methods (for get_interests - must fail) ---

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from persistent storage.
        Raises exception if store is unavailable.
        """
        def _get(client, k):
            return client.get(k)
        return self._execute_with_retry(_get, key)

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        """
        Set a value in persistent storage with optional TTL in seconds.
        Raises exception if store is unavailable.
        """
        def _set(client, k, v, t):
            if t > 0:
                client.setex(k, t, v)
            else:
                client.set(k, v)
        self._execute_with_retry(_set, key, str(value), ttl)
