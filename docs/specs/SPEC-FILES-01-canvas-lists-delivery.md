# SPEC-FILES-01: Full Slack File-Type Support — Canvas, Lists, and Document-Content Delivery

**Status**: Design Review  
**Date**: 2026-06-23  
**Author**: Claude Code  
**Scope**: Extend file delivery API to support Canvas, Lists, and markdown-to-document-type conversion

---

## Executive Summary

This specification defines a comprehensive feature to deliver content to three Slack content types beyond traditional file uploads:

1. **Canvas**: Create, edit, and share workspace and channel-attached canvases with markdown content
2. **Lists**: Create and manage Slack Lists (paid plan feature) with markdown-to-list conversion
3. **Document Content Delivery**: Convert markdown to Canvas and List structures without needing external transcoding tools

The feature enables seamless document-to-Slack delivery workflows (e.g., "convert this markdown report to a Canvas in #announcements") while maintaining backward compatibility with existing file upload APIs.

---

## Scope

### In Scope

- **Workspace-level Canvas** (via `canvases.create`): Standalone canvases in the workspace
- **Channel-attached Canvas** (via `conversations.canvases.create`): Canvases pinned to a channel
- **Lists** (via `slackLists.*`): Create, update, delete, and manage list items with markdown parsing
- **Content Conversion**: Markdown → Canvas (passthrough + validation), Markdown → List (structured parsing)
- **File Upload Enhancement**: Binary file support, `thread_ts` parameter, multi-channel sharing via `files.completeUploadExternal`
- **MCP Tool Registration**: All new functions exposed as MCP tools in `slack_mcp_server.py`
- **Access Control**: Set/delete access rules for Canvas and Lists (manage who can view/edit)
- **Error Handling**: `ContentConversionError` for transformation failures, `SlackAPIError` for API errors
- **Markdown Parsing**: Lightweight pure-Python parser (no system binaries)

### Out of Scope

- **Image/Audio/Video Transcoding**: No Pillow, ffmpeg, LibreOffice, or media processing
- **Scheduled Delivery**: No "deliver at a future time" — all operations are on-demand only
- **List Column Schema Reading**: Slack API does not provide a documented method; document as limitation
- **Advanced Canvas Formatting**: Support markdown only; Block Kit / rich formatting deferred
- **Webhook Delivery**: No push-based workflows (only request/response)

---

## Requirements & IDs

### A. File Upload Enhancements (FILES-01-R1 through FILES-01-R4)

#### FILES-01-R1: Binary Content + File Path Support
**Requirement**: `upload_file()` must accept content as `str | bytes` AND optionally read from disk.

**API Change**:
```python
async def upload_file(
    token: str,
    channels: list[str],
    content: str | bytes | None = None,
    file_path: str | None = None,
    filename: str,
    title: str | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    """
    Upload a file (binary or text) to channels.
    
    Either `content` or `file_path` must be provided (not both).
    
    Args:
        token: Slack bot token
        channels: List of channel IDs (max 100 per API limit)
        content: File content as str or bytes. If None, read from file_path.
        file_path: Path to file on disk. Reads as binary. Mutually exclusive with content.
        filename: Name for the uploaded file
        title: Optional display title
        thread_ts: Optional thread timestamp to attach upload to a thread
    
    Returns:
        Dict with 'files' list containing uploaded file objects
    
    Raises:
        SlackAPIError: On API errors or plan/permission failures
        FileNotFoundError: If file_path does not exist
        ValueError: If neither content nor file_path is provided, or both are provided
    """
```

**Backward Compatibility**: Existing code using `upload_file(token, channels, content_str, filename)` continues to work.

**Acceptance Criteria**:
- `upload_file()` accepts `content: str` (existing)
- `upload_file()` accepts `content: bytes` (new)
- `upload_file()` accepts `file_path: str` (new) and reads file as binary
- Raises `ValueError` if both `content` and `file_path` are provided
- Raises `ValueError` if neither are provided
- `thread_ts` parameter is optional and passed to `files.completeUploadExternal`
- Tests verify both string and bytes content work
- Tests verify file_path reading works for binary files

#### FILES-01-R2: Multi-Channel Sharing via `files.completeUploadExternal`
**Requirement**: When sharing to multiple channels, use `files.completeUploadExternal` with the `channels` parameter (up to 100 channels) instead of looping over `chat.postMessage`.

**API Change**: Refactor the 3-step upload flow (already implemented) to use `channels` array in `completeUploadExternal`.

**Current Implementation Issue**: Line 67-81 in `files.py` loops over `channels[1:]` with per-channel `chat.postMessage` calls. This is inefficient and non-atomic.

