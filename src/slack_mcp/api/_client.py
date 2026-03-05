"""Shared Slack HTTP client."""

from __future__ import annotations

import anyio
import httpx
from typing import Any


SLACK_API_BASE = "https://slack.com/api"


class SlackAPIError(Exception):
    """Raised when the Slack API returns an error response."""

    def __init__(self, endpoint: str, error: str, response: dict[str, Any]) -> None:
        self.endpoint = endpoint
        self.error = error
        self.response = response
        super().__init__(f"Slack API error on {endpoint}: {error}")


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
        response = await client.get(
            f"{SLACK_API_BASE}/{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            await anyio.sleep(retry_after)
            response = await client.get(
                f"{SLACK_API_BASE}/{endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                params=params or {},
            )

        data: dict[str, Any] = response.json()
        if not data.get("ok"):
            raise SlackAPIError(endpoint, data.get("error", "unknown_error"), data)
        return data


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
        response = await client.post(
            f"{SLACK_API_BASE}/{endpoint}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json=json_data or {},
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            await anyio.sleep(retry_after)
            response = await client.post(
                f"{SLACK_API_BASE}/{endpoint}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=json_data or {},
            )

        data: dict[str, Any] = response.json()
        if not data.get("ok"):
            raise SlackAPIError(endpoint, data.get("error", "unknown_error"), data)
        return data
