#!/usr/bin/env python3
"""Slack Listener Agent - polls channels for new messages and prints them.

Usage:
    uv run agents/slack_listener.py --channel C1234567890
    uv run agents/slack_listener.py --channel C1234567890 --interval 30
    uv run agents/slack_listener.py --channel general --interval 10 --limit 10
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slack_mpm.api import messages
from slack_mpm.auth.token_manager import TokenManager


def _format_message(msg: dict) -> str:
    """Format a Slack message dict for terminal output."""
    ts = msg.get("ts", "")
    user = msg.get("user", msg.get("bot_id", "unknown"))
    text = msg.get("text", "")

    # Convert Unix timestamp to readable datetime
    try:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%H:%M:%S")
    except (ValueError, TypeError):
        dt = ts

    return f"[{dt}] {user}: {text}"


async def poll_channel(
    token: str,
    channel: str,
    interval: int,
    limit: int,
    show_history: bool,
) -> None:
    """Poll a channel for new messages and print them.

    Args:
        token: Slack bot token.
        channel: Channel ID to poll.
        interval: Polling interval in seconds.
        limit: Max messages to fetch per poll.
        show_history: If True, print last `limit` messages on startup.
    """
    # Track the timestamp of the last seen message
    last_ts: str | None = None

    print(f"Listening on channel {channel} (polling every {interval}s). Ctrl+C to stop.")
    print("-" * 60)

    # On startup, optionally fetch recent history
    if show_history:
        try:
            data = await messages.list_history(token, channel, limit=limit)
            msgs = data.get("messages", [])
            msgs.reverse()  # Oldest first
            for msg in msgs:
                print(_format_message(msg))
            if msgs:
                last_ts = msgs[-1].get("ts")
        except Exception as exc:
            print(f"Warning: Could not fetch history: {exc}", file=sys.stderr)

    # Poll loop
    while True:
        await asyncio.sleep(interval)
        try:
            params: dict = {"limit": limit}
            if last_ts:
                params["oldest"] = last_ts

            data = await messages.list_history(token, channel, **params)
            new_msgs = data.get("messages", [])
            new_msgs.reverse()  # Oldest first

            for msg in new_msgs:
                msg_ts = msg.get("ts", "")
                # Skip the message that marks our cursor position
                if last_ts and msg_ts <= last_ts:
                    continue
                print(_format_message(msg))
                last_ts = msg_ts

        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"Error polling channel: {exc}", file=sys.stderr)


def main() -> None:
    """Entry point for the Slack listener agent."""
    parser = argparse.ArgumentParser(
        description="Poll a Slack channel for new messages and print them to stdout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/slack_listener.py --channel C1234567890
  uv run agents/slack_listener.py --channel C1234567890 --interval 10
  uv run agents/slack_listener.py --channel C1234567890 --no-history
        """,
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Slack channel ID (e.g., C1234567890) to listen to",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max messages to fetch per poll (default: 20)",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Skip showing recent message history on startup",
    )
    args = parser.parse_args()

    manager = TokenManager()
    try:
        token = manager.get_token()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(
            poll_channel(
                token=token,
                channel=args.channel,
                interval=args.interval,
                limit=args.limit,
                show_history=not args.no_history,
            )
        )
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
