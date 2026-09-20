"""Shared helpers for the Tag Manager MCP server."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger that writes to stderr.

    stdout is reserved for the MCP stdio transport, so handlers must never
    write there.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def load_dotenv(dotenv_path: str = ".env") -> None:
    """Load a .env file into os.environ without overwriting existing values."""
    path = Path(dotenv_path)
    if not path.exists():
        return

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def optional(**kwargs: Any) -> Dict[str, Any]:
    """Drop unset (None) values from a set of API query parameters.

    ``google-api-python-client`` serialises whatever it is handed, so passing
    ``pageToken=None`` puts a literal ``pageToken=None`` on the query string
    rather than omitting it. Every optional parameter in this server therefore
    goes through here instead of being passed directly.
    """
    return {key: value for key, value in kwargs.items() if value is not None}
