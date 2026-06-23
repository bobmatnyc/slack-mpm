"""Tests for ContentConversionError."""

from __future__ import annotations

import pytest


def test_content_conversion_error_message() -> None:
    """ContentConversionError stores and exposes the message."""
    from slack_mpm.content.errors import ContentConversionError

    exc = ContentConversionError("Something went wrong")
    assert exc.message == "Something went wrong"
    assert str(exc) == "Something went wrong"


def test_content_conversion_error_original_error() -> None:
    """ContentConversionError stores the original_error."""
    from slack_mpm.content.errors import ContentConversionError

    original = ValueError("bad input")
    exc = ContentConversionError("Conversion failed", original_error=original)
    assert exc.original_error is original


def test_content_conversion_error_no_original() -> None:
    """ContentConversionError works without original_error."""
    from slack_mpm.content.errors import ContentConversionError

    exc = ContentConversionError("Simple error")
    assert exc.original_error is None


def test_content_conversion_error_is_exception() -> None:
    """ContentConversionError is an Exception subclass."""
    from slack_mpm.content.errors import ContentConversionError

    with pytest.raises(ContentConversionError, match="test"):
        raise ContentConversionError("test")
