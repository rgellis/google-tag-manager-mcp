"""Environments service -- named preview and publish targets for a container.

Covers the ``accounts.containers.environments`` resource in full: list, get,
create, update, delete, reauthorize.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import container_path, environment_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        Environment,
        ListEnvironmentsResponse,
    )

logger = get_logger(__name__)


class EnvironmentsService:
    """Manage a container's environments."""

    def list_environments(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListEnvironmentsResponse]:
        """List a container's environments.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            page_token: Continuation token from a previous response.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"listing environments for {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .list(parent=parent, **optional(pageToken=page_token))
                .execute()
            ),
        )

    def get_environment(
        self, ctx: Context, account_id: str, container_id: str, environment_id: str
    ) -> Awaitable[Environment]:
        """Retrieve one environment.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.
        """
        client = get_client()
        path = environment_path(account_id, container_id, environment_id)
        return execute(
            ctx,
            f"getting environment {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .get(path=path)
                .execute()
            ),
        )

    async def create_environment(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        environment: Dict[str, Any],
    ) -> Environment:
        """Create an environment in a container.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment: Environment resource, e.g.
                ``{"name": "Staging", "description": "Pre-release checks"}``.
        """
        client = get_client()
        client.require_write("create_environment")
        parent = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"creating an environment in {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .create(parent=parent, body=cast("Environment", environment))
                .execute()
            ),
        )
        logger.info("Created environment in %s", parent)
        return result

    async def update_environment(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        environment_id: str,
        environment: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Environment:
        """Update an environment.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.
            environment: Environment resource with the fields to change.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the environment.
        """
        client = get_client()
        client.require_write("update_environment")
        path = environment_path(account_id, container_id, environment_id)
        result = await execute(
            ctx,
            f"updating environment {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .update(
                    path=path,
                    body=cast("Environment", environment),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Updated environment %s", path)
        return result

    async def delete_environment(
        self, ctx: Context, account_id: str, container_id: str, environment_id: str
    ) -> Dict[str, Any]:
        """Delete an environment.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_environment")
        path = environment_path(account_id, container_id, environment_id)
        await execute(
            ctx,
            f"deleting environment {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .delete(path=path)
                .execute()
            ),
        )
        logger.info("Deleted environment %s", path)
        return {"path": path, "status": "deleted"}

    async def reauthorize_environment(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        environment_id: str,
        environment: Optional[Dict[str, Any]] = None,
    ) -> Environment:
        """Regenerate an environment's authorization code.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.
            environment: Environment resource to send as the request body. The
                API requires a body here even though it uses none of it, so an
                empty object is sent when nothing is given.
        """
        client = get_client()
        client.require_write("reauthorize_environment")
        path = environment_path(account_id, container_id, environment_id)
        body = cast("Environment", environment if environment is not None else {})
        result = await execute(
            ctx,
            f"reauthorizing environment {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .environments()
                .reauthorize(path=path, body=body)
                .execute()
            ),
        )
        logger.info("Reauthorized environment %s", path)
        return result


def create_environments_tools(
    service: EnvironmentsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by an EnvironmentsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_environments(
        ctx: Context,
        account_id: str,
        container_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List a container's environments.

        Every container has a Live and a Latest environment; the rest are
        user-created preview targets.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each environment's path, environmentId, name, type, url,
            containerVersionId and authorizationCode.
        """
        return cast(
            Dict[str, Any],
            await service.list_environments(ctx, account_id, container_id, page_token),
        )

    async def get_environment(
        ctx: Context, account_id: str, container_id: str, environment_id: str
    ) -> Dict[str, Any]:
        """Get one container environment.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.

        Returns:
            The environment's name, type, url, authorizationCode, pinned
            containerVersionId and fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_environment(
                ctx, account_id, container_id, environment_id
            ),
        )

    async def create_environment(
        ctx: Context, account_id: str, container_id: str, environment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an environment in a container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment: Environment resource. Requires name, e.g.
                {"name": "Staging", "description": "Pre-release checks",
                 "url": "https://staging.example.com",
                 "enableDebug": true}.

        Returns:
            The created environment, including its authorizationCode.
        """
        return cast(
            Dict[str, Any],
            await service.create_environment(
                ctx, account_id, container_id, environment
            ),
        )

    async def update_environment(
        ctx: Context,
        account_id: str,
        container_id: str,
        environment_id: str,
        environment: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a container environment.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.
            environment: Environment resource with the fields to change.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the environment changed in the meantime.

        Returns:
            The updated environment.
        """
        return cast(
            Dict[str, Any],
            await service.update_environment(
                ctx,
                account_id,
                container_id,
                environment_id,
                environment,
                fingerprint,
            ),
        )

    async def delete_environment(
        ctx: Context, account_id: str, container_id: str, environment_id: str
    ) -> Dict[str, Any]:
        """Delete a container environment.

        The built-in Live and Latest environments cannot be deleted.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_environment(
            ctx, account_id, container_id, environment_id
        )

    async def reauthorize_environment(
        ctx: Context,
        account_id: str,
        container_id: str,
        environment_id: str,
        environment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Regenerate an environment's authorization code.

        Use this when a preview link has leaked: the old code stops working
        immediately, so anything embedding it must be updated.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            environment_id: Numeric environment ID.
            environment: Optional Environment body. The API requires a body but
                uses none of it, so leaving this unset sends an empty object.

        Returns:
            The environment, carrying its new authorizationCode.
        """
        return cast(
            Dict[str, Any],
            await service.reauthorize_environment(
                ctx, account_id, container_id, environment_id, environment
            ),
        )

    return [
        list_environments,
        get_environment,
        create_environment,
        update_environment,
        delete_environment,
        reauthorize_environment,
    ]


def register_environments_tools(mcp: FastMCP[Any]) -> EnvironmentsService:
    """Register the environments tools with an MCP server."""
    service = EnvironmentsService()
    for tool in create_environments_tools(service):
        mcp.tool(tool)
    return service
