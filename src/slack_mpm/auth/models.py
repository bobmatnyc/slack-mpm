"""Pydantic models for Slack authentication."""

from enum import Enum

from pydantic import BaseModel, Field


class TokenStatus(str, Enum):
    """Status of a Slack token."""

    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    UNKNOWN = "unknown"


class SlackToken(BaseModel):
    """Represents a Slack API token with metadata."""

    token: str = Field(..., description="The Slack API token value")
    token_type: str = Field(..., description="Type of token: 'bot' or 'user'")
    status: TokenStatus = Field(default=TokenStatus.UNKNOWN, description="Validation status")
    team_id: str | None = Field(default=None, description="Slack workspace/team ID")
    team_name: str | None = Field(default=None, description="Slack workspace name")
    user_id: str | None = Field(default=None, description="User ID associated with token")
    bot_id: str | None = Field(default=None, description="Bot ID (for bot tokens)")
    scopes: list[str] = Field(default_factory=list, description="OAuth scopes granted")

    class Config:
        """Pydantic config."""

        frozen = False

    def is_bot_token(self) -> bool:
        """Return True if this is a bot token."""
        return self.token.startswith("xoxb-")

    def is_user_token(self) -> bool:
        """Return True if this is a user token."""
        return self.token.startswith("xoxp-")

    def mask(self) -> str:
        """Return a masked version of the token for display."""
        if len(self.token) <= 10:
            return "***"
        return self.token[:6] + "..." + self.token[-4:]


class WorkspaceInfo(BaseModel):
    """Information about a Slack workspace."""

    team_id: str = Field(..., description="Workspace team ID")
    team_name: str = Field(..., description="Workspace name")
    team_domain: str | None = Field(default=None, description="Workspace URL domain")
    team_url: str | None = Field(default=None, description="Workspace URL")
    enterprise_id: str | None = Field(default=None, description="Enterprise grid ID")
    enterprise_name: str | None = Field(default=None, description="Enterprise grid name")
