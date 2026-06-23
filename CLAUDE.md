# slack-mpm: MCP Server for Slack

**Version**: 0.1.4 | **Python**: 3.10+ | **Package Manager**: uv | **Entry Point**: `slack-mpm` CLI

## Project Overview

slack-mpm is a **Model Context Protocol (MCP) server and Python API library** for Slack workspace integration. It exposes 40+ Slack operations as MCP tools for use with Claude Desktop and provides a clean async Python API for building Slack integrations.

### Core Components

- **Python API Library** (`src/slack_mpm/api/`): 8 submodules providing async Slack API wrappers
- **Authentication** (`src/slack_mpm/auth/`): Token management and validation
- **CLI** (`src/slack_mpm/cli/`): Command-line interface (`setup`, `doctor`, `mcp`)
- **MCP Server** (`src/slack_mpm/server/`): MCP protocol adapter registering tools for Claude Desktop
- **Agent Scripts** (`agents/`): Standalone automation tools (listener, notifier, responder, digest, archiver)

### Slack Tool Coverage

**40+ tools across 8 categories**: Channels (8), Messages (13), Users (5), Files (5), Workspace (4), Reminders (4), Bookmarks (3), Scheduled Messages (3).

---

## 🔴 Critical Workflows

### Setup & Installation

**Single path**: `make install`

```bash
# Full dev setup (dependencies + pre-commit hooks)
make install-dev

# Verify installation
uv run slack-mpm doctor
```

**What happens**:
- `uv sync` installs all dependencies from `uv.lock`
- Pre-commit hooks registered (ruff, mypy, bandit, detect-secrets)
- `.env.local` must be created manually (see `.env.local.example`)

### Running Tests

**Single path**: `make test`

```bash
# Run all tests (pytest in asyncio_mode=auto)
make test

# Run with coverage report (HTML + terminal)
make test-cov
```

**Configuration**: `pyproject.toml` [tool.pytest.ini_options] — `testpaths = ["tests"]`, `asyncio_mode = "auto"`

### Code Quality Checks (Pre-Commit)

**Must pass before commit**. Three tools enforce quality:

| Tool | Command | Purpose |
|------|---------|---------|
| **ruff** | `make lint` (check), `make format` (fix) | Linting (E,F,I,UP rules), imports, upgrades; line-length 100 |
| **mypy** | `make type-check` | Type safety (strict mode, py310) |
| **bandit** | Pre-commit hook | Security scanning |
| **detect-secrets** | Pre-commit hook | Prevent secrets in commits |

**Single path for all checks**:

```bash
# Lint only (does NOT fix)
make lint

# Lint + auto-fix issues
make format

# Type checking
make type-check

# All quality gates (lint + test), used before release
make pre-publish
```

### Building & Publishing

**Single path for releases**: `make publish` (patch), `make publish-minor`, `make publish-major`

```bash
# Bump patch (0.1.4 → 0.1.5), build, publish to PyPI + create GitHub Release
make publish

# Bump minor (0.1.4 → 0.2.0)
make publish-minor

# Bump major (0.1.4 → 1.0.0)
make publish-major

# Publish current version without bumping (no version changes)
make publish-only

# Build wheel + sdist (no publish)
make build
```

**Requires**: `PYPI_TOKEN` in `.env.local` or `../gworkspace-mcp/.env.local`

---

## 🟡 Important Workflows

### Version Management

```bash
# Show current version (reads from VERSION file)
make version

# Bump patch in-place (syncs VERSION, pyproject.toml, __version__.py)
make bump-patch

# Bump minor in-place
make bump-minor

# Bump major in-place
make bump-major

# Sync VERSION file to pyproject.toml and __version__.py (if manual edit)
make sync-versions

# Create git tag for current version
make tag

# Push commits + tags
make push
make push-tags
```

**Files tracked**:
- `VERSION` (source of truth)
- `pyproject.toml` (synced from VERSION)
- `src/slack_mpm/__version__.py` (synced from VERSION)

### Running Code Locally

**MCP server mode** (for Claude Desktop):
```bash
uv run slack-mpm mcp
```

**CLI verification**:
```bash
uv run slack-mpm setup       # Verify Slack token works
uv run slack-mpm doctor      # Health check
uv run slack-mpm --help      # Show all CLI commands
```

### Using the Python API

```python
import asyncio
from slack_mpm.api import messages, channels
from slack_mpm.auth.token_manager import TokenManager

async def main():
    token = TokenManager().get_token()  # Reads from .env.local or .env
    await messages.send_message(token, "#general", "Hello!")
    channels_data = await channels.list_channels(token)

asyncio.run(main())
```

---

## 🟢 Standard Practices

### Code Conventions

- **Language**: Python 3.10+ only
- **Type hints**: Required (mypy --strict enforced)
- **Line length**: 100 characters (ruff configured)
- **Async-first**: All Slack API calls use `async`/`await` with httpx
- **Dependency Injection**: TokenManager passed explicitly (no globals)
- **Imports**: Organized by ruff (E,F,I rules)

### Project Structure

