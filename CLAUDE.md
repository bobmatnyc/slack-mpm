# Slack MCP - Project Context

## What This Is
Python MCP server + API library for Slack workspace integration.
Provides:
1. Clean Python API: `from slack_mcp.api import messages; await messages.send_message(...)`
2. MCP server: wraps the API for Claude Desktop (`uv run slack-mcp mcp`)
3. Agent scripts: standalone Python scripts in `agents/`

## Setup
```bash
cp .env.local.example .env.local
# Add SLACK_BOT_TOKEN=xoxb-...
uv sync
```

## Run
```bash
uv run slack-mcp setup    # verify tokens
uv run slack-mcp doctor   # health check
uv run slack-mcp mcp      # start MCP server (for Claude Desktop)
```

## Test
```bash
uv run pytest
uv run pytest --cov=src --cov-report=html
```

## Architecture
```
src/slack_mcp/
├── api/          # Pure Slack API functions (library layer)
│   ├── _client.py      # Shared httpx client + SlackAPIError
│   ├── channels.py     # 8 channel operations
│   ├── messages.py     # 13 message operations
│   ├── users.py        # 5 user operations
│   ├── files.py        # 5 file operations
│   ├── workspace.py    # 4 workspace operations
│   ├── reminders.py    # 4 reminder operations
│   ├── bookmarks.py    # 3 bookmark operations
│   └── scheduled.py    # 3 scheduled message operations
├── auth/         # Token management from .env/.env.local
├── cli/          # Click CLI commands
└── server/       # Thin MCP adapter over api/

agents/           # Standalone Python agent scripts
```

## Claude Desktop Config
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "slack": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/slack-mcp", "slack-mcp", "mcp"]
    }
  }
}
```

## Key APIs Used
- `conversations.list / info / create / invite / kick / join / setTopic`
- `chat.postMessage / postEphemeral / update / delete / scheduleMessage`
- `chat.getPermalink / scheduledMessages.list / deleteScheduledMessage`
- `reactions.add / remove`
- `pins.add / remove`
- `conversations.history / replies`
- `users.list / info / lookupByEmail / conversations`
- `files.getUploadURLExternal / completeUploadExternal / list / info / delete`
- `reminders.add / list / complete / delete`
- `bookmarks.list / add / remove`
- `auth.test / team.info / emoji.list / bots.info`
- `search.messages` (user token required)

## Token Scopes Needed
### Bot Token (xoxb-)
`channels:read`, `channels:write`, `channels:manage`, `chat:write`,
`users:read`, `files:read`, `files:write`, `reactions:write`, `pins:write`,
`bookmarks:read`, `bookmarks:write`, `emoji:read`, `groups:read`, `groups:write`,
`im:read`, `im:write`, `mpim:read`, `mpim:write`

### User Token (xoxp-, optional)
`search:read`, `reminders:read`, `reminders:write`
