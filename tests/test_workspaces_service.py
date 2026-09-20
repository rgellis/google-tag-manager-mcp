"""Tests for WorkspacesService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.workspaces_service import (
    WorkspacesService,
    register_workspaces_tools,
)
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    CONTAINER_PATH,
    WORKSPACE_ID,
    WORKSPACE_PATH,
    workspaces_resource,
)


@pytest.fixture
def service() -> WorkspacesService:
    return WorkspacesService()


@pytest.fixture
def resource(mock_api: Mock) -> Any:
    return workspaces_resource(mock_api)


@pytest.mark.asyncio
async def test_list_workspaces(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.list.return_value.execute.return_value = {"workspace": []}

    result = await service.list_workspaces(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"workspace": []}
    resource.list.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_list_workspaces_pages(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.list.return_value.execute.return_value = {}

    await service.list_workspaces(mock_ctx, ACCOUNT_ID, CONTAINER_ID, "token")

    resource.list.assert_called_once_with(parent=CONTAINER_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_get_workspace(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.get.return_value.execute.return_value = {"name": "Default"}

    result = await service.get_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"name": "Default"}
    resource.get.assert_called_once_with(path=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_get_workspace_status(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.getStatus.return_value.execute.return_value = {"workspaceChange": []}

    result = await service.get_workspace_status(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"workspaceChange": []}
    resource.getStatus.assert_called_once_with(path=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_create_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"name": "Consent mode"}
    resource.create.return_value.execute.return_value = body

    result = await service.create_workspace(mock_ctx, ACCOUNT_ID, CONTAINER_ID, body)

    assert result == body
    install_client.require_write.assert_called_once_with("create_workspace")
    resource.create.assert_called_once_with(parent=CONTAINER_PATH, body=body)


@pytest.mark.asyncio
async def test_update_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.update.return_value.execute.return_value = {}

    await service.update_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, {"name": "W"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_workspace")
    resource.update.assert_called_once_with(
        path=WORKSPACE_PATH, body={"name": "W"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_workspace_without_a_fingerprint(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.update.return_value.execute.return_value = {}

    await service.update_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, {"name": "W"}
    )

    resource.update.assert_called_once_with(path=WORKSPACE_PATH, body={"name": "W"})


@pytest.mark.asyncio
async def test_delete_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.delete.return_value.execute.return_value = ""

    result = await service.delete_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"path": WORKSPACE_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_workspace")


@pytest.mark.asyncio
async def test_sync_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.sync.return_value.execute.return_value = {"syncStatus": {}}

    result = await service.sync_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"syncStatus": {}}
    install_client.require_write.assert_called_once_with("sync_workspace")
    resource.sync.assert_called_once_with(path=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_resolve_workspace_conflict(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.resolve_conflict.return_value.execute.return_value = ""
    entity = {"tag": {"tagId": "1"}, "changeStatus": "updated"}

    result = await service.resolve_workspace_conflict(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, entity, "fp"
    )

    assert result == {"path": WORKSPACE_PATH, "status": "resolved"}
    install_client.require_write.assert_called_once_with("resolve_workspace_conflict")
    resource.resolve_conflict.assert_called_once_with(
        path=WORKSPACE_PATH, body=entity, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_resolve_workspace_conflict_without_a_fingerprint(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.resolve_conflict.return_value.execute.return_value = ""

    await service.resolve_workspace_conflict(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, {"tag": {}}
    )

    resource.resolve_conflict.assert_called_once_with(
        path=WORKSPACE_PATH, body={"tag": {}}
    )


@pytest.mark.asyncio
async def test_quick_preview_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource.quick_preview.return_value.execute.return_value = {"containerVersion": {}}

    result = await service.quick_preview_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"containerVersion": {}}
    install_client.require_write.assert_called_once_with("quick_preview_workspace")
    resource.quick_preview.assert_called_once_with(path=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_create_version_sends_an_empty_body_by_default(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    created = {"containerVersion": {"containerVersionId": "9"}}
    resource.create_version.return_value.execute.return_value = created

    result = await service.create_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == created
    install_client.require_write.assert_called_once_with("create_version")
    resource.create_version.assert_called_once_with(path=WORKSPACE_PATH, body={})


@pytest.mark.asyncio
async def test_create_version_passes_version_options(
    service: WorkspacesService, resource: Any, mock_ctx: AsyncMock
) -> None:
    resource.create_version.return_value.execute.return_value = {}
    options = {"name": "Release", "notes": "notes"}

    await service.create_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, options
    )

    resource.create_version.assert_called_once_with(path=WORKSPACE_PATH, body=options)


@pytest.mark.asyncio
async def test_bulk_update_workspace(
    service: WorkspacesService,
    resource: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    change = {"change": [{"changeStatus": "added", "tag": {"tagId": "new_1"}}]}
    resource.bulk_update.return_value.execute.return_value = {}

    await service.bulk_update_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, change
    )

    install_client.require_write.assert_called_once_with("bulk_update_workspace")
    resource.bulk_update.assert_called_once_with(path=WORKSPACE_PATH, body=change)


@pytest.mark.asyncio
async def test_workspaces_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_workspaces_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_workspaces",
        "get_workspace",
        "get_workspace_status",
        "create_workspace",
        "update_workspace",
        "delete_workspace",
        "sync_workspace",
        "resolve_workspace_conflict",
        "quick_preview_workspace",
        "create_version",
        "bulk_update_workspace",
    }