```
src/slack_mpm/
├── api/                # API wrappers for Slack operations
│   ├── _client.py      # Shared httpx client + error handling
│   ├── _pagination.py  # Pagination helper
│   ├── channels.py     # 8 channel operations
│   ├── messages.py     # 13 message operations
│   ├── users.py        # 5 user operations
│   ├── files.py        # 5 file operations
│   ├── workspace.py    # 4 workspace operations
│   ├── reminders.py    # 4 reminder operations
│   ├── bookmarks.py    # 3 bookmark operations
│   └── scheduled.py    # 3 scheduled message operations
├── auth/               # Authentication & token management
│   ├── models.py       # SlackToken, TokenStatus, WorkspaceInfo
│   └── token_manager.py # TokenManager (loads .env.local / .env)
├── cli/                # CLI entry point
│   └── main.py         # Commands: setup, doctor, mcp
└── server/             # MCP server adapter
    └── slack_mcp_server.py # SlackMCPServer class

agents/                 # Standalone automation scripts
├── slack_listener.py   # Channel message poller
├── slack_notifier.py   # Send notifications
├── slack_responder.py  # Auto-responder bot
├── slack_digest.py     # Activity digest
└── slack_archiver.py   # History export

tests/                  # Pytest test suite
```

### Testing Requirements

- **Framework**: pytest (asyncio_mode=auto)
- **Coverage**: Recommend >80% (use `make test-cov`)
- **Location**: `tests/` directory (mirrors `src/slack_mpm/`)
- **Async tests**: Use `async def test_*()` (pytest-asyncio handles)

### Pre-Commit Hooks

Registered on `uv sync` via `.pre-commit-config.yaml`:

1. **trailing-whitespace**: Remove trailing spaces
2. **end-of-file-fixer**: Single newline at EOF
3. **check-yaml/json/toml**: Syntax validation
4. **check-merge-conflict**: Prevent unresolved conflicts
5. **check-added-large-files**: Block files >1MB
6. **ruff (with --fix)**: Auto-fix linting issues
7. **ruff-format**: Format code
8. **mypy**: Type checking (strict, ignoring tests)
9. **bandit**: Security scanning
10. **detect-secrets**: Prevent secret commits
11. **commitizen**: Enforce conventional commits

---

## 🟢 Common Development Tasks

### Running Everything Locally

```bash
# Install dev dependencies
make install-dev

# Run all tests
make test

# Run tests with coverage
make test-cov

# Check types
make type-check

# Lint (no fixes)
make lint

# Format code
make format
```

### Adding New Slack API Wrappers

1. Create new file in `src/slack_mpm/api/` (e.g., `conversations.py`)
2. Import `SlackAPIClient` from `_client.py`
3. Define async functions with full type hints
4. Add to `src/slack_mpm/api/__init__.py` exports
5. Register as MCP tool in `src/slack_mpm/server/slack_mcp_server.py`
6. Write tests in `tests/api/test_conversations.py`

### Adding New CLI Commands

1. Add function to `src/slack_mpm/cli/main.py`
2. Decorate with `@click.command()` and `@click.option()`
3. Ensure it integrates with TokenManager
4. Document in `uv run slack-mpm --help`

---

## ⚪ Optional Enhancements

- **OpenAPI/Swagger**: Not currently used; consider if SDK generation needed
- **GraphQL**: Not needed; REST API suffices
- **Additional docs**: See DEVELOPER.md, CODE_STRUCTURE.md for deeper context

---

## Configuration Files

| File | Purpose |
|------|---------|
| `VERSION` | Current version (source of truth) |
| `pyproject.toml` | Package metadata, dependencies, tool configs |
| `uv.lock` | Locked dependency versions (commit to git) |
| `.env.local` | Local secrets (`SLACK_BOT_TOKEN`, `PYPI_TOKEN`) — NOT in git |
| `.env.local.example` | Template for `.env.local` |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, mypy, bandit, detect-secrets) |
| `Makefile` | Build, test, lint, format, version, publish targets |
| `.gitignore` | Ignores venv, __pycache__, .claude-mpm/, etc. |

---

## Environment Variables

```bash
# Required for CLI/API operations
SLACK_BOT_TOKEN=xoxb-...          # Bot token from Slack App

# Optional: User token for search_messages + reminders
SLACK_USER_TOKEN=xoxp-...         # User token (if using search/reminders)

# Optional: CLI operations (e.g., use_user_token flag)
# See each API function's use_user_token parameter

# For publishing
PYPI_TOKEN=pypi-...               # PyPI token (in .env.local for make publish)
```

---

## Quick Reference: Single-Path Commands

```bash
# Setup
make install             # Install in dev mode
make install-dev         # Install with dev dependencies

# Testing
make test                # Run pytest
make test-cov            # Run pytest with coverage

# Quality
make lint                # Check code (no fix)
make format              # Lint + auto-fix + format
make type-check          # Type checking (strict)
make pre-publish         # Lint + test (pre-release check)

# Building & Publishing
make build               # Build wheel + sdist
make version             # Show current version
make bump-patch          # Bump patch version (x.y.Z+1)
make bump-minor          # Bump minor version (x.Y+1.0)
make bump-major          # Bump major version (X+1.0.0)
make publish             # Full patch release (bump + build + PyPI + GitHub)
make publish-minor       # Full minor release
make publish-major       # Full major release
make publish-only        # Publish without version bump

# Git Operations
make tag                 # Create tag for current version
make push                # Push commits
make push-tags           # Push tags

# Cleanup
make clean               # Remove build artifacts
```

---

## Support

- **Slack API docs**: https://api.slack.com/methods
- **MCP docs**: https://modelcontextprotocol.io
- **Python docs**: https://docs.python.org/3.10
- **uv docs**: https://docs.astral.sh/uv/

See [DEVELOPER.md](/Users/masa/Projects/slack-mpm/DEVELOPER.md) for setup, development workflow, and release procedures.
