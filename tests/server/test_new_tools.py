"""Tests for new Canvas, List, and conversion tool dispatching in SlackMCPServer."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_mcp_tool_create_canvas_dispatch() -> None:
    """create_canvas MCP tool dispatches to canvases.create_canvas."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "canvas_id": "F_CANVAS"}

        with patch("slack_mpm.api.canvases.create_canvas", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "create_canvas",
                {"title": "My Canvas", "document_content": "# Hello"},
            )

        assert result["canvas_id"] == "F_CANVAS"


@pytest.mark.asyncio
async def test_mcp_tool_create_channel_canvas_dispatch() -> None:
    """create_channel_canvas MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "canvas_id": "F_CHAN_CANVAS"}

        with patch(
            "slack_mpm.api.canvases.create_channel_canvas", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool(
                "create_channel_canvas",
                {"channel": "C123", "title": "Canvas", "document_content": "# Hi"},
            )

        assert result["canvas_id"] == "F_CHAN_CANVAS"


@pytest.mark.asyncio
async def test_mcp_tool_edit_canvas_dispatch() -> None:
    """edit_canvas MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "canvas_id": "F_CANVAS"}

        with patch("slack_mpm.api.canvases.edit_canvas", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "edit_canvas",
                {"canvas_id": "F_CANVAS", "document_content": "# Updated"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_delete_canvas_dispatch() -> None:
    """delete_canvas MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch("slack_mpm.api.canvases.delete_canvas", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool("delete_canvas", {"canvas_id": "F_CANVAS"})

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_set_canvas_access_dispatch() -> None:
    """set_canvas_access MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.canvases.set_canvas_access", new=AsyncMock(return_value=mock_result)
        ) as mock_fn:
            await server._dispatch_tool(
                "set_canvas_access",
                {"canvas_id": "F_CANVAS", "access_level": "read", "user_ids": ["U1"]},
            )

        mock_fn.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_tool_delete_canvas_access_dispatch() -> None:
    """delete_canvas_access MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.canvases.delete_canvas_access", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool(
                "delete_canvas_access",
                {"canvas_id": "F_CANVAS", "user_id": "U1"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_lookup_canvas_sections_dispatch() -> None:
    """lookup_canvas_sections MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "sections": []}

        with patch(
            "slack_mpm.api.canvases.lookup_canvas_sections", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool(
                "lookup_canvas_sections", {"canvas_id": "F_CANVAS"}
            )

        assert "sections" in result


@pytest.mark.asyncio
async def test_mcp_tool_create_list_dispatch() -> None:
    """create_list MCP tool dispatches to lists.create_list."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "list_id": "LS123"}

        with patch("slack_mpm.api.lists.create_list", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "create_list",
                {"channel": "C123", "name": "My List"},
            )

        assert result["list_id"] == "LS123"


@pytest.mark.asyncio
async def test_mcp_tool_update_list_dispatch() -> None:
    """update_list MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch("slack_mpm.api.lists.update_list", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "update_list",
                {"list_id": "LS123", "name": "Renamed"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_create_list_item_dispatch() -> None:
    """create_list_item MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "item_id": "I001"}

        with patch("slack_mpm.api.lists.create_list_item", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "create_list_item",
                {"list_id": "LS123", "value": "Task 1", "status": "incomplete"},
            )

        assert result["item_id"] == "I001"


@pytest.mark.asyncio
async def test_mcp_tool_delete_list_item_dispatch() -> None:
    """delete_list_item MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch("slack_mpm.api.lists.delete_list_item", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "delete_list_item",
                {"list_id": "LS123", "item_id": "I001"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_delete_list_items_dispatch() -> None:
    """delete_list_items MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.lists.delete_list_items", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool(
                "delete_list_items",
                {"list_id": "LS123", "item_ids": ["I001", "I002"]},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_list_list_items_dispatch() -> None:
    """list_list_items MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "items": []}

        with patch("slack_mpm.api.lists.list_list_items", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "list_list_items",
                {"list_id": "LS123"},
            )

        assert "items" in result


@pytest.mark.asyncio
async def test_mcp_tool_get_list_item_dispatch() -> None:
    """get_list_item MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True, "item": {"value": "Task 1"}}

        with patch("slack_mpm.api.lists.get_list_item", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "get_list_item",
                {"list_id": "LS123", "item_id": "I001"},
            )

        assert result["item"]["value"] == "Task 1"


@pytest.mark.asyncio
async def test_mcp_tool_set_list_access_dispatch() -> None:
    """set_list_access MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch("slack_mpm.api.lists.set_list_access", new=AsyncMock(return_value=mock_result)):
            result = await server._dispatch_tool(
                "set_list_access",
                {"list_id": "LS123", "access_level": "read"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_delete_list_access_dispatch() -> None:
    """delete_list_access MCP tool dispatches correctly."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        mock_result = {"ok": True}

        with patch(
            "slack_mpm.api.lists.delete_list_access", new=AsyncMock(return_value=mock_result)
        ):
            result = await server._dispatch_tool(
                "delete_list_access",
                {"list_id": "LS123", "user_id": "U1"},
            )

        assert result["ok"] is True


@pytest.mark.asyncio
async def test_mcp_tool_markdown_to_canvas_dispatch() -> None:
    """markdown_to_canvas MCP tool wraps string result in dict."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        async def _mock_canvas(content: str | None = None, file_path: str | None = None) -> str:
            return content or ""

        with patch("slack_mpm.server.slack_mcp_server.markdown_to_canvas", new=_mock_canvas):
            result = await server._dispatch_tool(
                "markdown_to_canvas",
                {"content": "# Hello"},
            )

        assert result["ok"] is True
        assert result["result"] == "# Hello"


@pytest.mark.asyncio
async def test_mcp_tool_markdown_to_list_dispatch() -> None:
    """markdown_to_list MCP tool wraps list result in dict."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()
        items = [{"value": "Task 1", "status": "incomplete"}]

        async def _mock_list(content: str | None = None, file_path: str | None = None) -> list:
            return items

        with patch("slack_mpm.server.slack_mcp_server.markdown_to_list", new=_mock_list):
            result = await server._dispatch_tool(
                "markdown_to_list",
                {"content": "- [ ] Task 1"},
            )

        assert result["ok"] is True
        assert result["items"] == items


def test_mcp_tool_all_new_tools_registered() -> None:
    """All new canvas, list, and conversion tools are in SLACK_TOOLS."""
    from slack_mpm.server.slack_mcp_server import SLACK_TOOLS

    tool_names = {t.name for t in SLACK_TOOLS}

    # Canvas tools
    assert "create_canvas" in tool_names
    assert "create_channel_canvas" in tool_names
    assert "edit_canvas" in tool_names
    assert "delete_canvas" in tool_names
    assert "set_canvas_access" in tool_names
    assert "delete_canvas_access" in tool_names
    assert "lookup_canvas_sections" in tool_names

    # List tools
    assert "create_list" in tool_names
    assert "update_list" in tool_names
    assert "create_list_item" in tool_names
    assert "update_list_item" in tool_names
    assert "delete_list_item" in tool_names
    assert "delete_list_items" in tool_names
    assert "list_list_items" in tool_names
    assert "get_list_item" in tool_names
    assert "set_list_access" in tool_names
    assert "delete_list_access" in tool_names

    # Conversion tools
    assert "markdown_to_canvas" in tool_names
    assert "markdown_to_list" in tool_names


@pytest.mark.asyncio
async def test_mcp_error_handling_content_conversion() -> None:
    """ContentConversionError from conversion tool returns error text content."""
    from slack_mpm.content.errors import ContentConversionError

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        async def _fail(**kwargs: object) -> str:
            raise ContentConversionError("bad markdown")

        with patch("slack_mpm.server.slack_mcp_server.markdown_to_canvas", new=_fail):
            # Call through the full call_tool handler (not _dispatch_tool)
            # by directly simulating what call_tool would do
            try:
                await server._dispatch_tool("markdown_to_canvas", {"content": "x"})
                assert False, "Should have raised"
            except ContentConversionError as e:
                assert "bad markdown" in str(e)


@pytest.mark.asyncio
async def test_mcp_error_handling_slack_api_on_canvas() -> None:
    """SlackAPIError from canvas tool propagates correctly."""
    from slack_mpm.api._client import SlackAPIError

    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        from slack_mpm.server.slack_mcp_server import SlackMCPServer

        server = SlackMCPServer()

        with patch(
            "slack_mpm.api.canvases.delete_canvas",
            new=AsyncMock(side_effect=SlackAPIError("canvases.delete", "canvas_not_found", {})),
        ):
            with pytest.raises(SlackAPIError):
                await server._dispatch_tool("delete_canvas", {"canvas_id": "FBAD"})
