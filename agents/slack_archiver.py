#!/usr/bin/env python3
"""Slack Archiver Agent - exports channel message history to JSON or Markdown.

Downloads full channel history and saves to a structured archive with thread replies.

Usage:
    uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/
    uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --format markdown
    uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --days 30
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slack_mpm.api import channels, messages, users
from slack_mpm.auth.token_manager import TokenManager


def _ts_to_dt(ts: str) -> datetime:
    """Convert Slack timestamp to datetime."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(tz=timezone.utc)


async def fetch_all_history(
    token: str,
    channel_id: str,
    oldest: str | None,
) -> list[dict]:
    """Fetch complete channel history with pagination.

    Args:
        token: Slack bot token.
        channel_id: Channel to fetch history from.
        oldest: Optional oldest Unix timestamp to start from.

    Returns:
        List of all message dicts (newest first).
    """
    all_msgs: list[dict] = []
    cursor: str | None = None

    while True:
        params: dict = {"channel": channel_id, "limit": 200}
        if oldest:
            params["oldest"] = oldest
        if cursor:
            params["cursor"] = cursor

        data = await messages.list_history(token, channel_id, limit=200, oldest=oldest)
        batch = data.get("messages", [])
        all_msgs.extend(batch)

        # Check if there are more pages
        if data.get("has_more") and batch:
            # Use the oldest ts in the batch as cursor for next page
            # (conversations.history paginates backward by default)
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        else:
            break

    return all_msgs


async def fetch_thread(token: str, channel_id: str, thread_ts: str) -> list[dict]:
    """Fetch all replies in a thread.

    Args:
        token: Slack bot token.
        channel_id: Channel containing the thread.
        thread_ts: Parent message timestamp.

    Returns:
        List of reply dicts (not including the parent).
    """
    try:
        data = await messages.get_thread_replies(token, channel_id, thread_ts)
        replies = data.get("messages", [])
        return replies[1:]  # Skip the first message (parent)
    except Exception:
        return []


async def build_user_cache(token: str, user_ids: set[str]) -> dict[str, str]:
    """Build a cache of user IDs to display names.

    Args:
        token: Slack bot token.
        user_ids: Set of user IDs to look up.

    Returns:
        Dict mapping user_id -> display name.
    """
    cache: dict[str, str] = {}
    for uid in user_ids:
        try:
            data = await users.get_user_info(token, uid)
            profile = data.get("user", {}).get("profile", {})
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or uid
            )
            cache[uid] = name
        except Exception:
            cache[uid] = uid
    return cache


def _msg_to_markdown(msg: dict, user_cache: dict[str, str], indent: str = "") -> str:
    """Convert a message dict to a Markdown line."""
    user_id = msg.get("user", msg.get("bot_id", "unknown"))
    name = user_cache.get(user_id, user_id)
    ts = _ts_to_dt(msg.get("ts", "")).strftime("%Y-%m-%d %H:%M UTC")
    text = msg.get("text", "").replace("\n", "\n" + indent + "  ")
    return f"{indent}**{name}** [{ts}]\n{indent}  {text}\n"


