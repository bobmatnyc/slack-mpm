"""Slack user API functions."""

from __future__ import annotations

from typing import Any

from slack_mcp.api._client import slack_get, slack_post


async def list_users(token: str, limit: int = 200) -> dict[str, Any]:
    """List all users in the workspace with pagination.

    Args:
        token: Slack bot token.
        limit: Maximum number of users to return.

    Returns:
        Dict with 'members' list.
    """
    all_members: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor

        data = await slack_get(token, "users.list", params)
        all_members.extend(data.get("members", []))

        next_cursor = data.get("response_metadata", {}).get("next_cursor")
        if not next_cursor or len(all_members) >= limit:
            break
        cursor = next_cursor

    return {"ok": True, "members": all_members[:limit]}


async def get_user_info(token: str, user: str) -> dict[str, Any]:
    """Get detailed information about a user.

    Args:
        token: Slack bot token.
        user: User ID (e.g., 'U1234567890').

    Returns:
        Dict with 'user' object.
    """
    return await slack_get(token, "users.info", {"user": user})


async def get_user_by_email(token: str, email: str) -> dict[str, Any]:
    """Look up a user by their email address.

    Args:
        token: Slack bot token.
        email: Email address to look up.

    Returns:
        Dict with 'user' object.
    """
    return await slack_get(token, "users.lookupByEmail", {"email": email})


async def open_dm(token: str, users: list[str]) -> dict[str, Any]:
    """Open a direct message channel with one or more users.

    Args:
        token: Slack bot token.
        users: List of user IDs to open a DM with.

    Returns:
        Dict with 'channel' object containing the DM channel ID.
    """
    return await slack_post(token, "conversations.open", {"users": ",".join(users)})


async def list_user_channels(token: str, user: str) -> dict[str, Any]:
    """List all channels a user is a member of.

    Args:
        token: Slack bot token.
        user: User ID to list channels for.

    Returns:
        Dict with 'channels' list.
    """
    all_channels: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {"user": user, "limit": 200}
        if cursor:
            params["cursor"] = cursor

        data = await slack_get(token, "users.conversations", params)
        all_channels.extend(data.get("channels", []))

        next_cursor = data.get("response_metadata", {}).get("next_cursor")
        if not next_cursor:
            break
        cursor = next_cursor

    return {"ok": True, "channels": all_channels}
