# Code Analysis: slack-mpm
**Date:** 2026-03-10
**Analyst:** Claude Sonnet 4.6 (Research Agent)
**Scope:** Full codebase — `/Users/masa/Projects/slack-mpm/src/slack_mpm/`

---

## 1. Architecture Overview

slack-mpm is a Model Context Protocol (MCP) server that exposes Slack workspace operations as MCP tools consumable by Claude Desktop. The project follows a clean three-layer architecture: a thin **CLI layer** (`cli/main.py`) that wires up Click commands and launches the server; a **server layer** (`server/slack_mcp_server.py`) that acts as an adapter between the MCP protocol and the Slack API; and an **API layer** (`api/`) containing eight domain modules (`channels`, `messages`, `users`, `files`, `workspace`, `reminders`, `bookmarks`, `scheduled`) each wrapping specific Slack REST endpoints. Cross-cutting infrastructure is split between `api/_client.py` (shared HTTP client with rate-limit handling) and `auth/` (token loading, validation, masking). The separation of concerns is generally sound for a project of this size: each domain module is a thin wrapper over `slack_get`/`slack_post` with no business logic bleed, and the MCP server is correctly positioned as a dispatch layer rather than a business layer. The main structural weaknesses are (a) a 1029-line monolithic server file that inlines all 42 tool schema definitions as a module-level list literal, (b) duplicate rate-limit retry logic in both `slack_get` and `slack_post`, (c) three independent pagination loops with copy-pasted structure, (d) no logging anywhere in the codebase, and (e) `TokenManager` is constructed directly inside every CLI command and inside `SlackMCPServer.__init__`, preventing injection or testing without env-var patching.

---

## 2. File-by-File Summary Table

| File | Purpose | Key Issues |
|---|---|---|
| `__init__.py` | Package root; re-exports `__version__` | Clean |
| `__version__.py` | Hardcoded version string | Clean |
| `cli/main.py` | Click CLI: `setup`, `doctor`, `mcp` commands | Hardcoded `TokenManager()` construction (lines 24, 125, 195); nested async closures for sync/async bridge; `doctor` command hard-codes dep names without cross-checking `pyproject.toml` |
| `auth/models.py` | Pydantic models: `SlackToken`, `TokenStatus`, `WorkspaceInfo` | `Config` inner class deprecated in Pydantic v2 (use `model_config`); `WorkspaceInfo` is defined but never used |
| `auth/token_manager.py` | `TokenManager`: env loading, token access, `auth.test` validation | Creates a new `httpx.AsyncClient` per call inside `_validate_token` (line 185); `SLACK_API_BASE` constant duplicated from `api/_client.py` (line 11); `_load_env()` is a module-level function with side effects called on every `TokenManager()` construction |
| `api/_client.py` | `slack_get` / `slack_post` shared HTTP functions; `SlackAPIError` | Rate-limit retry logic copy-pasted between `slack_get` (lines 48-55) and `slack_post` (lines 91-101); new `httpx.AsyncClient` created on every call (no connection pooling); `SLACK_API_BASE` duplicated from `token_manager.py` |
| `api/channels.py` | Channel CRUD: list, info, create, archive, invite, kick, join, topic | Pagination loop (lines 32-47) structurally identical to loops in `users.py` and `users.list_user_channels` |
| `api/messages.py` | Message operations: send, update, delete, history, search, reactions, pins, threads | `reply_in_thread` (line 251) duplicates `send_message` logic by calling `chat.postMessage` directly instead of delegating to `send_message()` |
| `api/users.py` | User operations: list, info, by-email, open DM, list user channels | Two separate pagination loops (lines 23-34 and 91-102) with copy-paste structure; `list_user_channels` has no `limit` parameter, fetching all pages unconditionally |
| `api/files.py` | File upload (v2 API), list, info, delete, share | `import httpx` inside function body (line 32) breaks module-level import convention; `upload_file` for multiple channels incorrectly calls `files.sharedPublicURL` which is deprecated/broken (lines 69-81); silently posts a message instead of actually sharing a file |
| `api/workspace.py` | Workspace info, emoji list, bot info, auth test | `auth_test` uses `slack_post` for an endpoint that accepts GET (line 55); trivially thin wrappers |
| `api/reminders.py` | Reminder CRUD | Clean; appropriately thin |
| `api/bookmarks.py` | Bookmark list, add, remove | Clean; appropriately thin |
| `api/scheduled.py` | Schedule, list, delete scheduled messages | Clean; appropriately thin |
| `server/slack_mcp_server.py` | MCP adapter: tool registry (SLACK_TOOLS), dispatcher, server runner | 1029-line file; all 42 tool schemas inlined as a 841-line module-level list literal; `_dispatch_tool` reconstructs the full `handlers` dict on every call (line 901); `_setup_handlers` uses nested closures that close over `self` without `__slots__`; no logging; errors swallowed to `TextContent` without structured logging |
| `tests/test_auth.py` | Unit tests for `TokenManager` and `SlackToken` | Good coverage of token lifecycle; one test writes to the real project `.env.local` file (lines 157, 173) — fragile in CI |
| `tests/test_server.py` | Unit tests for MCP tool dispatch | Only 6 of 42 tools have dispatch tests; test isolation requires `SlackMCPServer` re-import inside each test due to module caching |

