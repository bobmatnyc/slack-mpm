"""Slack MCP Server - thin MCP adapter over the Slack API client library."""

from __future__ import annotations

import json
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from slack_mpm.api import (
    bookmarks,
    canvases,
    channels,
    files,
    lists,
    messages,
    reminders,
    scheduled,
    users,
    workspace,
)
from slack_mpm.api._client import SlackAPIError
from slack_mpm.auth.token_manager import TokenManager
from slack_mpm.content import ContentConversionError, markdown_to_canvas, markdown_to_list


def _pick(args: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    """Return a subset of dict containing only specified keys that are present."""
    return {k: v for k, v in args.items() if k in keys}


async def _wrap_conversion_result(coro: Any) -> dict[str, Any]:
    """Await a coroutine returning a string and wrap it in a dict.

    Why: _dispatch_tool must return dict[str, Any]; conversion tools return str/list.
    What: Awaits the coroutine and wraps the result under 'result' key.
    Test: Pass an async function returning "hello", assert {"result": "hello"} returned.
    """
    value = await coro
    return {"ok": True, "result": value}


async def _wrap_list_result(coro: Any) -> dict[str, Any]:
    """Await a coroutine returning a list and wrap it in a dict.

    Why: _dispatch_tool must return dict[str, Any]; list conversion returns a list.
    What: Awaits the coroutine and wraps the result under 'items' key.
    Test: Pass an async function returning [{"value": "x"}], assert items key present.
    """
    value = await coro
    return {"ok": True, "items": value}


SLACK_TOOLS: list[types.Tool] = [
    # -------------------------------------------------------------------------
    # Channel tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="list_channels",
        description="List all channels in the Slack workspace (public and private).",
        inputSchema={
            "type": "object",
            "properties": {
                "types": {
                    "type": "string",
                    "description": "Comma-separated channel types: public_channel, private_channel, mpim, im",  # noqa: E501
                    "default": "public_channel,private_channel",
                },
                "exclude_archived": {
                    "type": "boolean",
                    "description": "Exclude archived channels from results",
                    "default": True,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of channels to return",
                    "default": 100,
                },
                "name_filter": {
                    "type": "string",
                    "description": "Optional substring to filter channel names (case-insensitive)",
                },
            },
        },
    ),
    types.Tool(
        name="get_channel_info",
        description="Get detailed information about a specific Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID (e.g., C1234567890)",
                },
            },
            "required": ["channel"],
        },
    ),
    types.Tool(
        name="create_channel",
        description="Create a new Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Channel name (lowercase, no spaces, use hyphens)",
                },
                "is_private": {
                    "type": "boolean",
                    "description": "Create as private channel",
                    "default": False,
                },
            },
            "required": ["name"],
        },
    ),
    types.Tool(
        name="archive_channel",
        description="Archive a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to archive",
                },
            },
            "required": ["channel"],
        },
    ),
    types.Tool(
        name="invite_to_channel",
        description="Invite one or more users to a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to invite users to",
                },
                "users": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs to invite",
                },
            },
            "required": ["channel", "users"],
        },
    ),
    types.Tool(
        name="kick_from_channel",
        description="Remove a user from a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID",
                },
                "user": {
                    "type": "string",
                    "description": "User ID to remove",
                },
            },
            "required": ["channel", "user"],
        },
    ),
    types.Tool(
        name="join_channel",
        description="Join a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to join",
                },
            },
            "required": ["channel"],
        },
    ),
    types.Tool(
        name="set_channel_topic",
        description="Set the topic for a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID",
                },
                "topic": {
                    "type": "string",
                    "description": "New topic text",
                },
            },
            "required": ["channel", "topic"],
        },
    ),
    # -------------------------------------------------------------------------
    # Message tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="send_message",
        description="Send a message to a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID or name to send to",
                },
                "text": {
                    "type": "string",
                    "description": "Message text",
                },
                "blocks": {
                    "type": "array",
                    "description": "Block Kit blocks array for rich formatting",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Thread timestamp to reply in a thread",
                },
                "unfurl_links": {
                    "type": "boolean",
                    "description": "Whether to unfurl links",
                    "default": True,
                },
                "use_user_token": {
                    "type": "boolean",
                    "description": "Send as the authenticated user (requires xoxp- user token) rather than the bot",  # noqa: E501
                    "default": False,
                },
            },
            "required": ["channel", "text"],
        },
    ),
    types.Tool(
        name="send_ephemeral",
        description="Send an ephemeral message visible only to a specific user.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID where the ephemeral message appears",
                },
                "user": {
                    "type": "string",
                    "description": "User ID who will see the message",
                },
                "text": {
                    "type": "string",
                    "description": "Message text",
                },
            },
            "required": ["channel", "user", "text"],
        },
    ),
    types.Tool(
        name="update_message",
        description="Update/edit an existing Slack message.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "ts": {
                    "type": "string",
                    "description": "Timestamp of the message to update",
                },
                "text": {
                    "type": "string",
                    "description": "New text for the message",
                },
                "use_user_token": {
                    "type": "boolean",
                    "description": "Send as the authenticated user (requires xoxp- user token) rather than the bot",  # noqa: E501
                    "default": False,
                },
            },
            "required": ["channel", "ts", "text"],
        },
    ),
    types.Tool(
        name="delete_message",
        description="Delete a Slack message.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "ts": {
                    "type": "string",
                    "description": "Timestamp of the message to delete",
                },
            },
            "required": ["channel", "ts"],
        },
    ),
    types.Tool(
        name="get_permalink",
        description="Get a permanent link to a Slack message.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "message_ts": {
                    "type": "string",
                    "description": "Timestamp of the message",
                },
            },
            "required": ["channel", "message_ts"],
        },
    ),
    types.Tool(
        name="search_messages",
        description=(
            "Search for messages across the workspace. "
            "Requires a user token (xoxp-) with search:read scope — "
            "bot tokens (xoxb-) are not supported by Slack's search API."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 20,
                },
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="list_history",
        description="Fetch message history from a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to fetch history from",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return",
                    "default": 100,
                },
                "oldest": {
                    "type": "string",
                    "description": "Only messages after this Unix timestamp",
                },
                "latest": {
                    "type": "string",
                    "description": "Only messages before this Unix timestamp",
                },
            },
            "required": ["channel"],
        },
    ),
    types.Tool(
        name="add_reaction",
        description="Add an emoji reaction to a Slack message.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Message timestamp",
                },
                "name": {
                    "type": "string",
                    "description": "Emoji name without colons (e.g., 'thumbsup')",
                },
                "use_user_token": {
                    "type": "boolean",
                    "description": "React as the authenticated user (requires xoxp- user token) rather than the bot",  # noqa: E501
                    "default": False,
                },
            },
            "required": ["channel", "timestamp", "name"],
        },
    ),
    types.Tool(
        name="remove_reaction",
        description="Remove an emoji reaction from a Slack message.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "timestamp": {
                    "type": "string",
                    "description": "Message timestamp",
                },
                "name": {
                    "type": "string",
                    "description": "Emoji name without colons (e.g., 'thumbsup')",
                },
                "use_user_token": {
                    "type": "boolean",
                    "description": "Remove reaction as the authenticated user (requires xoxp- user token) rather than the bot",  # noqa: E501
                    "default": False,
                },
            },
            "required": ["channel", "timestamp", "name"],
        },
    ),
    types.Tool(
        name="pin_message",
        description="Pin a message in a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "ts": {
                    "type": "string",
                    "description": "Message timestamp to pin (e.g. '1234567890.123456')",
                },
            },
            "required": ["channel", "ts"],
        },
    ),
    types.Tool(
        name="unpin_message",
        description="Unpin a message from a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the message",
                },
                "ts": {
                    "type": "string",
                    "description": "Message timestamp to unpin (e.g. '1234567890.123456')",
                },
            },
            "required": ["channel", "ts"],
        },
    ),
    types.Tool(
        name="reply_in_thread",
        description="Reply to a message in a Slack thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the thread",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Timestamp of the parent message",
                },
                "text": {
                    "type": "string",
                    "description": "Reply text",
                },
                "use_user_token": {
                    "type": "boolean",
                    "description": "Send as the authenticated user (requires xoxp- user token) rather than the bot",  # noqa: E501
                    "default": False,
                },
            },
            "required": ["channel", "thread_ts", "text"],
        },
    ),
    types.Tool(
        name="get_thread_replies",
        description="Fetch all replies in a Slack thread.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID containing the thread",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Timestamp of the parent message",
                },
            },
            "required": ["channel", "thread_ts"],
        },
    ),
    # -------------------------------------------------------------------------
    # User tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="list_users",
        description="List all users in the Slack workspace.",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of users to return",
                    "default": 200,
                },
            },
        },
    ),
    types.Tool(
        name="get_user_info",
        description="Get detailed information about a Slack user.",
        inputSchema={
            "type": "object",
            "properties": {
                "user": {
                    "type": "string",
                    "description": "User ID (e.g., U1234567890)",
                },
            },
            "required": ["user"],
        },
    ),
    types.Tool(
        name="get_user_by_email",
        description="Look up a Slack user by their email address.",
        inputSchema={
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Email address to look up",
                },
            },
            "required": ["email"],
        },
    ),
    types.Tool(
        name="open_dm",
        description="Open a direct message channel with one or more Slack users.",
        inputSchema={
            "type": "object",
            "properties": {
                "users": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs to open a DM with",
                },
            },
            "required": ["users"],
        },
    ),
    types.Tool(
        name="list_user_channels",
        description="List all channels a specific Slack user is a member of.",
        inputSchema={
            "type": "object",
            "properties": {
                "user": {
                    "type": "string",
                    "description": "User ID to list channels for",
                },
            },
            "required": ["user"],
        },
    ),
    # -------------------------------------------------------------------------
    # File tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="upload_file",
        description=(
            "Upload a file to one or more Slack channels. "
            "Provide either 'content' (UTF-8 text only) or 'file_path' (disk path for binary or text files), not both."  # noqa: E501
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of channel IDs to share the file in (max 100)",
                },
                "content": {
                    "type": "string",
                    "description": "File content as text (mutually exclusive with file_path)",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to file on disk (mutually exclusive with content)",
                },
                "filename": {
                    "type": "string",
                    "description": "Name for the uploaded file",
                },
                "title": {
                    "type": "string",
                    "description": "Optional display title for the file",
                },
                "thread_ts": {
                    "type": "string",
                    "description": "Optional thread timestamp to attach upload to a thread",
                },
            },
            "required": ["channels", "filename"],
        },
    ),
    types.Tool(
        name="list_files",
        description="List files in the Slack workspace or a specific channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Optional channel ID to filter files by",
                },
                "count": {
                    "type": "integer",
                    "description": "Maximum number of files to return",
                    "default": 100,
                },
            },
        },
    ),
    types.Tool(
        name="get_file_info",
        description="Get detailed information about a Slack file.",
        inputSchema={
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "File ID (e.g., F1234567890)",
                },
            },
            "required": ["file"],
        },
    ),
    types.Tool(
        name="delete_file",
        description="Delete a file from Slack.",
        inputSchema={
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "File ID to delete",
                },
            },
            "required": ["file"],
        },
    ),
    types.Tool(
        name="share_file",
        description="Share an existing Slack file to additional channels.",
        inputSchema={
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "File ID to share",
                },
                "channels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of channel IDs to share the file to",
                },
            },
            "required": ["file", "channels"],
        },
    ),
    # -------------------------------------------------------------------------
    # Workspace tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="get_workspace_info",
        description="Get information about the current Slack workspace.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="list_emojis",
        description="List all custom emoji in the Slack workspace.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="get_bot_info",
        description="Get information about the bot associated with the current token.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="auth_test",
        description="Validate the Slack token and get workspace/user info.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    # -------------------------------------------------------------------------
    # Reminder tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="add_reminder",
        description="Create a reminder for the authenticated user.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Reminder message text",
                },
                "time": {
                    "type": "string",
                    "description": "When to remind — Unix timestamp or natural language (e.g., 'in 30 minutes', 'tomorrow at 9am')",  # noqa: E501
                },
            },
            "required": ["text", "time"],
        },
    ),
    types.Tool(
        name="list_reminders",
        description="List all reminders for the authenticated user.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    types.Tool(
        name="complete_reminder",
        description="Mark a reminder as complete.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder": {
                    "type": "string",
                    "description": "Reminder ID to complete",
                },
            },
            "required": ["reminder"],
        },
    ),
    types.Tool(
        name="delete_reminder",
        description="Delete a reminder.",
        inputSchema={
            "type": "object",
            "properties": {
                "reminder": {
                    "type": "string",
                    "description": "Reminder ID to delete",
                },
            },
            "required": ["reminder"],
        },
    ),
    # -------------------------------------------------------------------------
    # Bookmark tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="list_bookmarks",
        description="List all bookmarks in a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Channel ID to list bookmarks for",
                },
            },
            "required": ["channel_id"],
        },
    ),
    types.Tool(
        name="add_bookmark",
        description="Add a bookmark to a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Channel ID to add the bookmark to",
                },
                "title": {
                    "type": "string",
                    "description": "Display title for the bookmark",
                },
                "link": {
                    "type": "string",
                    "description": "URL for the bookmark",
                },
                "emoji": {
                    "type": "string",
                    "description": "Optional emoji name without colons (e.g., 'bookmark')",
                },
            },
            "required": ["channel_id", "title", "link"],
        },
    ),
    types.Tool(
        name="remove_bookmark",
        description="Remove a bookmark from a Slack channel.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Channel ID containing the bookmark",
                },
                "bookmark_id": {
                    "type": "string",
                    "description": "Bookmark ID to remove",
                },
            },
            "required": ["channel_id", "bookmark_id"],
        },
    ),
    # -------------------------------------------------------------------------
    # Scheduled message tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="schedule_message",
        description="Schedule a message to be sent at a future time.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to send the message to",
                },
                "text": {
                    "type": "string",
                    "description": "Message text",
                },
                "post_at": {
                    "type": "integer",
                    "description": "Unix timestamp (seconds since epoch) when to send the message",
                },
            },
            "required": ["channel", "text", "post_at"],
        },
    ),
    types.Tool(
        name="list_scheduled_messages",
        description="List all pending scheduled messages.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Optional channel ID to filter by",
                },
            },
        },
    ),
    types.Tool(
        name="delete_scheduled_message",
        description="Cancel/delete a scheduled message before it is sent.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID the message was scheduled for",
                },
                "scheduled_message_id": {
                    "type": "string",
                    "description": "Scheduled message ID to cancel",
                },
            },
            "required": ["channel", "scheduled_message_id"],
        },
    ),
    # -------------------------------------------------------------------------
    # Canvas tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="create_canvas",
        description="Create a workspace-level canvas with markdown content. Requires canvases:write scope.",  # noqa: E501
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Canvas title",
                },
                "document_content": {
                    "type": "string",
                    "description": "Markdown content for the canvas",
                },
            },
            "required": ["title", "document_content"],
        },
    ),
    types.Tool(
        name="create_channel_canvas",
        description="Create a canvas attached to a Slack channel. Requires canvases:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to attach the canvas to",
                },
                "title": {
                    "type": "string",
                    "description": "Canvas title",
                },
                "document_content": {
                    "type": "string",
                    "description": "Markdown content for the canvas",
                },
            },
            "required": ["channel", "title", "document_content"],
        },
    ),
    types.Tool(
        name="edit_canvas",
        description="Edit (replace content of) an existing canvas. Requires canvases:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "canvas_id": {
                    "type": "string",
                    "description": "Canvas ID to edit",
                },
                "document_content": {
                    "type": "string",
                    "description": "New markdown content",
                },
                "operation_id": {
                    "type": "string",
                    "description": "Optional idempotency key for the edit",
                },
            },
            "required": ["canvas_id", "document_content"],
        },
    ),
    types.Tool(
        name="delete_canvas",
        description="Delete a canvas. Requires canvases:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "canvas_id": {
                    "type": "string",
                    "description": "Canvas ID to delete",
                },
            },
            "required": ["canvas_id"],
        },
    ),
    types.Tool(
        name="set_canvas_access",
        description="Set access rules for a canvas (grant read/write/owner to users or groups).",
        inputSchema={
            "type": "object",
            "properties": {
                "canvas_id": {
                    "type": "string",
                    "description": "Canvas ID",
                },
                "access_level": {
                    "type": "string",
                    "description": "Access level: 'read', 'write', or 'owner'",
                },
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs to grant access to",
                },
                "group_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of group IDs to grant access to",
                },
            },
            "required": ["canvas_id", "access_level"],
        },
    ),
    types.Tool(
        name="delete_canvas_access",
        description="Revoke access to a canvas for a user or group.",
        inputSchema={
            "type": "object",
            "properties": {
                "canvas_id": {
                    "type": "string",
                    "description": "Canvas ID",
                },
                "user_id": {
                    "type": "string",
                    "description": "User ID to revoke access for",
                },
                "group_id": {
                    "type": "string",
                    "description": "Group ID to revoke access for",
                },
            },
            "required": ["canvas_id"],
        },
    ),
    types.Tool(
        name="lookup_canvas_sections",
        description="Look up sections/blocks in a canvas. Requires canvases:read scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "canvas_id": {
                    "type": "string",
                    "description": "Canvas ID",
                },
            },
            "required": ["canvas_id"],
        },
    ),
    # -------------------------------------------------------------------------
    # List tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="create_list",
        description=(
            "Create a new Slack List in a channel. "
            "Requires lists:write scope and a paid Slack plan."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID to create the list in",
                },
                "name": {
                    "type": "string",
                    "description": "List name",
                },
                "items": {
                    "type": "array",
                    "description": "Optional initial list items (each is a dict with key-value pairs)",  # noqa: E501
                },
            },
            "required": ["channel", "name"],
        },
    ),
    types.Tool(
        name="update_list",
        description="Update a Slack List's metadata (name, description). Requires lists:write scope.",  # noqa: E501
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID to update",
                },
                "name": {
                    "type": "string",
                    "description": "New list name (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "New list description (optional)",
                },
            },
            "required": ["list_id"],
        },
    ),
    types.Tool(
        name="create_list_item",
        description="Add a new item to a Slack List. Requires lists:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "value": {
                    "type": "string",
                    "description": "Item text/value",
                },
                "status": {
                    "type": "string",
                    "description": "Optional status (e.g., 'incomplete', 'complete')",
                },
            },
            "required": ["list_id", "value"],
        },
    ),
    types.Tool(
        name="update_list_item",
        description="Update an existing Slack List item. Requires lists:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to update",
                },
                "value": {
                    "type": "string",
                    "description": "New item text (optional)",
                },
                "status": {
                    "type": "string",
                    "description": "New status (optional)",
                },
            },
            "required": ["list_id", "item_id"],
        },
    ),
    types.Tool(
        name="delete_list_item",
        description="Delete a single item from a Slack List. Requires lists:write scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID to delete",
                },
            },
            "required": ["list_id", "item_id"],
        },
    ),
    types.Tool(
        name="delete_list_items",
        description="Delete multiple items from a Slack List in one call. Requires lists:write scope.",  # noqa: E501
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of item IDs to delete",
                },
            },
            "required": ["list_id", "item_ids"],
        },
    ),
    types.Tool(
        name="list_list_items",
        description="Fetch all items in a Slack List (paginated). Requires lists:read scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max items per page (default 100)",
                    "default": 100,
                },
            },
            "required": ["list_id"],
        },
    ),
    types.Tool(
        name="get_list_item",
        description="Get details for a single Slack List item. Requires lists:read scope.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID",
                },
            },
            "required": ["list_id", "item_id"],
        },
    ),
    types.Tool(
        name="set_list_access",
        description="Set access rules for a Slack List (grant read/write/owner to users or groups).",  # noqa: E501
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "access_level": {
                    "type": "string",
                    "description": "Access level: 'read', 'write', or 'owner'",
                },
                "user_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user IDs to grant access to",
                },
                "group_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of group IDs to grant access to",
                },
            },
            "required": ["list_id", "access_level"],
        },
    ),
    types.Tool(
        name="delete_list_access",
        description="Revoke access to a Slack List for a user or group.",
        inputSchema={
            "type": "object",
            "properties": {
                "list_id": {
                    "type": "string",
                    "description": "List ID",
                },
                "user_id": {
                    "type": "string",
                    "description": "User ID to revoke access for",
                },
                "group_id": {
                    "type": "string",
                    "description": "Group ID to revoke access for",
                },
            },
            "required": ["list_id"],
        },
    ),
    # -------------------------------------------------------------------------
    # Content conversion tools
    # -------------------------------------------------------------------------
    types.Tool(
        name="markdown_to_canvas",
        description=(
            "Validate and prepare markdown content for canvas creation. "
            "Accepts a markdown string or a file path, returns the validated content "
            "suitable for create_canvas() or create_channel_canvas()."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Markdown string (mutually exclusive with file_path)",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to a .md file to read (mutually exclusive with content)",
                },
            },
        },
    ),
    types.Tool(
        name="markdown_to_list",
        description=(
            "Convert markdown to Slack List items. "
            "Parses checklists (- [ ] / - [x]), bullet lists (- item), and tables. "
            "Returns a list of dicts with 'value' and optional 'status'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Markdown string (mutually exclusive with file_path)",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path to a .md file to read (mutually exclusive with content)",
                },
            },
        },
    ),
]


