"""Markdown to Canvas conversion."""

from __future__ import annotations

from slack_mpm.content._markdown import make_parser, read_content
from slack_mpm.content.errors import ContentConversionError


async def markdown_to_canvas(
    content: str | None = None,
    file_path: str | None = None,
) -> str:
    """Convert markdown to canvas document_content.

    Why: Slack Canvas natively accepts markdown; this function validates input
    and handles file reading so callers get clean, canvas-ready content.
    What: Reads content from string or file, validates it parses as markdown,
    and returns the validated string suitable for canvases.create().
    Test: Pass valid markdown string, assert same string returned; pass empty
    string, assert ContentConversionError raised.

    Args:
        content: Markdown string.
        file_path: Path to a .md file (read as UTF-8).

    Returns:
        Validated markdown string suitable for canvas creation.

    Raises:
        ContentConversionError: On invalid markdown or empty content.
        FileNotFoundError: If file_path does not exist.
        ValueError: If neither content nor file_path is provided (or both).
    """
    try:
        raw = read_content(content, file_path, caller="markdown_to_canvas")
    except (ValueError, FileNotFoundError):
        raise

    if not raw.strip():
        raise ContentConversionError(
            "markdown_to_canvas: content is empty — provide non-empty markdown"
        )

    # Validate that the content is parseable markdown (will always succeed for
    # CommonMark, but catches non-string or encoding edge cases handled above).
    try:
        parser = make_parser()
        parser.render(raw)
    except Exception as exc:
        raise ContentConversionError(
            f"markdown_to_canvas: failed to parse markdown — {exc}",
            original_error=exc,
        ) from exc

    return raw
