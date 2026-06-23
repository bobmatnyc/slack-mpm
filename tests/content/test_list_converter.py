"""Tests for markdown_to_list content converter."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_markdown_to_list_checklist() -> None:
    """markdown_to_list parses - [ ] and - [x] checklist syntax."""
    from slack_mpm.content.list_converter import markdown_to_list

    md = "- [ ] Task 1\n- [x] Task 2\n- [ ] Task 3"
    result = await markdown_to_list(content=md)

    assert len(result) == 3
    assert result[0] == {"value": "Task 1", "status": "incomplete"}
    assert result[1] == {"value": "Task 2", "status": "complete"}
    assert result[2] == {"value": "Task 3", "status": "incomplete"}


@pytest.mark.asyncio
async def test_markdown_to_list_checklist_status() -> None:
    """markdown_to_list maps - [x] to complete and - [ ] to incomplete."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="- [x] Done\n- [ ] Pending")
    assert result[0]["status"] == "complete"
    assert result[1]["status"] == "incomplete"


@pytest.mark.asyncio
async def test_markdown_to_list_checklist_case_insensitive() -> None:
    """markdown_to_list handles - [X] (uppercase X) as complete."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="- [X] Done")
    assert result[0]["status"] == "complete"


@pytest.mark.asyncio
async def test_markdown_to_list_bullet_list() -> None:
    """markdown_to_list parses bullet lists without status."""
    from slack_mpm.content.list_converter import markdown_to_list

    md = "- Apple\n- Banana\n- Cherry"
    result = await markdown_to_list(content=md)

    assert len(result) == 3
    assert result[0] == {"value": "Apple"}
    assert "status" not in result[0]


@pytest.mark.asyncio
async def test_markdown_to_list_table() -> None:
    """markdown_to_list parses markdown tables as list items."""
    from slack_mpm.content.list_converter import markdown_to_list

    md = "| Name | Status |\n| --- | --- |\n| Task 1 | pending |\n| Task 2 | done |"
    result = await markdown_to_list(content=md)

    assert len(result) == 2
    assert "Task 1" in result[0]["value"]
    assert "pending" in result[0]["value"]


@pytest.mark.asyncio
async def test_markdown_to_list_mixed() -> None:
    """markdown_to_list handles checklist and bullet items together."""
    from slack_mpm.content.list_converter import markdown_to_list

    md = "- [ ] Task 1\n- [x] Done\n- Regular item"
    result = await markdown_to_list(content=md)

    assert len(result) == 3
    assert result[0]["status"] == "incomplete"
    assert result[1]["status"] == "complete"
    assert "status" not in result[2]


@pytest.mark.asyncio
async def test_markdown_to_list_ignores_headings() -> None:
    """markdown_to_list ignores # heading lines."""
    from slack_mpm.content.list_converter import markdown_to_list

    md = "# My Tasks\n## Subtasks\n- [ ] Task 1\n- Item 2"
    result = await markdown_to_list(content=md)

    assert len(result) == 2
    assert result[0]["value"] == "Task 1"
    assert result[1]["value"] == "Item 2"


@pytest.mark.asyncio
async def test_markdown_to_list_from_file(tmp_path: Path) -> None:
    """markdown_to_list reads from file_path."""
    from slack_mpm.content.list_converter import markdown_to_list

    md_file = tmp_path / "tasks.md"
    md_file.write_text("- [ ] Task 1\n- [x] Done", encoding="utf-8")

    result = await markdown_to_list(file_path=str(md_file))
    assert len(result) == 2


@pytest.mark.asyncio
async def test_markdown_to_list_file_not_found() -> None:
    """markdown_to_list raises FileNotFoundError for missing file."""
    from slack_mpm.content.list_converter import markdown_to_list

    with pytest.raises(FileNotFoundError):
        await markdown_to_list(file_path="/nonexistent/tasks.md")


@pytest.mark.asyncio
async def test_markdown_to_list_neither_raises() -> None:
    """markdown_to_list raises ValueError when neither content nor file_path given."""
    from slack_mpm.content.list_converter import markdown_to_list

    with pytest.raises(ValueError, match="must be provided"):
        await markdown_to_list()


@pytest.mark.asyncio
async def test_markdown_to_list_empty_content() -> None:
    """markdown_to_list returns empty list for empty content."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="")
    assert result == []


@pytest.mark.asyncio
async def test_markdown_to_list_whitespace_only() -> None:
    """markdown_to_list returns empty list for whitespace-only content."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="   \n\t  ")
    assert result == []


@pytest.mark.asyncio
async def test_markdown_to_list_returns_list_of_dicts() -> None:
    """markdown_to_list return type is list[dict]."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="- Item 1\n- [ ] Task")
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, dict)
        assert "value" in item


@pytest.mark.asyncio
async def test_markdown_to_list_star_bullet() -> None:
    """markdown_to_list handles * bullet syntax."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="* First\n* Second")
    assert len(result) == 2
    assert result[0]["value"] == "First"


@pytest.mark.asyncio
async def test_markdown_to_list_plus_bullet() -> None:
    """markdown_to_list handles + bullet syntax."""
    from slack_mpm.content.list_converter import markdown_to_list

    result = await markdown_to_list(content="+ Alpha\n+ Beta")
    assert len(result) == 2
    assert result[0]["value"] == "Alpha"
