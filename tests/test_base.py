"""Tests for off-loop dispatch and error translation."""

from __future__ import annotations

import asyncio
import threading
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from googleapiclient.errors import HttpError

from src.client import ReadOnlyError
from src.services.base import STATUS_HINTS, execute, http_error_message


def http_error(status: int, body: bytes) -> HttpError:
    response = Mock()
    response.status = status
    return HttpError(response, body)


def test_http_error_message_uses_the_json_error_body() -> None:
    error = http_error(400, b'{"error": {"message": "Bad fingerprint"}}')
    message = http_error_message(error)
    assert message.startswith("HTTP 400: Bad fingerprint")


def test_http_error_message_falls_back_on_unparseable_bodies() -> None:
    error = http_error(500, b"not json at all")
    assert http_error_message(error).startswith("HTTP 500: ")


def test_http_error_message_falls_back_on_a_json_non_object() -> None:
    error = http_error(500, b'"just a string"')
    assert http_error_message(error).startswith("HTTP 500: ")


def test_http_error_message_falls_back_when_error_is_not_an_object() -> None:
    error = http_error(500, b'{"error": "flat"}')
    assert http_error_message(error).startswith("HTTP 500: ")


def test_http_error_message_falls_back_on_an_empty_message() -> None:
    error = http_error(500, b'{"error": {"message": ""}}')
    assert http_error_message(error).startswith("HTTP 500: ")


@pytest.mark.parametrize("status", sorted(STATUS_HINTS))
def test_documented_statuses_carry_their_hint(status: int) -> None:
    error = http_error(status, b'{"error": {"message": "nope"}}')
    message = http_error_message(error)
    assert STATUS_HINTS[status] in message


def test_undocumented_statuses_get_no_hint() -> None:
    error = http_error(418, b'{"error": {"message": "teapot"}}')
    assert http_error_message(error) == "HTTP 418: teapot"


@pytest.mark.asyncio
async def test_execute_returns_the_calls_result(mock_ctx: AsyncMock) -> None:
    assert await execute(mock_ctx, "doing a thing", lambda: {"ok": True}) == {
        "ok": True
    }


@pytest.mark.asyncio
async def test_execute_runs_the_call_off_the_event_loop(
    mock_ctx: AsyncMock,
) -> None:
    caller = threading.current_thread().ident

    def call() -> int | None:
        return threading.current_thread().ident

    worker = await execute(mock_ctx, "checking the thread", call)
    assert worker != caller


@pytest.mark.asyncio
async def test_execute_lets_a_read_only_refusal_through(mock_ctx: AsyncMock) -> None:
    def call() -> Any:
        raise ReadOnlyError("refusing")

    with pytest.raises(ReadOnlyError, match="refusing"):
        await execute(mock_ctx, "writing", call)


@pytest.mark.asyncio
async def test_execute_translates_an_http_error(mock_ctx: AsyncMock) -> None:
    def call() -> Any:
        raise http_error(403, b'{"error": {"message": "Forbidden"}}')

    with pytest.raises(Exception) as caught:
        await execute(mock_ctx, "listing tags", call)

    message = str(caught.value)
    assert "Tag Manager API error while listing tags" in message
    assert "HTTP 403: Forbidden" in message


@pytest.mark.asyncio
async def test_execute_wraps_any_other_exception(mock_ctx: AsyncMock) -> None:
    def call() -> Any:
        raise ValueError("boom")

    with pytest.raises(Exception, match="Failed while listing tags: boom"):
        await execute(mock_ctx, "listing tags", call)


@pytest.mark.asyncio
async def test_execute_does_not_block_the_loop(mock_ctx: AsyncMock) -> None:
    """A slow synchronous call must not stop other coroutines running."""
    order: list[str] = []
    started = threading.Event()

    def slow() -> str:
        started.set()
        threading.Event().wait(0.05)
        order.append("api")
        return "done"

    async def other() -> None:
        started.wait(1.0)
        order.append("loop")

    result, _ = await asyncio.gather(execute(mock_ctx, "being slow", slow), other())

    assert result == "done"
    assert order == ["loop", "api"]