---

## 3. Findings Per Focus Area

### 3.1 Best Practices

**Missing logging (all files)**
There is no `import logging` anywhere in the production codebase. The MCP server silently swallows `SlackAPIError` and `ValueError` into `TextContent` strings (server/slack_mcp_server.py:879-882) with no structured logging. Debugging misbehaving tools in production requires attaching a debugger or reading Claude Desktop's raw stdio.

**Deprecated Pydantic v2 Config pattern**
`auth/models.py:29-32` uses the Pydantic v1-style inner `Config` class:
```python
class Config:
    frozen = False
```
Pydantic v2 uses `model_config = ConfigDict(frozen=False)`. This produces a deprecation warning at runtime and will break on a future Pydantic v2 minor that removes the compat shim.

**`auth.test` called via POST when GET is valid**
`api/workspace.py:55` calls `slack_post(token, "auth.test", {})`. The Slack `auth.test` method accepts both GET and POST, but the convention in the rest of the module is GET for read operations. This is inconsistent with the pattern in `token_manager.py:186` which also uses POST. Minor but inconsistent.

**Lazy import inside function body**
`api/files.py:32`:
```python
import httpx
```
This import is buried inside `upload_file()` rather than at module top-level. It obscures the dependency, prevents static analysis tools from seeing it, and adds a (tiny) runtime lookup cost on every call.

**Unchecked `int()` conversion on Retry-After header**
`api/_client.py:49` and `api/_client.py:91`:
```python
retry_after = int(response.headers.get("Retry-After", "1"))
```
If Slack ever sends a non-integer `Retry-After` value (fractional seconds, date-string), this raises `ValueError` uncaught, surfacing as an unhandled exception instead of a graceful retry.

**`sys.exit(1)` inside async callback**
`cli/main.py:35` and `cli/main.py:60`: `sys.exit(1)` is called inside `_validate()` which runs inside `asyncio.run()`. While this technically works, it exits from within the async context, bypassing any cleanup. Using a return value and raising after `asyncio.run()` would be cleaner.

**Type annotation coverage**
All public functions have complete type hints. `mypy --strict` is configured in `pyproject.toml`. The `_pick` helper uses `dict[str, Any]` correctly. No gaps found in the API layer. The `handlers` dict in `_dispatch_tool` (server/slack_mcp_server.py:901) is typed `dict[str, Any]` rather than `dict[str, Callable]`, losing type safety for the values.

**Docstrings**
All public functions have Google-style docstrings with Args/Returns sections. Private helpers (`_load_env`, `_pick`, `_mask_token`, `_get_token`) have adequate single-line docstrings.

---

### 3.2 Code Reuse / Duplication

**Pagination loop (3 copies)**

Structurally identical cursor-based pagination loops appear in:
- `api/channels.py:32-47` (list_channels)
- `api/users.py:23-34` (list_users)
- `api/users.py:88-102` (list_user_channels)

Each loop follows the same pattern:
```python
all_items: list[...] = []
cursor: str | None = None
while True:
    params = {...}
    if cursor:
        params["cursor"] = cursor
    data = await slack_get(token, endpoint, params)
    all_items.extend(data.get(key, []))
    next_cursor = data.get("response_metadata", {}).get("next_cursor")
    if not next_cursor or len(all_items) >= limit:
        break
    cursor = next_cursor
```
A shared `async def paginate(token, endpoint, key, limit, base_params)` helper in `_client.py` would eliminate all three copies.

**Rate-limit retry logic (2 copies)**