class SlackMCPServer:
    """Thin MCP adapter that exposes Slack API functions as MCP tools."""

    def __init__(self, token_manager: TokenManager | None = None) -> None:
        """Initialize the Slack MCP server.

        Args:
            token_manager: Optional :class:`~slack_mpm.auth.token_manager.TokenManager`
                instance.  When ``None`` (the default), a fresh ``TokenManager()``
                is constructed automatically, preserving the existing behaviour for
                production use while allowing tests to supply a pre-configured or
                mock instance without env-var patching.
        """
        self.server: Server = Server("slack-mpm")
        self._token_manager = token_manager or TokenManager()
        self._setup_handlers()

    def _get_token(self, prefer_user: bool = False) -> str:
        """Get the best available token.

        Args:
            prefer_user: If True, prefer user token over bot token.

        Returns:
            Token string.

        Raises:
            ValueError: If no token is configured.
        """
        return self._token_manager.get_token(prefer_user=prefer_user)

    def _resolve_write_token(self, arguments: dict[str, Any], bot_token: str) -> str:
        """Resolve the token to use for a write operation.

        When ``use_user_token`` is ``True`` in *arguments*, the user token is
        returned.  If no user token is configured in that case, a
        :class:`~slack_mpm.api._client.SlackAPIError` is raised with a clear
        message so the MCP caller receives actionable feedback.

        When ``use_user_token`` is ``False`` or absent, *bot_token* is
        returned unchanged — preserving the existing default behaviour.

        Args:
            arguments: Tool arguments dict from the MCP client.
            bot_token: The bot token (xoxb-) to use when not overriding.

        Returns:
            The token string to pass to the API call.

        Raises:
            SlackAPIError: If ``use_user_token=True`` but no user token is
                configured.
        """
        if arguments.get("use_user_token"):
            user_token = self._token_manager.user_token
            if not user_token:
                raise SlackAPIError(
                    "token_resolution",
                    "user_token_not_configured",
                    {
                        "message": (
                            "User token (xoxp-) not configured. "
                            "Set SLACK_USER_TOKEN environment variable."
                        )
                    },
                )
            return user_token
        return bot_token

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers on the server."""

        @self.server.list_tools()  # type: ignore
        async def list_tools() -> list[types.Tool]:
            return SLACK_TOOLS

        @self.server.call_tool()  # type: ignore
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
            try:
                result = await self._dispatch_tool(name, arguments)
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            except SlackAPIError as e:
                return [types.TextContent(type="text", text=f"Slack API error: {e.error}")]
            except ContentConversionError as e:
                return [
                    types.TextContent(type="text", text=f"Content conversion error: {e.message}")
                ]
            except ValueError as e:
                return [types.TextContent(type="text", text=str(e))]

    async def _dispatch_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Route tool calls to the appropriate API function.

        Args:
            name: Tool name to invoke.
            arguments: Arguments passed by the MCP client.

        Returns:
            Response dict from the Slack API.

        Raises:
            ValueError: If the tool name is not recognized.
            SlackAPIError: If the Slack API returns an error.
        """
        token = self._get_token()
        user_token = self._token_manager.user_token

        handlers: dict[str, Any] = {
            # Channels
            "list_channels": lambda a: channels.list_channels(
                token, **_pick(a, ["types", "exclude_archived", "limit", "name_filter"])
            ),
            "get_channel_info": lambda a: channels.get_channel_info(token, a["channel"]),
            "create_channel": lambda a: channels.create_channel(
                token, a["name"], **_pick(a, ["is_private"])
            ),
            "archive_channel": lambda a: channels.archive_channel(token, a["channel"]),
            "invite_to_channel": lambda a: channels.invite_to_channel(
                token, a["channel"], a["users"]
            ),
            "kick_from_channel": lambda a: channels.kick_from_channel(
                token, a["channel"], a["user"]
            ),
            "join_channel": lambda a: channels.join_channel(token, a["channel"]),
            "set_channel_topic": lambda a: channels.set_channel_topic(
                token, a["channel"], a["topic"]
            ),
            # Messages
            "send_message": lambda a: messages.send_message(
                self._resolve_write_token(a, token),
                a["channel"],
                a["text"],
                **_pick(a, ["blocks", "thread_ts", "unfurl_links"]),
            ),
            "send_ephemeral": lambda a: messages.send_ephemeral(
                user_token or token, a["channel"], a["user"], a["text"]
            ),
            "update_message": lambda a: messages.update_message(
                self._resolve_write_token(a, token), a["channel"], a["ts"], a["text"]
            ),
            "delete_message": lambda a: messages.delete_message(
                user_token or token, a["channel"], a["ts"]
            ),
            "get_permalink": lambda a: messages.get_permalink(token, a["channel"], a["message_ts"]),
            "search_messages": lambda a: messages.search_messages(
                user_token or token,
                a["query"],
                **_pick(a, ["count"]),
            ),
            "list_history": lambda a: messages.list_history(
                token, a["channel"], **_pick(a, ["limit", "oldest", "latest"])
            ),
            "add_reaction": lambda a: messages.add_reaction(
                self._resolve_write_token(a, token), a["channel"], a["timestamp"], a["name"]
            ),
            "remove_reaction": lambda a: messages.remove_reaction(
                self._resolve_write_token(a, token), a["channel"], a["timestamp"], a["name"]
            ),
            "pin_message": lambda a: messages.pin_message(
                user_token or token, a["channel"], a["ts"]
            ),
            "unpin_message": lambda a: messages.unpin_message(
                user_token or token, a["channel"], a["ts"]
            ),
            "reply_in_thread": lambda a: messages.reply_in_thread(
                self._resolve_write_token(a, token), a["channel"], a["thread_ts"], a["text"]
            ),
            "get_thread_replies": lambda a: messages.get_thread_replies(
                token, a["channel"], a["thread_ts"]
            ),
            # Users
            "list_users": lambda a: users.list_users(token, **_pick(a, ["limit"])),
            "get_user_info": lambda a: users.get_user_info(token, a["user"]),
            "get_user_by_email": lambda a: users.get_user_by_email(token, a["email"]),
            "open_dm": lambda a: users.open_dm(token, a["users"]),
            "list_user_channels": lambda a: users.list_user_channels(token, a["user"]),
            # Files
            "upload_file": lambda a: files.upload_file(
                token,
                a["channels"],
                content=a.get("content"),
                filename=a.get("filename", ""),
                **_pick(a, ["title", "file_path", "thread_ts"]),
            ),
            "list_files": lambda a: files.list_files(token, **_pick(a, ["channel", "count"])),
            "get_file_info": lambda a: files.get_file_info(token, a["file"]),
            "delete_file": lambda a: files.delete_file(token, a["file"]),
            "share_file": lambda a: files.share_file(token, a["file"], a["channels"]),
            # Workspace
            "get_workspace_info": lambda a: workspace.get_workspace_info(token),
            "list_emojis": lambda a: workspace.list_emojis(token),
            "get_bot_info": lambda a: workspace.get_bot_info(token),
            "auth_test": lambda a: workspace.auth_test(token),
            # Reminders
            "add_reminder": lambda a: reminders.add_reminder(
                user_token or token, a["text"], a["time"]
            ),
            "list_reminders": lambda a: reminders.list_reminders(user_token or token),
            "complete_reminder": lambda a: reminders.complete_reminder(
                user_token or token, a["reminder"]
            ),
            "delete_reminder": lambda a: reminders.delete_reminder(
                user_token or token, a["reminder"]
            ),
            # Bookmarks
            "list_bookmarks": lambda a: bookmarks.list_bookmarks(token, a["channel_id"]),
            "add_bookmark": lambda a: bookmarks.add_bookmark(
                token,
                a["channel_id"],
                a["title"],
                a["link"],
                **_pick(a, ["emoji"]),
            ),
            "remove_bookmark": lambda a: bookmarks.remove_bookmark(
                token, a["channel_id"], a["bookmark_id"]
            ),
            # Scheduled messages
            "schedule_message": lambda a: scheduled.schedule_message(
                user_token or token, a["channel"], a["text"], a["post_at"]
            ),
            "list_scheduled_messages": lambda a: scheduled.list_scheduled_messages(
                token, **_pick(a, ["channel"])
            ),
            "delete_scheduled_message": lambda a: scheduled.delete_scheduled_message(
                token, a["channel"], a["scheduled_message_id"]
            ),
            # Canvases
            "create_canvas": lambda a: canvases.create_canvas(
                token, a["title"], a["document_content"]
            ),
            "create_channel_canvas": lambda a: canvases.create_channel_canvas(
                token, a["channel"], a["title"], a["document_content"]
            ),
            "edit_canvas": lambda a: canvases.edit_canvas(
                token,
                a["canvas_id"],
                a["document_content"],
                **_pick(a, ["operation_id"]),
            ),
            "delete_canvas": lambda a: canvases.delete_canvas(token, a["canvas_id"]),
            "set_canvas_access": lambda a: canvases.set_canvas_access(
                token,
                a["canvas_id"],
                a["access_level"],
                **_pick(a, ["user_ids", "group_ids"]),
            ),
            "delete_canvas_access": lambda a: canvases.delete_canvas_access(
                token,
                a["canvas_id"],
                **_pick(a, ["user_id", "group_id"]),
            ),
            "lookup_canvas_sections": lambda a: canvases.lookup_canvas_sections(
                token, a["canvas_id"]
            ),
            # Lists
            "create_list": lambda a: lists.create_list(
                token, a["channel"], a["name"], **_pick(a, ["items"])
            ),
            "update_list": lambda a: lists.update_list(
                token, a["list_id"], **_pick(a, ["name", "description"])
            ),
            "create_list_item": lambda a: lists.create_list_item(
                token, a["list_id"], a["value"], **_pick(a, ["status"])
            ),
            "update_list_item": lambda a: lists.update_list_item(
                token,
                a["list_id"],
                a["item_id"],
                **_pick(a, ["value", "status"]),
            ),
            "delete_list_item": lambda a: lists.delete_list_item(token, a["list_id"], a["item_id"]),
            "delete_list_items": lambda a: lists.delete_list_items(
                token, a["list_id"], a["item_ids"]
            ),
            "list_list_items": lambda a: lists.list_list_items(
                token, a["list_id"], **_pick(a, ["limit"])
            ),
            "get_list_item": lambda a: lists.get_list_item(token, a["list_id"], a["item_id"]),
            "set_list_access": lambda a: lists.set_list_access(
                token,
                a["list_id"],
                a["access_level"],
                **_pick(a, ["user_ids", "group_ids"]),
            ),
            "delete_list_access": lambda a: lists.delete_list_access(
                token,
                a["list_id"],
                **_pick(a, ["user_id", "group_id"]),
            ),
            # Content conversion (return wrapped dict so dispatch stays uniform)
            "markdown_to_canvas": lambda a: _wrap_conversion_result(
                markdown_to_canvas(**_pick(a, ["content", "file_path"]))
            ),
            "markdown_to_list": lambda a: _wrap_list_result(
                markdown_to_list(**_pick(a, ["content", "file_path"]))
            ),
        }

        if name not in handlers:
            raise ValueError(f"Unknown tool: {name}")

        result: dict[str, Any] = await handlers[name](arguments)
        return result

    async def run(self) -> None:
        """Run the MCP server over stdio."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )
