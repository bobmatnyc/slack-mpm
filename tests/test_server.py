"""Tests for Slack MCP server."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_server_lists_tools() -> None:
    """Server returns all expected tools."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_names = [t.name for t in SLACK_TOOLS]

    # Channel tools
    assert "list_channels" in tool_names
    assert "get_channel_info" in tool_names
    assert "create_channel" in tool_names
    assert "archive_channel" in tool_names
    assert "invite_to_channel" in tool_names
    assert "kick_from_channel" in tool_names
    assert "join_channel" in tool_names
    assert "set_channel_topic" in tool_names

    # Message tools
    assert "send_message" in tool_names
    assert "send_ephemeral" in tool_names
    assert "update_message" in tool_names
    assert "delete_message" in tool_names
    assert "get_permalink" in tool_names
    assert "search_messages" in tool_names
    assert "list_history" in tool_names
    assert "add_reaction" in tool_names
    assert "remove_reaction" in tool_names
    assert "pin_message" in tool_names
    assert "unpin_message" in tool_names
    assert "reply_in_thread" in tool_names
    assert "get_thread_replies" in tool_names

    # User tools
    assert "list_users" in tool_names
    assert "get_user_info" in tool_names
    assert "get_user_by_email" in tool_names
    assert "open_dm" in tool_names
    assert "list_user_channels" in tool_names

    # File tools
    assert "upload_file" in tool_names
    assert "list_files" in tool_names
    assert "get_file_info" in tool_names
    assert "delete_file" in tool_names
    assert "share_file" in tool_names

    # Workspace tools
    assert "get_workspace_info" in tool_names
    assert "list_emojis" in tool_names
    assert "get_bot_info" in tool_names
    assert "auth_test" in tool_names

    # Reminder tools
    assert "add_reminder" in tool_names
    assert "list_reminders" in tool_names
    assert "complete_reminder" in tool_names
    assert "delete_reminder" in tool_names

    # Bookmark tools
    assert "list_bookmarks" in tool_names
    assert "add_bookmark" in tool_names
    assert "remove_bookmark" in tool_names

    # Scheduled message tools
    assert "schedule_message" in tool_names
    assert "list_scheduled_messages" in tool_names
    assert "delete_scheduled_message" in tool_names


@pytest.mark.asyncio
async def test_server_tool_count() -> None:
    """Server exposes at least 40 tools."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    assert len(SLACK_TOOLS) >= 40


@pytest.mark.asyncio
async def test_dispatch_unknown_tool() -> None:
    """Dispatching unknown tool raises ValueError."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        with pytest.raises(ValueError, match="Unknown tool"):
            await server._dispatch_tool("nonexistent_tool", {})


@pytest.mark.asyncio
async def test_dispatch_list_channels() -> None:
    """list_channels tool dispatches to channels.list_channels."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        mock_result = {"ok": True, "channels": [{"id": "C123", "name": "general"}]}
        with patch("slack_mpm.api.channels.list_channels", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool("list_channels", {})
            assert result["ok"] is True
            assert len(result["channels"]) == 1


@pytest.mark.asyncio
async def test_dispatch_send_message() -> None:
    """send_message tool dispatches to messages.send_message."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        mock_result = {"ok": True, "ts": "1234567890.123456", "channel": "C123"}
        with patch("slack_mpm.api.messages.send_message", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "send_message",
                {"channel": "C123", "text": "Hello!"},
            )
            assert result["ok"] is True
            assert result["ts"] == "1234567890.123456"


@pytest.mark.asyncio
async def test_dispatch_get_channel_info() -> None:
    """get_channel_info tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        mock_result = {"ok": True, "channel": {"id": "C123", "name": "general"}}
        with patch(
            "slack_mpm.api.channels.get_channel_info", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool("get_channel_info", {"channel": "C123"})
            assert result["ok"] is True
            assert result["channel"]["id"] == "C123"


@pytest.mark.asyncio
async def test_dispatch_list_users() -> None:
    """list_users tool dispatches to users.list_users."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        mock_result = {"ok": True, "members": [{"id": "U123", "name": "alice"}]}
        with patch("slack_mpm.api.users.list_users", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool("list_users", {})
            assert result["ok"] is True
            assert len(result["members"]) == 1


@pytest.mark.asyncio
async def test_tool_schemas_have_required_fields() -> None:
    """All tools with required inputs declare them in inputSchema."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tools_with_channel = {
        "get_channel_info", "archive_channel", "invite_to_channel",
        "kick_from_channel", "join_channel", "set_channel_topic",
        "send_ephemeral", "update_message", "delete_message", "get_permalink",
        "list_history", "add_reaction", "remove_reaction", "pin_message",
        "unpin_message", "reply_in_thread", "get_thread_replies",
    }

    tool_map = {t.name: t for t in SLACK_TOOLS}

    for name in tools_with_channel:
        tool = tool_map[name]
        schema = tool.inputSchema
        required = schema.get("required", [])
        assert "channel" in required, f"Tool '{name}' should have 'channel' in required"
