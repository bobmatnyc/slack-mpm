"""Tests for Slack MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


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
        "get_channel_info",
        "archive_channel",
        "invite_to_channel",
        "kick_from_channel",
        "join_channel",
        "set_channel_topic",
        "send_ephemeral",
        "update_message",
        "delete_message",
        "get_permalink",
        "list_history",
        "add_reaction",
        "remove_reaction",
        "pin_message",
        "unpin_message",
        "reply_in_thread",
        "get_thread_replies",
    }

    tool_map = {t.name: t for t in SLACK_TOOLS}

    for name in tools_with_channel:
        tool = tool_map[name]
        schema = tool.inputSchema
        required = schema.get("required", [])
        assert "channel" in required, f"Tool '{name}' should have 'channel' in required"


# ---------------------------------------------------------------------------
# use_user_token schema tests
# ---------------------------------------------------------------------------


def test_use_user_token_present_in_send_message_schema() -> None:
    """send_message tool schema includes optional use_user_token property."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_map = {t.name: t for t in SLACK_TOOLS}
    schema = tool_map["send_message"].inputSchema
    assert "use_user_token" in schema["properties"]
    assert "use_user_token" not in schema.get("required", [])
    assert schema["properties"]["use_user_token"]["type"] == "boolean"


def test_use_user_token_present_in_update_message_schema() -> None:
    """update_message tool schema includes optional use_user_token property."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_map = {t.name: t for t in SLACK_TOOLS}
    schema = tool_map["update_message"].inputSchema
    assert "use_user_token" in schema["properties"]
    assert "use_user_token" not in schema.get("required", [])


def test_use_user_token_present_in_reply_in_thread_schema() -> None:
    """reply_in_thread tool schema includes optional use_user_token property."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_map = {t.name: t for t in SLACK_TOOLS}
    schema = tool_map["reply_in_thread"].inputSchema
    assert "use_user_token" in schema["properties"]
    assert "use_user_token" not in schema.get("required", [])


def test_use_user_token_present_in_add_reaction_schema() -> None:
    """add_reaction tool schema includes optional use_user_token property."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_map = {t.name: t for t in SLACK_TOOLS}
    schema = tool_map["add_reaction"].inputSchema
    assert "use_user_token" in schema["properties"]
    assert "use_user_token" not in schema.get("required", [])


def test_use_user_token_present_in_remove_reaction_schema() -> None:
    """remove_reaction tool schema includes optional use_user_token property."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_map = {t.name: t for t in SLACK_TOOLS}
    schema = tool_map["remove_reaction"].inputSchema
    assert "use_user_token" in schema["properties"]
    assert "use_user_token" not in schema.get("required", [])


# ---------------------------------------------------------------------------
# _resolve_write_token unit tests
# ---------------------------------------------------------------------------


def test_resolve_write_token_returns_bot_by_default() -> None:
    """_resolve_write_token returns the bot token when use_user_token is absent."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-bot"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        result = server._resolve_write_token({}, "xoxb-bot")
        assert result == "xoxb-bot"


def test_resolve_write_token_returns_bot_when_false() -> None:
    """_resolve_write_token returns the bot token when use_user_token=False."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-bot"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        result = server._resolve_write_token({"use_user_token": False}, "xoxb-bot")
        assert result == "xoxb-bot"


def test_resolve_write_token_returns_user_token_when_requested() -> None:
    """_resolve_write_token returns the user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        result = server._resolve_write_token({"use_user_token": True}, "xoxb-bot")
        assert result == "xoxp-user"


def test_resolve_write_token_raises_when_user_token_missing() -> None:
    """_resolve_write_token raises SlackAPIError when use_user_token=True but no user token."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-bot"}, clear=True):
        from slack_mpm.api._client import SlackAPIError
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        with pytest.raises(SlackAPIError) as exc_info:
            server._resolve_write_token({"use_user_token": True}, "xoxb-bot")

        assert exc_info.value.error == "user_token_not_configured"
        assert "SLACK_USER_TOKEN" in exc_info.value.response["message"]


# ---------------------------------------------------------------------------
# Dispatch tests: use_user_token routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_send_message_uses_bot_token_by_default() -> None:
    """send_message dispatches with bot token when use_user_token not set."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "ts": "123.456", "channel": "C123"}

        with patch(
            "slack_mpm.api.messages.send_message", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool("send_message", {"channel": "C123", "text": "hi"})
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxb-bot"


@pytest.mark.asyncio
async def test_dispatch_send_message_uses_user_token_when_requested() -> None:
    """send_message dispatches with user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "ts": "123.456", "channel": "C123"}

        with patch(
            "slack_mpm.api.messages.send_message", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "send_message",
                {"channel": "C123", "text": "hi", "use_user_token": True},
            )
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxp-user"


@pytest.mark.asyncio
async def test_dispatch_send_message_error_when_user_token_missing() -> None:
    """send_message raises SlackAPIError when use_user_token=True but no user token."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-bot"}, clear=True):
        from slack_mpm.api._client import SlackAPIError
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        with pytest.raises(SlackAPIError) as exc_info:
            await server._dispatch_tool(
                "send_message",
                {"channel": "C123", "text": "hi", "use_user_token": True},
            )
        assert exc_info.value.error == "user_token_not_configured"


@pytest.mark.asyncio
async def test_dispatch_reply_in_thread_uses_user_token_when_requested() -> None:
    """reply_in_thread dispatches with user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "ts": "123.456", "channel": "C123"}

        with patch(
            "slack_mpm.api.messages.reply_in_thread", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "reply_in_thread",
                {
                    "channel": "C123",
                    "thread_ts": "111.222",
                    "text": "reply",
                    "use_user_token": True,
                },
            )
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxp-user"


@pytest.mark.asyncio
async def test_dispatch_update_message_uses_user_token_when_requested() -> None:
    """update_message dispatches with user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "ts": "123.456", "channel": "C123", "text": "updated"}

        with patch(
            "slack_mpm.api.messages.update_message", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "update_message",
                {
                    "channel": "C123",
                    "ts": "111.222",
                    "text": "updated",
                    "use_user_token": True,
                },
            )
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxp-user"


@pytest.mark.asyncio
async def test_dispatch_add_reaction_uses_user_token_when_requested() -> None:
    """add_reaction dispatches with user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.messages.add_reaction", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "add_reaction",
                {
                    "channel": "C123",
                    "timestamp": "111.222",
                    "name": "thumbsup",
                    "use_user_token": True,
                },
            )
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxp-user"


@pytest.mark.asyncio
async def test_dispatch_remove_reaction_uses_user_token_when_requested() -> None:
    """remove_reaction dispatches with user token when use_user_token=True."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.messages.remove_reaction", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "remove_reaction",
                {
                    "channel": "C123",
                    "timestamp": "111.222",
                    "name": "thumbsup",
                    "use_user_token": True,
                },
            )
            called_token = mock_fn.call_args[0][0]
            assert called_token == "xoxp-user"