**New Implementation**:
```python
# Step 3: Complete upload with all channels at once
complete_payload: dict[str, Any] = {
    "files": [{"id": file_id, "title": title or filename}],
    "channels": channels,  # Pass all channels, max 100
}
result = await slack_post(token, "files.completeUploadExternal", complete_payload)
```

**Acceptance Criteria**:
- Single `files.completeUploadExternal` call handles all channels (≤100)
- No per-channel `chat.postMessage` loop
- Gracefully handle >100 channels by batching (error or split into multiple uploads)
- Tests verify multi-channel sharing with single API call
- No regression for single-channel uploads

#### FILES-01-R3: Modern 3-Step Upload Preserved
**Requirement**: Preserve existing `getUploadURLExternal` → `POST` → `completeUploadExternal` flow (already implemented; no API changes).

**Acceptance Criteria**:
- `getUploadURLExternal` call to fetch upload URL and file ID
- Direct HTTP POST to provided URL with file bytes
- `completeUploadExternal` call to register upload
- Tests verify all three steps execute in order

#### FILES-01-R4: Legacy `files.upload` Sunset
**Requirement**: Document that `files.upload` is deprecated (Slack sunset Nov 2025); do not use it.

**Acceptance Criteria**:
- No calls to `files.upload` in the codebase
- Comment in `files.py` explaining the 3-step flow is required

---

### B. Canvas Support (CANVAS-01-R1 through CANVAS-01-R7)

**Required Scopes**: `canvases:read`, `canvases:write`

#### CANVAS-01-R1: Create Workspace Canvas
**Requirement**: `create_canvas()` creates a standalone canvas in the workspace.

**API**:
```python
async def create_canvas(
    token: str,
    title: str,
    document_content: str,  # Markdown
) -> dict[str, Any]:
    """
    Create a workspace-level canvas.
    
    Args:
        token: Slack bot token (requires canvases:write)
        title: Canvas title
        document_content: Markdown content for the canvas
    
    Returns:
        Dict with 'canvas_id', 'is_empty', 'created_at'
    
    Raises:
        SlackAPIError: On API errors or insufficient permissions
    """
    # Endpoint: canvases.create
```

**Slack Endpoint**: `canvases.create`

**Acceptance Criteria**:
- Calls `canvases.create` with title and document_content
- Returns canvas_id from response
- Tests verify canvas creation with markdown content

#### CANVAS-01-R2: Create Channel Canvas
**Requirement**: `create_channel_canvas()` creates a canvas attached to a channel.

**API**:
```python
async def create_channel_canvas(
    token: str,
    channel: str,
    title: str,
    document_content: str,  # Markdown
) -> dict[str, Any]:
    """
    Create a channel-attached canvas.
    
    Args:
        token: Slack bot token (requires canvases:write)
        channel: Channel ID to attach the canvas to
        title: Canvas title
        document_content: Markdown content for the canvas
    
    Returns:
        Dict with 'canvas_id', 'is_empty', 'created_at'
    
    Raises:
        SlackAPIError: On API errors, channel not found, or insufficient permissions
    """
    # Endpoint: conversations.canvases.create
```

**Slack Endpoint**: `conversations.canvases.create`

**Acceptance Criteria**:
- Calls `conversations.canvases.create` with channel, title, document_content
- Returns canvas_id
- Tests verify channel canvas creation

#### CANVAS-01-R3: Edit Canvas
**Requirement**: `edit_canvas()` updates the content of an existing canvas.

**API**:
```python
async def edit_canvas(
    token: str,
    canvas_id: str,
    document_content: str,  # Markdown
    operation_id: str | None = None,
) -> dict[str, Any]:
    """
    Edit an existing canvas.
    
    Args:
        token: Slack bot token (requires canvases:write)
        canvas_id: Canvas ID to edit
        document_content: New markdown content
        operation_id: Optional idempotency key for the edit
    
    Returns:
        Dict with 'canvas_id' and operation metadata
    
    Raises:
        SlackAPIError: On API errors or canvas not found
    """
    # Endpoint: canvases.edit
```

**Slack Endpoint**: `canvases.edit`

**Acceptance Criteria**:
- Calls `canvases.edit` with canvas_id and document_content
- operation_id optional (for idempotency)
- Tests verify canvas update

#### CANVAS-01-R4: Delete Canvas
**Requirement**: `delete_canvas()` removes a canvas.

**API**:
```python
async def delete_canvas(token: str, canvas_id: str) -> dict[str, Any]:
    """Delete a canvas."""
    # Endpoint: canvases.delete
```

