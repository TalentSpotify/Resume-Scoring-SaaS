"""
Shared utility helpers.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def safe_filename(name: str) -> str:
    """Sanitize a filename for S3 keys."""
    import re
    return re.sub(r"[^\w\-.]", "_", name)
