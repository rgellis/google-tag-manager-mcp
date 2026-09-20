"""Tags service -- the tags a container fires.

Covers ``accounts.containers.workspaces.tags`` in full: list, get, create,
update, delete, revert.
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
        ListTagsResponse,
        RevertTagResponse,
        Tag,
    )

logger = get_logger(__name__)


def _tag_path(
    account_id: str, container_id: str, workspace_id: str, tag_id: str
) -> str:
    return workspace_child_path(
        account_id, container_id, workspace_id, "tags", tag_id, "tag_id"
    )


class TagsService:
    """Manage the tags in a workspace."""

    def list_tags(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListTagsResponse]:
        """List the tags in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().tags()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing tags in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_tag(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
    ) -> Awaitable[Tag]:
        """Retrieve one tag.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.
        """
        resource = get_client().service.accounts().containers().workspaces().tags()
        path = _tag_path(account_id, container_id, workspace_id, tag_id)
        return execute(
            ctx, f"getting tag {path}", lambda: resource.get(path=path).execute()
        )

    async def create_tag(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag: Dict[str, Any],
    ) -> Tag:
        """Create a tag in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag: Tag resource, requiring at least ``name`` and ``type``.
        """
        client = get_client()
        client.require_write("create_tag")
        resource = client.service.accounts().containers().workspaces().tags()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a tag in {parent}",
            lambda: resource.create(parent=parent, body=cast("Tag", tag)).execute(),
        )
        logger.info("Created tag in %s", parent)
        return result

    async def update_tag(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
        tag: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Tag:
        """Update a tag.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.
            tag: Tag resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the tag.
        """
        client = get_client()
        client.require_write("update_tag")
        resource = client.service.accounts().containers().workspaces().tags()
        path = _tag_path(account_id, container_id, workspace_id, tag_id)
        result = await execute(
            ctx,
            f"updating tag {path}",
            lambda: resource.update(
                path=path, body=cast("Tag", tag), **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Updated tag %s", path)
        return result

    async def delete_tag(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
    ) -> Dict[str, Any]:
        """Delete a tag from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_tag")
        resource = client.service.accounts().containers().workspaces().tags()
        path = _tag_path(account_id, container_id, workspace_id, tag_id)
        await execute(
            ctx, f"deleting tag {path}", lambda: resource.delete(path=path).execute()
        )
        logger.info("Deleted tag %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_tag(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertTagResponse:
        """Discard a workspace's changes to one tag.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the tag.
        """
        client = get_client()
        client.require_write("revert_tag")
        resource = client.service.accounts().containers().workspaces().tags()
        path = _tag_path(account_id, container_id, workspace_id, tag_id)
        result = await execute(
            ctx,
            f"reverting tag {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted tag %s", path)
        return result


def create_tags_tools(service: TagsService) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a TagsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_tags(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the tags in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each tag's tagId, name, type, parameter list, firingTriggerId and
            blockingTriggerId.
        """
        return cast(
            Dict[str, Any],
            await service.list_tags(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_tag(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
    ) -> Dict[str, Any]:
        """Get one tag from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.

        Returns:
            The tag's full configuration, including its fingerprint -- which
            update_tag and revert_tag need.
        """
        return cast(
            Dict[str, Any],
            await service.get_tag(ctx, account_id, container_id, workspace_id, tag_id),
        )

    async def create_tag(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a tag in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag: Tag resource. Requires name and type, e.g.
                {"name": "GA4 - purchase",
                 "type": "gaawe",
                 "parameter": [{"type": "template", "key": "eventName",
                                "value": "purchase"}],
                 "firingTriggerId": ["12"]}.
                Tag types are Tag Manager's internal codes -- "gaawe" is a GA4
                event, "googtag" a Google tag, "html" a custom HTML tag. Copy
                the shape from an existing tag via get_tag when unsure.

        Returns:
            The created tag, including its new tagId.
        """
        return cast(
            Dict[str, Any],
            await service.create_tag(ctx, account_id, container_id, workspace_id, tag),
        )

    async def update_tag(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
        tag: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a tag in a workspace.

        The tag you send replaces the stored one, so read it with get_tag
        first and send the whole thing back with your edits applied. Omitted
        fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.
            tag: Complete Tag resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the tag changed in the meantime.

        Returns:
            The updated tag.
        """
        return cast(
            Dict[str, Any],
            await service.update_tag(
                ctx, account_id, container_id, workspace_id, tag_id, tag, fingerprint
            ),
        )

    async def delete_tag(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
    ) -> Dict[str, Any]:
        """Delete a tag from a workspace.

        This affects the workspace only. The tag keeps running in production
        until a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_tag(
            ctx, account_id, container_id, workspace_id, tag_id
        )

    async def revert_tag(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        tag_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one tag.

        Restores the tag to the state of the container version the workspace
        was branched from, leaving the workspace's other changes alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            tag_id: Numeric tag ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored tag, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_tag(
                ctx, account_id, container_id, workspace_id, tag_id, fingerprint
            ),
        )

    return [list_tags, get_tag, create_tag, update_tag, delete_tag, revert_tag]


def register_tags_tools(mcp: FastMCP[Any]) -> TagsService:
    """Register the tags tools with an MCP server."""
    service = TagsService()
    for tool in create_tags_tools(service):
        mcp.tool(tool)
    return service
