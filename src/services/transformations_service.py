"""Transformations service -- event data rewriting in a server container.

Covers ``accounts.containers.workspaces.transformations`` in full: list, get,
create, update, delete, revert.

A Transformation edits event data after a client has claimed the
request but before tags see it -- redacting a field, say. Server
containers only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import workspace_child_path, workspace_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        ListTransformationsResponse,
        RevertTransformationResponse,
        Transformation,
    )

logger = get_logger(__name__)


def _transformation_path(
    account_id: str, container_id: str, workspace_id: str, transformation_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "transformations",
        transformation_id,
        "transformation_id",
    )


class TransformationsService:
    """Manage the transformations in a workspace."""

    def list_transformations(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListTransformationsResponse]:
        """List the transformations in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = (
            get_client().service.accounts().containers().workspaces().transformations()
        )
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing transformations in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_transformation(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
    ) -> Awaitable[Transformation]:
        """Retrieve one transformation.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.
        """
        resource = (
            get_client().service.accounts().containers().workspaces().transformations()
        )
        path = _transformation_path(
            account_id, container_id, workspace_id, transformation_id
        )
        return execute(
            ctx,
            f"getting transformation {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_transformation(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation: Dict[str, Any],
    ) -> Transformation:
        """Create a transformation in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation: Transformation resource to create.
        """
        client = get_client()
        client.require_write("create_transformation")
        resource = client.service.accounts().containers().workspaces().transformations()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a transformation in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("Transformation", transformation)
            ).execute(),
        )
        logger.info("Created transformation in %s", parent)
        return result

    async def update_transformation(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
        transformation: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Transformation:
        """Update a transformation.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.
            transformation: Transformation resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the transformation.
        """
        client = get_client()
        client.require_write("update_transformation")
        resource = client.service.accounts().containers().workspaces().transformations()
        path = _transformation_path(
            account_id, container_id, workspace_id, transformation_id
        )
        result = await execute(
            ctx,
            f"updating transformation {path}",
            lambda: resource.update(
                path=path,
                body=cast("Transformation", transformation),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated transformation %s", path)
        return result

    async def delete_transformation(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
    ) -> Dict[str, Any]:
        """Delete a transformation from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_transformation")
        resource = client.service.accounts().containers().workspaces().transformations()
        path = _transformation_path(
            account_id, container_id, workspace_id, transformation_id
        )
        await execute(
            ctx,
            f"deleting transformation {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted transformation %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_transformation(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertTransformationResponse:
        """Discard a workspace's changes to one transformation.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the transformation.
        """
        client = get_client()
        client.require_write("revert_transformation")
        resource = client.service.accounts().containers().workspaces().transformations()
        path = _transformation_path(
            account_id, container_id, workspace_id, transformation_id
        )
        result = await execute(
            ctx,
            f"reverting transformation {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted transformation %s", path)
        return result


def create_transformations_tools(
    service: TransformationsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a TransformationsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_transformations(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the transformations in a workspace.

        A web container returns an empty list; transformations exist only in
        server containers.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each transformation's transformationId, name, type and parameter
            list.
        """
        return cast(
            Dict[str, Any],
            await service.list_transformations(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_transformation(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
    ) -> Dict[str, Any]:
        """Get one transformation from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.

        Returns:
            The transformation's full configuration, including its fingerprint --
            which update_transformation and revert_transformation need.
        """
        return cast(
            Dict[str, Any],
            await service.get_transformation(
                ctx, account_id, container_id, workspace_id, transformation_id
            ),
        )

    async def create_transformation(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a transformation in a workspace.

        Only server containers accept transformations. Creating one in a
        web container fails.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation: Transformation resource. Requires name and type, e.g.
                {"name": "Redact email", "type": "sgtmTransformation",
                 "parameter": [...]}.

        Returns:
            The created transformation, including its new transformationId.
        """
        return cast(
            Dict[str, Any],
            await service.create_transformation(
                ctx, account_id, container_id, workspace_id, transformation
            ),
        )

    async def update_transformation(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
        transformation: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a transformation in a workspace.

        The transformation you send replaces the stored one, so read it with
        get_transformation first and send the whole thing back with your edits
        applied. Omitted fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.
            transformation: Complete Transformation resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the transformation changed in the meantime.

        Returns:
            The updated transformation.
        """
        return cast(
            Dict[str, Any],
            await service.update_transformation(
                ctx,
                account_id,
                container_id,
                workspace_id,
                transformation_id,
                transformation,
                fingerprint,
            ),
        )

    async def delete_transformation(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
    ) -> Dict[str, Any]:
        """Delete a transformation from a workspace.

        This affects the workspace only. The transformation stays in production until
        a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_transformation(
            ctx, account_id, container_id, workspace_id, transformation_id
        )

    async def revert_transformation(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        transformation_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one transformation.

        Restores the transformation to the state of the container version the
        workspace was branched from, leaving the workspace's other changes
        alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            transformation_id: Numeric transformation ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored transformation, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_transformation(
                ctx,
                account_id,
                container_id,
                workspace_id,
                transformation_id,
                fingerprint,
            ),
        )

    return [
        list_transformations,
        get_transformation,
        create_transformation,
        update_transformation,
        delete_transformation,
        revert_transformation,
    ]


def register_transformations_tools(mcp: FastMCP[Any]) -> TransformationsService:
    """Register the transformations tools with an MCP server."""
    service = TransformationsService()
    for tool in create_transformations_tools(service):
        mcp.tool(tool)
    return service
