"""Slack workspace API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def get_workspace_info(token: str) -> dict[str, Any]:
    """Get information about the current Slack workspace.

    Args:
        token: Slack bot token.

    Returns:
        Dict with 'team' object containing workspace details.
    """
    return await slack_get(token, "team.info")


async def list_emojis(token: str) -> dict[str, Any]:
    """List all custom emoji in the workspace.

    Args:
        token: Slack bot token.

    Returns:
        Dict with 'emoji' object mapping emoji names to image URLs.
    """
    return await slack_get(token, "emoji.list")


async def get_bot_info(token: str) -> dict[str, Any]:
    """Get information about the bot associated with the token.

    Args:
        token: Slack bot token.

    Returns:
        Dict with 'bot' object containing bot details.
    """
    return await slack_get(token, "bots.info")


async def auth_test(token: str) -> dict[str, Any]:
    """Validate a Slack token and get workspace/user info.

    Args:
        token: Slack bot or user token to validate.

    Returns:
        Dict with 'url', 'team', 'user', 'team_id', 'user_id', and optionally 'bot_id'.
    """
    return await slack_post(token, "auth.test", {})
