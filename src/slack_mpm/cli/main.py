"""CLI entry points for Slack MCP server."""

import asyncio
import sys

import click

from slack_mpm.__version__ import __version__
from slack_mpm.auth.token_manager import TokenManager


@click.group()
@click.version_option(version=__version__, prog_name="slack-mpm")
def main() -> None:
    """Slack MCP Server - Slack workspace integration via Model Context Protocol."""


@main.command()
def setup() -> None:
    """Verify Slack token configuration and workspace connectivity."""
    click.echo("Slack MCP Setup")
    click.echo("=" * 50)

    manager = TokenManager()

    # Check bot token
    if not manager.has_bot_token():
        click.echo(click.style("ERROR: SLACK_BOT_TOKEN is not set.", fg="red"))
        click.echo()
        click.echo("To fix this:")
        click.echo("  1. Copy .env.local.example to .env.local")
        click.echo("  2. Add your Slack bot token: SLACK_BOT_TOKEN=xoxb-...")
        click.echo()
        click.echo("Get a bot token at: https://api.slack.com/apps")
        sys.exit(1)

    click.echo(f"Bot token found: {_mask_token(manager.bot_token or '')}")

    if manager.has_user_token():
        click.echo(f"User token found: {_mask_token(manager.user_token or '')}")
    else:
        click.echo(click.style("User token: not configured (optional)", fg="yellow"))

    # Validate tokens
    click.echo()
    click.echo("Validating bot token...")

    async def _validate() -> None:
        bot_result = await manager.validate_bot_token()
        if bot_result.status.value == "valid":
            click.echo(click.style("Bot token: VALID", fg="green"))
            if bot_result.team_name:
                click.echo(f"  Workspace: {bot_result.team_name}")
            if bot_result.team_id:
                click.echo(f"  Team ID:   {bot_result.team_id}")
            if bot_result.user_id:
                click.echo(f"  Bot User:  {bot_result.user_id}")
        else:
            click.echo(click.style(f"Bot token: INVALID ({bot_result.status.value})", fg="red"))
            sys.exit(1)

        if manager.has_user_token():
            click.echo()
            click.echo("Validating user token...")
            user_result = await manager.validate_user_token()
            if user_result.status.value == "valid":
                click.echo(click.style("User token: VALID", fg="green"))
                if user_result.user_id:
                    click.echo(f"  User ID: {user_result.user_id}")
            else:
                click.echo(
                    click.style(f"User token: INVALID ({user_result.status.value})", fg="yellow")
                )

    asyncio.run(_validate())

    click.echo()
    click.echo(click.style("Setup complete! Run 'slack-mpm mcp' to start the server.", fg="green"))


@main.command()
def doctor() -> None:
    """Check Slack MCP installation health and configuration status."""
    click.echo("Slack MCP Doctor")
    click.echo("=" * 50)

    # Check Python version
    py_version = sys.version_info
    py_ok = py_version >= (3, 10)
    py_status = click.style("OK", fg="green") if py_ok else click.style("FAIL", fg="red")
    click.echo(f"Python version {py_version.major}.{py_version.minor}: [{py_status}]")

    if not py_ok:
        click.echo(click.style("  Requires Python 3.10+", fg="red"))

    # Check dependencies
    click.echo()
    click.echo("Checking dependencies...")

    deps = {
        "mcp": "mcp",
        "click": "click",
        "pydantic": "pydantic",
        "httpx": "httpx",
        "dotenv": "dotenv",
        "anyio": "anyio",
    }

    all_deps_ok = True
    for name, module in deps.items():
        try:
            __import__(module)
            click.echo(f"  {name}: [{click.style('OK', fg='green')}]")
        except ImportError:
            click.echo(f"  {name}: [{click.style('MISSING', fg='red')}]")
            all_deps_ok = False

    if not all_deps_ok:
        click.echo(click.style("\nRun 'uv sync' to install missing dependencies.", fg="yellow"))

    # Check token configuration
    click.echo()
    click.echo("Checking token configuration...")

    manager = TokenManager()

    if manager.has_bot_token():
        click.echo(
            f"  SLACK_BOT_TOKEN: [{click.style('SET', fg='green')}] "
            f"({_mask_token(manager.bot_token or '')})"
        )
    else:
        click.echo(f"  SLACK_BOT_TOKEN: [{click.style('MISSING', fg='red')}] (required)")

    if manager.has_user_token():
        click.echo(
            f"  SLACK_USER_TOKEN: [{click.style('SET', fg='green')}] "
            f"({_mask_token(manager.user_token or '')})"
        )
    else:
        click.echo(
            f"  SLACK_USER_TOKEN: [{click.style('NOT SET', fg='yellow')}] "
            "(optional, needed for search/status)"
        )

    if manager.signing_secret:
        click.echo(f"  SLACK_SIGNING_SECRET: [{click.style('SET', fg='green')}]")
    else:
        click.echo(
            f"  SLACK_SIGNING_SECRET: [{click.style('NOT SET', fg='yellow')}] (optional)"
        )

    if manager.team_id:
        click.echo(
            f"  SLACK_TEAM_ID: [{click.style('SET', fg='green')}] ({manager.team_id})"
        )
    else:
        click.echo(f"  SLACK_TEAM_ID: [{click.style('NOT SET', fg='yellow')}] (optional)")

    # Token validation
    if manager.has_bot_token():
        click.echo()
        click.echo("Validating tokens...")

        async def _check_tokens() -> None:
            result = await manager.validate_bot_token()
            if result.status.value == "valid":
                team = result.team_name or "unknown"
                click.echo(
                    f"  Bot token auth.test: [{click.style('PASS', fg='green')}] "
                    f"(workspace: {team})"
                )
            else:
                click.echo(
                    f"  Bot token auth.test: [{click.style('FAIL', fg='red')}] "
                    f"(status: {result.status.value})"
                )

        asyncio.run(_check_tokens())

    click.echo()
    if manager.has_bot_token() and all_deps_ok and py_ok:
        click.echo(click.style("All checks passed! Ready to run.", fg="green"))
    else:
        click.echo(click.style("Some checks failed. See above for details.", fg="yellow"))


@main.command(name="mcp")
def mcp_server() -> None:
    """Start the Slack MCP server in stdio mode for use with Claude Desktop."""
    import anyio

    from slack_mpm.server.slack_mcp_server import SlackMCPServer

    server = SlackMCPServer()

    async def _run() -> None:
        await server.run()

    anyio.run(_run)


def _mask_token(token: str) -> str:
    """Return a masked version of a token for display."""
    if not token or len(token) <= 10:
        return "***"
    return token[:6] + "..." + token[-4:]


if __name__ == "__main__":
    main()
