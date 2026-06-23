"""Pytest configuration and session-wide fixtures.

Why: Prevents real .env.local tokens from leaking into tests.
TokenManager._load_env() walks CWD and all parent directories loading
.env.local with override=True. When a real .env.local exists anywhere up
the tree (e.g. the main checkout that this worktree lives under), it
overwrites the environment that patch.dict(clear=True) carefully set,
causing 17+ failures whenever a developer has real Slack credentials
present locally (issue #4).

Strategy (two layers):
  1. Monkeypatch TokenManager._load_env to a no-op for the entire
     test session so the parent-dir walk can never fire during tests.
  2. Remove SLACK_BOT_TOKEN / SLACK_USER_TOKEN from os.environ before
     each test so shell-provided tokens cannot bleed in either.

Tests that NEED specific tokens must set them explicitly via their own
patch.dict (which runs AFTER the autouse fixture yields), so those tests
are unaffected.

How to test: Run `make test` with real env vars present:
  env SLACK_BOT_TOKEN=xoxb-real SLACK_USER_TOKEN=xoxp-real uv run pytest -q
All 122 tests should pass.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest


@pytest.fixture(scope="session", autouse=True)
def _disable_load_env() -> Generator[None, None, None]:
    """Monkeypatch _load_env to a no-op for the entire test session.

    Why: Prevents TokenManager from walking the filesystem for .env.local
    files during tests. Without this patch, a real .env.local anywhere up
    the directory tree (override=True) overwrites the carefully isolated
    environments set by individual tests' patch.dict(clear=True) calls.
    What: Replaces slack_mpm.auth.token_manager._load_env with a function
    that does nothing, then restores the original after the session ends.
    Test: Verify by running tests with real env vars present — all pass.
    """
    with patch("slack_mpm.auth.token_manager._load_env", return_value=None):
        yield


@pytest.fixture(autouse=True)
def _clear_slack_tokens() -> Generator[None, None, None]:
    """Remove real Slack tokens from os.environ before each test.

    Why: Shell-provided tokens (e.g. from a developer's shell profile or
    CI secrets exported into the process) would leak into tests that expect
    no tokens to be present. Removing them before each test ensures a clean
    baseline; tests that need specific tokens set them explicitly via their
    own patch.dict calls which run after this fixture yields.
    What: Deletes SLACK_BOT_TOKEN and SLACK_USER_TOKEN from os.environ,
    then restores original values after each test.
    Test: Run `env SLACK_BOT_TOKEN=xoxb-fake uv run pytest -q` — passes.
    """
    # Save any real tokens that exist in the environment.
    saved: dict[str, str] = {}
    for var in ("SLACK_BOT_TOKEN", "SLACK_USER_TOKEN"):
        if var in os.environ:
            saved[var] = os.environ.pop(var)

    yield

    # Restore saved tokens so we don't permanently alter the process env.
    os.environ.update(saved)
