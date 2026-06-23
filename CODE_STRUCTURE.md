# CODE_STRUCTURE.md: Project Architecture Overview

This document describes the organization and responsibilities of each module in slack-mpm.

---

## Directory Layout

```
slack-mpm/
├── src/slack_mpm/              # Main package
│   ├── api/                    # Slack API wrapper modules
│   ├── auth/                   # Authentication & token management
│   ├── cli/                    # Command-line interface
│   ├── server/                 # MCP server adapter
│   ├── __init__.py
│   └── __version__.py
├── agents/                     # Standalone automation scripts
├── tests/                      # Pytest test suite
├── docs/                       # Documentation (research/)
├── Makefile                    # Build & release automation
├── pyproject.toml              # Package metadata & tool config
├── uv.lock                     # Locked dependencies
├── VERSION                     # Current version (source of truth)
├── .env.local.example          # Configuration template
├── .pre-commit-config.yaml     # Pre-commit hooks
├── .gitignore                  # Git ignore patterns
├── .secrets.baseline           # detect-secrets baseline
├── README.md                   # User guide & quick start
├── CLAUDE.md                   # Agentic coder quick reference
├── DEVELOPER.md                # Development workflow
└── CODE_STRUCTURE.md           # This file
```

---

## Core Modules

### `src/slack_mpm/api/` — Slack API Wrappers

Provides clean, typed async functions for Slack operations. Each submodule maps to a Slack API domain.

#### `_client.py` — Shared HTTP Client

**Responsibilities**:
- `SlackAPIClient` class: httpx-based HTTP wrapper around Slack API
- `SlackAPIError` exception: Raised on API errors (401, 404, rate limits, etc.)
- Token validation, error response parsing, automatic retries

**Key exports**:
- `SlackAPIClient(token: str)` — Constructor
- `client.post(method: str, data: dict) -> dict` — Make API call
- `SlackAPIError` — Exception for API failures

**Example**:
```python
client = SlackAPIClient(token)
response = await client.post("chat.postMessage", {
    "channel": "#general",
    "text": "Hello"
})
```

#### `_pagination.py` — Pagination Helper

**Responsibilities**:
- `paginate()` async generator: Handle cursor-based pagination
- Fetch all results across multiple API calls automatically

**Key exports**:
- `paginate(client, method, data, key)` — Iterate through paginated results

**Example**:
```python
async for batch in paginate(client, "users.list", {}, "members"):
    for user in batch:
        print(user["name"])
```

#### `channels.py` — Channel Operations (8 tools)

**Provides**:
- `list_channels(token)` — List all channels
- `get_channel_info(token, channel)` — Get channel details
- `create_channel(token, name, is_private)` — Create channel
- `archive_channel(token, channel)` — Archive channel
- `invite_to_channel(token, channel, users)` — Add members
- `kick_from_channel(token, channel, user)` — Remove member
- `join_channel(token, channel)` — Join channel
- `set_channel_topic(token, channel, topic)` — Update topic

**Dependencies**: `_client.py`

#### `messages.py` — Message Operations (13 tools)

**Provides**:
- `send_message(token, channel, text, blocks, thread_ts)` — Send message
- `send_ephemeral(token, channel, user, text)` — Send ephemeral (visible to one user)
- `update_message(token, channel, ts, text, blocks)` — Edit message
- `delete_message(token, channel, ts)` — Delete message
- `get_permalink(token, channel, message_ts)` — Get message link
- `search_messages(token, query, use_user_token)` — Search (requires user token)
- `list_history(token, channel, limit)` — Fetch channel history
- `add_reaction(token, channel, ts, emoji)` — Add emoji reaction
- `remove_reaction(token, channel, ts, emoji)` — Remove reaction
- `pin_message(token, channel, ts)` — Pin message
- `unpin_message(token, channel, ts)` — Unpin message
- `reply_in_thread(token, channel, thread_ts, text, blocks)` — Reply in thread
- `get_thread_replies(token, channel, thread_ts)` — Fetch thread

**Dependencies**: `_client.py`, `_pagination.py`

#### `users.py` — User Operations (5 tools)

**Provides**:
- `list_users(token)` — List all users
- `get_user_info(token, user_id)` — Get user details
- `get_user_by_email(token, email)` — Look up user by email
- `open_dm(token, users)` — Open DM with user(s)
- `list_user_channels(token, user_id)` — Get user's channels

**Dependencies**: `_client.py`

#### `files.py` — File Operations (5 tools)

**Provides**:
- `upload_file(token, channels, file_path, title, initial_comment)` — Upload file
- `list_files(token, limit)` — List workspace files
- `get_file_info(token, file_id)` — Get file details
- `delete_file(token, file_id)` — Delete file
- `share_file(token, file_id, channels)` — Share existing file