**Slack Endpoint**: `canvases.delete`

**Acceptance Criteria**:
- Calls `canvases.delete`
- Returns ok=true on success
- Tests verify deletion

#### CANVAS-01-R5: Set Canvas Access
**Requirement**: `set_canvas_access()` grants/updates access for users/groups to a canvas.

**API**:
```python
async def set_canvas_access(
    token: str,
    canvas_id: str,
    access_level: str,  # "read", "write", "owner"
    user_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Set access rules for a canvas.
    
    Args:
        token: Slack bot token
        canvas_id: Canvas ID
        access_level: "read", "write", or "owner"
        user_ids: List of user IDs to grant access to
        group_ids: List of group IDs to grant access to
    
    Returns:
        Dict with access control details
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: canvases.access.set
```

**Slack Endpoint**: `canvases.access.set`

**Acceptance Criteria**:
- Calls `canvases.access.set`
- Supports user_ids and/or group_ids
- Tests verify access is set

#### CANVAS-01-R6: Delete Canvas Access
**Requirement**: `delete_canvas_access()` revokes access for a user/group.

**API**:
```python
async def delete_canvas_access(
    token: str,
    canvas_id: str,
    user_id: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """
    Revoke access to a canvas.
    
    Args:
        token: Slack bot token
        canvas_id: Canvas ID
        user_id: User ID to revoke access for
        group_id: Group ID to revoke access for
    
    Returns:
        Dict with ok=true
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: canvases.access.delete
```

**Slack Endpoint**: `canvases.access.delete`

**Acceptance Criteria**:
- Calls `canvases.access.delete`
- Supports user_id or group_id (or both)
- Tests verify access is revoked

#### CANVAS-01-R7: Lookup Canvas Sections
**Requirement**: `lookup_canvas_sections()` lists sections/blocks within a canvas for navigation.

**API**:
```python
async def lookup_canvas_sections(
    token: str,
    canvas_id: str,
) -> dict[str, Any]:
    """
    Look up sections/blocks in a canvas.
    
    Returns:
        Dict with 'sections' list (headings, metadata)
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: canvases.sections.lookup
```

**Slack Endpoint**: `canvases.sections.lookup`

**Acceptance Criteria**:
- Calls `canvases.sections.lookup`
- Returns sections metadata
- Tests verify section lookup

---

### C. Lists Support (LISTS-01-R1 through LISTS-01-R9)

**Required Scopes**: `lists:read`, `lists:write`  
**Limitation**: Slack API does not provide a documented method to read list column schema; workaround: accept column names as input parameters when creating/updating.

#### LISTS-01-R1: Create List
**Requirement**: `create_list()` creates a new List in a channel.

**API**:
```python
async def create_list(
    token: str,
    channel: str,
    name: str,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Create a new List in a channel.
    
    Args:
        token: Slack bot token (requires lists:write)
        channel: Channel ID to create the list in
        name: List name
        items: Optional initial list items (each is a dict with key-value pairs)
    
    Returns:
        Dict with 'list_id', 'name', 'channel_id'
    
    Raises:
        SlackAPIError: On API errors, channel not found, or plan/permission failures
    """
    # Endpoint: slackLists.create
```

**Slack Endpoint**: `slackLists.create`

**Acceptance Criteria**:
- Calls `slackLists.create`
- Creates list in the specified channel
- Optional initial items
- Returns list_id
- Tests verify list creation

#### LISTS-01-R2: Update List
**Requirement**: `update_list()` updates list metadata (name, description).

**API**:
```python
async def update_list(
    token: str,
    list_id: str,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """
    Update a list's metadata.
    
    Args:
        token: Slack bot token
        list_id: List ID to update
        name: New list name (optional)
        description: New list description (optional)
    
    Returns:
        Dict with updated list metadata
    
    Raises:
        SlackAPIError: On API errors or list not found
    """
    # Endpoint: slackLists.update
```

**Slack Endpoint**: `slackLists.update`

**Acceptance Criteria**:
- Calls `slackLists.update`
- Updates name and/or description
- Tests verify list update

#### LISTS-01-R3: Create List Item
**Requirement**: `create_list_item()` adds a single item to a list.

**API**:
```python
async def create_list_item(
    token: str,
    list_id: str,
    value: str,
    status: str | None = None,  # "incomplete", "complete", etc.
) -> dict[str, Any]:
    """
    Create a new item in a list.
    
    Args:
        token: Slack bot token
        list_id: List ID
        value: Item text/value
        status: Optional status (e.g., "incomplete", "complete" for checkboxes)
    
    Returns:
        Dict with 'item_id', 'value', 'status'
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: slackLists.items.create
```

