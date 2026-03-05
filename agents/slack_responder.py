#!/usr/bin/env python3
"""Slack Responder Agent - monitors for mentions/DMs and auto-responds.

Polls for messages mentioning the bot user or direct messages, and replies
with a configured response. Useful for automated acknowledgements, out-of-office
bots, or simple chatbots.

Usage:
    uv run agents/slack_responder.py --response "Thanks, I'll get back to you shortly!"
    uv run agents/slack_responder.py --channel C1234567890 --response "Got it!"
    uv run agents/slack_responder.py --response "Away: back Monday" --interval 60
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slack_mcp.api import messages, workspace
from slack_mcp.auth.token_manager import TokenManager


async def get_bot_user_id(token: str) -> str | None:
    """Get the user ID of the bot associated with the token.

    Args:
        token: Slack bot token.

    Returns:
        Bot user ID string, or None if it cannot be determined.
    """
    try:
        data = await workspace.auth_test(token)
        return data.get("user_id")
    except Exception:
        return None


async def monitor_and_respond(
    token: str,
    response_text: str,
    channel: str | None,
    interval: int,
    dry_run: bool,
) -> None:
    """Monitor for mentions and DMs, auto-reply with configured response.

    Args:
        token: Slack bot token.
        response_text: Text to reply with.
        channel: Optional channel ID to monitor; if None monitors all DMs.
        interval: Polling interval in seconds.
        dry_run: If True, print what would be sent but do not actually send.
    """
    bot_user_id = await get_bot_user_id(token)
    if bot_user_id:
        print(f"Bot user ID: {bot_user_id}")

    # Track last-seen timestamps per channel to avoid re-processing
    last_seen: dict[str, str] = {}
    responded: set[str] = set()  # Track ts values already responded to

    # Initialize last_seen with current time to avoid responding to old messages
    now_ts = str(datetime.now(tz=timezone.utc).timestamp())

    if channel:
        last_seen[channel] = now_ts
        channels_to_monitor = [channel]
        print(f"Monitoring channel {channel} for mentions (polling every {interval}s).")
    else:
        print(f"Monitoring DMs for messages (polling every {interval}s).")

    print(f"Auto-response: '{response_text}'")
    if dry_run:
        print("[DRY RUN - no messages will be sent]")
    print("-" * 60)

    while True:
        await asyncio.sleep(interval)

        try:
            if channel:
                # Monitor specific channel for @mentions
                oldest = last_seen.get(channel, now_ts)
                data = await messages.list_history(token, channel, limit=20, oldest=oldest)
                msgs = data.get("messages", [])

                for msg in msgs:
                    msg_ts = msg.get("ts", "")
                    if msg_ts in responded:
                        continue

                    msg_text = msg.get("text", "")
                    msg_user = msg.get("user", "")

                    # Check if bot is mentioned or if message is from a user (not bot)
                    is_mention = bot_user_id and f"<@{bot_user_id}>" in msg_text
                    is_from_user = msg_user and msg_user != bot_user_id

                    if is_mention and is_from_user:
                        print(f"Mention from {msg_user}: {msg_text[:80]}...")
                        if not dry_run:
                            await messages.reply_in_thread(
                                token=token,
                                channel=channel,
                                thread_ts=msg_ts,
                                text=response_text,
                            )
                        else:
                            print(f"  -> Would reply: {response_text}")
                        responded.add(msg_ts)

                    if msg_ts > last_seen.get(channel, "0"):
                        last_seen[channel] = msg_ts

            else:
                # Monitor DM channels
                # Get list of DM channels (im type)
                from slack_mcp.api import channels as ch_api

                dm_data = await ch_api.list_channels(token, types="im", exclude_archived=True)
                dm_channels = dm_data.get("channels", [])

                for dm in dm_channels:
                    dm_id = dm.get("id", "")
                    if not dm_id:
                        continue

                    oldest = last_seen.get(dm_id, now_ts)
                    try:
                        hist = await messages.list_history(token, dm_id, limit=10, oldest=oldest)
                    except Exception:
                        continue

                    for msg in hist.get("messages", []):
                        msg_ts = msg.get("ts", "")
                        if msg_ts in responded:
                            continue

                        msg_user = msg.get("user", "")
                        msg_text = msg.get("text", "")

                        # Only respond to messages from real users (not the bot itself)
                        if msg_user and msg_user != bot_user_id:
                            print(f"DM from {msg_user}: {msg_text[:80]}")
                            if not dry_run:
                                await messages.send_message(
                                    token=token,
                                    channel=dm_id,
                                    text=response_text,
                                    thread_ts=msg_ts,
                                )
                            else:
                                print(f"  -> Would reply: {response_text}")
                            responded.add(msg_ts)

                        if msg_ts > last_seen.get(dm_id, "0"):
                            last_seen[dm_id] = msg_ts

        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"Error in monitoring loop: {exc}", file=sys.stderr)


def main() -> None:
    """Entry point for the Slack responder agent."""
    parser = argparse.ArgumentParser(
        description="Monitor Slack for mentions/DMs and auto-respond.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/slack_responder.py --response "Thanks, I'll get back to you!"
  uv run agents/slack_responder.py --channel C1234567890 --response "Got it!"
  uv run agents/slack_responder.py --response "Out of office" --interval 60 --dry-run
        """,
    )
    parser.add_argument(
        "--response",
        required=True,
        help="Text to auto-respond with when a message is received",
    )
    parser.add_argument(
        "--channel",
        help="Channel ID to monitor for @mentions. If omitted, monitors all DMs.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without actually sending",
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
            monitor_and_respond(
                token=token,
                response_text=args.response,
                channel=args.channel,
                interval=args.interval,
                dry_run=args.dry_run,
            )
        )
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
