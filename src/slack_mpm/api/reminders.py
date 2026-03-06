"""Slack reminders API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def add_reminder(token: str, text: str, time: str) -> dict[str, Any]:
    """Create a reminder for the authenticated user.

    Args:
        token: Slack user token.
        text: Reminder message text.
        time: When to remind — Unix timestamp, natural language (e.g., 'in 30 minutes'),
              or specific time (e.g., 'tomorrow at 9am').

    Returns:
        Dict with 'reminder' object.
    """
    return await slack_post(token, "reminders.add", {"text": text, "time": time})


async def list_reminders(token: str) -> dict[str, Any]:
    """List all reminders for the authenticated user.

    Args:
        token: Slack user token.

    Returns:
        Dict with 'reminders' list.
    """
    return await slack_get(token, "reminders.list")


async def complete_reminder(token: str, reminder: str) -> dict[str, Any]:
    """Mark a reminder as complete.

    Args:
        token: Slack user token.
        reminder: Reminder ID to complete.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "reminders.complete", {"reminder": reminder})


async def delete_reminder(token: str, reminder: str) -> dict[str, Any]:
    """Delete a reminder.

    Args:
        token: Slack user token.
        reminder: Reminder ID to delete.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "reminders.delete", {"reminder": reminder})
