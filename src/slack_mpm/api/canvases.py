"""Slack Canvas API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_post


async def create_canvas(
    token: str,
    title: str,
    document_content: str,
) -> dict[str, Any]:
    """Create a workspace-level canvas.

    Why: Enables creating standalone canvases in the workspace for document delivery.
    What: Calls canvases.create with title and markdown document_content.
    Test: Mock slack_post, assert called with canvases.create, verify canvas_id returned.

    Args:
        token: Slack bot token (requires canvases:write).
        title: Canvas title.
        document_content: Markdown content for the canvas.

    Returns:
        Dict with 'canvas_id', 'is_empty', 'created_at'.

    Raises:
        SlackAPIError: On API errors or insufficient permissions.
    """
    payload: dict[str, Any] = {
        "title": title,
        "document_content": {"type": "markdown", "markdown": document_content},
    }
    return await slack_post(token, "canvases.create", payload)


async def create_channel_canvas(
    token: str,
    channel: str,
    title: str,
    document_content: str,
) -> dict[str, Any]:
    """Create a channel-attached canvas.

    Why: Pins a canvas directly to a channel for persistent reference.
    What: Calls conversations.canvases.create with channel, title, and markdown content.
    Test: Mock slack_post, verify conversations.canvases.create called with channel param.

    Args:
        token: Slack bot token (requires canvases:write).
        channel: Channel ID to attach the canvas to.
        title: Canvas title.
        document_content: Markdown content for the canvas.

    Returns:
        Dict with 'canvas_id', 'is_empty', 'created_at'.

    Raises:
        SlackAPIError: On API errors, channel not found, or insufficient permissions.
    """
    payload: dict[str, Any] = {
        "channel_id": channel,
        "title": title,
        "document_content": {"type": "markdown", "markdown": document_content},
    }
    return await slack_post(token, "conversations.canvases.create", payload)


async def edit_canvas(
    token: str,
    canvas_id: str,
    document_content: str,
    operation_id: str | None = None,
) -> dict[str, Any]:
    """Edit an existing canvas.

    Why: Allows updating canvas content after creation for iterative document delivery.
    What: Calls canvases.edit with canvas_id and replacement markdown content.
    Test: Mock slack_post, verify canvases.edit called with canvas_id and content.

    Args:
        token: Slack bot token (requires canvases:write).
        canvas_id: Canvas ID to edit.
        document_content: New markdown content.
        operation_id: Optional idempotency key for the edit.

    Returns:
        Dict with 'canvas_id' and operation metadata.

    Raises:
        SlackAPIError: On API errors or canvas not found.
    """
    payload: dict[str, Any] = {
        "canvas_id": canvas_id,
        "changes": [
            {
                "operation": "replace",
                "document_content": {"type": "markdown", "markdown": document_content},
            }
        ],
    }
    if operation_id is not None:
        payload["operation_id"] = operation_id
    return await slack_post(token, "canvases.edit", payload)


async def delete_canvas(token: str, canvas_id: str) -> dict[str, Any]:
    """Delete a canvas.

    Why: Removes a canvas when no longer needed.
    What: Calls canvases.delete with canvas_id.
    Test: Mock slack_post, assert canvases.delete called, verify ok=true response.

    Args:
        token: Slack bot token (requires canvases:write).
        canvas_id: Canvas ID to delete.

    Returns:
        Dict with ok=true on success.

    Raises:
        SlackAPIError: On API errors or canvas not found.
    """
    return await slack_post(token, "canvases.delete", {"canvas_id": canvas_id})


async def set_canvas_access(
    token: str,
    canvas_id: str,
    access_level: str,
    user_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Set access rules for a canvas.

    Why: Controls who can view or edit a canvas for secure document sharing.
    What: Calls canvases.access.set with access_level and optional user/group IDs.
    Test: Mock slack_post, verify canvases.access.set called with correct access_level.

    Args:
        token: Slack bot token (requires canvases:write).
        canvas_id: Canvas ID.
        access_level: "read", "write", or "owner".
        user_ids: List of user IDs to grant access to.
        group_ids: List of group IDs to grant access to.

    Returns:
        Dict with access control details.

    Raises:
        SlackAPIError: On API errors.
    """
    payload: dict[str, Any] = {
        "canvas_id": canvas_id,
        "access_level": access_level,
    }
    if user_ids is not None:
        payload["user_ids"] = user_ids
    if group_ids is not None:
        payload["group_ids"] = group_ids
    return await slack_post(token, "canvases.access.set", payload)


async def delete_canvas_access(
    token: str,
    canvas_id: str,
    user_id: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Revoke access to a canvas.

    Why: Removes specific users or groups from canvas access.
    What: Calls canvases.access.delete with canvas_id and user or group ID.
    Test: Mock slack_post, verify canvases.access.delete called with canvas_id.

    Args:
        token: Slack bot token (requires canvases:write).
        canvas_id: Canvas ID.
        user_id: User ID to revoke access for.
        group_id: Group ID to revoke access for.

    Returns:
        Dict with ok=true.

    Raises:
        SlackAPIError: On API errors.
    """
    payload: dict[str, Any] = {"canvas_id": canvas_id}
    if user_id is not None:
        payload["user_id"] = user_id
    if group_id is not None:
        payload["group_id"] = group_id
    return await slack_post(token, "canvases.access.delete", payload)


async def lookup_canvas_sections(
    token: str,
    canvas_id: str,
) -> dict[str, Any]:
    """Look up sections/blocks in a canvas.

    Why: Enables navigation and targeted editing of specific canvas sections.
    What: Calls canvases.sections.lookup and returns section metadata.
    Test: Mock slack_post, verify canvases.sections.lookup called, check sections key.

    Args:
        token: Slack bot token (requires canvases:read).
        canvas_id: Canvas ID.

    Returns:
        Dict with 'sections' list containing headings and metadata.

    Raises:
        SlackAPIError: On API errors.
    """
    return await slack_post(token, "canvases.sections.lookup", {"canvas_id": canvas_id})
