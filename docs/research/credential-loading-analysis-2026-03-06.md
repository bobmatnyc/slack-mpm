# Credential/Token Loading Analysis

Date: 2026-03-06
Scope: How SLACK_BOT_TOKEN is loaded, where the bug lives, and what to change.

---

## Summary of Bug

When Claude Desktop launches the MCP server via `uv run slack-mpm mcp`, the working
directory (CWD) is NOT the project directory -- it is typically the user's home
directory or whatever the OS assigns to a GUI-spawned process. The `_load_env()`
function in `token_manager.py` only looks for `.env` / `.env.local` relative to
`Path.cwd()`, so those files are never found, and `SLACK_BOT_TOKEN` stays unset.

---

## File-by-File Findings

### `src/slack_mpm/auth/token_manager.py` -- PRIMARY LOCATION OF BUG

```
Lines 15-31  _load_env()
Lines 37-43  TokenManager.__init__()  reads os.environ after _load_env()
```

**What it does today:**

```python
def _load_env() -> None:
    cwd = Path.cwd()                          # line 21 -- THE PROBLEM
    env_path = cwd / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False) # line 26
    env_local_path = cwd / ".env.local"
    if env_local_path.exists():
        load_dotenv(env_local_path, override=True) # line 31
```

**What it should do:**

Search a set of candidate directories instead of only CWD:
1. CWD (keep current behaviour for CLI use)
2. The directory of `token_manager.py` itself, then walk upward to find the
   project root (i.e. `Path(__file__).parent` walked up until `.env.local` or
   `pyproject.toml` is found).
3. The user's home directory (`Path.home()`).

python-dotenv's `find_dotenv()` helper can also automate this: it walks upward
from the caller's file and stops at a `.env` file or the filesystem root.

**Env var names checked (lines 40-43):**

| Variable              | Required | Used for                    |
|-----------------------|----------|-----------------------------|
| `SLACK_BOT_TOKEN`     | Yes      | All bot API calls           |
| `SLACK_USER_TOKEN`    | No       | search.messages, reminders  |
| `SLACK_SIGNING_SECRET`| No       | Webhook verification        |
| `SLACK_TEAM_ID`       | No       | Informational               |

---

### `src/slack_mpm/api/_client.py` -- NO TOKEN LOADING HERE

The HTTP client functions (`slack_get`, `slack_post`) receive the token as a
function argument -- they do NOT read from the environment or do any dotenv
loading. Token injection happens exclusively through `TokenManager`.

---

### `src/slack_mpm/server/slack_mpm_server.py` -- SERVER STARTUP

```
Line 833  self._token_manager = TokenManager()
```

`SlackMCPServer.__init__` constructs a `TokenManager`, which is when `_load_env()`
runs. There is no additional dotenv loading in the server module itself.

The `mcp` CLI command (cli/main.py line 195) constructs `SlackMCPServer()` directly,
so fixing `_load_env()` in `token_manager.py` is sufficient -- no changes needed
to the server or CLI wiring.

---

### `src/slack_mpm/cli/main.py` -- CLI COMMANDS

Both `setup` (line 24) and `doctor` (line 125) also construct `TokenManager()`
directly, so they share the same bug when invoked outside the project directory.

---

### `.env.local.example` -- ENV FILE TEMPLATE

Located at project root. Documents four env vars:
- `SLACK_BOT_TOKEN=xoxb-your-bot-token-here`
- `SLACK_USER_TOKEN=xoxp-your-user-token-here`
- `SLACK_SIGNING_SECRET=your-signing-secret-here`
- `SLACK_TEAM_ID=T0XXXXXXXXX`

No `.env` or `.env.local` file is committed (correct -- secrets stay local).

---

### `pyproject.toml` -- ENTRY POINTS

```toml
[project.scripts]
slack-mpm = "slack_mpm.cli.main:main"   # line 20
```

`python-dotenv>=1.0.0` is already a declared dependency (line 15). No new
dependency is required for the fix.

---

## dotenv Library Usage

`python-dotenv` is already imported and used:
- `from dotenv import load_dotenv` (token_manager.py line 8)
- `load_dotenv(path, override=False/True)` is called with explicit paths.

The library also provides `find_dotenv(usecwd=False)` which walks upward from
the calling file to locate a `.env` file automatically. This could replace
the manual path construction entirely.

---

## Root Cause (One Sentence)

`_load_env()` at line 21 of `token_manager.py` anchors its search to
`Path.cwd()`, which is unpredictable when launched by Claude Desktop (a GUI
process that sets CWD to `~` or `/`), so `.env.local` is never found.

---

## Recommended Fix

Modify `_load_env()` in `/Users/masa/Projects/slack-mpm/src/slack_mpm/auth/token_manager.py`
to search multiple candidate directories in priority order:

1. `Path.cwd()` and its ancestors (current behaviour, covers CLI use)
2. The project root anchored at `__file__` (covers MCP server launched from any CWD)
3. `Path.home()` (covers a token placed in `~/.env.local`)

Concrete candidate list to iterate:

```python
candidates = [
    Path.cwd(),
    Path(__file__).resolve().parent.parent.parent.parent,  # project root when installed in src layout
    Path.home(),
]
```

Or use `find_dotenv` from python-dotenv as an alternative strategy:

```python
from dotenv import find_dotenv, load_dotenv

path = find_dotenv(".env.local", usecwd=True)   # walks upward from CWD
if not path:
    path = find_dotenv(".env.local", usecwd=False)  # walks upward from __file__
if path:
    load_dotenv(path, override=True)
```

Either approach makes the fix self-contained to `_load_env()` with no changes
required anywhere else in the codebase.

---

## Files That Need Changes

| File | Change |
|------|--------|
| `src/slack_mpm/auth/token_manager.py` | Expand `_load_env()` to search beyond CWD |

No other files require modification. The dependency (`python-dotenv`) is already
declared in `pyproject.toml`.
