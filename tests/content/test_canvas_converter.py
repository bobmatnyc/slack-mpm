"""Tests for markdown_to_canvas content converter."""

from __future__ import annotations

from pathlib import Path

import pytest

from slack_mpm.content.errors import ContentConversionError


@pytest.mark.asyncio
async def test_markdown_to_canvas_from_string() -> None:
    """markdown_to_canvas returns validated markdown string from input string."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    md = "# Hello\n\nThis is **bold** text."
    result = await markdown_to_canvas(content=md)
    assert result == md


@pytest.mark.asyncio
async def test_markdown_to_canvas_from_file(tmp_path: Path) -> None:
    """markdown_to_canvas reads from file_path and returns its content."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    md_file = tmp_path / "report.md"
    md_file.write_text("# Report\nContent", encoding="utf-8")

    result = await markdown_to_canvas(file_path=str(md_file))
    assert "Report" in result


@pytest.mark.asyncio
async def test_markdown_to_canvas_file_not_found() -> None:
    """markdown_to_canvas raises FileNotFoundError for missing file."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    with pytest.raises(FileNotFoundError):
        await markdown_to_canvas(file_path="/nonexistent/path.md")


@pytest.mark.asyncio
async def test_markdown_to_canvas_invalid_input_neither() -> None:
    """markdown_to_canvas raises ValueError when neither content nor file_path given."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    with pytest.raises(ValueError, match="must be provided"):
        await markdown_to_canvas()


@pytest.mark.asyncio
async def test_markdown_to_canvas_invalid_input_both(tmp_path: Path) -> None:
    """markdown_to_canvas raises ValueError when both content and file_path given."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    md_file = tmp_path / "file.md"
    md_file.write_text("content", encoding="utf-8")

    with pytest.raises(ValueError, match="not both"):
        await markdown_to_canvas(content="text", file_path=str(md_file))


@pytest.mark.asyncio
async def test_markdown_to_canvas_empty_content_raises() -> None:
    """markdown_to_canvas raises ContentConversionError for empty/whitespace input."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    with pytest.raises(ContentConversionError, match="empty"):
        await markdown_to_canvas(content="   \n\t  ")


@pytest.mark.asyncio
async def test_markdown_to_canvas_validation_passthrough() -> None:
    """markdown_to_canvas correctly handles complex markdown structures."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    complex_md = """# Title

## Section 1

- Item 1
- Item 2

```python
print("hello")
```

| Col1 | Col2 |
|------|------|
| A    | B    |
"""
    result = await markdown_to_canvas(content=complex_md)
    assert result == complex_md


@pytest.mark.asyncio
async def test_markdown_to_canvas_returns_string() -> None:
    """markdown_to_canvas return type is str."""
    from slack_mpm.content.canvas_converter import markdown_to_canvas

    result = await markdown_to_canvas(content="# Hello")
    assert isinstance(result, str)
