"""Tests for EnvironmentsService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.environments_service import (
    EnvironmentsService,
    register_environments_tools,
)
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    CONTAINER_PATH,
    container_child,
)

ENVIRONMENT_ID = "5"
ENVIRONMENT_PATH = f"{CONTAINER_PATH}/environments/{ENVIRONMENT_ID}"


@pytest.fixture
def service() -> EnvironmentsService:
    return EnvironmentsService()


@pytest.fixture
def resource(mock_api: Mock) -> Any:
    return container_child(mock_api, "environments")


@pytest.mark.asyncio
async def test_list_environments(
    service: EnvironmentsService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.list.return_value.execute.return_value = {"environment": []}

    result = await service.list_environments(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"environment": []}
    resource.list.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_list_environments_pages(
    service: EnvironmentsService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.list.return_value.execute.return_value = {}

    await service.list_environments(mock_ctx, ACCOUNT_ID, CONTAINER_ID, "token")

    resource.list.assert_called_once_with(parent=CONTAINER_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_get_environment(
    service: EnvironmentsService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.get.return_value.execute.return_value = {"name": "Staging"}

    result = await service.get_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID
    )

    assert result == {"name": "Staging"}
    resource.get.assert_called_once_with(path=ENVIRONMENT_PATH)


@pytest.mark.asyncio
async def test_create_environment(
    service: EnvironmentsService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"name": "Staging"}
    resource.create.return_value.execute.return_value = body

    result = await service.create_environment(mock_ctx, ACCOUNT_ID, CONTAINER_ID, body)

    assert result == body
    install_client.require_write.assert_called_once_with("create_environment")
    resource.create.assert_called_once_with(parent=CONTAINER_PATH, body=body)


@pytest.mark.asyncio
async def test_update_environment(
    service: EnvironmentsService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.update.return_value.execute.return_value = {}

    await service.update_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID, {"name": "S"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_environment")
    resource.update.assert_called_once_with(
        path=ENVIRONMENT_PATH, body={"name": "S"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_environment_without_a_fingerprint(
    service: EnvironmentsService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.update.return_value.execute.return_value = {}

    await service.update_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID, {"name": "S"}
    )

    resource.update.assert_called_once_with(path=ENVIRONMENT_PATH, body={"name": "S"})


@pytest.mark.asyncio
async def test_delete_environment(
    service: EnvironmentsService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.delete.return_value.execute.return_value = ""

    result = await service.delete_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID
    )

    assert result == {"path": ENVIRONMENT_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_environment")


@pytest.mark.asyncio
async def test_reauthorize_sends_an_empty_body_by_default(
    service: EnvironmentsService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    """The API requires a body it makes no use of."""
    resource.reauthorize.return_value.execute.return_value = {
        "authorizationCode": "new"
    }

    result = await service.reauthorize_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID
    )

    assert result == {"authorizationCode": "new"}
    install_client.require_write.assert_called_once_with("reauthorize_environment")
    resource.reauthorize.assert_called_once_with(path=ENVIRONMENT_PATH, body={})


@pytest.mark.asyncio
async def test_reauthorize_passes_a_supplied_body(
    service: EnvironmentsService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.reauthorize.return_value.execute.return_value = {}

    await service.reauthorize_environment(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, ENVIRONMENT_ID, {"name": "Staging"}
    )

    resource.reauthorize.assert_called_once_with(
        path=ENVIRONMENT_PATH, body={"name": "Staging"}
    )


@pytest.mark.asyncio
async def test_environments_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_environments_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_environments",
        "get_environment",
        "create_environment",
        "update_environment",
        "delete_environment",
        "reauthorize_environment",
    }
