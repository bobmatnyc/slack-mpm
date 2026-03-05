"""Slack channel API functions."""

from __future__ import annotations

from typing import Any

from slack_mcp.api._client import slack_get, slack_post


async def list_channels(
    token: str,
    types: str = "public_channel,private_channel",
    exclude_archived: bool = True,
    limit: int = 200,
) -> dict[str, Any]:
    """List all channels in the workspace with pagination.

    Args:
        token: Slack bot token.
        types: Comma-separated list of channel types to include.
        exclude_archived: If True, exclude archived channels.
        limit: Maximum number of channels per page request.

    Returns:
        Dict with 'channels' list and metadata.
    """
    all_channels: list[dict[str, Any]] = []
    cursor: str | None = None

    while True:
        params: dict[str, Any] = {
            "types": types,
            "exclude_archived": str(exclude_archived).lower(),
            "limit": min(limit, 200),
        }
        if cursor:
            params["cursor"] = cursor

        data = await slack_get(token, "conversations.list", params)
        all_channels.extend(data.get("channels", []))

        next_cursor = data.get("response_metadata", {}).get("next_cursor")
        if not next_cursor or len(all_channels) >= limit:
            break
        cursor = next_cursor

    return {"ok": True, "channels": all_channels[:limit]}


async def get_channel_info(token: str, channel: str) -> dict[str, Any]:
    """Get detailed information about a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID (e.g., 'C1234567890').

    Returns:
        Dict with 'channel' info object.
    """
    return await slack_get(token, "conversations.info", {"channel": channel, "include_num_members": "true"})


async def create_channel(token: str, name: str, is_private: bool = False) -> dict[str, Any]:
    """Create a new Slack channel.

    Args:
        token: Slack bot token.
        name: Name for the new channel (lowercase, no spaces).
        is_private: If True, create as a private channel.

    Returns:
        Dict with 'channel' object of the newly created channel.
    """
    return await slack_post(token, "conversations.create", {"name": name, "is_private": is_private})


async def archive_channel(token: str, channel: str) -> dict[str, Any]:
    """Archive a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID to archive.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "conversations.archive", {"channel": channel})


async def invite_to_channel(token: str, channel: str, users: list[str]) -> dict[str, Any]:
    """Invite one or more users to a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID to invite users to.
        users: List of user IDs to invite.

    Returns:
        Dict with 'channel' object.
    """
    return await slack_post(
        token,
        "conversations.invite",
        {"channel": channel, "users": ",".join(users)},
    )


async def kick_from_channel(token: str, channel: str, user: str) -> dict[str, Any]:
    """Remove a user from a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID.
        user: User ID to remove.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "conversations.kick", {"channel": channel, "user": user})


async def join_channel(token: str, channel: str) -> dict[str, Any]:
    """Join a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID to join.

    Returns:
        Dict with 'channel' object.
    """
    return await slack_post(token, "conversations.join", {"channel": channel})


async def set_channel_topic(token: str, channel: str, topic: str) -> dict[str, Any]:
    """Set the topic for a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID.
        topic: New topic text.

    Returns:
        Dict with 'topic' field on success.
    """
    return await slack_post(token, "conversations.setTopic", {"channel": channel, "topic": topic})
