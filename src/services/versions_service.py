"""Versions service -- container versions and the headers that index them.

Covers ``accounts.containers.versions`` and
``accounts.containers.version_headers`` in full. Both resources describe the
same objects: a version header is the cheap summary (ID, name, entity counts),
a version is the full snapshot of every tag, trigger and variable it contains.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import container_path, version_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        ContainerVersion,
        ContainerVersionHeader,
        ListContainerVersionsResponse,
        PublishContainerVersionResponse,
    )

logger = get_logger(__name__)


class VersionsService:
    """Read, publish and manage a container's versions."""

    def list_version_headers(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        include_deleted: Optional[bool] = None,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListContainerVersionsResponse]:
        """List a container's version headers.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            include_deleted: Also return versions that have been deleted.
            page_token: Continuation token from a previous response.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"listing version headers for {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .version_headers()
                .list(
                    parent=parent,
                    **optional(includeDeleted=include_deleted, pageToken=page_token),
                )
                .execute()
            ),
        )

    def get_latest_version_header(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Awaitable[ContainerVersionHeader]:
        """Retrieve the header of the most recently created version.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"getting the latest version header for {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .version_headers()
                .latest(parent=parent)
                .execute()
            ),
        )

    def get_version(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        container_version_id: Optional[str] = None,
    ) -> Awaitable[ContainerVersion]:
        """Retrieve one container version in full.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            container_version_id: Overrides the version named in the path. The
                API exposes it; passing the ID once in ``version_id`` is the
                sane way to call this.
        """
        client = get_client()
        path = version_path(account_id, container_id, version_id)
        return execute(
            ctx,
            f"getting container version {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .get(path=path, **optional(containerVersionId=container_version_id))
                .execute()
            ),
        )

    def get_live_version(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Awaitable[ContainerVersion]:
        """Retrieve the version currently published to production.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"getting the live container version for {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .live(parent=parent)
                .execute()
            ),
        )

    async def update_version(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        container_version: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> ContainerVersion:
        """Update a container version's name or notes.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            container_version: ContainerVersion resource with the fields to
                change.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the version.
        """
        client = get_client()
        client.require_write("update_version")
        path = version_path(account_id, container_id, version_id)
        result = await execute(
            ctx,
            f"updating container version {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .update(
                    path=path,
                    body=cast("ContainerVersion", container_version),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Updated container version %s", path)
        return result

    async def delete_version(
        self, ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> Dict[str, Any]:
        """Delete a container version.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_version")
        path = version_path(account_id, container_id, version_id)
        await execute(
            ctx,
            f"deleting container version {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .delete(path=path)
                .execute()
            ),
        )
        logger.info("Deleted container version %s", path)
        return {"path": path, "status": "deleted"}

    async def undelete_version(
        self, ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> ContainerVersion:
        """Restore a previously deleted container version.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
        """
        client = get_client()
        client.require_write("undelete_version")
        path = version_path(account_id, container_id, version_id)
        result = await execute(
            ctx,
            f"undeleting container version {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .undelete(path=path)
                .execute()
            ),
        )
        logger.info("Undeleted container version %s", path)
        return result

    async def publish_version(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        fingerprint: Optional[str] = None,
    ) -> PublishContainerVersionResponse:
        """Publish a container version to production.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            fingerprint: When given, the publish is rejected unless it matches
                the fingerprint currently stored for the version.
        """
        client = get_client()
        client.require_write("publish_version")
        path = version_path(account_id, container_id, version_id)
        result = await execute(
            ctx,
            f"publishing container version {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .publish(path=path, **optional(fingerprint=fingerprint))
                .execute()
            ),
        )
        logger.info("Published container version %s", path)
        return result

    async def set_latest_version(
        self, ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> ContainerVersion:
        """Set the version workspaces sync against.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
        """
        client = get_client()
        client.require_write("set_latest_version")
        path = version_path(account_id, container_id, version_id)
        result = await execute(
            ctx,
            f"setting container version {path} as latest",
            lambda: (
                client.service.accounts()
                .containers()
                .versions()
                .set_latest(path=path)
                .execute()
            ),
        )
        logger.info("Set container version %s as latest", path)
        return result


def create_versions_tools(
    service: VersionsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a VersionsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_version_headers(
        ctx: Context,
        account_id: str,
        container_id: str,
        include_deleted: Optional[bool] = None,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List a container's version history as lightweight headers.

        Prefer this over fetching versions when you want the history: a header
        carries the ID, name and entity counts without the full snapshot of
        every tag in the version.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            include_deleted: Also return deleted versions.
            page_token: Continuation token from a previous response.

        Returns:
            Each header's containerVersionId, name, deleted flag and counts of
            tags, triggers and variables.
        """
        return cast(
            Dict[str, Any],
            await service.list_version_headers(
                ctx, account_id, container_id, include_deleted, page_token
            ),
        )

    async def get_latest_version_header(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Get the header of a container's most recently created version.

        This is the newest version, which is not necessarily the published one
        -- use get_live_version for what production is serving.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The latest version header.
        """
        return cast(
            Dict[str, Any],
            await service.get_latest_version_header(ctx, account_id, container_id),
        )

    async def get_version(
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        container_version_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get one container version, including every entity it contains.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            container_version_id: Rarely needed; overrides the version in the
                path. Leave unset.

        Returns:
            The version with its full tag, trigger, variable, folder and
            built-in variable lists.
        """
        return cast(
            Dict[str, Any],
            await service.get_version(
                ctx, account_id, container_id, version_id, container_version_id
            ),
        )

    async def get_live_version(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Get the container version currently published to production.

        This is what visitors to the site are actually running, which is the
        right starting point for "what is live right now".

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The live version with its full entity lists.
        """
        return cast(
            Dict[str, Any],
            await service.get_live_version(ctx, account_id, container_id),
        )

    async def update_version(
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        container_version: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a container version's name or notes.

        Only the metadata is editable. A version's entities are a frozen
        snapshot; to change them, edit a workspace and create a new version.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            container_version: ContainerVersion resource, e.g.
                {"name": "Release 2026-09", "notes": "Adds consent mode"}.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the version changed in the meantime.

        Returns:
            The updated version.
        """
        return cast(
            Dict[str, Any],
            await service.update_version(
                ctx,
                account_id,
                container_id,
                version_id,
                container_version,
                fingerprint,
            ),
        )

    async def delete_version(
        ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> Dict[str, Any]:
        """Delete a container version.

        Deletion is reversible with undelete_version. The live version cannot
        be deleted.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_version(ctx, account_id, container_id, version_id)

    async def undelete_version(
        ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> Dict[str, Any]:
        """Restore a deleted container version.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.

        Returns:
            The restored version.
        """
        return cast(
            Dict[str, Any],
            await service.undelete_version(ctx, account_id, container_id, version_id),
        )

    async def publish_version(
        ctx: Context,
        account_id: str,
        container_id: str,
        version_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish a container version to production.

        This takes effect on the live site immediately, for every visitor, with
        no staged rollout. The only way back is to publish an earlier version
        over the top. Confirm the version is the intended one before calling.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.
            fingerprint: Fingerprint from a previous read. When given, the
                publish fails if the version changed in the meantime.

        Returns:
            The published version, plus compilerError if the container failed
            to compile.
        """
        return cast(
            Dict[str, Any],
            await service.publish_version(
                ctx, account_id, container_id, version_id, fingerprint
            ),
        )

    async def set_latest_version(
        ctx: Context, account_id: str, container_id: str, version_id: str
    ) -> Dict[str, Any]:
        """Set the version that workspaces sync against.

        This is the baseline used to detect conflicts when a workspace syncs.
        It does not change what is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            version_id: Numeric container version ID.

        Returns:
            The version now marked as latest.
        """
        return cast(
            Dict[str, Any],
            await service.set_latest_version(ctx, account_id, container_id, version_id),
        )

    return [
        list_version_headers,
        get_latest_version_header,
        get_version,
        get_live_version,
        update_version,
        delete_version,
        undelete_version,
        publish_version,
        set_latest_version,
    ]


def register_versions_tools(mcp: FastMCP[Any]) -> VersionsService:
    """Register the versions tools with an MCP server."""
    service = VersionsService()
    for tool in create_versions_tools(service):
        mcp.tool(tool)
    return service