**Dependencies**: `_client.py`

#### `workspace.py` — Workspace Operations (4 tools)

**Provides**:
- `get_workspace_info(token)` — Get team/workspace info
- `list_emojis(token)` — List custom emoji
- `get_bot_info(token)` — Get bot user info
- `auth_test(token)` — Validate token

**Dependencies**: `_client.py`

#### `reminders.py` — Reminder Operations (4 tools)

**Provides**:
- `add_reminder(token, text, time, use_user_token)` — Create reminder
- `list_reminders(token, use_user_token)` — List reminders
- `complete_reminder(token, reminder_id, use_user_token)` — Mark complete
- `delete_reminder(token, reminder_id, use_user_token)` — Delete reminder

**Note**: Requires `SLACK_USER_TOKEN` for some operations (use_user_token=True)

**Dependencies**: `_client.py`

#### `bookmarks.py` — Bookmark Operations (3 tools)

**Provides**:
- `list_bookmarks(token, channel)` — List channel bookmarks
- `add_bookmark(token, channel, title, link, emoji)` — Add bookmark
- `remove_bookmark(token, channel, bookmark_id)` — Remove bookmark

**Dependencies**: `_client.py`

#### `scheduled.py` — Scheduled Message Operations (3 tools)

**Provides**:
- `schedule_message(token, channel, text, post_at, blocks)` — Schedule message
- `list_scheduled_messages(token)` — List pending scheduled messages
- `delete_scheduled_message(token, channel, scheduled_message_id)` — Cancel scheduled

**Dependencies**: `_client.py`

#### `__init__.py` — Public API Exports

Exports all public functions for easy access:
```python
from slack_mpm.api import messages, channels, users, files, ...
```

---

### `src/slack_mpm/auth/` — Authentication & Token Management

#### `models.py` — Data Models

**Defines**:
- `SlackToken(token: str, type: TokenType)` — Token representation
- `TokenStatus(is_valid: bool, workspace_name: str, bot_user_id: str, expires_at: datetime)` — Token validation result
- `WorkspaceInfo(team_id: str, team_name: str, user_id: str)` — Workspace metadata

#### `token_manager.py` — Token Resolution

**Provides**:
- `TokenManager(token_source: str | None = None)` — Load token from environment
  - Priority: explicit `token_source` parameter > `SLACK_BOT_TOKEN` env var > `.env.local` > `.env`
- `get_token()` — Retrieve current token (string)
- `validate_token()` → `TokenStatus` — Check if token works
- Optional `use_user_token` parameter in some API functions (uses `SLACK_USER_TOKEN`)

**Example**:
```python
tm = TokenManager()
token = tm.get_token()  # Loads SLACK_BOT_TOKEN

status = tm.validate_token()
if status.is_valid:
    print(f"Valid in {status.workspace_name}")
```

---

### `src/slack_mpm/cli/` — Command-Line Interface

#### `main.py` — CLI Entry Point

**Commands**:
- `slack-mpm setup` — Verify Slack token and workspace connection
- `slack-mpm doctor` — Health check (token validation, workspace info, bot status)
- `slack-mpm mcp` — Start MCP server for Claude Desktop
- `slack-mpm --help` — Show all commands

**Implementation**:
- Uses Click framework for command parsing
- TokenManager for token resolution
- Integrates with SlackMCPServer

**Example**:
```bash
uv run slack-mpm setup       # Verify token works
uv run slack-mpm mcp         # Start MCP server
```

---

### `src/slack_mpm/server/` — MCP Server Adapter

#### `slack_mcp_server.py` — MCP Protocol Implementation

**Provides**:
- `SlackMCPServer` class: Adapter implementing MCP protocol
- Registers 40+ Slack tools for Claude Desktop
- Wraps API functions as MCP tool definitions

**Responsibilities**:
- Initialize MCP server with stdio transport
- Define tools with input schemas
- Map tool calls to api module functions
- Handle token resolution per request
- Error handling & response formatting

**Architecture**:
```python
class SlackMCPServer:
    def __init__(self):
        self.server = Server("slack-mpm")
        self._register_tools()

    def _register_tools(self):
        # Register messages, channels, users, files, etc. as MCP tools
        self.server.add_tool("send_message", ...)
        ...

    async def handle_request(self, request):
        # Execute tool and return result
        ...
```

**Example tool registration**:
```python
self.server.add_tool(
    "send_message",
    "Send a message to a Slack channel",
    messages.send_message,
    {
        "channel": {"type": "string", "description": "Channel ID or #name"},
        "text": {"type": "string", "description": "Message text"},
    }
)
```

---

## Supporting Modules

### `src/slack_mpm/__version__.py`

Single constant:
```python
__version__ = "0.1.4"
```

