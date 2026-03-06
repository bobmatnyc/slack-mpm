"""Slack scheduled messages API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def schedule_message(
    token: str,
    channel: str,
    text: str,
    post_at: int,
) -> dict[str, Any]:
    """Schedule a message to be sent at a future time.

    Args:
        token: Slack bot token.
        channel: Channel ID to send the message to.
        text: Message text.
        post_at: Unix timestamp (seconds since epoch) when to send the message.

    Returns:
        Dict with 'scheduled_message_id', 'channel', and 'post_at'.
    """
    return await slack_post(
        token,
        "chat.scheduleMessage",
        {"channel": channel, "text": text, "post_at": post_at},
    )


async def list_scheduled_messages(
    token: str,
    channel: str | None = None,
) -> dict[str, Any]:
    """List all pending scheduled messages.

    Args:
        token: Slack bot token.
        channel: Optional channel ID to filter by.

    Returns:
        Dict with 'scheduled_messages' list.
    """
    params: dict[str, Any] = {}
    if channel:
        params["channel"] = channel

    return await slack_get(token, "chat.scheduledMessages.list", params)


async def delete_scheduled_message(
    token: str,
    channel: str,
    scheduled_message_id: str,
) -> dict[str, Any]:
    """Cancel/delete a scheduled message before it is sent.

    Args:
        token: Slack bot token.
        channel: Channel ID the message was scheduled for.
        scheduled_message_id: The scheduled message ID to cancel.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(
        token,
        "chat.deleteScheduledMessage",
        {"channel": channel, "scheduled_message_id": scheduled_message_id},
    )
