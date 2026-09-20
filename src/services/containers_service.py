"""Containers service -- the container is the unit a website or app loads.

Covers the ``accounts.containers`` resource in full: list, get, create, update,
delete, combine, lookup, move_tag_id and snippet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import account_path, container_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        Container,
        GetContainerSnippetResponse,
        ListContainersResponse,
    )

logger = get_logger(__name__)


class ContainersService:
    """Manage the containers belonging to a Tag Manager account."""

    def list_containers(
        self, ctx: Context, account_id: str, page_token: Optional[str] = None
    ) -> Awaitable[ListContainersResponse]:
        """List the containers in an account.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            page_token: Continuation token from a previous response.
        """
        client = get_client()
        parent = account_path(account_id)
        return execute(
            ctx,
            f"listing containers in {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .list(parent=parent, **optional(pageToken=page_token))
                .execute()
            ),
        )

    def get_container(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Awaitable[Container]:
        """Retrieve one container.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
        """
        client = get_client()
        path = container_path(account_id, container_id)
        return execute(
            ctx,
            f"getting container {path}",
            lambda: client.service.accounts().containers().get(path=path).execute(),
        )

    def lookup_container(
        self,
        ctx: Context,
        tag_id: Optional[str] = None,
        destination_id: Optional[str] = None,
    ) -> Awaitable[Container]:
        """Find a container by its public tag ID or a linked destination ID.

        The one Tag Manager read that needs no account ID, which makes it the
        way in when all you have is the GTM-XXXXXXX from a site's source.

        Args:
            ctx: FastMCP context.
            tag_id: Public tag ID, e.g. ``GTM-XXXXXXX``.
            destination_id: Destination ID linked to a container, e.g.
                ``AW-123456789`` or ``G-ABC123``.
        """
        client = get_client()
        if (tag_id is None) == (destination_id is None):
            raise ValueError(
                "Pass exactly one of tag_id or destination_id: the API accepts "
                "only one and silently ignores the second."
            )
        target = tag_id or destination_id
        return execute(
            ctx,
            f"looking up the container for {target}",
            lambda: (
                client.service.accounts()
                .containers()
                .lookup(**optional(tagId=tag_id, destinationId=destination_id))
                .execute()
            ),
        )

    def get_container_snippet(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Awaitable[GetContainerSnippetResponse]:
        """Get the HTML install snippet for a container.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
        """
        client = get_client()
        path = container_path(account_id, container_id)
        return execute(
            ctx,
            f"getting the install snippet for {path}",
            lambda: client.service.accounts().containers().snippet(path=path).execute(),
        )

    async def create_container(
        self, ctx: Context, account_id: str, container: Dict[str, Any]
    ) -> Container:
        """Create a container in an account.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container: Container resource, e.g.
                ``{"name": "example.com", "usageContext": ["web"]}``.
        """
        client = get_client()
        client.require_write("create_container")
        parent = account_path(account_id)
        result = await execute(
            ctx,
            f"creating a container in {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .create(parent=parent, body=cast("Container", container))
                .execute()
            ),
        )
        logger.info("Created container in %s", parent)
        return result

    async def update_container(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        container: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Container:
        """Update a container's settings.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            container: Container resource with the fields to change.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the container.
        """
        client = get_client()
        client.require_write("update_container")
        path = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"updating container {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .update(
                    path=path,
                    body=cast("Container", container),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Updated container %s", path)
        return result

    async def delete_container(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Delete a container and everything in it.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_container")
        path = container_path(account_id, container_id)
        await execute(
            ctx,
            f"deleting container {path}",
            lambda: client.service.accounts().containers().delete(path=path).execute(),
        )
        logger.info("Deleted container %s", path)
        return {"path": path, "status": "deleted"}

    async def combine_containers(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        other_container_id: str,
        setting_source: Optional[str] = None,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Container:
        """Merge another container into this one.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric ID of the container that survives the merge.
            other_container_id: Numeric ID of the container merged into it.
            setting_source: Which container's settings to keep afterwards --
                ``current``, ``other`` or ``settingSourceUnspecified``.
            allow_user_permission_feature_update: Must be true for the merge to
                be allowed to turn the user-permissions feature on.
        """
        client = get_client()
        client.require_write("combine_containers")
        path = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"combining container {other_container_id} into {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .combine(
                    path=path,
                    **optional(
                        containerId=other_container_id,
                        settingSource=setting_source,
                        allowUserPermissionFeatureUpdate=(
                            allow_user_permission_feature_update
                        ),
                    ),
                )
                .execute()
            ),
        )
        logger.info("Combined container %s into %s", other_container_id, path)
        return result

    async def move_tag_id(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        tag_id: Optional[str] = None,
        tag_name: Optional[str] = None,
        copy_settings: Optional[bool] = None,
        copy_users: Optional[bool] = None,
        copy_terms_of_service: Optional[bool] = None,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Container:
        """Move a tag ID out of a container into a new one.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric ID of the container holding the tag ID.
            tag_id: The tag ID to move out, e.g. ``GTM-XXXXXXX``.
            tag_name: Name for the newly created container.
            copy_settings: Copy tag settings across to the new container.
            copy_users: Copy users across to the new container.
            copy_terms_of_service: Must be true to accept the terms of service
                copied across; the call fails otherwise.
            allow_user_permission_feature_update: Must be true for the move to
                be allowed to turn the user-permissions feature on.
        """
        client = get_client()
        client.require_write("move_tag_id")
        path = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"moving tag ID {tag_id} out of {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .move_tag_id(
                    path=path,
                    **optional(
                        tagId=tag_id,
                        tagName=tag_name,
                        copySettings=copy_settings,
                        copyUsers=copy_users,
                        copyTermsOfService=copy_terms_of_service,
                        allowUserPermissionFeatureUpdate=(
                            allow_user_permission_feature_update
                        ),
                    ),
                )
                .execute()
            ),
        )
        logger.info("Moved tag ID %s out of %s", tag_id, path)
        return result


def create_containers_tools(
    service: ContainersService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a ContainersService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_containers(
        ctx: Context, account_id: str, page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List the containers in a Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each container's path, containerId, publicId (GTM-XXXXXXX), name,
            usageContext, domainName and tagIds.
        """
        return cast(
            Dict[str, Any], await service.list_containers(ctx, account_id, page_token)
        )

    async def get_container(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Get one Tag Manager container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The container's path, containerId, publicId, name, usageContext,
            features, tagIds and fingerprint.
        """
        return cast(
            Dict[str, Any], await service.get_container(ctx, account_id, container_id)
        )

    async def lookup_container(
        ctx: Context,
        tag_id: Optional[str] = None,
        destination_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find a container from its public GTM-XXXXXXX tag ID.

        Use this when you have a tag ID from a website's source but no account
        ID. Pass exactly one of the two arguments.

        Args:
            tag_id: Public tag ID, e.g. GTM-XXXXXXX.
            destination_id: Linked destination ID, e.g. AW-123456789 or G-ABC123.

        Returns:
            The matching container, including the accountId and containerId
            needed by every other tool.
        """
        return cast(
            Dict[str, Any], await service.lookup_container(ctx, tag_id, destination_id)
        )

    async def get_container_snippet(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Get the HTML install snippet for a container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The snippet to paste into a page, under "snippet".
        """
        return cast(
            Dict[str, Any],
            await service.get_container_snippet(ctx, account_id, container_id),
        )

    async def create_container(
        ctx: Context, account_id: str, container: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a container in a Tag Manager account.

        Args:
            account_id: Numeric Tag Manager account ID.
            container: Container resource. Requires name and usageContext, e.g.
                {"name": "example.com", "usageContext": ["web"]}. usageContext
                is one of web, android, ios, amp or server.

        Returns:
            The created container, including its new containerId and publicId.
        """
        return cast(
            Dict[str, Any], await service.create_container(ctx, account_id, container)
        )

    async def update_container(
        ctx: Context,
        account_id: str,
        container_id: str,
        container: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a container's settings.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            container: Container resource with the fields to change, e.g.
                {"name": "example.com (web)", "notes": "Owned by marketing"}.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the container changed in the meantime.

        Returns:
            The updated container.
        """
        return cast(
            Dict[str, Any],
            await service.update_container(
                ctx, account_id, container_id, container, fingerprint
            ),
        )

    async def delete_container(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Delete a container, and with it every workspace, tag and version.

        This cannot be undone through the API, and any site still loading the
        container's snippet stops receiving tags.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_container(ctx, account_id, container_id)

    async def combine_containers(
        ctx: Context,
        account_id: str,
        container_id: str,
        other_container_id: str,
        setting_source: Optional[str] = None,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Merge one container into another.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric ID of the container that survives the merge.
            other_container_id: Numeric ID of the container merged into it.
            setting_source: Whose settings survive -- "current", "other" or
                "settingSourceUnspecified".
            allow_user_permission_feature_update: Must be true if the merge
                would turn the user-permissions feature on.

        Returns:
            The surviving container.
        """
        return cast(
            Dict[str, Any],
            await service.combine_containers(
                ctx,
                account_id,
                container_id,
                other_container_id,
                setting_source,
                allow_user_permission_feature_update,
            ),
        )

    async def move_tag_id(
        ctx: Context,
        account_id: str,
        container_id: str,
        tag_id: Optional[str] = None,
        tag_name: Optional[str] = None,
        copy_settings: Optional[bool] = None,
        copy_users: Optional[bool] = None,
        copy_terms_of_service: Optional[bool] = None,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Move a tag ID out of a container into a newly created one.

        The inverse of combine_containers: it splits a tag ID off a container
        that holds several.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric ID of the container holding the tag ID.
            tag_id: The tag ID to move out, e.g. GTM-XXXXXXX.
            tag_name: Name for the newly created container.
            copy_settings: Copy tag settings to the new container.
            copy_users: Copy users to the new container.
            copy_terms_of_service: Must be true to accept the copied terms of
                service; the call fails otherwise.
            allow_user_permission_feature_update: Must be true if the move would
                turn the user-permissions feature on.

        Returns:
            The container the tag ID was moved into.
        """
        return cast(
            Dict[str, Any],
            await service.move_tag_id(
                ctx,
                account_id,
                container_id,
                tag_id,
                tag_name,
                copy_settings,
                copy_users,
                copy_terms_of_service,
                allow_user_permission_feature_update,
            ),
        )

    return [
        list_containers,
        get_container,
        lookup_container,
        get_container_snippet,
        create_container,
        update_container,
        delete_container,
        combine_containers,
        move_tag_id,
    ]


def register_containers_tools(mcp: FastMCP[Any]) -> ContainersService:
    """Register the containers tools with an MCP server."""
    service = ContainersService()
    for tool in create_containers_tools(service):
        mcp.tool(tool)
    return service
