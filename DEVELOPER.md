# DEVELOPER.md: Development Guide for slack-mpm

This guide covers setting up a local development environment, running tests, contributing code, and releasing new versions.

## Initial Setup

### 1. Clone & Install Dependencies

```bash
git clone <repository>
cd slack-mpm
make install-dev
```

This runs `uv sync`, installs all dev dependencies, and registers pre-commit hooks.

### 2. Create Local Configuration

```bash
cp .env.local.example .env.local
# Edit .env.local and add your Slack tokens:
# SLACK_BOT_TOKEN=xoxb-...
# SLACK_USER_TOKEN=xoxp-...  (optional, for search/reminders)
```

### 3. Verify Installation

```bash
uv run slack-mpm doctor      # Health check
uv run slack-mpm setup       # Validate tokens
```

---

## Development Workflow

### Working on Features

1. **Create a branch** from `main`
   ```bash
   git checkout -b feature/short-description
   ```

2. **Write code** with type hints:
   ```python
   from slack_mpm.auth.token_manager import TokenManager
   from slack_mpm.api import messages

   async def send_notification(text: str) -> None:
       token = TokenManager().get_token()
       await messages.send_message(token, "#alerts", text)
   ```

3. **Write tests** in `tests/`:
   ```python
   import pytest
   from slack_mpm.api import messages

   @pytest.mark.asyncio
   async def test_send_message(mock_token):
       result = await messages.send_message(mock_token, "#test", "Hello")
       assert result is not None
   ```

4. **Run quality checks**:
   ```bash
   make format         # Auto-fix code style + imports
   make lint           # Check (should pass after format)
   make type-check     # Type validation
   make test           # Run pytest
   ```

5. **Pre-commit validates automatically**:
   ```bash
   git add src/slack_mpm/new_feature.py
   git commit -m "feat: add new feature"
   # Pre-commit hooks run: ruff, mypy, bandit, detect-secrets
   # If any fail, fix and re-commit
   ```

### Code Organization

**API Modules** (`src/slack_mpm/api/`):
- Each file represents one Slack API domain (channels, messages, users, etc.)
- Use `SlackAPIClient` from `_client.py` for HTTP calls
- Define async functions with full type hints
- Export all public functions in `__init__.py`

**Example**:
```python
# src/slack_mpm/api/my_feature.py
from slack_mpm.api._client import SlackAPIClient

async def my_operation(token: str, param: str) -> dict[str, Any]:
    """Do something with Slack API."""
    client = SlackAPIClient(token)
    response = await client.post("method.name", {"key": param})
    return response
```

### Testing Strategy

- **Location**: `tests/` mirrors `src/slack_mpm/`
- **Framework**: pytest with asyncio_mode=auto
- **Async tests**: Use `@pytest.mark.asyncio` or just `async def test_*()`
- **Mocking**: Use `unittest.mock.AsyncMock` or pytest fixtures

Example test:
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_operation():
    with patch("slack_mpm.api.my_feature.SlackAPIClient") as mock_client:
        mock_client.return_value.post = AsyncMock(
            return_value={"ok": True, "result": "data"}
        )
        result = await my_operation("token", "param")
        assert result["ok"] is True
```

Run tests:
```bash
make test              # All tests
make test-cov          # With coverage report (htmlcov/)
```

---

## Code Quality Standards

### Type Hints (Required)

All code must type hints. mypy runs in **strict mode**:

```python
from typing import Any

