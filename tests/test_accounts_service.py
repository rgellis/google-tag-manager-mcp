"""Tests for AccountsService and UserPermissionsService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.accounts_service import AccountsService, register_accounts_tools
from src.services.user_permissions_service import (
    UserPermissionsService,
    register_user_permissions_tools,
)
from tests.conftest import ACCOUNT_ID, ACCOUNT_PATH, accounts_resource

PERMISSION_ID = "88"
PERMISSION_PATH = f"{ACCOUNT_PATH}/user_permissions/{PERMISSION_ID}"


@pytest.fixture
def service() -> AccountsService:
    return AccountsService()


@pytest.fixture
def permissions() -> UserPermissionsService:
    return UserPermissionsService()


@pytest.mark.asyncio
async def test_list_accounts(
    service: AccountsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    expected = {"account": [{"accountId": ACCOUNT_ID, "name": "Acme"}]}
    accounts_resource(mock_api).list.return_value.execute.return_value = expected

    result = await service.list_accounts(mock_ctx)

    assert result == expected
    accounts_resource(mock_api).list.assert_called_once_with()


@pytest.mark.asyncio
async def test_list_accounts_passes_optional_arguments(
    service: AccountsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    accounts_resource(mock_api).list.return_value.execute.return_value = {}

    await service.list_accounts(mock_ctx, "token", True)

    accounts_resource(mock_api).list.assert_called_once_with(
        pageToken="token", includeGoogleTags=True
    )


@pytest.mark.asyncio
async def test_get_account(
    service: AccountsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    accounts_resource(mock_api).get.return_value.execute.return_value = {"name": "Acme"}

    result = await service.get_account(mock_ctx, ACCOUNT_ID)

    assert result == {"name": "Acme"}
    accounts_resource(mock_api).get.assert_called_once_with(path=ACCOUNT_PATH)


@pytest.mark.asyncio
async def test_update_account(
    service: AccountsService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    accounts_resource(mock_api).update.return_value.execute.return_value = {
        "name": "New"
    }

    result = await service.update_account(mock_ctx, ACCOUNT_ID, {"name": "New"})

    assert result == {"name": "New"}
    install_client.require_write.assert_called_once_with("update_account")
    accounts_resource(mock_api).update.assert_called_once_with(
        path=ACCOUNT_PATH, body={"name": "New"}
    )


@pytest.mark.asyncio
async def test_update_account_sends_a_fingerprint(
    service: AccountsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    accounts_resource(mock_api).update.return_value.execute.return_value = {}

    await service.update_account(mock_ctx, ACCOUNT_ID, {"name": "New"}, "fp")

    accounts_resource(mock_api).update.assert_called_once_with(
        path=ACCOUNT_PATH, body={"name": "New"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_accounts_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_accounts_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {"list_accounts", "get_account", "update_account"}


def permissions_resource(mock_api: Mock) -> Any:
    return accounts_resource(mock_api).user_permissions.return_value


@pytest.mark.asyncio
async def test_list_user_permissions(
    permissions: UserPermissionsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    expected = {"userPermission": [{"emailAddress": "a@b.com"}]}
    permissions_resource(mock_api).list.return_value.execute.return_value = expected

    result = await permissions.list_user_permissions(mock_ctx, ACCOUNT_ID)

    assert result == expected
    permissions_resource(mock_api).list.assert_called_once_with(parent=ACCOUNT_PATH)


@pytest.mark.asyncio
async def test_list_user_permissions_pages(
    permissions: UserPermissionsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    permissions_resource(mock_api).list.return_value.execute.return_value = {}

    await permissions.list_user_permissions(mock_ctx, ACCOUNT_ID, "token")

    permissions_resource(mock_api).list.assert_called_once_with(
        parent=ACCOUNT_PATH, pageToken="token"
    )


@pytest.mark.asyncio
async def test_get_user_permission(
    permissions: UserPermissionsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    permissions_resource(mock_api).get.return_value.execute.return_value = {"a": 1}

    result = await permissions.get_user_permission(mock_ctx, ACCOUNT_ID, PERMISSION_ID)

    assert result == {"a": 1}
    permissions_resource(mock_api).get.assert_called_once_with(path=PERMISSION_PATH)


@pytest.mark.asyncio
async def test_create_user_permission(
    permissions: UserPermissionsService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"emailAddress": "a@b.com", "accountAccess": {"permission": "user"}}
    permissions_resource(mock_api).create.return_value.execute.return_value = body

    result = await permissions.create_user_permission(mock_ctx, ACCOUNT_ID, body)

    assert result == body
    install_client.require_write.assert_called_once_with("create_user_permission")
    permissions_resource(mock_api).create.assert_called_once_with(
        parent=ACCOUNT_PATH, body=body
    )


@pytest.mark.asyncio
async def test_update_user_permission_takes_no_fingerprint(
    permissions: UserPermissionsService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    """Alone among the update methods, this one has no fingerprint parameter."""
    body = {"accountAccess": {"permission": "admin"}}
    permissions_resource(mock_api).update.return_value.execute.return_value = body

    result = await permissions.update_user_permission(
        mock_ctx, ACCOUNT_ID, PERMISSION_ID, body
    )

    assert result == body
    install_client.require_write.assert_called_once_with("update_user_permission")
    permissions_resource(mock_api).update.assert_called_once_with(
        path=PERMISSION_PATH, body=body
    )


@pytest.mark.asyncio
async def test_delete_user_permission(
    permissions: UserPermissionsService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    permissions_resource(mock_api).delete.return_value.execute.return_value = ""

    result = await permissions.delete_user_permission(
        mock_ctx, ACCOUNT_ID, PERMISSION_ID
    )

    assert result == {"path": PERMISSION_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_user_permission")


@pytest.mark.asyncio
async def test_user_permissions_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_user_permissions_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_user_permissions",
        "get_user_permission",
        "create_user_permission",
        "update_user_permission",
        "delete_user_permission",
    }
