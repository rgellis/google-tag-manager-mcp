"""Zones service -- delegated sections of a Tag Manager 360 container.

Covers ``accounts.containers.workspaces.zones`` in full: list, get,
create, update, delete, revert.

A Zone lets one container load another under a boundary, so a team can
be given its own container without being given the parent. Zones are a
Tag Manager 360 feature; a standard container has none.
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
        ListZonesResponse,
        RevertZoneResponse,
        Zone,
    )

logger = get_logger(__name__)


def _zone_path(
    account_id: str, container_id: str, workspace_id: str, zone_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "zones",
        zone_id,
        "zone_id",
    )


class ZonesService:
    """Manage the zones in a workspace."""

    def list_zones(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListZonesResponse]:
        """List the zones in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().zones()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing zones in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_zone(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
    ) -> Awaitable[Zone]:
        """Retrieve one zone.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.
        """
        resource = get_client().service.accounts().containers().workspaces().zones()
        path = _zone_path(account_id, container_id, workspace_id, zone_id)
        return execute(
            ctx,
            f"getting zone {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_zone(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone: Dict[str, Any],
    ) -> Zone:
        """Create a zone in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone: Zone resource to create.
        """
        client = get_client()
        client.require_write("create_zone")
        resource = client.service.accounts().containers().workspaces().zones()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a zone in {parent}",
            lambda: resource.create(parent=parent, body=cast("Zone", zone)).execute(),
        )
        logger.info("Created zone in %s", parent)
        return result

    async def update_zone(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
        zone: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Zone:
        """Update a zone.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.
            zone: Zone resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the zone.
        """
        client = get_client()
        client.require_write("update_zone")
        resource = client.service.accounts().containers().workspaces().zones()
        path = _zone_path(account_id, container_id, workspace_id, zone_id)
        result = await execute(
            ctx,
            f"updating zone {path}",
            lambda: resource.update(
                path=path,
                body=cast("Zone", zone),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated zone %s", path)
        return result

    async def delete_zone(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
    ) -> Dict[str, Any]:
        """Delete a zone from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_zone")
        resource = client.service.accounts().containers().workspaces().zones()
        path = _zone_path(account_id, container_id, workspace_id, zone_id)
        await execute(
            ctx,
            f"deleting zone {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted zone %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_zone(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertZoneResponse:
        """Discard a workspace's changes to one zone.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the zone.
        """
        client = get_client()
        client.require_write("revert_zone")
        resource = client.service.accounts().containers().workspaces().zones()
        path = _zone_path(account_id, container_id, workspace_id, zone_id)
        result = await execute(
            ctx,
            f"reverting zone {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted zone %s", path)
        return result


def create_zones_tools(
    service: ZonesService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a ZonesService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_zones(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the zones in a workspace.

        A standard (non-360) container returns an empty list.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each zone's zoneId, name, childContainer list, boundary and
            typeRestriction.
        """
        return cast(
            Dict[str, Any],
            await service.list_zones(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_zone(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
    ) -> Dict[str, Any]:
        """Get one zone from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.

        Returns:
            The zone's full configuration, including its fingerprint --
            which update_zone and revert_zone need.
        """
        return cast(
            Dict[str, Any],
            await service.get_zone(
                ctx, account_id, container_id, workspace_id, zone_id
            ),
        )

    async def create_zone(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a zone in a workspace.

        Zones require Tag Manager 360. Creating one in a standard container
        fails.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone: Zone resource. Requires name, e.g.
                {"name": "Marketing zone",
                 "childContainer": [{"publicId": "GTM-XXXXXXX"}],
                 "boundary": {"condition": [...]}}.

        Returns:
            The created zone, including its new zoneId.
        """
        return cast(
            Dict[str, Any],
            await service.create_zone(
                ctx, account_id, container_id, workspace_id, zone
            ),
        )

    async def update_zone(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
        zone: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a zone in a workspace.

        The zone you send replaces the stored one, so read it with
        get_zone first and send the whole thing back with your edits
        applied. Omitted fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.
            zone: Complete Zone resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the zone changed in the meantime.

        Returns:
            The updated zone.
        """
        return cast(
            Dict[str, Any],
            await service.update_zone(
                ctx,
                account_id,
                container_id,
                workspace_id,
                zone_id,
                zone,
                fingerprint,
            ),
        )

    async def delete_zone(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
    ) -> Dict[str, Any]:
        """Delete a zone from a workspace.

        This affects the workspace only. The zone stays in production until
        a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_zone(
            ctx, account_id, container_id, workspace_id, zone_id
        )

    async def revert_zone(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        zone_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one zone.

        Restores the zone to the state of the container version the
        workspace was branched from, leaving the workspace's other changes
        alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            zone_id: Numeric zone ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored zone, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_zone(
                ctx,
                account_id,
                container_id,
                workspace_id,
                zone_id,
                fingerprint,
            ),
        )

    return [
        list_zones,
        get_zone,
        create_zone,
        update_zone,
        delete_zone,
        revert_zone,
    ]


def register_zones_tools(mcp: FastMCP[Any]) -> ZonesService:
    """Register the zones tools with an MCP server."""
    service = ZonesService()
    for tool in create_zones_tools(service):
        mcp.tool(tool)
    return service