Synced from `VERSION` file by `make sync-versions`.

---

## Agent Scripts

Standalone automation tools in `agents/` directory (not installed as package).

| Script | Purpose |
|--------|---------|
| `slack_listener.py` | Poll channel and print new messages |
| `slack_notifier.py` | Send notifications or files to channels |
| `slack_responder.py` | Monitor for @mentions, auto-reply |
| `slack_digest.py` | Generate activity summary (users, threads) |
| `slack_archiver.py` | Export channel history to JSON/Markdown |

Run with:
```bash
uv run agents/slack_listener.py --channel C1234567890
uv run agents/slack_notifier.py --channel C1234567890 --message "Alert!"
```

---

## Test Suite

### Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures (mocks, tokens)
├── api/
│   ├── test_channels.py
│   ├── test_messages.py
│   ├── test_users.py
│   ├── test_files.py
│   ├── test_workspace.py
│   ├── test_reminders.py
│   ├── test_bookmarks.py
│   ├── test_scheduled.py
│   └── test_client.py
├── auth/
│   ├── test_token_manager.py
│   └── test_models.py
├── cli/
│   └── test_main.py
└── server/
    └── test_slack_mcp_server.py
```

### Testing Guidelines

- Use `@pytest.mark.asyncio` or `async def test_*()`
- Mock `SlackAPIClient` for unit tests
- Use fixtures from `conftest.py` (mock_token, mock_client)
- Test both success and error paths

---

## Data Flow Examples

### Sending a Message (API path)

```
User Code
  ↓
slack_mpm.api.messages.send_message(token, channel, text)
  ↓
_client.SlackAPIClient(token).post("chat.postMessage", {...})
  ↓
httpx.AsyncClient.post(https://slack.com/api/chat.postMessage)
  ↓
Slack API
  ↓
{ok: true, ts: "1234567890.123456"}
  ↓
Returns to User Code
```

### Using via MCP Server (Claude Desktop path)

```
Claude Desktop
  ↓
send_message tool call → MCP protocol
  ↓
slack-mpm mcp server
  ↓
slack_mpm.server.slack_mcp_server.SlackMCPServer._handle_tool_call()
  ↓
slack_mpm.api.messages.send_message(...)
  ↓
_client.SlackAPIClient.post(...)
  ↓
Slack API
  ↓
Response → MCP protocol → Claude Desktop
```

---

## Key Design Decisions

### Async/Await First
All API calls are async to enable concurrent operations and integration with async frameworks.

### Dependency Injection
`TokenManager` is passed explicitly (not global), enabling multi-token scenarios and testability.

### Separated Concerns
- **api/**: Slack API wrapping (no UI, no CLI)
- **auth/**: Token resolution (no API calls)
- **cli/**: Command-line interface (uses api + auth)
- **server/**: MCP adapter (uses api + auth)

### Type Safety
Full type hints + mypy strict mode prevent runtime errors.

### Error Handling
`SlackAPIError` wraps HTTP errors with detailed messaging for easier debugging.

---

## Adding New Functionality

### New API Wrapper
1. Create `src/slack_mpm/api/domain.py` with async functions
2. Export in `src/slack_mpm/api/__init__.py`
3. Register in `src/slack_mpm/server/slack_mcp_server.py`
4. Write tests in `tests/api/test_domain.py`

### New CLI Command
1. Add function to `src/slack_mpm/cli/main.py`
2. Decorate with `@click.command()`
3. Test with `uv run slack-mpm command-name`

### New Agent Script
1. Create `agents/my_script.py`
2. Use TokenManager and api modules
3. Run with `uv run agents/my_script.py`

---

## Dependencies

See `pyproject.toml` for exact versions:
- **mcp>=1.3.1** — Model Context Protocol
- **click>=8.1.0** — CLI framework
- **pydantic>=2.10.5** — Data validation
- **httpx>=0.28.1** — Async HTTP client
- **python-dotenv>=1.0.0** — Load .env files
- **anyio>=4.0.0** — Async compatibility layer

Dev dependencies:
- **pytest>=8.0.0** — Testing framework
- **pytest-asyncio>=0.23.0** — Async test support
- **pytest-cov>=4.0.0** — Coverage reports
- **ruff>=0.9.0** — Linter & formatter
- **mypy>=1.13.0** — Type checker
- **twine>=6.0.0** — PyPI upload

---

## Performance Considerations

- **Pagination**: `_pagination.py` handles Slack's 200-item default limit
- **Rate Limiting**: `_client.py` implements exponential backoff for 429 responses
- **Connection Pooling**: httpx client is shared across requests
- **Async Concurrency**: Multiple API calls can run concurrently with asyncio

---

See [DEVELOPER.md](/Users/masa/Projects/slack-mpm/DEVELOPER.md) for development workflow.