**Slack Endpoint**: `slackLists.items.create`

**Acceptance Criteria**:
- Calls `slackLists.items.create`
- Creates item with value and optional status
- Returns item_id
- Tests verify item creation

#### LISTS-01-R4: Update List Item
**Requirement**: `update_list_item()` updates an existing list item.

**API**:
```python
async def update_list_item(
    token: str,
    list_id: str,
    item_id: str,
    value: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """
    Update a list item.
    
    Args:
        token: Slack bot token
        list_id: List ID
        item_id: Item ID to update
        value: New item text (optional)
        status: New status (optional)
    
    Returns:
        Dict with updated item metadata
    
    Raises:
        SlackAPIError: On API errors or item not found
    """
    # Endpoint: slackLists.items.update
```

**Slack Endpoint**: `slackLists.items.update`

**Acceptance Criteria**:
- Calls `slackLists.items.update`
- Updates value and/or status
- Tests verify item update

#### LISTS-01-R5: Delete Single List Item
**Requirement**: `delete_list_item()` removes a single item from a list.

**API**:
```python
async def delete_list_item(
    token: str,
    list_id: str,
    item_id: str,
) -> dict[str, Any]:
    """Delete a single list item."""
    # Endpoint: slackLists.items.delete
```

**Slack Endpoint**: `slackLists.items.delete`

**Acceptance Criteria**:
- Calls `slackLists.items.delete`
- Returns ok=true
- Tests verify item deletion

#### LISTS-01-R6: Delete Multiple List Items
**Requirement**: `delete_list_items()` removes multiple items in a single call.

**API**:
```python
async def delete_list_items(
    token: str,
    list_id: str,
    item_ids: list[str],
) -> dict[str, Any]:
    """
    Delete multiple list items.
    
    Args:
        token: Slack bot token
        list_id: List ID
        item_ids: List of item IDs to delete
    
    Returns:
        Dict with deletion results
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: slackLists.items.deleteMultiple
```

**Slack Endpoint**: `slackLists.items.deleteMultiple`

**Acceptance Criteria**:
- Calls `slackLists.items.deleteMultiple`
- Deletes multiple items in one call
- Tests verify batch deletion

#### LISTS-01-R7: List List Items (Paginated)
**Requirement**: `list_list_items()` fetches all items in a list with pagination.

**API**:
```python
async def list_list_items(
    token: str,
    list_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """
    Fetch items from a list (paginated).
    
    Args:
        token: Slack bot token
        list_id: List ID
        limit: Max items per page (default 100)
    
    Returns:
        Dict with 'items' list and 'paging' info
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: slackLists.items.list (use _pagination.paginate helper)
```

**Slack Endpoint**: `slackLists.items.list`

**Acceptance Criteria**:
- Uses `paginate()` helper from `_pagination.py`
- Returns all items across pages
- Tests verify pagination works

#### LISTS-01-R8: Get Single List Item
**Requirement**: `get_list_item()` fetches details for a single item.

**API**:
```python
async def get_list_item(
    token: str,
    list_id: str,
    item_id: str,
) -> dict[str, Any]:
    """
    Get details for a single list item.
    
    Args:
        token: Slack bot token
        list_id: List ID
        item_id: Item ID
    
    Returns:
        Dict with 'item' object containing value, status, metadata
    
    Raises:
        SlackAPIError: On API errors
    """
    # Endpoint: slackLists.items.info
```

**Slack Endpoint**: `slackLists.items.info`

**Acceptance Criteria**:
- Calls `slackLists.items.info`
- Returns item details
- Tests verify item fetch

#### LISTS-01-R9: List Access Control (set & delete)
**Requirement**: `set_list_access()` and `delete_list_access()` manage who can view/edit a list.

**API**:
```python
async def set_list_access(
    token: str,
    list_id: str,
    access_level: str,  # "read", "write", "owner"
    user_ids: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Set access rules for a list."""
    # Endpoint: slackLists.access.set

async def delete_list_access(
    token: str,
    list_id: str,
    user_id: str | None = None,
    group_id: str | None = None,
) -> dict[str, Any]:
    """Revoke access to a list."""
    # Endpoint: slackLists.access.delete
```

**Slack Endpoints**: `slackLists.access.set`, `slackLists.access.delete`

**Acceptance Criteria**:
- Both functions work analogously to Canvas access control
- Tests verify access set and revoked

---

### D. Content Conversion Layer (CONVERT-01-R1 through CONVERT-01-R3)

