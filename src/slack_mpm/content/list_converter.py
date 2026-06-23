"""Markdown to List conversion."""

from __future__ import annotations

import re
from typing import Any

from slack_mpm.content._markdown import read_content
from slack_mpm.content.errors import ContentConversionError

# Regex patterns for checklist items
_CHECKLIST_INCOMPLETE = re.compile(r"^\s*[-*+]\s+\[\s\]\s+(.*)")
_CHECKLIST_COMPLETE = re.compile(r"^\s*[-*+]\s+\[x\]\s+(.*)", re.IGNORECASE)
_BULLET_ITEM = re.compile(r"^\s*[-*+]\s+(.*)")
_HEADING = re.compile(r"^\s*#{1,6}\s+")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")


def _parse_table_rows(lines: list[str]) -> list[dict[str, Any]]:
    """Parse a markdown table into list items.

    Why: Tables are a common structured-data format that maps naturally to list rows.
    What: Extracts the header row for column names and data rows as joined values.
    Test: Pass a valid 2-column table, assert rows returned with correct values.
    """
    items: list[dict[str, Any]] = []
    header: list[str] = []
    parsing_header = True

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip separator lines (e.g., | --- | --- |)
        if _TABLE_SEPARATOR.match(stripped):
            parsing_header = False
            continue

        # Split on pipe, strip whitespace, filter empty
        cells = [c.strip() for c in stripped.strip("|").split("|")]

        if parsing_header:
            header = cells
            parsing_header = False
        else:
            if header:
                value = " | ".join(cells)
            else:
                value = " | ".join(cells)
            if value.strip():
                items.append({"value": value})

    return items


async def markdown_to_list(
    content: str | None = None,
    file_path: str | None = None,
) -> list[dict[str, Any]]:
    """Convert markdown to list items.

    Why: Enables bulk creation of Slack list items from markdown checklists/tables.
    What: Parses checklists (- [ ]/- [x]), bullet lists (- item), and tables;
    returns list of dicts with 'value' and optional 'status'.
    Test: Pass "- [ ] Task\\n- [x] Done\\n- Item", assert three items returned
    with correct statuses.

    Parsing rules:
    - ``- [ ] Task``  → status="incomplete"
    - ``- [x] Done``  → status="complete"
    - ``- Regular``   → no status
    - Table rows      → joined cell values, no status
    - Headings (#)    → ignored

    Args:
        content: Markdown string.
        file_path: Path to a .md file (read as UTF-8).

    Returns:
        List of dicts, each with 'value' and optional 'status'.

    Raises:
        ContentConversionError: On parsing errors.
        FileNotFoundError: If file_path does not exist.
        ValueError: If neither content nor file_path is provided (or both).
    """
    try:
        raw = read_content(content, file_path, caller="markdown_to_list")
    except (ValueError, FileNotFoundError):
        raise

    if not raw.strip():
        return []

    try:
        return _parse_markdown_to_items(raw)
    except ContentConversionError:
        raise
    except Exception as exc:
        raise ContentConversionError(
            f"markdown_to_list: unexpected parsing error — {exc}",
            original_error=exc,
        ) from exc


def _parse_markdown_to_items(raw: str) -> list[dict[str, Any]]:
    """Parse raw markdown string into list item dicts.

    Why: Separates parsing logic from I/O concerns for testability.
    What: Detects table vs. list structures and delegates accordingly.
    Test: Pass mixed checklist + bullet markdown, verify all items parsed.
    """
    lines = raw.splitlines()
    items: list[dict[str, Any]] = []

    # Detect if there's a table (pipe-delimited lines)
    table_lines: list[str] = []
    list_lines: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_table:
                # End of table block; parse what we have
                items.extend(_parse_table_rows(table_lines))
                table_lines = []
                in_table = False
            continue

        # Table detection: line contains pipe characters (not checklist)
        if (
            "|" in stripped
            and not _CHECKLIST_INCOMPLETE.match(line)
            and not _CHECKLIST_COMPLETE.match(line)
            and not _BULLET_ITEM.match(line)
        ):  # noqa: E501
            in_table = True
            table_lines.append(line)
        else:
            if in_table:
                # Transition out of table
                items.extend(_parse_table_rows(table_lines))
                table_lines = []
                in_table = False
            list_lines.append(line)

    # Flush any remaining table lines
    if table_lines:
        items.extend(_parse_table_rows(table_lines))

    # Parse non-table lines
    for line in list_lines:
        m_incomplete = _CHECKLIST_INCOMPLETE.match(line)
        m_complete = _CHECKLIST_COMPLETE.match(line)
        m_bullet = _BULLET_ITEM.match(line)

        if m_incomplete:
            items.append({"value": m_incomplete.group(1).strip(), "status": "incomplete"})
        elif m_complete:
            items.append({"value": m_complete.group(1).strip(), "status": "complete"})
        elif m_bullet:
            items.append({"value": m_bullet.group(1).strip()})
        elif _HEADING.match(line):
            # Headings are ignored
            continue
        # Other lines (blank, code fences, etc.) are silently skipped

    return items
