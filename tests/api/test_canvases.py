"""Tests for Slack Canvas API functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from slack_mpm.api._client import SlackAPIError


@pytest.mark.asyncio
async def test_create_canvas_success() -> None:
    """create_canvas calls canvases.create and returns canvas_id."""
    from slack_mpm.api.canvases import create_canvas

    mock_response = {"ok": True, "canvas_id": "F_CANVAS123", "is_empty": False}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await create_canvas("xoxb-token", "My Canvas", "# Hello\nWorld")

    assert result["canvas_id"] == "F_CANVAS123"
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][1] == "canvases.create"
    payload = call_args[0][2]
    assert payload["title"] == "My Canvas"
    assert payload["document_content"]["type"] == "markdown"
    assert "Hello" in payload["document_content"]["markdown"]


@pytest.mark.asyncio
async def test_create_canvas_api_error() -> None:
    """create_canvas raises SlackAPIError on API failure."""
    from slack_mpm.api.canvases import create_canvas

    with patch(
        "slack_mpm.api.canvases.slack_post",
        new=AsyncMock(side_effect=SlackAPIError("canvases.create", "missing_scope", {})),
    ):
        with pytest.raises(SlackAPIError) as exc_info:
            await create_canvas("xoxb-token", "Title", "content")

    assert exc_info.value.error == "missing_scope"


@pytest.mark.asyncio
async def test_create_channel_canvas_success() -> None:
    """create_channel_canvas calls conversations.canvases.create with channel param."""
    from slack_mpm.api.canvases import create_channel_canvas

    mock_response = {"ok": True, "canvas_id": "F_CHAN_CANVAS"}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await create_channel_canvas("xoxb-token", "C123", "Channel Canvas", "# Content")

    assert result["canvas_id"] == "F_CHAN_CANVAS"
    call_args = mock_post.call_args
    assert call_args[0][1] == "conversations.canvases.create"
    payload = call_args[0][2]
    assert payload["channel_id"] == "C123"
    assert payload["title"] == "Channel Canvas"


@pytest.mark.asyncio
async def test_create_channel_canvas_not_found() -> None:
    """create_channel_canvas raises SlackAPIError when channel not found."""
    from slack_mpm.api.canvases import create_channel_canvas

    with patch(
        "slack_mpm.api.canvases.slack_post",
        new=AsyncMock(
            side_effect=SlackAPIError("conversations.canvases.create", "channel_not_found", {})
        ),
    ):
        with pytest.raises(SlackAPIError) as exc_info:
            await create_channel_canvas("xoxb-token", "CBAD", "Canvas", "content")

    assert exc_info.value.error == "channel_not_found"


@pytest.mark.asyncio
async def test_edit_canvas_success() -> None:
    """edit_canvas calls canvases.edit with canvas_id and content."""
    from slack_mpm.api.canvases import edit_canvas

    mock_response = {"ok": True, "canvas_id": "F_CANVAS123"}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await edit_canvas("xoxb-token", "F_CANVAS123", "# Updated")

    assert result["canvas_id"] == "F_CANVAS123"
    call_args = mock_post.call_args
    assert call_args[0][1] == "canvases.edit"
    payload = call_args[0][2]
    assert payload["canvas_id"] == "F_CANVAS123"
    assert payload["changes"][0]["operation"] == "replace"


@pytest.mark.asyncio
async def test_edit_canvas_with_operation_id() -> None:
    """edit_canvas passes operation_id when provided."""
    from slack_mpm.api.canvases import edit_canvas

    mock_response = {"ok": True, "canvas_id": "F_CANVAS123"}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await edit_canvas("xoxb-token", "F_CANVAS123", "# Content", operation_id="op-123")

    payload = mock_post.call_args[0][2]
    assert payload["operation_id"] == "op-123"


@pytest.mark.asyncio
async def test_delete_canvas_success() -> None:
    """delete_canvas calls canvases.delete and returns ok=true."""
    from slack_mpm.api.canvases import delete_canvas

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await delete_canvas("xoxb-token", "F_CANVAS123")

    assert result["ok"] is True
    call_args = mock_post.call_args
    assert call_args[0][1] == "canvases.delete"
    assert call_args[0][2]["canvas_id"] == "F_CANVAS123"


@pytest.mark.asyncio
async def test_set_canvas_access_success() -> None:
    """set_canvas_access calls canvases.access.set with access_level."""
    from slack_mpm.api.canvases import set_canvas_access

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await set_canvas_access("xoxb-token", "F_CANVAS123", "read", user_ids=["U1", "U2"])

    assert result["ok"] is True
    payload = mock_post.call_args[0][2]
    assert payload["canvas_id"] == "F_CANVAS123"
    assert payload["access_level"] == "read"
    assert payload["user_ids"] == ["U1", "U2"]


@pytest.mark.asyncio
async def test_set_canvas_access_with_group_ids() -> None:
    """set_canvas_access supports group_ids."""
    from slack_mpm.api.canvases import set_canvas_access

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await set_canvas_access("xoxb-token", "F_CANVAS123", "write", group_ids=["G1"])

    payload = mock_post.call_args[0][2]
    assert payload["group_ids"] == ["G1"]
    assert "user_ids" not in payload


@pytest.mark.asyncio
async def test_delete_canvas_access_success() -> None:
    """delete_canvas_access calls canvases.access.delete."""
    from slack_mpm.api.canvases import delete_canvas_access

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await delete_canvas_access("xoxb-token", "F_CANVAS123", user_id="U1")

    assert result["ok"] is True
    payload = mock_post.call_args[0][2]
    assert payload["canvas_id"] == "F_CANVAS123"
    assert payload["user_id"] == "U1"


@pytest.mark.asyncio
async def test_lookup_canvas_sections() -> None:
    """lookup_canvas_sections calls canvases.sections.lookup."""
    from slack_mpm.api.canvases import lookup_canvas_sections

    mock_response = {"ok": True, "sections": [{"id": "sec1", "heading": "Introduction"}]}
    with patch(
        "slack_mpm.api.canvases.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await lookup_canvas_sections("xoxb-token", "F_CANVAS123")

    assert "sections" in result
    assert result["sections"][0]["heading"] == "Introduction"
    call_args = mock_post.call_args
    assert call_args[0][1] == "canvases.sections.lookup"
    assert call_args[0][2]["canvas_id"] == "F_CANVAS123"
