"""User permissions service -- who can do what in a Tag Manager account.

Covers the ``accounts.user_permissions`` resource in full: list, get, create,
update, delete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import account_path, user_permission_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        ListUserPermissionsResponse,
        UserPermission,
    )

logger = get_logger(__name__)


class UserPermissionsService:
    """Manage account and container access for Tag Manager users."""

    def list_user_permissions(
        self, ctx: Context, account_id: str, page_token: Optional[str] = None
    ) -> Awaitable[ListUserPermissionsResponse]:
        """List every user permission on an account.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            page_token: Continuation token from a previous response.
        """
        client = get_client()
        parent = account_path(account_id)
        return execute(
            ctx,
            f"listing user permissions for {parent}",
            lambda: (
                client.service.accounts()
                .user_permissions()
                .list(parent=parent, **optional(pageToken=page_token))
                .execute()
            ),
        )

    def get_user_permission(
        self, ctx: Context, account_id: str, permission_id: str
    ) -> Awaitable[UserPermission]:
        """Retrieve one user permission.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.
        """
        client = get_client()
        path = user_permission_path(account_id, permission_id)
        return execute(
            ctx,
            f"getting user permission {path}",
            lambda: (
                client.service.accounts().user_permissions().get(path=path).execute()
            ),
        )

    async def create_user_permission(
        self, ctx: Context, account_id: str, user_permission: Dict[str, Any]
    ) -> UserPermission:
        """Grant a user access to an account and its containers.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            user_permission: UserPermission resource, e.g.
                ``{"emailAddress": "a@b.com", "accountAccess": {"permission":
                "user"}, "containerAccess": [{"containerId": "1", "permission":
                "publish"}]}``.
        """
        client = get_client()
        client.require_write("create_user_permission")
        parent = account_path(account_id)
        result = await execute(
            ctx,
            f"creating a user permission on {parent}",
            lambda: (
                client.service.accounts()
                .user_permissions()
                .create(parent=parent, body=cast("UserPermission", user_permission))
                .execute()
            ),
        )
        logger.info("Created user permission on %s", parent)
        return result

    async def update_user_permission(
        self,
        ctx: Context,
        account_id: str,
        permission_id: str,
        user_permission: Dict[str, Any],
    ) -> UserPermission:
        """Change an existing user's access.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.
            user_permission: UserPermission resource with the new access levels.
        """
        client = get_client()
        client.require_write("update_user_permission")
        path = user_permission_path(account_id, permission_id)
        result = await execute(
            ctx,
            f"updating user permission {path}",
            lambda: (
                client.service.accounts()
                .user_permissions()
                .update(path=path, body=cast("UserPermission", user_permission))
                .execute()
            ),
        )
        logger.info("Updated user permission %s", path)
        return result

    async def delete_user_permission(
        self, ctx: Context, account_id: str, permission_id: str
    ) -> Dict[str, Any]:
        """Revoke a user's access to an account.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_user_permission")
        path = user_permission_path(account_id, permission_id)
        await execute(
            ctx,
            f"deleting user permission {path}",
            lambda: (
                client.service.accounts().user_permissions().delete(path=path).execute()
            ),
        )
        logger.info("Deleted user permission %s", path)
        return {"path": path, "status": "deleted"}


def create_user_permissions_tools(
    service: UserPermissionsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a UserPermissionsService."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_user_permissions(
        ctx: Context, account_id: str, page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List who has access to a Tag Manager account, and at what level.

        Args:
            account_id: Numeric Tag Manager account ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each permission's path, emailAddress, accountAccess and per-container
            containerAccess entries.
        """
        return cast(
            Dict[str, Any],
            await service.list_user_permissions(ctx, account_id, page_token),
        )

    async def get_user_permission(
        ctx: Context, account_id: str, permission_id: str
    ) -> Dict[str, Any]:
        """Get one user's access to a Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.

        Returns:
            The permission's emailAddress, accountAccess and containerAccess.
        """
        return cast(
            Dict[str, Any],
            await service.get_user_permission(ctx, account_id, permission_id),
        )

    async def create_user_permission(
        ctx: Context, account_id: str, user_permission: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Grant a user access to a Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.
            user_permission: UserPermission resource. Requires emailAddress and
                accountAccess; containerAccess sets per-container levels, e.g.
                {"emailAddress": "a@b.com",
                 "accountAccess": {"permission": "user"},
                 "containerAccess": [{"containerId": "1234567",
                                      "permission": "publish"}]}.
                Account permission is "admin" or "user"; container permission is
                "read", "edit", "approve" or "publish".

        Returns:
            The created permission, including its assigned path.
        """
        return cast(
            Dict[str, Any],
            await service.create_user_permission(ctx, account_id, user_permission),
        )

    async def update_user_permission(
        ctx: Context,
        account_id: str,
        permission_id: str,
        user_permission: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Change a user's access to a Tag Manager account.

        The request replaces the stored access levels rather than merging into
        them, so send the complete accountAccess and containerAccess you want.

        Args:
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.
            user_permission: UserPermission resource with the new access levels.

        Returns:
            The updated permission.
        """
        return cast(
            Dict[str, Any],
            await service.update_user_permission(
                ctx, account_id, permission_id, user_permission
            ),
        )

    async def delete_user_permission(
        ctx: Context, account_id: str, permission_id: str
    ) -> Dict[str, Any]:
        """Revoke a user's access to a Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.
            permission_id: Numeric user permission ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_user_permission(ctx, account_id, permission_id)

    return [
        list_user_permissions,
        get_user_permission,
        create_user_permission,
        update_user_permission,
        delete_user_permission,
    ]


def register_user_permissions_tools(mcp: FastMCP[Any]) -> UserPermissionsService:
    """Register the user permissions tools with an MCP server."""
    service = UserPermissionsService()
    for tool in create_user_permissions_tools(service):
        mcp.tool(tool)
    return service
