"""Token manager for Slack bot/user token lifecycle."""

import os
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from slack_mcp.auth.models import SlackToken, TokenStatus

SLACK_API_BASE = "https://slack.com/api"


def _load_env() -> None:
    """Load environment variables from .env and .env.local files.

    Priority: .env loaded first (base), then .env.local overrides.
    Searches from CWD upward for env files.
    """
    cwd = Path.cwd()

    # Load base .env (do not override existing env vars)
    env_path = cwd / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    # Load .env.local last so it overrides base .env
    env_local_path = cwd / ".env.local"
    if env_local_path.exists():
        load_dotenv(env_local_path, override=True)


class TokenManager:
    """Manages Slack bot and user tokens loaded from environment variables."""

    def __init__(self) -> None:
        """Initialize token manager and load tokens from environment."""
        _load_env()
        self._bot_token: Optional[str] = os.environ.get("SLACK_BOT_TOKEN")
        self._user_token: Optional[str] = os.environ.get("SLACK_USER_TOKEN")
        self._signing_secret: Optional[str] = os.environ.get("SLACK_SIGNING_SECRET")
        self._team_id: Optional[str] = os.environ.get("SLACK_TEAM_ID")

    @property
    def bot_token(self) -> Optional[str]:
        """Return the bot token if available."""
        return self._bot_token

    @property
    def user_token(self) -> Optional[str]:
        """Return the user token if available."""
        return self._user_token

    @property
    def signing_secret(self) -> Optional[str]:
        """Return the signing secret if available."""
        return self._signing_secret

    @property
    def team_id(self) -> Optional[str]:
        """Return the configured team ID if available."""
        return self._team_id

    def has_bot_token(self) -> bool:
        """Return True if a bot token is configured."""
        return bool(self._bot_token)

    def has_user_token(self) -> bool:
        """Return True if a user token is configured."""
        return bool(self._user_token)

    def get_token(self, prefer_user: bool = False) -> str:
        """Return the best available token.

        Args:
            prefer_user: If True, prefer user token over bot token.

        Returns:
            The token string.

        Raises:
            ValueError: If no token is configured.
        """
        if prefer_user and self._user_token:
            return self._user_token
        if self._bot_token:
            return self._bot_token
        if self._user_token:
            return self._user_token
        raise ValueError(
            "No Slack token configured. Set SLACK_BOT_TOKEN in your .env.local file."
        )

    async def validate_bot_token(self) -> SlackToken:
        """Validate the bot token by calling auth.test API.

        Returns:
            SlackToken with validation results.

        Raises:
            ValueError: If no bot token is configured.
        """
        if not self._bot_token:
            return SlackToken(
                token="",
                token_type="bot",
                status=TokenStatus.MISSING,
            )

        return await self._validate_token(self._bot_token, "bot")

    async def validate_user_token(self) -> SlackToken:
        """Validate the user token by calling auth.test API.

        Returns:
            SlackToken with validation results.

        Raises:
            ValueError: If no user token is configured.
        """
        if not self._user_token:
            return SlackToken(
                token="",
                token_type="user",
                status=TokenStatus.MISSING,
            )

        return await self._validate_token(self._user_token, "user")

    async def _validate_token(self, token: str, token_type: str) -> SlackToken:
        """Call auth.test to validate a token and return token info.

        Args:
            token: The Slack token to validate.
            token_type: Either 'bot' or 'user'.

        Returns:
            SlackToken with status and metadata populated.
        """
        slack_token = SlackToken(token=token, token_type=token_type)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{SLACK_API_BASE}/auth.test",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json; charset=utf-8",
                    },
                    json={},
                )
                data = response.json()

                if data.get("ok"):
                    slack_token.status = TokenStatus.VALID
                    slack_token.team_id = data.get("team_id")
                    slack_token.team_name = data.get("team")
                    slack_token.user_id = data.get("user_id")
                    slack_token.bot_id = data.get("bot_id")
                else:
                    slack_token.status = TokenStatus.INVALID

        except httpx.RequestError:
            slack_token.status = TokenStatus.UNKNOWN

        return slack_token
