"""Tests for Slack Files API - enhanced upload_file function."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_url_data() -> dict:
    return {"ok": True, "upload_url": "https://files.slack.com/upload/v1/abc", "file_id": "F_TEST"}


@pytest.fixture
def mock_complete_data() -> dict:
    return {"ok": True, "files": [{"id": "F_TEST", "name": "test.txt"}]}


@pytest.mark.asyncio
async def test_upload_file_text_content(mock_url_data: dict, mock_complete_data: dict) -> None:
    """upload_file accepts str content (backward compatible)."""
    from slack_mpm.api.files import upload_file

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch("slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)),
        patch("slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        result = await upload_file(
            "xoxb-token", ["C123"], content="hello world", filename="test.txt"
        )

    assert result["ok"] is True


@pytest.mark.asyncio
async def test_upload_file_binary_content(mock_url_data: dict, mock_complete_data: dict) -> None:
    """upload_file accepts bytes content."""
    from slack_mpm.api.files import upload_file

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch(
            "slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)
        ) as mock_get,
        patch("slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        result = await upload_file(
            "xoxb-token", ["C123"], content=b"\x89PNG\r\n", filename="image.png"
        )

    assert result["ok"] is True
    # Verify length was correctly computed for binary
    get_params = mock_get.call_args[0][2]
    assert get_params["length"] == 6  # len(b"\x89PNG\r\n")


@pytest.mark.asyncio
async def test_upload_file_from_path(
    mock_url_data: dict, mock_complete_data: dict, tmp_path: Path
) -> None:
    """upload_file reads content from file_path."""
    from slack_mpm.api.files import upload_file

    test_file = tmp_path / "report.md"
    test_file.write_text("# Report\nContent here", encoding="utf-8")

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch("slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)),
        patch("slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        result = await upload_file(
            "xoxb-token", ["C123"], file_path=str(test_file), filename="report.md"
        )

    assert result["ok"] is True


@pytest.mark.asyncio
async def test_upload_file_both_content_and_path_raises() -> None:
    """upload_file raises ValueError if both content and file_path are provided."""
    from slack_mpm.api.files import upload_file

    with pytest.raises(ValueError, match="not both"):
        await upload_file(
            "xoxb-token",
            ["C123"],
            content="text",
            file_path="/some/path",
            filename="test.txt",
        )


@pytest.mark.asyncio
async def test_upload_file_neither_content_nor_path_raises() -> None:
    """upload_file raises ValueError if neither content nor file_path is provided."""
    from slack_mpm.api.files import upload_file

    with pytest.raises(ValueError, match="must be provided"):
        await upload_file("xoxb-token", ["C123"], filename="test.txt")


@pytest.mark.asyncio
async def test_upload_file_path_not_found_raises() -> None:
    """upload_file raises FileNotFoundError if file_path does not exist."""
    from slack_mpm.api.files import upload_file

    with pytest.raises(FileNotFoundError):
        await upload_file(
            "xoxb-token",
            ["C123"],
            file_path="/nonexistent/path/file.txt",
            filename="file.txt",
        )


@pytest.mark.asyncio
async def test_upload_file_with_thread_ts(mock_url_data: dict, mock_complete_data: dict) -> None:
    """upload_file passes thread_ts to completeUploadExternal."""
    from slack_mpm.api.files import upload_file

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch("slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)),
        patch(
            "slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)
        ) as mock_post,
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        await upload_file(
            "xoxb-token",
            ["C123"],
            content="hello",
            filename="test.txt",
            thread_ts="1234567890.123456",
        )

    complete_payload = mock_post.call_args[0][2]
    assert complete_payload["thread_ts"] == "1234567890.123456"


@pytest.mark.asyncio
async def test_upload_file_multi_channel_batch(
    mock_url_data: dict, mock_complete_data: dict
) -> None:
    """upload_file uses channels array in completeUploadExternal (single API call)."""
    from slack_mpm.api.files import upload_file

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch("slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)),
        patch(
            "slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)
        ) as mock_post,
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        await upload_file(
            "xoxb-token",
            ["C1", "C2", "C3"],
            content="hello",
            filename="test.txt",
        )

    # Only one slack_post call (completeUploadExternal), not one per channel
    assert mock_post.call_count == 1
    complete_payload = mock_post.call_args[0][2]
    assert complete_payload["channels"] == ["C1", "C2", "C3"]


@pytest.mark.asyncio
async def test_upload_file_three_step_flow(mock_url_data: dict, mock_complete_data: dict) -> None:
    """upload_file executes all three steps: getUploadURLExternal, POST, completeUploadExternal."""
    from slack_mpm.api.files import upload_file

    mock_upload_resp = MagicMock()
    mock_upload_resp.raise_for_status = MagicMock()

    with (
        patch(
            "slack_mpm.api.files.slack_get", new=AsyncMock(return_value=mock_url_data)
        ) as mock_get,
        patch(
            "slack_mpm.api.files.slack_post", new=AsyncMock(return_value=mock_complete_data)
        ) as mock_post,
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_upload_resp)
        mock_client_cls.return_value = mock_client

        await upload_file("xoxb-token", ["C123"], content="data", filename="file.txt")

    # Step 1: getUploadURLExternal
    mock_get.assert_called_once()
    assert mock_get.call_args[0][1] == "files.getUploadURLExternal"

    # Step 2: Direct HTTP POST to upload URL
    mock_client.post.assert_called_once_with(
        "https://files.slack.com/upload/v1/abc",
        content=b"data",
        headers={"Content-Type": "application/octet-stream"},
    )

    # Step 3: completeUploadExternal
    mock_post.assert_called_once()
    assert mock_post.call_args[0][1] == "files.completeUploadExternal"