**Location**: New module `src/slack_mpm/content/` (pure Python, no system binaries)

#### CONVERT-01-R1: Markdown to Canvas
**Requirement**: `markdown_to_canvas()` accepts markdown and prepares it for canvas creation.

**API**:
```python
from slack_mpm.content import markdown_to_canvas

async def markdown_to_canvas(
    content: str | None = None,
    file_path: str | None = None,
) -> str:
    """
    Convert markdown to canvas document_content.
    
    Since Canvas natively accepts markdown, this function:
    1. Reads content from file_path if provided
    2. Validates markdown syntax
    3. Returns content ready for canvas.create()
    
    Args:
        content: Markdown string
        file_path: Path to .md file (read as UTF-8)
    
    Returns:
        Validated markdown string suitable for canvas creation
    
    Raises:
        ContentConversionError: On invalid markdown or file read errors
        FileNotFoundError: If file_path does not exist
        ValueError: If neither content nor file_path provided
    """
```

**Mapping Rules**:
- Markdown headings → Canvas headings (passthrough)
- Code blocks → Canvas code blocks (passthrough)
- Lists and emphasis → Canvas native formatting (passthrough)

**Acceptance Criteria**:
- Reads markdown from string or file
- Validates markdown (basic syntax check)
- Returns content suitable for `create_canvas()`
- Raises `ContentConversionError` on invalid input
- Tests verify file reading and validation

#### CONVERT-01-R2: Markdown to List
**Requirement**: `markdown_to_list()` parses markdown structures into Slack list items.

**API**:
```python
from slack_mpm.content import markdown_to_list

async def markdown_to_list(
    content: str | None = None,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Convert markdown to list items.
    
    Parsing rules:
    - Markdown table (pipe-delimited) → List with columns from header
    - Checklist items (- [ ]) → List items with status="incomplete"
    - Checked items (- [x]) → List items with status="complete"
    - Bullet lists (- item) → List items with no status
    - Lines starting with # (headings) → Ignored (metadata only)
    
    Args:
        content: Markdown string
        file_path: Path to .md file
    
    Returns:
        List of dicts, each with 'value' and optional 'status'
        Example: [
            {"value": "Task 1", "status": "incomplete"},
            {"value": "Task 2", "status": "complete"},
            {"value": "Regular item"}
        ]
    
    Raises:
        ContentConversionError: On parsing errors
        FileNotFoundError: If file_path does not exist
        ValueError: If neither content nor file_path provided
    """
```

**Mapping Rules**:
| Markdown | List Item | Status |
|----------|-----------|--------|
| `- [ ] Task` | "Task" | "incomplete" |
| `- [x] Done` | "Done" | "complete" |
| `- Regular` | "Regular" | None |
| Table row | Row values joined | None |

**Acceptance Criteria**:
- Parses checklist syntax (`- [ ]`, `- [x]`)
- Extracts checklist status to list item status
- Parses markdown tables as columns/items
- Parses bullet lists as simple items
- Returns list of dicts with 'value' and optional 'status'
- Raises `ContentConversionError` on invalid syntax
- Tests verify all mapping rules

#### CONVERT-01-R3: Error Handling
**Requirement**: New `ContentConversionError` exception for content transformation failures.

**API**:
```python
class ContentConversionError(Exception):
    """Raised when markdown conversion fails."""
    def __init__(self, message: str, original_error: Exception | None = None):
        self.message = message
        self.original_error = original_error
        super().__init__(message)
```

**Acceptance Criteria**:
- New exception class in `src/slack_mpm/content/__init__.py`
- Wraps parsing/validation errors with descriptive messages
- Tests verify exception is raised on invalid input

---

### E. MCP Tool Registration (MCP-01-R1)

#### MCP-01-R1: Register Canvas, Lists, and Conversion Tools
**Requirement**: Expose all new API functions as MCP tools in `slack_mcp_server.py`.

**Changes to `slack_mcp_server.py`**:
1. Import new modules:
   ```python
   from slack_mpm.api import canvases, lists
   from slack_mpm.content import markdown_to_canvas, markdown_to_list
   ```
2. Add Canvas tools to `SLACK_TOOLS` list:
   - `create_canvas`, `create_channel_canvas`, `edit_canvas`, `delete_canvas`
   - `set_canvas_access`, `delete_canvas_access`, `lookup_canvas_sections`
3. Add List tools to `SLACK_TOOLS` list:
   - `create_list`, `update_list`, `create_list_item`, `update_list_item`
   - `delete_list_item`, `delete_list_items`, `list_list_items`, `get_list_item`
   - `set_list_access`, `delete_list_access`