async def archive_channel(
    token: str,
    channel_id: str,
    output_dir: Path,
    fmt: str,
    days: int | None,
    include_threads: bool,
) -> None:
    """Archive channel history to files.

    Args:
        token: Slack bot token.
        channel_id: Channel to archive.
        output_dir: Directory to save archive files.
        fmt: Output format: 'json' or 'markdown'.
        days: If set, only archive messages from the last N days.
        include_threads: If True, fetch and include thread replies.
    """
    # Get channel info
    try:
        ch_data = await channels.get_channel_info(token, channel_id)
        ch_name = ch_data.get("channel", {}).get("name", channel_id)
    except Exception:
        ch_name = channel_id

    print(f"Archiving #{ch_name} ({channel_id})...")

    # Calculate oldest timestamp if filtering by days
    oldest: str | None = None
    if days:
        oldest = str(time.time() - (days * 86400))
        print(f"Fetching last {days} day(s) of history...")

    # Fetch all messages
    all_msgs = await fetch_all_history(token, channel_id, oldest)
    all_msgs.reverse()  # Chronological order

    real_msgs = [m for m in all_msgs if not m.get("subtype")]
    print(f"Fetched {len(real_msgs)} messages.")

    # Fetch thread replies if requested
    threads: dict[str, list[dict]] = {}
    if include_threads:
        thread_parents = [m for m in real_msgs if int(m.get("reply_count", 0)) > 0]
        print(f"Fetching {len(thread_parents)} thread(s)...")
        for msg in thread_parents:
            ts = msg.get("ts", "")
            if ts:
                replies = await fetch_thread(token, channel_id, ts)
                if replies:
                    threads[ts] = replies

    # Build user cache
    all_user_ids: set[str] = set()
    for msg in real_msgs:
        if msg.get("user"):
            all_user_ids.add(msg["user"])
    for replies in threads.values():
        for r in replies:
            if r.get("user"):
                all_user_ids.add(r["user"])

    print(f"Resolving {len(all_user_ids)} user(s)...")
    user_cache = await build_user_cache(token, all_user_ids)

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        # Build JSON archive
        archive_data = {
            "channel_id": channel_id,
            "channel_name": ch_name,
            "archived_at": datetime.now(tz=timezone.utc).isoformat(),
            "message_count": len(real_msgs),
            "messages": [],
        }

        for msg in real_msgs:
            msg_ts = msg.get("ts", "")
            entry: dict = {
                "ts": msg_ts,
                "datetime": _ts_to_dt(msg_ts).isoformat(),
                "user_id": msg.get("user", ""),
                "user_name": user_cache.get(msg.get("user", ""), msg.get("user", "")),
                "text": msg.get("text", ""),
                "reply_count": msg.get("reply_count", 0),
                "reactions": msg.get("reactions", []),
            }
            if msg_ts in threads:
                entry["replies"] = [
                    {
                        "ts": r.get("ts", ""),
                        "datetime": _ts_to_dt(r.get("ts", "")).isoformat(),
                        "user_id": r.get("user", ""),
                        "user_name": user_cache.get(r.get("user", ""), r.get("user", "")),
                        "text": r.get("text", ""),
                    }
                    for r in threads[msg_ts]
                ]
            archive_data["messages"].append(entry)  # type: ignore[union-attr]

        output_file = output_dir / f"{ch_name}_{timestamp}.json"
        output_file.write_text(json.dumps(archive_data, indent=2, ensure_ascii=False))
        print(f"JSON archive saved: {output_file}")

    else:
        # Build Markdown archive
        lines: list[str] = [
            f"# Slack Archive: #{ch_name}\n",
            f"**Channel ID:** {channel_id}  \n",
            f"**Archived:** {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n",
            f"**Messages:** {len(real_msgs)}\n\n",
            "---\n\n",
        ]

        for msg in real_msgs:
            msg_ts = msg.get("ts", "")
            lines.append(_msg_to_markdown(msg, user_cache))

            if msg_ts in threads:
                lines.append("\n  _Thread replies:_\n\n")
                for reply in threads[msg_ts]:
                    lines.append(_msg_to_markdown(reply, user_cache, indent="  "))
            lines.append("\n")

        output_file = output_dir / f"{ch_name}_{timestamp}.md"
        output_file.write_text("".join(lines), encoding="utf-8")
        print(f"Markdown archive saved: {output_file}")

    print("Archive complete.")


def main() -> None:
    """Entry point for the Slack archiver agent."""
    parser = argparse.ArgumentParser(
        description="Export Slack channel history to JSON or Markdown files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/
  uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --format markdown
  uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --days 30
  uv run agents/slack_archiver.py --channel C1234567890 --output ./archive/ --no-threads
        """,
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Slack channel ID (e.g., C1234567890) to archive",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory for archive files",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format: json or markdown (default: json)",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Only archive messages from the last N days (default: all history)",
    )
    parser.add_argument(
        "--no-threads",
        action="store_true",
        help="Skip fetching thread replies",
    )
    args = parser.parse_args()

    manager = TokenManager()
    try:
        token = manager.get_token()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(
        archive_channel(
            token=token,
            channel_id=args.channel,
            output_dir=args.output,
            fmt=args.format,
            days=args.days,
            include_threads=not args.no_threads,
        )
    )


if __name__ == "__main__":
    main()