async def send_message(
    token: str,
    channel: str,
    text: str,
    blocks: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Send a message to a channel."""
    ...
```

Check types:
```bash
make type-check
```

### Linting & Formatting

**ruff** enforces:
- Line length: 100 characters
- Import organization (ruff-sort)
- Upgrade syntax (py310+)
- Remove unused imports/variables

Auto-fix issues:
```bash
make format
```

Check without fixing:
```bash
make lint
```

### Pre-Commit Hooks

Hooks run automatically on `git commit`:

| Hook | Fixes | Purpose |
|------|-------|---------|
| trailing-whitespace | Yes | Remove trailing spaces |
| end-of-file-fixer | Yes | Single newline at EOF |
| check-yaml/json/toml | No | Syntax validation |
| ruff (--fix) | Yes | Auto-fix linting |
| ruff-format | Yes | Format code |
| mypy | No | Type checking |
| bandit | No | Security scanning |
| detect-secrets | No | Prevent secrets in commits |
| commitizen | No | Enforce conventional commits |

If a hook fails, fix the issue and re-commit:
```bash
git add .
git commit -m "feat: description"
```

---

## Release Workflow

### Version Format

slack-mpm uses **semantic versioning**: MAJOR.MINOR.PATCH (e.g., 0.1.4)

- **PATCH** (0.1.Z): Bug fixes, minor improvements
- **MINOR** (0.Y.0): New features, backward compatible
- **MAJOR** (X.0.0): Breaking changes

### Publishing a Release

**Single-path release commands**:

```bash
# Patch release: 0.1.4 → 0.1.5
make publish

# Minor release: 0.1.4 → 0.2.0
make publish-minor

# Major release: 0.1.4 → 1.0.0
make publish-major

# Publish current version without bumping
make publish-only
```

**What `make publish` does**:
1. Run `make pre-publish` (lint + test checks)
2. Bump patch version in VERSION file
3. Sync version to `pyproject.toml` and `__version__.py`
4. Create commit: "chore: bump version to 0.1.5"
5. Create git tag: "v0.1.5"
6. Push commits and tags to origin
7. Build wheel + sdist
8. Upload to PyPI (using PYPI_TOKEN)
9. Create GitHub Release with auto-generated notes
10. Display success message

### Release Prerequisites

**Ensure**:
1. Working directory is clean (`git status`)
2. All tests pass (`make test`)
3. Code is linted (`make lint`)
4. PYPI_TOKEN is set in `.env.local` or `../gworkspace-mcp/.env.local`
5. GitHub CLI (`gh`) is installed for GitHub Release creation

**Pre-release check** (runs automatically in publish):
```bash
make pre-publish
```

### Troubleshooting Releases

**"Working directory is not clean"**:
```bash
git status
git add .
git commit -m "fix: description"
git checkout -b my-branch  # Or resolve conflicts
```

**PYPI_TOKEN not found**:
```bash
# Add to .env.local:
PYPI_TOKEN=pypi-AgEIcHlwaS5vcmc...
```

**Tag already exists**:
```bash
git tag -d v0.1.4
git push origin --delete v0.1.4
make publish  # Retry
```

---

## Manual Version Bumping (if needed)

If you need to bump version without publishing:

```bash
# Bump patch locally (doesn't commit)
make bump-patch

# Or manually:
echo "0.1.5" > VERSION
make sync-versions

# Verify
make version
```

---

## Adding New Features

### Slack API Wrapper

1. **Create API module** in `src/slack_mpm/api/`:
   ```python
   # src/slack_mpm/api/new_domain.py
   from slack_mpm.api._client import SlackAPIClient

   async def new_operation(
       token: str,
       param: str,
   ) -> dict[str, Any]:
       client = SlackAPIClient(token)
       return await client.post("domain.operation", {"param": param})
   ```

2. **Export in `__init__.py`**:
   ```python
   # src/slack_mpm/api/__init__.py
   from slack_mpm.api.new_domain import new_operation
   ```

3. **Add test** in `tests/api/`:
   ```python
   # tests/api/test_new_domain.py
   @pytest.mark.asyncio
   async def test_new_operation():
       result = await new_operation("token", "value")
       assert result is not None
   ```

4. **Register as MCP tool** in `src/slack_mpm/server/slack_mcp_server.py`:
   ```python
   # In SlackMCPServer.__init__() or tools() method
   server.add_tool(
       "new_operation",
       "Description of the operation",
       new_operation,
       {
           "token": {"type": "string", "description": "Bot token"},
           "param": {"type": "string", "description": "Parameter"},
       }
   )
   ```

### CLI Command

1. **Add to `src/slack_mpm/cli/main.py`**:
   ```python
   import click
   from slack_mpm.auth.token_manager import TokenManager

   @click.command()
   @click.option("--name", required=True, help="Name")
   def my_command(name: str) -> None:
       """My new command."""
       token = TokenManager().get_token()
       # Do something
       click.echo(f"Done: {name}")

   # Add to cli() group:
   @click.group()
   def cli() -> None:
       ...

   cli.add_command(my_command)
   ```

2. **Test it**:
   ```bash
   uv run slack-mpm my-command --name test
   ```

---

## Debugging

### Enable Debug Logging

Set env var before running:
```bash
DEBUG=1 uv run slack-mpm doctor
```

### Check httpx Requests

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Run your code — httpx will log requests/responses
```

### Test API Wrapper Locally

```python
import asyncio
from slack_mpm.api import messages
from slack_mpm.auth.token_manager import TokenManager

async def test():
    token = TokenManager().get_token()
    result = await messages.send_message(token, "#test", "Hello")
    print(result)

asyncio.run(test())
```

---

## Common Issues

| Issue | Solution |
|-------|----------|
| ImportError in tests | Ensure `PYTHONPATH` includes `src/`: `export PYTHONPATH=src` |
| "token invalid" | Verify SLACK_BOT_TOKEN in .env.local, check it in Slack App settings |
| mypy type errors | Add type hints to functions; check with `make type-check` |
| ruff lint fails | Run `make format` to auto-fix |
| Pre-commit hook fails | Fix the issue (lint, type check, secrets) and re-commit |
| Pytest not finding tests | Ensure tests are in `tests/` with `test_*.py` naming |

---

## Resources

- **Slack API**: https://api.slack.com/methods
- **MCP**: https://modelcontextprotocol.io
- **pytest**: https://docs.pytest.org/
- **mypy**: https://www.mypy-lang.org/
- **ruff**: https://docs.astral.sh/ruff/
- **uv**: https://docs.astral.sh/uv/

See [CLAUDE.md](/Users/masa/Projects/slack-mpm/CLAUDE.md) for agentic coder quick reference and project overview.
