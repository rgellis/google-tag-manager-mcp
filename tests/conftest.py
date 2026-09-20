"""Shared test fixtures for the Tag Manager MCP server."""

from __future__ import annotations

from typing import Any, AsyncIterator, Iterator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from src.client import SCOPES_FULL, TagManagerClient, set_client

ACCOUNT_ID = "6000000000"
CONTAINER_ID = "7000000"
WORKSPACE_ID = "3"
ENTITY_ID = "42"

ACCOUNT_PATH = f"accounts/{ACCOUNT_ID}"
CONTAINER_PATH = f"{ACCOUNT_PATH}/containers/{CONTAINER_ID}"
WORKSPACE_PATH = f"{CONTAINER_PATH}/workspaces/{WORKSPACE_ID}"


@pytest.fixture
def mock_api() -> Mock:
    """A mock of the Tag Manager resource client.

    Mirrors the nesting of the real client so services can be exercised as
    written: service.accounts().containers().workspaces().tags().list().execute()
    """
    return Mock()


@pytest.fixture
def mock_client(mock_api: Mock) -> Mock:
    """A mock TagManagerClient wrapping the mock API."""
    client = Mock(spec=TagManagerClient)
    client.service = mock_api
    client.read_only = False
    client.scopes = list(SCOPES_FULL)
    client.require_write = Mock(return_value=None)
    return client


@pytest.fixture(autouse=True)
def install_client(mock_client: Mock) -> Iterator[Mock]:
    """Install the mock client globally for the duration of each test."""
    set_client(mock_client)
    yield mock_client
    set_client(None)


@pytest_asyncio.fixture
async def mock_ctx() -> AsyncIterator[AsyncMock]:
    """A mock FastMCP context."""
    ctx = AsyncMock()
    ctx.log = AsyncMock()
    yield ctx


def accounts_resource(mock_api: Mock) -> Any:
    """The mock standing in for ``service.accounts()``."""
    return mock_api.accounts.return_value


def containers_resource(mock_api: Mock) -> Any:
    """The mock standing in for ``service.accounts().containers()``."""
    return accounts_resource(mock_api).containers.return_value


def workspaces_resource(mock_api: Mock) -> Any:
    """The mock for ``...containers().workspaces()``."""
    return containers_resource(mock_api).workspaces.return_value


def container_child(mock_api: Mock, name: str) -> Any:
    """The mock for a container-scoped sub-resource, e.g. ``versions``."""
    return getattr(containers_resource(mock_api), name).return_value


def workspace_child(mock_api: Mock, name: str) -> Any:
    """The mock for a workspace-scoped sub-resource, e.g. ``tags``."""
    return getattr(workspaces_resource(mock_api), name).return_value
