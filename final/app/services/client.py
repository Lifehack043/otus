"""Shared HTTP client with proper SSL configuration."""

import httpx
import truststore


def create_client(timeout: float = 5.0) -> httpx.AsyncClient:
    """Create an async client with system trust store for SSL."""
    ssl_context = truststore.SSLContext()
    return httpx.AsyncClient(
        timeout=timeout,
        verify=ssl_context,
    )