4. Add conversion tools to `SLACK_TOOLS` list:
   - `markdown_to_canvas` (takes `content` or `file_path`, returns markdown)
   - `markdown_to_list` (takes `content` or `file_path`, returns list items)
5. Update `_dispatch_tool()` handlers dict with dispatch lambdas for all new tools

**Acceptance Criteria**:
- All Canvas functions registered as MCP tools with proper input schemas
- All List functions registered as MCP tools with proper input schemas
- Conversion tools registered with `content` and `file_path` parameters
- Tool definitions include descriptions and required/optional fields
- Tests verify tool dispatch works for each function

---

### F. Documentation & Configuration (DOC-01-R1)

#### DOC-01-R1: Update `.env.local.example`
**Requirement**: Document new required scopes for Canvas and List operations.

**File**: `.env.local.example`

**Changes**:
```bash
# Existing
SLACK_BOT_TOKEN=xoxb-your-token-here

# New scopes required for canvas and list operations
# Bot token must have these scopes:
#   - canvases:read (read canvas content)
#   - canvases:write (create, edit, delete canvases)
#   - lists:read (read lists and items)
#   - lists:write (create, update, delete lists and items)
#   - files:write (upload files via modern 3-step API)
#
# Note: Canvas and List operations require a paid Slack plan.
```

**Acceptance Criteria**:
- Scopes documented in `.env.local.example`
- Paid plan requirement noted
- Scope requirements match API functions

---

## Dependencies

### New Dependency

**Markdown Parser**: One of:
1. `markdown-it-py` (recommended) — CommonMark-compliant, pure Python, lightweight
2. `mistune` — Fast, also pure Python

**Recommendation**: Use `markdown-it-py` for CommonMark compliance and robust parsing.

**pyproject.toml Addition**:
```toml
[project]
dependencies = [
    ...
    "markdown-it-py>=3.0.0",
]
```

**No other external dependencies** — all conversion logic is custom Python.

---

## Architecture & Data Flow

### Module Structure

```
src/slack_mpm/
├── api/
│   ├── canvases.py          # NEW: workspace & channel canvas functions
│   ├── lists.py             # NEW: list and list item functions
│   ├── files.py             # MODIFIED: binary support, thread_ts, batch share
│   ├── _client.py           # (no changes)
│   ├── _pagination.py       # (no changes)
│   └── __init__.py          # Export new modules
├── content/                 # NEW directory
│   ├── __init__.py          # Export conversion functions
│   ├── _markdown.py         # Markdown parsing utilities
│   ├── canvas_converter.py  # markdown_to_canvas()
│   ├── list_converter.py    # markdown_to_list()
│   └── errors.py            # ContentConversionError
├── server/
│   └── slack_mcp_server.py  # MODIFIED: register new tools
└── auth/
    └── token_manager.py     # (no changes)
```

### Typical Workflow: Markdown → Canvas → Workspace

```
User requests:
  "Convert this markdown report to a canvas"

Flow:
  1. MCP: Call markdown_to_canvas(file_path="/path/report.md")
      → Returns validated markdown string
  2. MCP: Call create_canvas(title="Report", document_content=markdown)
      → Slack API returns canvas_id
  3. MCP: Call set_canvas_access(canvas_id, access_level="read", user_ids=[...])
      → Access granted
  4. Return canvas_id + shareable link
```

### Typical Workflow: Markdown → List → Channel

```
User requests:
  "Create a task list in #tasks from this checklist"

Flow:
  1. MCP: Call markdown_to_list(content="- [ ] Task 1\n- [x] Done\n...")
      → Returns [{"value": "Task 1", "status": "incomplete"}, ...]
  2. MCP: Call create_list(channel="C123", name="Tasks")
      → Returns list_id
  3. MCP: Call create_list_item(list_id, value="Task 1", status="incomplete")
      → Repeats for each item
  4. Return list_id
```

---

## Error Handling

### SlackAPIError (Existing)
Raised on all Slack API failures (401, 403, 404, 429, 500, or `ok=false`).

**Examples**:
- `SlackAPIError("canvases.create", "channel_not_found", {...})`
- `SlackAPIError("slackLists.create", "not_found", {...})`
- `SlackAPIError("files.getUploadURLExternal", "restricted_files_plan", {...})`

### ContentConversionError (New)
Raised on markdown parsing or conversion failures.

**Examples**:
```python
raise ContentConversionError("Invalid markdown table structure: missing pipe separators")
raise ContentConversionError("File not found: /path/to/file.md", original_error=FileNotFoundError(...))
```

