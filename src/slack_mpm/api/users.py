"""Slack user API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post
from slack_mpm.api._pagination import paginate


async def list_users(token: str, limit: int = 200) -> dict[str, Any]:
    """List all users in the workspace with pagination.

    Args:
        token: Slack bot token.
        limit: Maximum number of users to return.

    Returns:
        Dict with 'members' list.
    """
    all_members: list[dict[str, Any]] = []

    async def _api_fn(**params: Any) -> dict[str, Any]:
        return await slack_get(token, "users.list", params)

    async for page in paginate(_api_fn, "members", limit=min(limit, 200)):
        all_members.extend(page)
        if len(all_members) >= limit:
            break

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

    async def _api_fn(**params: Any) -> dict[str, Any]:
        return await slack_get(token, "users.conversations", params)

    async for page in paginate(_api_fn, "channels", limit=200, user=user):
        all_channels.extend(page)

    return {"ok": True, "channels": all_channels}
