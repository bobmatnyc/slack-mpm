"""Slack file API functions.

Note: The legacy files.upload endpoint was deprecated by Slack and sunset Nov 2025.
All uploads use the modern 3-step flow:
  1. files.getUploadURLExternal  — obtain upload URL + file_id
  2. HTTP POST to upload URL     — stream bytes to S3
  3. files.completeUploadExternal — register upload in workspace
"""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def upload_file(
    token: str,
    channels: list[str],
    content: str | bytes | None = None,
    filename: str = "",
    title: str | None = None,
    file_path: str | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """Upload a file (binary or text) to one or more channels.

    Why: Provides a unified entry point for file delivery supporting both in-memory
    content and disk files, with batch multi-channel sharing in a single API call.
    What: Executes the 3-step upload flow: getUploadURLExternal → POST bytes →
    completeUploadExternal (with all channel IDs and optional thread_ts).
    Test: Mock slack_get/slack_post and httpx, assert three steps called in order;
    verify ValueError raised when both content and file_path provided.

    Uses the files.getUploadURLExternal + files.completeUploadExternal flow
    (Slack v2 file upload API, required since legacy files.upload was sunset Nov 2025).

    Either ``content`` or ``file_path`` must be provided (not both).

    Args:
        token: Slack bot token (requires files:write).
        channels: List of channel IDs to share the file in (max 100 per API limit).
        content: File content as str or bytes. If None, read from file_path.
        filename: Name for the uploaded file.
        title: Optional display title for the file.
        file_path: Path to file on disk. Reads as binary. Mutually exclusive with content.
        thread_ts: Optional thread timestamp to attach upload to a thread.

    Returns:
        Dict with 'files' list containing the uploaded file objects.

    Raises:
        SlackAPIError: On API errors or plan/permission failures.
        FileNotFoundError: If file_path does not exist.
        ValueError: If neither content nor file_path is provided, or both are provided.
    """
    import httpx

    # Resolve content bytes
    if content is not None and file_path is not None:
        raise ValueError("upload_file: provide either content or file_path, not both")
    if content is None and file_path is None:
        raise ValueError("upload_file: either content or file_path must be provided")

    if file_path is not None:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"upload_file: file not found: {file_path}")
        content_bytes = path.read_bytes()
        # Default filename to the file's name if not provided
        if not filename:
            filename = path.name
    else:
        # content is not None here
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content  # type: ignore[assignment]

    file_size = len(content_bytes)

    # Step 1: Get upload URL
    url_params: dict[str, Any] = {
        "filename": filename,
        "length": file_size,
    }
    if title:
        url_params["title"] = title

    url_data = await slack_get(token, "files.getUploadURLExternal", url_params)
    upload_url: str = url_data["upload_url"]
    file_id: str = url_data["file_id"]

    # Step 2: Upload the file bytes to the provided URL
    async with httpx.AsyncClient(timeout=60.0) as client:
        upload_resp = await client.post(
            upload_url,
            content=content_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        upload_resp.raise_for_status()

    # Step 3: Complete the upload, sharing to ALL channels in one call.
    # Slack's files.completeUploadExternal accepts EITHER channel_id (single str)
    # OR channels (array) — not both simultaneously.
    complete_payload: dict[str, Any] = {
        "files": [{"id": file_id, "title": title or filename}],
    }
    if len(channels) > 1:
        # Pass all channels to completeUploadExternal (max 100 per Slack docs)
        complete_payload["channels"] = channels
    else:
        complete_payload["channel_id"] = channels[0] if channels else ""

    if thread_ts is not None:
        complete_payload["thread_ts"] = thread_ts

    return await slack_post(token, "files.completeUploadExternal", complete_payload)


async def list_files(
    token: str,
    channel: str | None = None,
    count: int = 100,
) -> dict[str, Any]:
    """List files in the workspace or a specific channel.

    Args:
        token: Slack bot token.
        channel: Optional channel ID to filter by.
        count: Maximum number of files to return.

    Returns:
        Dict with 'files' list and 'paging' info.
    """
    params: dict[str, Any] = {"count": count}
    if channel:
        params["channel"] = channel

    return await slack_get(token, "files.list", params)


async def get_file_info(token: str, file: str) -> dict[str, Any]:
    """Get detailed information about a file.

    Args:
        token: Slack bot token.
        file: File ID (e.g., 'F1234567890').  # pragma: allowlist secret

    Returns:
        Dict with 'file' object.
    """
    return await slack_get(token, "files.info", {"file": file})


async def delete_file(token: str, file: str) -> dict[str, Any]:
    """Delete a file.

    Args:
        token: Slack bot token.
        file: File ID to delete.

    Returns:
        Dict with ok=True on success.
    """
    return await slack_post(token, "files.delete", {"file": file})


async def share_file(token: str, file: str, channels: list[str]) -> dict[str, Any]:
    """Share an existing file to additional channels.

    Args:
        token: Slack bot token.
        file: File ID to share.
        channels: List of channel IDs to share the file to.

    Returns:
        Dict with 'file' object showing updated shares.
    """
    results: list[dict[str, Any]] = []
    for channel in channels:
        result = await slack_post(
            token,
            "chat.postMessage",
            {"channel": channel, "text": "", "files": [{"id": file}]},
        )
        results.append(result)

    return {"ok": True, "shared_to": channels, "results": results}
