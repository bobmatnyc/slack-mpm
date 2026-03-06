#!/usr/bin/env python3
"""Slack Notifier Agent - sends messages or alerts to Slack channels.

Usage:
    uv run agents/slack_notifier.py --channel C1234567890 --message "Deploy complete"
    uv run agents/slack_notifier.py --channel C1234567890 --message "Alert!" --thread-ts 1234567890.123456
    echo "alert text" | uv run agents/slack_notifier.py --channel C1234567890
    cat report.txt | uv run agents/slack_notifier.py --channel C1234567890 --as-file --filename report.txt
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running as a standalone script from the project root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slack_mpm.api import files, messages
from slack_mpm.auth.token_manager import TokenManager


async def send_notification(
    token: str,
    channel: str,
    text: str,
    thread_ts: str | None,
    as_file: bool,
    filename: str,
    title: str | None,
) -> None:
    """Send a notification to a Slack channel.

    Args:
        token: Slack bot token.
        channel: Channel ID to send to.
        text: Message text or file content.
        thread_ts: Optional thread timestamp to reply in.
        as_file: If True, upload text as a file instead of a message.
        filename: Filename for file upload.
        title: Optional file title.
    """
    if as_file:
        result = await files.upload_file(
            token=token,
            channels=[channel],
            content=text,
            filename=filename,
            title=title,
        )
        file_id = result.get("files", [{}])[0].get("id", "unknown")
        print(f"File uploaded: {file_id}")
    else:
        result = await messages.send_message(
            token=token,
            channel=channel,
            text=text,
            thread_ts=thread_ts,
        )
        ts = result.get("ts", "unknown")
        print(f"Message sent: {ts}")


def main() -> None:
    """Entry point for the Slack notifier agent."""
    parser = argparse.ArgumentParser(
        description="Send messages or alerts to a Slack channel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run agents/slack_notifier.py --channel C1234567890 --message "Deploy complete"
  uv run agents/slack_notifier.py --channel C1234567890 --message "Alert!" --thread-ts 1234567890.123
  echo "alert text" | uv run agents/slack_notifier.py --channel C1234567890
  cat report.txt | uv run agents/slack_notifier.py --channel C1234567890 --as-file --filename report.txt
        """,
    )
    parser.add_argument(
        "--channel",
        required=True,
        help="Slack channel ID (e.g., C1234567890) to send to",
    )
    parser.add_argument(
        "--message",
        help="Message text to send. If not provided, reads from stdin.",
    )
    parser.add_argument(
        "--thread-ts",
        help="Thread timestamp to reply in a thread",
    )
    parser.add_argument(
        "--as-file",
        action="store_true",
        help="Upload the message content as a file instead of a text message",
    )
    parser.add_argument(
        "--filename",
        default="message.txt",
        help="Filename for file upload (default: message.txt)",
    )
    parser.add_argument(
        "--title",
        help="Optional title for file upload",
    )
    args = parser.parse_args()

    # Get message text from arg or stdin
    if args.message:
        text = args.message
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if not text:
            print("Error: No message text provided via --message or stdin.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Provide --message or pipe text via stdin.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    manager = TokenManager()
    try:
        token = manager.get_token()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(
            send_notification(
                token=token,
                channel=args.channel,
                text=text,
                thread_ts=args.thread_ts,
                as_file=args.as_file,
                filename=args.filename,
                title=args.title,
            )
        )
    except Exception as exc:
        print(f"Error sending notification: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
