"""Cursor-pagination helper for Slack API endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any


async def paginate(
    api_fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]],
    items_key: str,
    *,
    limit: int = 200,
    **kwargs: Any,
) -> AsyncGenerator[list[Any], None]:
    """Yield successive pages from a cursor-paginated Slack API endpoint.

    Args:
        api_fn: Async callable that accepts ``cursor`` and ``limit`` keyword
            arguments and returns a Slack API response dict.
        items_key: Key in the response dict that holds the list of items
            (e.g. ``"channels"``, ``"members"``).
        limit: Page size passed to ``api_fn`` on every request.
        **kwargs: Any extra fixed parameters forwarded to ``api_fn`` unchanged
            on every page request (e.g. ``types=``, ``user=``).

    Yields:
        One page of items at a time as a :class:`list`.
    """
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"limit": limit, **kwargs}
        if cursor:
            params["cursor"] = cursor
        resp = await api_fn(**params)
        yield resp.get(items_key, [])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
