"""Tests for token management."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from slack_mcp.auth.models import TokenStatus
from slack_mcp.auth.token_manager import TokenManager


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
