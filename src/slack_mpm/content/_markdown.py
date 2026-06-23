"""Shared markdown parsing utilities."""

from __future__ import annotations

from markdown_it import MarkdownIt  # type: ignore[import-not-found]


def make_parser() -> MarkdownIt:
    """Create a configured markdown-it parser instance.

    Why: Centralises parser creation so all converters share the same config.
    What: Returns a CommonMark-compliant MarkdownIt parser with tables enabled.
    Test: Call make_parser(), verify it has a 'render' method and can parse tables.
    """
    return MarkdownIt("commonmark").enable("table")


def read_content(
    content: str | None,
    file_path: str | None,
    caller: str = "conversion",
) -> str:
    """Read markdown content from a string or file path.

    Why: Both canvas and list converters need the same source-resolution logic.
    What: Returns content string; reads UTF-8 file if file_path provided.
    Test: Pass content="hello", verify "hello" returned; pass nonexistent file_path, verify
    FileNotFoundError raised.

    Args:
        content: Markdown string (mutually exclusive with file_path).
        file_path: Path to a .md file (read as UTF-8).
        caller: Label used in error messages (e.g., "markdown_to_canvas").

    Returns:
        Markdown string.

    Raises:
        ValueError: If neither or both of content/file_path are provided.
        FileNotFoundError: If file_path does not exist.
    """
    if content is not None and file_path is not None:
        raise ValueError(f"{caller}: provide either content or file_path, not both")
    if content is None and file_path is None:
        raise ValueError(f"{caller}: either content or file_path must be provided")

    if file_path is not None:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"{caller}: file not found: {file_path}")
        return path.read_text(encoding="utf-8")

    # content is not None here (type-narrowed by the guards above)
    return content  # type: ignore[return-value]
