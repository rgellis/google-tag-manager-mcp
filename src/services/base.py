"""Shared plumbing for Tag Manager service modules."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, TypeVar, cast

from fastmcp import Context
from googleapiclient.errors import HttpError

from src.client import ReadOnlyError
from src.utils import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

#: Appended to the API's own message for status codes whose Tag Manager meaning
#: is narrower than the generic HTTP one. Each of these cost real debugging time
#: before being written down.
STATUS_HINTS: Dict[int, str] = {
    400: (
        "a 400 here is usually either a malformed relative path or a stale "
        "fingerprint -- Tag Manager uses fingerprints for optimistic "
        "concurrency, so re-read the entity and resend with the fingerprint "
        "from that response"
    ),
    403: (
        "a 403 here usually means the authenticated user lacks the required "
        "Tag Manager permission on this account or container, or the token is "
        "missing the scope for this operation -- Tag Manager splits write "
        "access six ways, and a token minted with TAG_MANAGER_READ_ONLY=true "
        "cannot write at all"
    ),
    404: (
        "a 404 here usually means one of the IDs in the path does not exist or "
        "is not visible to this user -- check the account, container and "
        "workspace IDs against list_accounts, list_containers and "
        "list_workspaces rather than against the Tag Manager UI's URL, which "
        "shows different numbers"
    ),
    409: (
        "a 409 means the entity was modified since it was read -- re-read it "
        "and resend with the fingerprint from that response"
    ),
    429: (
        "Tag Manager enforces a per-minute and per-day quota per account; back "
        "off and retry rather than looping"
    ),
}


def http_error_message(error: HttpError) -> str:
    """Extract the most useful message available from an HttpError.

    The API returns a JSON error body that is far more informative than the
    exception's own repr, but it is not always present or well-formed.
    """
    status = error.resp.status

    detail = ""
    try:
        payload: object = json.loads(error.content.decode("utf-8"))
    except (ValueError, AttributeError, UnicodeDecodeError):
        payload = None

    if isinstance(payload, dict):
        inner = cast(Dict[str, Any], payload).get("error")
        if isinstance(inner, dict):
            detail = str(cast(Dict[str, Any], inner).get("message", ""))

    if not detail:
        detail = str(error)

    hint = STATUS_HINTS.get(status)
    if hint:
        detail += f" ({hint})"

    return f"HTTP {status}: {detail}"


async def execute(ctx: Context, description: str, call: Callable[[], T]) -> T:
    """Run a blocking API call off the event loop with uniform error handling.

    The Tag Manager client is synchronous, so every call is dispatched to a
    worker thread rather than blocking the MCP event loop.

    Args:
        ctx: FastMCP context, used for structured logging.
        description: Human-readable description of the operation, used in errors.
        call: Zero-argument callable performing the blocking API request.

    Returns:
        Whatever ``call`` returns.
    """
    try:
        return await asyncio.to_thread(call)
    except ReadOnlyError as e:
        logger.error(str(e))
        raise
    except HttpError as e:
        message = f"Tag Manager API error while {description}: {http_error_message(e)}"
        logger.error(message)
        raise Exception(message) from e
    except Exception as e:
        message = f"Failed while {description}: {e}"
        logger.error(message)
        raise Exception(message) from e
