"""Tests for VersionsService, covering versions and version headers."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.versions_service import VersionsService, register_versions_tools
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    CONTAINER_PATH,
    container_child,
)

VERSION_ID = "9"
VERSION_PATH = f"{CONTAINER_PATH}/versions/{VERSION_ID}"


@pytest.fixture
def service() -> VersionsService:
    return VersionsService()


@pytest.fixture
def versions(mock_api: Mock) -> Any:
    return container_child(mock_api, "versions")


@pytest.fixture
def headers(mock_api: Mock) -> Any:
    return container_child(mock_api, "version_headers")


@pytest.mark.asyncio
async def test_list_version_headers(
    service: VersionsService, headers: Any, mock_ctx: AsyncMock
) -> None:
    headers.list.return_value.execute.return_value = {"containerVersionHeader": []}

    result = await service.list_version_headers(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"containerVersionHeader": []}
    headers.list.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_list_version_headers_with_options(
    service: VersionsService, headers: Any, mock_ctx: AsyncMock
) -> None:
    headers.list.return_value.execute.return_value = {}

    await service.list_version_headers(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, True, "token"
    )

    headers.list.assert_called_once_with(
        parent=CONTAINER_PATH, includeDeleted=True, pageToken="token"
    )


@pytest.mark.asyncio
async def test_list_version_headers_sends_include_deleted_false(
    service: VersionsService, headers: Any, mock_ctx: AsyncMock
) -> None:
    """False is a meaningful value here, not an absence."""
    headers.list.return_value.execute.return_value = {}

    await service.list_version_headers(mock_ctx, ACCOUNT_ID, CONTAINER_ID, False)

    headers.list.assert_called_once_with(parent=CONTAINER_PATH, includeDeleted=False)


@pytest.mark.asyncio
async def test_get_latest_version_header(
    service: VersionsService, headers: Any, mock_ctx: AsyncMock
) -> None:
    headers.latest.return_value.execute.return_value = {"containerVersionId": "9"}

    result = await service.get_latest_version_header(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"containerVersionId": "9"}
    headers.latest.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_get_version(
    service: VersionsService, versions: Any, mock_ctx: AsyncMock
) -> None:
    versions.get.return_value.execute.return_value = {"name": "Release"}

    result = await service.get_version(mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID)

    assert result == {"name": "Release"}
    versions.get.assert_called_once_with(path=VERSION_PATH)


@pytest.mark.asyncio
async def test_get_version_with_an_explicit_version_override(
    service: VersionsService, versions: Any, mock_ctx: AsyncMock
) -> None:
    versions.get.return_value.execute.return_value = {}

    await service.get_version(mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID, "12")

    versions.get.assert_called_once_with(path=VERSION_PATH, containerVersionId="12")


@pytest.mark.asyncio
async def test_get_live_version(
    service: VersionsService, versions: Any, mock_ctx: AsyncMock
) -> None:
    versions.live.return_value.execute.return_value = {"containerVersionId": "8"}

    result = await service.get_live_version(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"containerVersionId": "8"}
    versions.live.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_update_version(
    service: VersionsService,
    versions: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    versions.update.return_value.execute.return_value = {}

    await service.update_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID, {"name": "R"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_version")
    versions.update.assert_called_once_with(
        path=VERSION_PATH, body={"name": "R"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_version_without_a_fingerprint(
    service: VersionsService, versions: Any, mock_ctx: AsyncMock
) -> None:
    versions.update.return_value.execute.return_value = {}

    await service.update_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID, {"name": "R"}
    )

    versions.update.assert_called_once_with(path=VERSION_PATH, body={"name": "R"})


@pytest.mark.asyncio
async def test_delete_version(
    service: VersionsService,
    versions: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    versions.delete.return_value.execute.return_value = ""

    result = await service.delete_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID
    )

    assert result == {"path": VERSION_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_version")


@pytest.mark.asyncio
async def test_undelete_version(
    service: VersionsService,
    versions: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    versions.undelete.return_value.execute.return_value = {"deleted": False}

    result = await service.undelete_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID
    )

    assert result == {"deleted": False}
    install_client.require_write.assert_called_once_with("undelete_version")
    versions.undelete.assert_called_once_with(path=VERSION_PATH)


@pytest.mark.asyncio
async def test_publish_version(
    service: VersionsService,
    versions: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    versions.publish.return_value.execute.return_value = {"containerVersion": {}}

    result = await service.publish_version(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID
    )

    assert result == {"containerVersion": {}}
    install_client.require_write.assert_called_once_with("publish_version")
    versions.publish.assert_called_once_with(path=VERSION_PATH)


@pytest.mark.asyncio
async def test_publish_version_with_a_fingerprint(
    service: VersionsService, versions: Any, mock_ctx: AsyncMock
) -> None:
    versions.publish.return_value.execute.return_value = {}

    await service.publish_version(mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID, "fp")

    versions.publish.assert_called_once_with(path=VERSION_PATH, fingerprint="fp")


@pytest.mark.asyncio
async def test_set_latest_version(
    service: VersionsService,
    versions: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    versions.set_latest.return_value.execute.return_value = {}

    await service.set_latest_version(mock_ctx, ACCOUNT_ID, CONTAINER_ID, VERSION_ID)

    install_client.require_write.assert_called_once_with("set_latest_version")
    versions.set_latest.assert_called_once_with(path=VERSION_PATH)


@pytest.mark.asyncio
async def test_versions_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_versions_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_version_headers",
        "get_latest_version_header",
        "get_version",
        "get_live_version",
        "update_version",
        "delete_version",
        "undelete_version",
        "publish_version",
        "set_latest_version",
    }