### Plan/Permission Failures
When API returns `restricted_action` or `not_paid_plan`:
```python
# SlackAPIError is raised with clear message
raise SlackAPIError(
    endpoint="slackLists.create",
    error="not_paid_plan",
    response={"error": "not_paid_plan", "needed": "pro"},
)
```

---

## Testing Strategy

### Unit Tests (mocked Slack API)

**File Structure**:
```
tests/
├── api/
│   ├── test_canvases.py     # NEW
│   ├── test_lists.py        # NEW
│   ├── test_files.py        # MODIFIED
│   └── test_client.py       # (no changes)
├── content/                 # NEW directory
│   ├── test_canvas_converter.py
│   ├── test_list_converter.py
│   └── test_errors.py
└── server/
    └── test_slack_mcp_server.py  # MODIFIED
```

### Test Coverage

#### Canvas Tests (`test_canvases.py`)
- `test_create_canvas_success()` — Mocked API, verify call and response
- `test_create_workspace_canvas_success()` — Verify `canvases.create` call
- `test_create_channel_canvas_success()` — Verify `conversations.canvases.create` call
- `test_create_channel_canvas_not_found()` — Channel doesn't exist → SlackAPIError
- `test_edit_canvas_success()` — Verify edit operation
- `test_delete_canvas_success()` — Verify deletion
- `test_set_canvas_access_success()` — Verify access control
- `test_delete_canvas_access_success()` — Verify access revocation
- `test_lookup_canvas_sections()` — Verify section lookup

#### List Tests (`test_lists.py`)
- `test_create_list_success()` — Verify list creation
- `test_create_list_not_paid_plan()` — Paid plan required → SlackAPIError
- `test_update_list()` — Verify metadata update
- `test_create_list_item()` — Verify item creation
- `test_update_list_item()` — Verify item update
- `test_delete_list_item()` — Single item deletion
- `test_delete_list_items_batch()` — Multiple items in one call
- `test_list_list_items_paginated()` — Verify pagination (use mock paginate helper)
- `test_get_list_item()` — Fetch single item
- `test_set_list_access()` — Access control
- `test_delete_list_access()` — Revoke access

#### File Upload Tests (`test_files.py` modifications)
- `test_upload_file_text_content()` — Existing behavior (str content)
- `test_upload_file_binary_content()` — NEW: bytes content
- `test_upload_file_from_path()` — NEW: file_path parameter, reads as binary
- `test_upload_file_both_content_and_path_raises()` — NEW: ValueError if both provided
- `test_upload_file_neither_content_nor_path_raises()` — NEW: ValueError if neither
- `test_upload_file_with_thread_ts()` — NEW: thread_ts attachment
- `test_upload_file_multi_channel_batch()` — NEW: files.completeUploadExternal with channels array

#### Content Conversion Tests (`test_canvas_converter.py`)
- `test_markdown_to_canvas_from_string()` — Input is markdown string
- `test_markdown_to_canvas_from_file()` — Read from .md file
- `test_markdown_to_canvas_file_not_found()` — FileNotFoundError
- `test_markdown_to_canvas_invalid_input()` — Neither content nor file_path
- `test_markdown_to_canvas_validation()` — Validate markdown syntax
- `test_markdown_to_canvas_returns_string()` — Output is markdown string ready for canvas.create()

#### List Conversion Tests (`test_list_converter.py`)
- `test_markdown_to_list_checklist()` — Parse checklist syntax (`- [ ]`, `- [x]`)
- `test_markdown_to_list_checklist_status()` — Verify status mapping (incomplete/complete)
- `test_markdown_to_list_bullet_list()` — Parse bullet lists (- item)
- `test_markdown_to_list_table()` — Parse markdown table into list items
- `test_markdown_to_list_mixed()` — Checklist + bullet items together
- `test_markdown_to_list_ignores_headings()` — # Headings are ignored
- `test_markdown_to_list_from_file()` — Read from .md file
- `test_markdown_to_list_invalid_syntax()` — Raises ContentConversionError
- `test_markdown_to_list_empty_content()` — Handle empty input
- `test_markdown_to_list_returns_list_of_dicts()` — Verify output structure

#### MCP Integration Tests (`test_slack_mcp_server.py` modifications)
- `test_mcp_tool_create_canvas_dispatch()` — MCP tool call → create_canvas()
- `test_mcp_tool_create_list_dispatch()` — MCP tool call → create_list()
- `test_mcp_tool_markdown_to_canvas_dispatch()` — MCP tool call → markdown_to_canvas()
- `test_mcp_tool_markdown_to_list_dispatch()` — MCP tool call → markdown_to_list()
- `test_mcp_tool_dispatch_all_new_tools_registered()` — All tools in list_tools()
- `test_mcp_error_handling_content_conversion()` — ContentConversionError → MCP error response
- `test_mcp_error_handling_slack_api()` — SlackAPIError → MCP error response

