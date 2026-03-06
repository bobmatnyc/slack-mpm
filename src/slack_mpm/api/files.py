"""Slack file API functions."""

from __future__ import annotations

from typing import Any

from slack_mpm.api._client import slack_get, slack_post


async def upload_file(
    token: str,
    channels: list[str],
    content: str,
    filename: str,
    title: str | None = None,
) -> dict[str, Any]:
    """Upload a file to one or more channels.

    Uses the files.getUploadURLExternal + files.completeUploadExternal flow
    (Slack v2 file upload API).

    Args:
        token: Slack bot token.
        channels: List of channel IDs to share the file in.
        content: File content as a string.
        filename: Name for the uploaded file.
        title: Optional display title for the file.

    Returns:
        Dict with 'files' list containing the uploaded file objects.
    """
    import httpx

    content_bytes = content.encode("utf-8")
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

    # Step 2: Upload the file to the provided URL
    async with httpx.AsyncClient(timeout=60.0) as client:
        upload_resp = await client.post(
            upload_url,
            content=content_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        upload_resp.raise_for_status()

    # Step 3: Complete the upload and share to channels
    complete_payload: dict[str, Any] = {
        "files": [{"id": file_id, "title": title or filename}],
        "channel_id": channels[0] if channels else "",
    }

    result = await slack_post(token, "files.completeUploadExternal", complete_payload)

    # Share to additional channels if more than one specified
    for extra_channel in channels[1:]:
        await slack_post(
            token,
            "files.sharedPublicURL",
            {"file": file_id},
        )
        await slack_post(
            token,
            "chat.postMessage",
            {"channel": extra_channel, "text": f"Shared file: {filename}", "attachments": [{"fallback": filename, "file_id": file_id}]},
        )

    return result


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
        file: File ID (e.g., 'F1234567890').

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
