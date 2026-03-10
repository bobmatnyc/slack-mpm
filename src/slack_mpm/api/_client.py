"""Shared Slack HTTP client."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

import anyio
import httpx

SLACK_API_BASE = "https://slack.com/api"


class SlackAPIError(Exception):
    """Raised when the Slack API returns an error response."""

    def __init__(self, endpoint: str, error: str, response: dict[str, Any]) -> None:
        self.endpoint = endpoint
        self.error = error
        self.response = response
        super().__init__(f"Slack API error on {endpoint}: {error}")


async def _request_with_retry(
    endpoint: str,
    request_fn: Callable[[], Coroutine[Any, Any, httpx.Response]],
    *,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Fire an HTTP request, retrying on 429 up to max_retries times.

    Args:
        endpoint: Slack API endpoint name, used only for error messages.
        request_fn: No-argument async callable that fires the actual httpx call
            and returns the raw :class:`httpx.Response`.
        max_retries: Maximum number of attempts (including the first one).

    Returns:
        Parsed JSON response from Slack on a successful (ok=true) response.

    Raises:
        SlackAPIError: On non-2xx non-429 responses or when ok=false.
    """
    for attempt in range(max_retries):
        response = await request_fn()

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            if attempt < max_retries - 1:
                await anyio.sleep(retry_after)
                continue
            # Exhausted retries — fall through to raise SlackAPIError below.

        data: dict[str, Any] = response.json()
        if not data.get("ok"):
            raise SlackAPIError(endpoint, data.get("error", "unknown_error"), data)
        return data

    # Should only be reached when every attempt returned 429.
    raise SlackAPIError(endpoint, "ratelimited", {})


async def slack_get(
    token: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make GET request to Slack API.

    Args:
        token: Slack API token (bot or user).
        endpoint: Slack API endpoint (e.g., 'conversations.list').
        params: Query parameters to include in the request.

    Returns:
        Parsed JSON response from Slack.

    Raises:
        SlackAPIError: If Slack returns ok=false.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _request_with_retry(
            endpoint,
            lambda: client.get(
                f"{SLACK_API_BASE}/{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
            ),
        )


async def slack_post(
    token: str,
    endpoint: str,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make POST request to Slack API.

    Args:
        token: Slack API token (bot or user).
        endpoint: Slack API endpoint (e.g., 'chat.postMessage').
        json_data: JSON body to send with the request.

    Returns:
        Parsed JSON response from Slack.

    Raises:
        SlackAPIError: If Slack returns ok=false.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await _request_with_retry(
            endpoint,
            lambda: client.post(
                f"{SLACK_API_BASE}/{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=json_data or {},
            ),
        )