`api/_client.py:48-55` (inside `slack_get`) and `api/_client.py:91-101` (inside `slack_post`) are near-identical:
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "1"))
    await anyio.sleep(retry_after)
    response = await client.<method>(...)
```
This should be extracted into a private `_request_with_retry` helper or wrapped in a custom `httpx` transport.

**`SLACK_API_BASE` constant (2 copies)**

Defined independently at:
- `auth/token_manager.py:11`
- `api/_client.py:10`

Both are `"https://slack.com/api"`. Should be defined once in `_client.py` and imported by `token_manager.py`.

**`_mask_token` logic (2 copies)**

Token masking logic:
```python
if not token or len(token) <= 10:
    return "***"
return token[:6] + "..." + token[-4:]
```
Appears in:
- `cli/main.py:204-207` (`_mask_token` function)
- `auth/models.py:43-46` (`SlackToken.mask()` method)

`cli/main.py` should call `SlackToken(token=t, token_type="bot").mask()` or expose `mask_token` as a utility in `auth/models.py`.

**`reply_in_thread` reimplements `send_message`**

`api/messages.py:250-254`:
```python
return await slack_post(
    token, "chat.postMessage",
    {"channel": channel, "thread_ts": thread_ts, "text": text},
)
```
This duplicates the `send_message` call. It should delegate to `send_message(token, channel, text, thread_ts=thread_ts)`.

---

### 3.3 Dependency Injection (DI)

**TokenManager hardcoded construction — three separate sites**

`TokenManager` is always constructed via `TokenManager()` with no parameters:
- `cli/main.py:24` (`setup` command)
- `cli/main.py:125` (`doctor` command)
- `server/slack_mcp_server.py:850` (`SlackMCPServer.__init__`)

This means:
1. Every test that touches `SlackMCPServer` or the CLI must patch `os.environ` to inject credentials rather than passing a configured `TokenManager`.
2. There is no way to substitute a mock or test double for `TokenManager` without env-var manipulation.
3. `SlackMCPServer` cannot be constructed with a pre-validated token.

A minimal improvement: accept `token_manager: TokenManager | None = None` in `SlackMCPServer.__init__` and default-construct only when `None`.

**Token string passed by value, not capability object**

All 30+ API functions accept `token: str`. The token string is the implicit capability object — there is no protocol or interface expressing "something that can provide a Slack token". If the token selection strategy changes (e.g., token rotation, per-tool token selection), every call site must be updated.

**`_load_env()` side effect on construction**

`token_manager.py:79`: `_load_env()` is called inside `TokenManager.__init__`. This mutates `os.environ` as a side effect of object construction. In tests, this can cause inter-test pollution if `monkeypatch`/`patch.dict` is not used correctly. The env loading should be separated from token reading so the two concerns can be tested independently.

**No service registry or factory**

The MCP server directly constructs `TokenManager` and calls API module functions (which are plain async functions). This is acceptable for the current scale but means there is no seam for adding cross-cutting concerns (auth refresh, metrics, circuit breaking) without modifying the API functions themselves.

---

### 3.4 SOA / Separation of Concerns

**`SlackMCPServer` is well-separated from API layer**

The server correctly delegates all Slack API calls to domain modules. There is no Slack API call inside `slack_mcp_server.py` directly — the `_dispatch_tool` method purely routes. This is good SOA practice.

**Tool schema definitions mixed with server logic**

The 841-line `SLACK_TOOLS` list (server/slack_mcp_server.py:31-841) is a module-level constant in the same file as the server class. As the tool count grows, this becomes unmanageable. Options:
- Move tool schemas to a separate `server/tools.py` or `server/schemas.py` module.
- Generate them from a data-driven config (e.g., YAML or structured dataclasses).

**`_dispatch_tool` rebuilds handler dict on every call**

`server/slack_mcp_server.py:901-1014`: The `handlers` dict containing 42 lambdas is constructed fresh on every `_dispatch_tool` invocation. This is pure overhead. The dict should be built once (in `__init__` or `_setup_handlers`) and stored as `self._handlers`.

**CLI `doctor` command has embedded dependency check logic**

`cli/main.py:100-116` hard-codes a `deps` dict mapping friendly names to import names. This duplicates information already in `pyproject.toml` and will silently go stale when dependencies change. This is minor but represents business logic (what's required?) embedded in presentation code (CLI output).

**`upload_file` multi-channel sharing is broken logic**

`api/files.py:67-81`: When uploading to more than one channel, the code calls `files.sharedPublicURL` (which requires the file to be publicly shared, a feature Slack has restricted) followed by `chat.postMessage` with an `attachments` block using `file_id`. This is not how Slack's v2 file API works for multi-channel sharing. This represents business logic implemented incorrectly against a poorly-understood API — a concern that should have been isolated behind a testable abstraction.

---

### 3.5 Anti-Patterns

**Global-scope mutable list (`SLACK_TOOLS`)**

`server/slack_mcp_server.py:31`: `SLACK_TOOLS` is a module-level list. While in practice nothing mutates it, there is no enforcement (e.g., `tuple` or `frozenset`). Any code that imports this module can append to `SLACK_TOOLS`. Typing it as `tuple[types.Tool, ...]` or using `Final` would make the intent explicit.

**Dict-of-lambdas dispatch table rebuilt on every call**

As noted above (`server/slack_mcp_server.py:901`), the handler dict is rebuilt on every tool call. This is a performance anti-pattern; for an MCP server that may handle thousands of calls per session, it adds unnecessary allocations.

**No abstractions for token type requirements**

Several tools silently fall back from user token to bot token when user token is absent:
```python
"search_messages": lambda a: messages.search_messages(user_token or token, ...)
"add_reminder":    lambda a: reminders.add_reminder(user_token or token, ...)
```
`search_messages` in `api/messages.py:131` then validates that the token starts with `xoxb-` and raises `ValueError`. This means the error surface for "user token required but bot token used" is a `ValueError` that only manifests at runtime. There is no type-level or early enforcement of the token-type requirement per tool. A `TokenRequirement` enum (BOT_ONLY, USER_PREFERRED, USER_REQUIRED) on each tool definition would make this explicit and testable.

**`WorkspaceInfo` model is dead code**

`auth/models.py:49-57`: `WorkspaceInfo` is defined and exported from `auth/__init__.py` but is not imported or used anywhere else in the codebase.

**Test writing to real filesystem**

`tests/test_auth.py:132-175`: `test_load_env_finds_dotenv_local_outside_cwd` writes to and reads from the actual project-root `.env.local` file. It preserves and restores content in a `try/finally`, but this is fragile: if the test runner is interrupted, the sentinel content remains. It also cannot run safely in parallel. A `tmp_path`-based approach with a mocked file-lookup path would be safer.

**Inconsistent error handling surface**

`SlackAPIError` is defined in `api/_client.py` and caught in `server/slack_mcp_server.py:879`. However, individual API functions can also raise `ValueError` (e.g., `messages.py:131`, `token_manager.py:131`). The server catches both at the top level but converts them to `TextContent` strings — making it impossible for callers to distinguish between "Slack returned an error" and "bad input" without string-parsing the response.

---

## 4. Priority-Ranked Improvement List

### High Priority

**H1 — Extract `_request_with_retry` to eliminate duplicated rate-limit logic**
- Files: `api/_client.py:41-60`, `api/_client.py:81-106`
- Risk: High — duplicate code means retry behavior diverges silently as the codebase evolves.
- Fix: Extract a private `async def _make_request(client, method, url, **kwargs)` that handles the 429 retry once, used by both `slack_get` and `slack_post`.

**H2 — Extract shared pagination helper**
- Files: `api/channels.py:32-47`, `api/users.py:23-34`, `api/users.py:88-102`
- Risk: High — any pagination bug (off-by-one on limit, wrong cursor key) must be fixed in three places.
- Fix: Add `async def paginate(token, endpoint, result_key, limit, params)` to `api/_client.py`.

**H3 — Add structured logging**
- Files: All production files (none have logging)
- Risk: High — production debugging is impossible without log output.
- Fix: Add `import logging; logger = logging.getLogger(__name__)` to `_client.py` and `slack_mcp_server.py`. Log at DEBUG for every API call (endpoint, status), at WARNING for rate-limit retries, at ERROR for `SlackAPIError`.

**H4 — Fix `upload_file` multi-channel sharing**
- File: `api/files.py:67-81`
- Risk: High — feature is silently broken for the multi-channel case. `files.sharedPublicURL` is restricted by Slack; the correct approach for multi-channel sharing with the v2 API is to pass multiple channel IDs in the `completeUploadExternal` payload.
- Fix: Pass `"channel_id": channels[0]` and share to additional channels by re-calling `completeUploadExternal` or restructuring the payload per Slack docs.

**H5 — Make `TokenManager` injectable in `SlackMCPServer`**
- File: `server/slack_mcp_server.py:850`
- Risk: Medium-High — current design prevents unit testing without env-var patching.
- Fix: `def __init__(self, token_manager: TokenManager | None = None)` and `self._token_manager = token_manager or TokenManager()`.

### Medium Priority

**M1 — Move `SLACK_TOOLS` to a dedicated `server/tools.py` module**
- File: `server/slack_mcp_server.py:31-841`
- Risk: Medium — the 841-line literal makes the server file unnavigable and makes it hard to add/remove tools without scrolling through a massive structure.

**M2 — Build `_handlers` dict once in `_setup_handlers`, not on every call**
- File: `server/slack_mcp_server.py:901-1014`
- Risk: Medium — unnecessary allocation on every tool dispatch; affects performance at scale.

**M3 — Remove duplicate `SLACK_API_BASE` constant**
- Files: `auth/token_manager.py:11`, `api/_client.py:10`
- Risk: Medium — if the base URL ever needs to change (e.g., for enterprise proxies), it must be changed in two places.
- Fix: Define once in `api/_client.py`, import in `token_manager.py`.

**M4 — Remove duplicate `_mask_token` / `SlackToken.mask()` logic**
- Files: `cli/main.py:203-207`, `auth/models.py:43-46`
- Risk: Low-Medium — masking format is duplicated; use `SlackToken.mask()` from CLI or extract a standalone utility.

**M5 — Fix deprecated Pydantic v2 Config class**
- File: `auth/models.py:29-32`
- Risk: Medium — will break on future Pydantic v2 minor that removes v1 compat.
- Fix: Replace `class Config: frozen = False` with `model_config = ConfigDict(frozen=False)` (or remove entirely since `frozen=False` is already the default).

**M6 — `reply_in_thread` should delegate to `send_message`**
- File: `api/messages.py:250-254`
- Risk: Low-Medium — `reply_in_thread` misses the `unfurl_links` and `blocks` parameters that `send_message` supports.

**M7 — Add `TokenRequirement` per tool and enforce at dispatch time**
- File: `server/slack_mcp_server.py:936-991`
- Risk: Medium — silent fallback from user to bot token for user-scoped APIs causes confusing failures.

### Low Priority

**L1 — Remove `WorkspaceInfo` dead code or use it**
- File: `auth/models.py:49-57`
- Risk: Low — dead code adds cognitive overhead and misleads future contributors.

**L2 — Move `import httpx` to module top in `api/files.py`**
- File: `api/files.py:32`
- Risk: Low.

**L3 — Type `handlers` dict as `dict[str, Callable[..., Coroutine]]` in `_dispatch_tool`**
- File: `server/slack_mcp_server.py:901`
- Risk: Low — improves type safety and mypy coverage.

**L4 — Type `SLACK_TOOLS` as `Final[tuple[types.Tool, ...]]`**
- File: `server/slack_mcp_server.py:31`
- Risk: Low — prevents accidental mutation of the tool registry.

**L5 — Refactor `test_load_env_finds_dotenv_local_outside_cwd` to avoid writing to real filesystem**
- File: `tests/test_auth.py:132-175`
- Risk: Low but fragile in CI — use a patched path lookup instead of writing to the actual project `.env.local`.

**L6 — `list_user_channels` has no `limit` parameter; fetches unboundedly**
- File: `api/users.py:78`
- Risk: Low — for large workspaces with many channels per user, this can return an unbounded list and exhaust memory.

**L7 — `doctor` command dependency list is not derived from `pyproject.toml`**
- File: `cli/main.py:100-107`
- Risk: Low — will silently miss checking new dependencies added to the project.

---

## 5. Summary Metrics

| Metric | Value |
|---|---|
| Source files | 14 Python files |
| Total source lines | ~1,800 |
| Test files | 2 |
| Test coverage (tools tested) | 6 of 42 tools have dispatch tests (14%) |
| Docstring coverage | ~100% (all public functions) |
| Type hint coverage | ~100% (mypy strict configured) |
| Logging statements | 0 |
| Duplicated code blocks | 5 distinct patterns |
| Dead code | 1 model (`WorkspaceInfo`) |
| Confirmed bugs | 1 (`upload_file` multi-channel) |
| Suspected bugs | 1 (`Retry-After` int conversion) |
