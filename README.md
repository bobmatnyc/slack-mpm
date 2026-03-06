# slack-mpm

A Python MCP (Model Context Protocol) server and API library for Slack workspace integration. Exposes 40+ Slack operations as MCP tools for use with Claude Desktop, and provides a clean async Python API for building Slack integrations.

## What It Is

- **Python API library**: `from slack_mpm.api import messages; await messages.send_message(...)`
- **MCP server**: wraps the API for Claude Desktop via `slack-mpm mcp`
- **Agent scripts**: standalone automation scripts in `agents/`

## Prerequisites

1. **Python 3.10+** and [uv](https://docs.astral.sh/uv/)
2. A **Slack App** with a bot token

### Creating a Slack App

1. Go to [https://api.slack.com/apps](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch", give it a name and select your workspace
3. Go to "OAuth & Permissions" and add these Bot Token Scopes:
   - `channels:read`, `channels:write`, `channels:manage`
   - `chat:write`, `chat:write.public`
   - `users:read`
   - `files:read`, `files:write`
   - `reactions:write`
   - `pins:write`
   - `bookmarks:read`, `bookmarks:write`
   - `emoji:read`
   - `groups:read`, `groups:write`
   - `im:read`, `im:write`
   - `mpim:read`, `mpim:write`
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

For `search_messages` and reminders, also create a User Token with `search:read`, `reminders:read`, `reminders:write`.

## Quick Start

```bash
git clone <repo>
cd slack-mpm
cp .env.local.example .env.local
# Edit .env.local and add your SLACK_BOT_TOKEN=xoxb-...

uv sync
uv run slack-mpm setup   # Verify your token works
uv run slack-mpm doctor  # Health check
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "slack": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/slack-mpm", "slack-mpm", "mcp"]
    }
  }
}
```

Restart Claude Desktop. You should see the Slack tools available.

## Available Tools

### Channel Tools (8)

| Tool | Description |
|------|-------------|
| `list_channels` | List all channels (public + private) |
| `get_channel_info` | Get details about a channel |
| `create_channel` | Create a new channel |
| `archive_channel` | Archive a channel |
| `invite_to_channel` | Invite users to a channel |
| `kick_from_channel` | Remove a user from a channel |
| `join_channel` | Join a channel |
| `set_channel_topic` | Set channel topic |

### Message Tools (13)

| Tool | Description |
|------|-------------|
| `send_message` | Send a message (supports blocks + threading) |
| `send_ephemeral` | Send a message visible only to one user |
| `update_message` | Edit an existing message |
| `delete_message` | Delete a message |
| `get_permalink` | Get a permanent link to a message |
| `search_messages` | Search messages (requires user token) |
| `list_history` | Fetch channel message history |
| `add_reaction` | Add emoji reaction |
| `remove_reaction` | Remove emoji reaction |
| `pin_message` | Pin a message |
| `unpin_message` | Unpin a message |
| `reply_in_thread` | Reply in a thread |
| `get_thread_replies` | Fetch all thread replies |

### User Tools (5)

| Tool | Description |
|------|-------------|
| `list_users` | List all workspace users |
| `get_user_info` | Get user details |
| `get_user_by_email` | Look up a user by email |
| `open_dm` | Open a DM channel with user(s) |
| `list_user_channels` | List channels a user belongs to |

### File Tools (5)

| Tool | Description |
|------|-------------|
| `upload_file` | Upload a file to channel(s) |
| `list_files` | List workspace files |
| `get_file_info` | Get file details |
| `delete_file` | Delete a file |
| `share_file` | Share an existing file to channels |

### Workspace Tools (4)

| Tool | Description |
|------|-------------|
| `get_workspace_info` | Get workspace/team info |
| `list_emojis` | List custom emoji |
| `get_bot_info` | Get bot details |
| `auth_test` | Validate token |

### Reminder Tools (4)

| Tool | Description |
|------|-------------|
| `add_reminder` | Create a reminder |
| `list_reminders` | List reminders |
| `complete_reminder` | Mark reminder complete |
| `delete_reminder` | Delete a reminder |

### Bookmark Tools (3)

| Tool | Description |
|------|-------------|
| `list_bookmarks` | List channel bookmarks |
| `add_bookmark` | Add a bookmark to a channel |
| `remove_bookmark` | Remove a bookmark |

### Scheduled Message Tools (3)

| Tool | Description |
|------|-------------|
| `schedule_message` | Schedule a future message |
| `list_scheduled_messages` | List pending scheduled messages |
| `delete_scheduled_message` | Cancel a scheduled message |

## Using the Python API Directly

```python
import asyncio
from slack_mpm.api import messages, channels, users
from slack_mpm.auth.token_manager import TokenManager

async def main():
    token = TokenManager().get_token()

    # Send a message
    await messages.send_message(token, "#general", "Hello from Python!")

    # List channels
    data = await channels.list_channels(token)
    for ch in data["channels"]:
        print(ch["name"])

    # Get user info
    user = await users.get_user_by_email(token, "person@example.com")
    print(user["user"]["real_name"])

asyncio.run(main())
```

## Agent Scripts

Standalone automation scripts in the `agents/` directory.

### `slack_listener.py` — Real-time channel monitor

Polls a channel and prints new messages as they arrive.

```bash
uv run agents/slack_listener.py --channel C1234567890
uv run agents/slack_listener.py --channel C1234567890 --interval 10
uv run agents/slack_listener.py --channel C1234567890 --no-history
```

### `slack_notifier.py` — Send notifications

Sends messages or file uploads to Slack channels from the command line or stdin.

```bash
uv run agents/slack_notifier.py --channel C1234567890 --message "Deploy complete"
echo "alert!" | uv run agents/slack_notifier.py --channel C1234567890
cat report.txt | uv run agents/slack_notifier.py --channel C1234567890 --as-file --filename report.txt
```

### `slack_responder.py` — Auto-responder bot

Monitors for @mentions or DMs and auto-replies with a configured message.

```bash
uv run agents/slack_responder.py --response "Thanks, I'll get back to you!"
uv run agents/slack_responder.py --channel C1234567890 --response "Got it!" --interval 60
uv run agents/slack_responder.py --response "Out of office" --dry-run
```

### `slack_digest.py` — Activity digest

Generates a summary of recent channel activity: message counts, active users, top threads.

```bash
uv run agents/slack_digest.py --channel C1234567890
uv run agents/slack_digest.py --channel C1234567890 --hours 168  # 1 week
uv run agents/slack_digest.py --channel C1234567890 --hours 24 --top-users 10
```

### `slack_archiver.py` — Channel history export

Exports complete channel message history to JSON or Markdown files with thread support.

```bash
uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/
uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --format markdown
uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --days 30
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest
uv run pytest --cov=src --cov-report=html

# Type checking
uv run mypy --strict src/

# Linting
uv run ruff check src/ agents/
uv run ruff format src/ agents/
```

## Project Structure

```
src/slack_mpm/
├── api/
│   ├── _client.py      # Shared httpx client + SlackAPIError
│   ├── channels.py     # Channel operations
│   ├── messages.py     # Message operations
│   ├── users.py        # User operations
│   ├── files.py        # File operations
│   ├── workspace.py    # Workspace operations
│   ├── reminders.py    # Reminder operations
│   ├── bookmarks.py    # Bookmark operations
│   └── scheduled.py    # Scheduled message operations
├── auth/
│   ├── models.py       # SlackToken, TokenStatus, WorkspaceInfo
│   └── token_manager.py # TokenManager (loads from .env.local)
├── cli/
│   └── main.py         # CLI: setup, doctor, mcp commands
└── server/
    └── slack_mpm_server.py  # SlackMCPServer (MCP adapter)

agents/
├── slack_listener.py   # Channel message poller
├── slack_notifier.py   # Send notifications
├── slack_responder.py  # Auto-responder bot
├── slack_digest.py     # Activity digest
└── slack_archiver.py   # History export
```
