"""Content conversion error types."""

from __future__ import annotations


class ContentConversionError(Exception):
    """Raised when markdown conversion fails.

    Why: Separates content-layer failures from Slack API failures so callers
    can handle malformed input distinctly from network/permission errors.
    What: Wraps parsing or validation errors with a descriptive message.
    Test: Instantiate with a message, verify str(exc) equals the message.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Initialize the error.

        Args:
            message: Human-readable description of what went wrong.
            original_error: The underlying exception that caused this error, if any.
        """
        self.message = message
        self.original_error = original_error
        super().__init__(message)
