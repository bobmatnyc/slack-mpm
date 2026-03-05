#!/usr/bin/env python3
"""Slack Digest Agent - generates activity digest for channels.

Summarizes recent activity: top messages, active users, thread highlights.

Usage:
    uv run agents/slack_digest.py --channel C1234567890
    uv run agents/slack_digest.py --channel C1234567890 --hours 24
    uv run agents/slack_digest.py --channel C1234567890 --hours 168 --top-users 10
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slack_mcp.api import channels, messages, users
from slack_mcp.auth.token_manager import TokenManager


def _ts_to_dt(ts: str) -> datetime:
    """Convert a Slack timestamp string to a datetime object."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(tz=timezone.utc)


async def build_digest(
    token: str,
    channel_id: str,
    hours: int,
    top_users: int,
    top_threads: int,
) -> None:
    """Build and print an activity digest for a channel.

    Args:
        token: Slack bot token.
        channel_id: Channel ID to generate digest for.
        hours: Number of hours of history to include.
        top_users: Number of top active users to display.
        top_threads: Number of top threads to display.
    """
    cutoff = time.time() - (hours * 3600)
    oldest = str(cutoff)

    # Fetch channel info
    try:
        ch_data = await channels.get_channel_info(token, channel_id)
        ch_name = ch_data.get("channel", {}).get("name", channel_id)
    except Exception:
        ch_name = channel_id

    print(f"Slack Digest: #{ch_name}")
    print(f"Period: Last {hours} hour(s)")
    print(f"Generated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Fetch messages
    try:
        hist_data = await messages.list_history(token, channel_id, limit=1000, oldest=oldest)
    except Exception as exc:
        print(f"Error fetching channel history: {exc}", file=sys.stderr)
        sys.exit(1)

    all_msgs = hist_data.get("messages", [])

    # Filter out subtypes (join/leave/etc), keep only real messages
    real_msgs = [m for m in all_msgs if not m.get("subtype") and m.get("text")]
    thread_parents = [m for m in real_msgs if int(m.get("reply_count", 0)) > 0]

    # User cache for display names
    user_cache: dict[str, str] = {}

    async def get_display_name(user_id: str) -> str:
        if user_id in user_cache:
            return user_cache[user_id]
        try:
            u_data = await users.get_user_info(token, user_id)
            profile = u_data.get("user", {}).get("profile", {})
            name = (
                profile.get("display_name")
                or profile.get("real_name")
                or user_id
            )
        except Exception:
            name = user_id
        user_cache[user_id] = name
        return name

    # Summary stats
    print(f"\nTotal messages: {len(real_msgs)}")
    print(f"Threads started: {len(thread_parents)}")

    # Active users
    user_counts: Counter[str] = Counter()
    for msg in real_msgs:
        user_id = msg.get("user", "")
        if user_id:
            user_counts[user_id] += 1

    if user_counts:
        print(f"\nTop {top_users} active users:")
        for user_id, count in user_counts.most_common(top_users):
            name = await get_display_name(user_id)
            print(f"  {name}: {count} message(s)")

    # Top threads by reply count
    if thread_parents:
        sorted_threads = sorted(
            thread_parents,
            key=lambda m: int(m.get("reply_count", 0)),
            reverse=True,
        )[:top_threads]

        print(f"\nTop {len(sorted_threads)} thread(s) by reply count:")
        for msg in sorted_threads:
            user_id = msg.get("user", "unknown")
            name = await get_display_name(user_id)
            reply_count = msg.get("reply_count", 0)
            text = msg.get("text", "")[:80].replace("\n", " ")
            ts = _ts_to_dt(msg.get("ts", "")).strftime("%H:%M UTC")
            print(f"  [{ts}] {name} ({reply_count} replies): {text}...")

    # Recent messages (last 5)
    if real_msgs:
        recent = list(reversed(real_msgs[:5]))
        print(f"\nMost recent {len(recent)} message(s):")
        for msg in recent:
            user_id = msg.get("user", "unknown")
            name = await get_display_name(user_id)
            text = msg.get("text", "")[:80].replace("\n", " ")
            ts = _ts_to_dt(msg.get("ts", "")).strftime("%H:%M UTC")
            print(f"  [{ts}] {name}: {text}")

    print("\n" + "=" * 60)
    print("Digest complete.")


def main() -> None:
    """Entry point for the Slack digest agent."""
    parser = argparse.ArgumentParser(
        description="Generate an activity digest for a Slack channel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/slack_digest.py --channel C1234567890
  uv run agents/slack_digest.py --channel C1234567890 --hours 24
  uv run agents/slack_digest.py --channel C1234567890 --hours 168 --top-users 10
        """,
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Slack channel ID (e.g., C1234567890) to generate digest for",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Number of hours of history to include (default: 24)",
    )
    parser.add_argument(
        "--top-users",
        type=int,
        default=5,
        help="Number of top active users to show (default: 5)",
    )
    parser.add_argument(
        "--top-threads",
        type=int,
        default=5,
        help="Number of top threads to show (default: 5)",
    )
    args = parser.parse_args()

    manager = TokenManager()
    try:
        token = manager.get_token()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(
        build_digest(
            token=token,
            channel_id=args.channel,
            hours=args.hours,
            top_users=args.top_users,
            top_threads=args.top_threads,
        )
    )


if __name__ == "__main__":
    main()
