"""Slack Lists API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_post
from slack_mpm.api._pagination import paginate


async def create_list(
    token: str,
    channel: str,
    name: str,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new List in a channel.

    Why: Creates structured lists in Slack channels for task tracking and data organization.
    What: Calls slackLists.create with channel, name, and optional initial items.
    Test: Mock slack_post, verify slackLists.create called, assert list_id in response.

    Args:
        token: Slack bot token (requires lists:write).
        channel: Channel ID to create the list in.
        name: List name.
        items: Optional initial list items (each is a dict with key-value pairs).

    Returns:
        Dict with 'list_id', 'name', 'channel_id'.

    Raises:
        SlackAPIError: On API errors, channel not found, or plan/permission failures.
    """
    payload: dict[str, Any] = {
        "channel": channel,
        "name": name,
    }
    if items is not None:
        payload["items"] = items
    return await slack_post(token, "slackLists.create", payload)


async def update_list(
    token: str,
    list_id: str,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Update a list's metadata.

    Why: Allows renaming or re-describing a list without recreating it.
    What: Calls slackLists.update with list_id and optional name/description.
    Test: Mock slack_post, verify slackLists.update called with correct list_id.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID to update.
        name: New list name (optional).
        description: New list description (optional).

    Returns:
        Dict with updated list metadata.

    Raises:
        SlackAPIError: On API errors or list not found.
    """
    payload: dict[str, Any] = {"list_id": list_id}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    return await slack_post(token, "slackLists.update", payload)


async def create_list_item(
    token: str,
    list_id: str,
    value: str,
    status: str | None = None,
) -> dict[str, Any]:
    """Create a new item in a list.

    Why: Adds entries to a Slack list for task or data tracking.
    What: Calls slackLists.items.create with value and optional status.
    Test: Mock slack_post, verify slackLists.items.create called, assert item_id returned.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        value: Item text/value.
        status: Optional status (e.g., "incomplete", "complete" for checkboxes).

    Returns:
        Dict with 'item_id', 'value', 'status'.

    Raises:
        SlackAPIError: On API errors.
    """
    payload: dict[str, Any] = {
        "list_id": list_id,
        "value": value,
    }
    if status is not None:
        payload["status"] = status
    return await slack_post(token, "slackLists.items.create", payload)


async def update_list_item(
    token: str,
    list_id: str,
    item_id: str,
    value: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Update a list item.

    Why: Modifies existing list items for task status changes and content edits.
    What: Calls slackLists.items.update with item_id and optional value/status.
    Test: Mock slack_post, verify slackLists.items.update called with correct item_id.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        item_id: Item ID to update.
        value: New item text (optional).
        status: New status (optional).

    Returns:
        Dict with updated item metadata.

    Raises:
        SlackAPIError: On API errors or item not found.
    """
    payload: dict[str, Any] = {
        "list_id": list_id,
        "item_id": item_id,
    }
    if value is not None:
        payload["value"] = value
    if status is not None:
        payload["status"] = status
    return await slack_post(token, "slackLists.items.update", payload)


async def delete_list_item(
    token: str,
    list_id: str,
    item_id: str,
) -> dict[str, Any]:
    """Delete a single list item.

    Why: Removes a single entry from a Slack list.
    What: Calls slackLists.items.delete with list_id and item_id.
    Test: Mock slack_post, assert slackLists.items.delete called, verify ok=true.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        item_id: Item ID to delete.

    Returns:
        Dict with ok=true on success.

    Raises:
        SlackAPIError: On API errors.
    """
    return await slack_post(
        token,
        "slackLists.items.delete",
        {"list_id": list_id, "item_id": item_id},
    )


async def delete_list_items(
    token: str,
    list_id: str,
    item_ids: list[str],
) -> dict[str, Any]:
    """Delete multiple list items in a single call.

    Why: Efficiently removes multiple entries without looping individual delete calls.
    What: Calls slackLists.items.deleteMultiple with a list of item_ids.
    Test: Mock slack_post, verify slackLists.items.deleteMultiple called with item_ids list.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        item_ids: List of item IDs to delete.

    Returns:
        Dict with deletion results.

    Raises:
        SlackAPIError: On API errors.
    """
    return await slack_post(
        token,
        "slackLists.items.deleteMultiple",
        {"list_id": list_id, "item_ids": item_ids},
    )


async def list_list_items(
    token: str,
    list_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Fetch all items in a list with pagination.

    Why: Retrieves the full contents of a Slack list, handling multi-page results.
    What: Uses the paginate helper to call slackLists.items.list and collect all items.
    Test: Mock paginate to yield two pages; assert all items collected in result.

    Args:
        token: Slack bot token (requires lists:read).
        list_id: List ID.
        limit: Max items per page (default 100).

    Returns:
        Dict with 'items' list and 'paging' info.

    Raises:
        SlackAPIError: On API errors.
    """
    all_items: list[Any] = []

    async def _fetch(**kwargs: Any) -> dict[str, Any]:
        return await slack_post(token, "slackLists.items.list", {**kwargs})

    async for page in paginate(_fetch, "items", limit=limit, list_id=list_id):
        all_items.extend(page)

    return {"ok": True, "items": all_items}


async def get_list_item(
    token: str,
    list_id: str,
    item_id: str,
) -> dict[str, Any]:
    """Get details for a single list item.

    Why: Fetches full metadata for a specific list entry.
    What: Calls slackLists.items.info with list_id and item_id.
    Test: Mock slack_post, verify slackLists.items.info called, assert item key present.

    Args:
        token: Slack bot token (requires lists:read).
        list_id: List ID.
        item_id: Item ID.

    Returns:
        Dict with 'item' object containing value, status, metadata.

    Raises:
        SlackAPIError: On API errors.
    """
    return await slack_post(
        token,
        "slackLists.items.info",
        {"list_id": list_id, "item_id": item_id},
    )


async def set_list_access(
    token: str,
    list_id: str,
    access_level: str,
    user_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Set access rules for a list.

    Why: Controls who can view or edit a Slack list for secure collaboration.
    What: Calls slackLists.access.set with access_level and optional user/group IDs.
    Test: Mock slack_post, verify slackLists.access.set called with correct access_level.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        access_level: "read", "write", or "owner".
        user_ids: List of user IDs to grant access to.
        group_ids: List of group IDs to grant access to.

    Returns:
        Dict with access control details.

    Raises:
        SlackAPIError: On API errors.
    """
    payload: dict[str, Any] = {
        "list_id": list_id,
        "access_level": access_level,
    }
    if user_ids is not None:
        payload["user_ids"] = user_ids
    if group_ids is not None:
        payload["group_ids"] = group_ids
    return await slack_post(token, "slackLists.access.set", payload)


async def delete_list_access(
    token: str,
    list_id: str,
    user_id: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Revoke access to a list.

    Why: Removes specific users or groups from list access.
    What: Calls slackLists.access.delete with list_id and user or group ID.
    Test: Mock slack_post, verify slackLists.access.delete called with list_id.

    Args:
        token: Slack bot token (requires lists:write).
        list_id: List ID.
        user_id: User ID to revoke access for.
        group_id: Group ID to revoke access for.

    Returns:
        Dict with ok=true.

    Raises:
        SlackAPIError: On API errors.
    """
    payload: dict[str, Any] = {"list_id": list_id}
    if user_id is not None:
        payload["user_id"] = user_id
    if group_id is not None:
        payload["group_id"] = group_id
    return await slack_post(token, "slackLists.access.delete", payload)