### Test Utilities

**Fixtures in `conftest.py`** (additions):
```python
@pytest.fixture
def mock_markdown_content():
    return """# Report
- [ ] Task 1
- [x] Task 2
- Regular item
"""

@pytest.fixture
def mock_table_markdown():
    return """| Name | Status |
| --- | --- |
| Task 1 | pending |
| Task 2 | done |
"""
```

---

## Acceptance Criteria Summary

### Canvas Features (CANVAS-01-R1 to R7)
- [x] Create workspace canvas with markdown
- [x] Create channel-attached canvas
- [x] Edit canvas content
- [x] Delete canvas
- [x] Set user/group access (read/write/owner)
- [x] Revoke access
- [x] Lookup canvas sections

### List Features (LISTS-01-R1 to R9)
- [x] Create list with initial items
- [x] Update list metadata
- [x] Create/update/delete list items
- [x] Batch delete multiple items
- [x] List items with pagination
- [x] Fetch single item details
- [x] Set/revoke list access

### File Upload Enhancements (FILES-01-R1 to R4)
- [x] Accept binary content (`bytes`)
- [x] Accept file path and read from disk
- [x] Support thread_ts for thread attachment
- [x] Batch multi-channel sharing via `files.completeUploadExternal`
- [x] Backward compatible with string content

### Content Conversion (CONVERT-01-R1 to R3)
- [x] Markdown → Canvas (passthrough + validation)
- [x] Markdown → List (parse checklist, bullet lists, tables)
- [x] ContentConversionError for parsing failures
- [x] Pure Python, no external transcoding tools

### MCP Integration (MCP-01-R1)
- [x] All Canvas functions registered as MCP tools
- [x] All List functions registered as MCP tools
- [x] Conversion functions registered as MCP tools
- [x] Tool schemas include descriptions and required fields
- [x] Error responses handled gracefully

### Scopes & Configuration (DOC-01-R1)
- [x] Scopes documented: `canvases:read`, `canvases:write`, `lists:read`, `lists:write`
- [x] `.env.local.example` updated with new scopes
- [x] Paid plan requirement documented
- [x] `markdown-it-py` added to `pyproject.toml`

---

## Known Limitations

1. **List Column Schema**: Slack API does not expose a method to read the column schema of an existing list. Workaround: Accept column definitions as input when creating/updating lists.
2. **Canvas Formatting**: Only markdown supported; Block Kit and rich formatting deferred to future enhancement.
3. **Rate Limiting**: Large batches of list items (>1000) may hit Slack rate limits. Implement in application logic if needed.
4. **No Scheduled Delivery**: All operations are synchronous, on-demand only.

---

## Implementation Notes for Engineer

1. **Reuse Existing Patterns**: Follow the style of `api/messages.py` and `api/channels.py` for function signatures and error handling.
2. **Pagination Helper**: Use the existing `paginate()` function from `_pagination.py` for `list_list_items()`.
3. **Token Management**: All functions receive `token: str` as the first parameter; use `TokenManager` for MCP dispatch.
4. **Markdown Parsing**: Keep content conversion pure Python. Use `markdown-it-py` for parsing, store custom mappings in dedicated converter modules.
5. **Testing**: Mock the `slack_get` and `slack_post` functions, not the entire `SlackAPIClient`, following the existing test pattern.
6. **Type Hints**: Use full type hints with `from __future__ import annotations` for all new modules.
7. **Documentation**: Add docstrings to all functions following the existing format (Args, Returns, Raises sections).

---

## Timeline & Phases

**Phase 1**: File upload enhancements (binary, file_path, thread_ts, batch share)  
**Phase 2**: Canvas API functions + MCP registration  
**Phase 3**: List API functions + MCP registration  
**Phase 4**: Content conversion (markdown→canvas, markdown→list)  
**Phase 5**: Integration tests + documentation + release

---

## Success Criteria

- All acceptance criteria met for A–F
- 95%+ test coverage for new modules
- Zero regressions in existing tests
- MCP tools discoverable and callable from Claude Desktop
- No breaking changes to existing APIs
- Comprehensive docstrings and error messages

---

**Version**: 1.0  
**Last Updated**: 2026-06-23  
**Next Review**: After implementation complete
