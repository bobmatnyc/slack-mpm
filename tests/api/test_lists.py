"""Tests for Slack Lists API functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from slack_mpm.api._client import SlackAPIError


@pytest.mark.asyncio
async def test_create_list_success() -> None:
    """create_list calls slackLists.create and returns list_id."""
    from slack_mpm.api.lists import create_list

    mock_response = {"ok": True, "list_id": "LS123", "name": "My List", "channel_id": "C123"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await create_list("xoxb-token", "C123", "My List")

    assert result["list_id"] == "LS123"
    call_args = mock_post.call_args
    assert call_args[0][1] == "slackLists.create"
    payload = call_args[0][2]
    assert payload["channel"] == "C123"
    assert payload["name"] == "My List"
    assert "items" not in payload


@pytest.mark.asyncio
async def test_create_list_with_initial_items() -> None:
    """create_list passes initial items when provided."""
    from slack_mpm.api.lists import create_list

    mock_response = {"ok": True, "list_id": "LS123"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await create_list("xoxb-token", "C123", "Tasks", items=[{"value": "Task 1"}])

    payload = mock_post.call_args[0][2]
    assert payload["items"] == [{"value": "Task 1"}]


@pytest.mark.asyncio
async def test_create_list_not_paid_plan() -> None:
    """create_list raises SlackAPIError when not on paid plan."""
    from slack_mpm.api.lists import create_list

    with patch(
        "slack_mpm.api.lists.slack_post",
        new=AsyncMock(side_effect=SlackAPIError("slackLists.create", "not_paid_plan", {})),
    ):
        with pytest.raises(SlackAPIError) as exc_info:
            await create_list("xoxb-token", "C123", "Tasks")

    assert exc_info.value.error == "not_paid_plan"


@pytest.mark.asyncio
async def test_update_list() -> None:
    """update_list calls slackLists.update with list_id."""
    from slack_mpm.api.lists import update_list

    mock_response = {"ok": True, "list_id": "LS123"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await update_list("xoxb-token", "LS123", name="Renamed List")

    assert result["ok"] is True
    payload = mock_post.call_args[0][2]
    assert payload["list_id"] == "LS123"
    assert payload["name"] == "Renamed List"
    assert "description" not in payload


@pytest.mark.asyncio
async def test_update_list_with_description() -> None:
    """update_list passes description when provided."""
    from slack_mpm.api.lists import update_list

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await update_list("xoxb-token", "LS123", description="A test list")

    payload = mock_post.call_args[0][2]
    assert payload["description"] == "A test list"


@pytest.mark.asyncio
async def test_create_list_item() -> None:
    """create_list_item calls slackLists.items.create and returns item_id."""
    from slack_mpm.api.lists import create_list_item

    mock_response = {"ok": True, "item_id": "I001", "value": "Task 1"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await create_list_item("xoxb-token", "LS123", "Task 1", status="incomplete")

    assert result["item_id"] == "I001"
    payload = mock_post.call_args[0][2]
    assert payload["list_id"] == "LS123"
    assert payload["value"] == "Task 1"
    assert payload["status"] == "incomplete"


@pytest.mark.asyncio
async def test_create_list_item_no_status() -> None:
    """create_list_item works without status."""
    from slack_mpm.api.lists import create_list_item

    mock_response = {"ok": True, "item_id": "I002"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        await create_list_item("xoxb-token", "LS123", "Plain item")

    payload = mock_post.call_args[0][2]
    assert "status" not in payload


@pytest.mark.asyncio
async def test_update_list_item() -> None:
    """update_list_item calls slackLists.items.update with item_id."""
    from slack_mpm.api.lists import update_list_item

    mock_response = {"ok": True, "item_id": "I001"}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await update_list_item("xoxb-token", "LS123", "I001", status="complete")

    assert result["ok"] is True
    payload = mock_post.call_args[0][2]
    assert payload["item_id"] == "I001"
    assert payload["status"] == "complete"


@pytest.mark.asyncio
async def test_delete_list_item() -> None:
    """delete_list_item calls slackLists.items.delete and returns ok=true."""
    from slack_mpm.api.lists import delete_list_item

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await delete_list_item("xoxb-token", "LS123", "I001")

    assert result["ok"] is True
    call_args = mock_post.call_args
    assert call_args[0][1] == "slackLists.items.delete"
    assert call_args[0][2] == {"list_id": "LS123", "item_id": "I001"}


@pytest.mark.asyncio
async def test_delete_list_items_batch() -> None:
    """delete_list_items calls slackLists.items.deleteMultiple with item_ids list."""
    from slack_mpm.api.lists import delete_list_items

    mock_response = {"ok": True, "deleted": 3}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await delete_list_items("xoxb-token", "LS123", ["I001", "I002", "I003"])

    assert result["ok"] is True
    call_args = mock_post.call_args
    assert call_args[0][1] == "slackLists.items.deleteMultiple"
    payload = call_args[0][2]
    assert payload["item_ids"] == ["I001", "I002", "I003"]


@pytest.mark.asyncio
async def test_list_list_items_paginated() -> None:
    """list_list_items collects all items across multiple pages."""
    from slack_mpm.api.lists import list_list_items

    page1_items = [{"item_id": "I001", "value": "Item 1"}]
    page2_items = [{"item_id": "I002", "value": "Item 2"}]

    # Mock paginate to yield two pages
    async def mock_paginate(api_fn: object, items_key: str, **kwargs: object):  # type: ignore
        yield page1_items
        yield page2_items

    with patch("slack_mpm.api.lists.paginate", new=mock_paginate):
        result = await list_list_items("xoxb-token", "LS123")

    assert result["ok"] is True
    assert len(result["items"]) == 2
    assert result["items"][0]["item_id"] == "I001"
    assert result["items"][1]["item_id"] == "I002"


@pytest.mark.asyncio
async def test_get_list_item() -> None:
    """get_list_item calls slackLists.items.info with list_id and item_id."""
    from slack_mpm.api.lists import get_list_item

    mock_response = {
        "ok": True,
        "item": {"item_id": "I001", "value": "Task 1", "status": "incomplete"},
    }
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await get_list_item("xoxb-token", "LS123", "I001")

    assert result["item"]["value"] == "Task 1"
    call_args = mock_post.call_args
    assert call_args[0][1] == "slackLists.items.info"
    assert call_args[0][2] == {"list_id": "LS123", "item_id": "I001"}


@pytest.mark.asyncio
async def test_set_list_access() -> None:
    """set_list_access calls slackLists.access.set with correct params."""
    from slack_mpm.api.lists import set_list_access

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await set_list_access("xoxb-token", "LS123", "write", user_ids=["U1"])

    assert result["ok"] is True
    payload = mock_post.call_args[0][2]
    assert payload["list_id"] == "LS123"
    assert payload["access_level"] == "write"
    assert payload["user_ids"] == ["U1"]


@pytest.mark.asyncio
async def test_delete_list_access() -> None:
    """delete_list_access calls slackLists.access.delete."""
    from slack_mpm.api.lists import delete_list_access

    mock_response = {"ok": True}
    with patch(
        "slack_mpm.api.lists.slack_post", new=AsyncMock(return_value=mock_response)
    ) as mock_post:
        result = await delete_list_access("xoxb-token", "LS123", user_id="U1")

    assert result["ok"] is True
    call_args = mock_post.call_args
    assert call_args[0][1] == "slackLists.access.delete"
    payload = call_args[0][2]
    assert payload["list_id"] == "LS123"
    assert payload["user_id"] == "U1"
