"""Slack message API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def send_message(
    token: str,
    channel: str,
    text: str,
    blocks: list[Any] | None = None,
    thread_ts: str | None = None,
    unfurl_links: bool = True,
) -> dict[str, Any]:
    """Send a message to a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID or name to send to.
        text: Message text (also used as fallback for blocks).
        blocks: Optional Block Kit blocks array for rich formatting.
        thread_ts: If provided, send as a reply in this thread.
        unfurl_links: Whether to unfurl links in the message.

    Returns:
        Dict with 'channel', 'ts', and 'message' fields.
    """
    payload: dict[str, Any] = {
        "channel": channel,
        "text": text,
        "unfurl_links": unfurl_links,
    }
    if blocks is not None:
        payload["blocks"] = blocks
    if thread_ts is not None:
        payload["thread_ts"] = thread_ts

    return await slack_post(token, "chat.postMessage", payload)


async def send_ephemeral(token: str, channel: str, user: str, text: str) -> dict[str, Any]:
    """Send an ephemeral message visible only to a specific user.

    Args:
        token: Slack bot token.
        channel: Channel ID where the ephemeral message appears.
        user: User ID who will see the message.
        text: Message text.

    Returns:
        Dict with 'message_ts' field.
    """
    return await slack_post(
        token,
        "chat.postEphemeral",
        {"channel": channel, "user": user, "text": text},
    )


async def update_message(token: str, channel: str, ts: str, text: str) -> dict[str, Any]:
    """Update an existing message.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        ts: Timestamp of the message to update.
        text: New text for the message.

    Returns:
        Dict with updated 'channel', 'ts', and 'text' fields.
    """
    return await slack_post(
        token,
        "chat.update",
        {"channel": channel, "ts": ts, "text": text},
    )


async def delete_message(token: str, channel: str, ts: str) -> dict[str, Any]:
    """Delete a message.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        ts: Timestamp of the message to delete.

    Returns:
        Dict with 'channel' and 'ts' on success.
    """
    return await slack_post(token, "chat.delete", {"channel": channel, "ts": ts})


async def get_permalink(token: str, channel: str, message_ts: str) -> dict[str, Any]:
    """Get a permanent link to a message.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        message_ts: Timestamp of the message.

    Returns:
        Dict with 'permalink' field.
    """
    return await slack_get(
        token,
        "chat.getPermalink",
        {"channel": channel, "message_ts": message_ts},
    )


async def search_messages(token: str, query: str, count: int = 20) -> dict[str, Any]:
    """Search for messages across the workspace.

    Note: Requires a user token (xoxp-) with search:read scope.

    Args:
        token: Slack user token (xoxp-).
        query: Search query string.
        count: Number of results to return.

    Returns:
        Dict with 'messages' containing matches and pagination info.
    """
    return await slack_get(
        token,
        "search.messages",
        {"query": query, "count": count, "highlight": "false"},
    )


async def list_history(
    token: str,
    channel: str,
    limit: int = 100,
    oldest: str | None = None,
    latest: str | None = None,
) -> dict[str, Any]:
    """Fetch message history from a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID to fetch history from.
        limit: Maximum number of messages to return.
        oldest: Only messages after this Unix timestamp.
        latest: Only messages before this Unix timestamp.

    Returns:
        Dict with 'messages' list and 'has_more' flag.
    """
    params: dict[str, Any] = {"channel": channel, "limit": limit}
    if oldest is not None:
        params["oldest"] = oldest
    if latest is not None:
        params["latest"] = latest

    return await slack_get(token, "conversations.history", params)


async def add_reaction(token: str, channel: str, timestamp: str, name: str) -> dict[str, Any]:
    """Add an emoji reaction to a message.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        timestamp: Message timestamp.
        name: Emoji name without colons (e.g., 'thumbsup').

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(
        token,
        "reactions.add",
        {"channel": channel, "timestamp": timestamp, "name": name},
    )


async def remove_reaction(token: str, channel: str, timestamp: str, name: str) -> dict[str, Any]:
    """Remove an emoji reaction from a message.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        timestamp: Message timestamp.
        name: Emoji name without colons (e.g., 'thumbsup').

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(
        token,
        "reactions.remove",
        {"channel": channel, "timestamp": timestamp, "name": name},
    )


async def pin_message(token: str, channel: str, timestamp: str) -> dict[str, Any]:
    """Pin a message in a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        timestamp: Message timestamp to pin.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "pins.add", {"channel": channel, "timestamp": timestamp})


async def unpin_message(token: str, channel: str, timestamp: str) -> dict[str, Any]:
    """Unpin a message from a channel.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the message.
        timestamp: Message timestamp to unpin.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "pins.remove", {"channel": channel, "timestamp": timestamp})


async def reply_in_thread(
    token: str, channel: str, thread_ts: str, text: str
) -> dict[str, Any]:
    """Reply to a message in a thread.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the thread.
        thread_ts: Timestamp of the parent message.
        text: Reply text.

    Returns:
        Dict with 'channel', 'ts', and 'message' fields.
    """
    return await slack_post(
        token,
        "chat.postMessage",
        {"channel": channel, "thread_ts": thread_ts, "text": text},
    )


async def get_thread_replies(token: str, channel: str, thread_ts: str) -> dict[str, Any]:
    """Fetch all replies in a thread.

    Args:
        token: Slack bot token.
        channel: Channel ID containing the thread.
        thread_ts: Timestamp of the parent message.

    Returns:
        Dict with 'messages' list (first message is the parent).
    """
    return await slack_get(
        token,
        "conversations.replies",
        {"channel": channel, "ts": thread_ts},
    )
