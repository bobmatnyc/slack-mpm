"""Tests for token management."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from slack_mcp.auth.models import TokenStatus
from slack_mcp.auth.token_manager import TokenManager, _load_env


def test_token_manager_no_tokens() -> None:
    """TokenManager reports no tokens when env vars are absent."""
    with patch.dict("os.environ", {}, clear=True):
        manager = TokenManager()
        assert not manager.has_bot_token()
        assert not manager.has_user_token()


def test_token_manager_bot_token() -> None:
    """TokenManager exposes bot token from environment variable."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test"}, clear=True):
        manager = TokenManager()
        assert manager.has_bot_token()
        assert manager.bot_token == "xoxb-test"


def test_token_manager_user_token() -> None:
    """TokenManager exposes user token from environment variable."""
    with patch.dict("os.environ", {"SLACK_USER_TOKEN": "xoxp-test"}, clear=True):
        manager = TokenManager()
        assert manager.has_user_token()
        assert manager.user_token == "xoxp-test"


def test_token_manager_both_tokens() -> None:
    """TokenManager handles both bot and user tokens simultaneously."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        manager = TokenManager()
        assert manager.has_bot_token()
        assert manager.has_user_token()
        assert manager.bot_token == "xoxb-bot"
        assert manager.user_token == "xoxp-user"


def test_get_token_returns_bot_by_default() -> None:
    """get_token() returns bot token when both are configured."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        manager = TokenManager()
        assert manager.get_token() == "xoxb-bot"


def test_get_token_prefers_user_when_requested() -> None:
    """get_token(prefer_user=True) returns user token when available."""
    env = {"SLACK_BOT_TOKEN": "xoxb-bot", "SLACK_USER_TOKEN": "xoxp-user"}
    with patch.dict("os.environ", env, clear=True):
        manager = TokenManager()
        assert manager.get_token(prefer_user=True) == "xoxp-user"


def test_get_token_falls_back_to_bot_when_no_user() -> None:
    """get_token(prefer_user=True) falls back to bot token when no user token."""
    with patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-bot"}, clear=True):
        manager = TokenManager()
        assert manager.get_token(prefer_user=True) == "xoxb-bot"


def test_get_token_raises_when_missing() -> None:
    """get_token() raises ValueError when no token is configured."""
    with patch.dict("os.environ", {}, clear=True):
        manager = TokenManager()
        with pytest.raises(ValueError, match="No Slack token"):
            manager.get_token()


def test_signing_secret_and_team_id() -> None:
    """TokenManager exposes signing secret and team ID from environment."""
    env = {
        "SLACK_BOT_TOKEN": "xoxb-test",
        "SLACK_SIGNING_SECRET": "secret123",
        "SLACK_TEAM_ID": "T0123456",
    }
    with patch.dict("os.environ", env, clear=True):
        manager = TokenManager()
        assert manager.signing_secret == "secret123"
        assert manager.team_id == "T0123456"


def test_slack_token_mask() -> None:
    """SlackToken.mask() returns a partially obscured token."""
    from slack_mcp.auth.models import SlackToken

    token = SlackToken(token="xoxb-123456789-abcdefg", token_type="bot")
    masked = token.mask()
    assert masked.startswith("xoxb-1")
    assert "..." in masked


def test_slack_token_is_bot() -> None:
    """SlackToken correctly identifies bot tokens."""
    from slack_mcp.auth.models import SlackToken

    bot_token = SlackToken(token="xoxb-123", token_type="bot")
    user_token = SlackToken(token="xoxp-123", token_type="user")
    assert bot_token.is_bot_token()
    assert not user_token.is_bot_token()


def test_slack_token_is_user() -> None:
    """SlackToken correctly identifies user tokens."""
    from slack_mcp.auth.models import SlackToken

    bot_token = SlackToken(token="xoxb-123", token_type="bot")
    user_token = SlackToken(token="xoxp-123", token_type="user")
    assert user_token.is_user_token()
    assert not bot_token.is_user_token()


def test_token_status_enum() -> None:
    """TokenStatus enum values are correct."""
    assert TokenStatus.VALID == "valid"
    assert TokenStatus.INVALID == "invalid"
    assert TokenStatus.MISSING == "missing"
    assert TokenStatus.UNKNOWN == "unknown"


def test_load_env_finds_dotenv_local_outside_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_load_env() loads .env.local from the project root when CWD has no env
    files, simulating how Claude Desktop launches the MCP server with CWD set
    to the home directory or /.

    Strategy: change the real process CWD to tmp_path (empty — no .env files)
    and place a sentinel .env.local in the project root (resolved via
    Path(__file__).parents[3] inside token_manager.py).  The __file__-based
    candidate must fire and load the token.
    """
    import slack_mcp.auth.token_manager as tm_module

    # The project root as seen by token_manager.py (4 levels up from the file).
    token_manager_path = Path(tm_module.__file__).resolve()
    project_root = token_manager_path.parents[3]
    env_local = project_root / ".env.local"

    # Preserve any existing .env.local so we don't destroy real credentials.
    original_content: bytes | None = None
    if env_local.exists():
        original_content = env_local.read_bytes()

    try:
        env_local.write_text("SLACK_BOT_TOKEN=xoxb-from-project-root\n")

        # Actually change the process CWD to an empty temp directory.
        monkeypatch.chdir(tmp_path)

        # Clear the environment so no pre-existing token interferes.
        monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_USER_TOKEN", raising=False)

        _load_env()

        assert os.environ.get("SLACK_BOT_TOKEN") == "xoxb-from-project-root"

    finally:
        # Restore original .env.local (or remove the sentinel we created).
        if original_content is not None:
            env_local.write_bytes(original_content)
        else:
            env_local.unlink(missing_ok=True)
