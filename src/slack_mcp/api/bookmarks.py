"""Slack bookmarks API functions."""

from __future__ import annotations

from typing import Any

from slack_mcp.api._client import slack_get, slack_post


async def list_bookmarks(token: str, channel_id: str) -> dict[str, Any]:
    """List all bookmarks in a channel.

    Args:
        token: Slack bot token.
        channel_id: Channel ID to list bookmarks for.

    Returns:
        Dict with 'bookmarks' list.
    """
    return await slack_get(token, "bookmarks.list", {"channel_id": channel_id})


async def add_bookmark(
    token: str,
    channel_id: str,
    title: str,
    link: str,
    emoji: str | None = None,
) -> dict[str, Any]:
    """Add a bookmark to a channel.

    Args:
        token: Slack bot token.
        channel_id: Channel ID to add the bookmark to.
        title: Display title for the bookmark.
        link: URL for the bookmark.
        emoji: Optional emoji to display with the bookmark (without colons).

    Returns:
        Dict with 'bookmark' object.
    """
    payload: dict[str, Any] = {
        "channel_id": channel_id,
        "title": title,
        "link": link,
        "type": "link",
    }
    if emoji is not None:
        payload["emoji"] = f":{emoji}:"

    return await slack_post(token, "bookmarks.add", payload)


async def remove_bookmark(token: str, channel_id: str, bookmark_id: str) -> dict[str, Any]:
    """Remove a bookmark from a channel.

    Args:
        token: Slack bot token.
        channel_id: Channel ID containing the bookmark.
        bookmark_id: Bookmark ID to remove.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(
        token,
        "bookmarks.remove",
        {"channel_id": channel_id, "bookmark_id": bookmark_id},
    )
