"""Version information for slack-mpm."""

from pathlib import Path

_VERSION_FILE = Path(__file__).parent / "VERSION"
__version__ = _VERSION_FILE.read_text().strip()
