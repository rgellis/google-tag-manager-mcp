"""Destinations service -- Google tag destinations linked to a container.

Covers the ``accounts.containers.destinations`` resource in full: list, get,
link.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import container_path, destination_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        Destination,
        ListDestinationsResponse,
    )

logger = get_logger(__name__)


class DestinationsService:
    """Manage the destinations (Ads, GA4, Floodlight) a container serves."""

    def list_destinations(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Awaitable[ListDestinationsResponse]:
        """List the destinations linked to a container.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"listing destinations for {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .destinations()
                .list(parent=parent)
                .execute()
            ),
        )

    def get_destination(
        self, ctx: Context, account_id: str, container_id: str, destination_id: str
    ) -> Awaitable[Destination]:
        """Retrieve one destination.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            destination_id: Destination ID, e.g. ``AW-123456789``.
        """
        client = get_client()
        path = destination_path(account_id, container_id, destination_id)
        return execute(
            ctx,
            f"getting destination {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .destinations()
                .get(path=path)
                .execute()
            ),
        )

    async def link_destination(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        destination_id: str,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Destination:
        """Link a destination to a container.

        The destination is removed from whichever container currently holds it,
        so this both links and unlinks.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            destination_id: Destination ID to link, e.g. ``AW-123456789``.
            allow_user_permission_feature_update: Must be true for the link to
                be allowed to turn the user-permissions feature on.
        """
        client = get_client()
        client.require_write("link_destination")
        parent = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"linking destination {destination_id} to {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .destinations()
                .link(
                    parent=parent,
                    **optional(
                        destinationId=destination_id,
                        allowUserPermissionFeatureUpdate=(
                            allow_user_permission_feature_update
                        ),
                    ),
                )
                .execute()
            ),
        )
        logger.info("Linked destination %s to %s", destination_id, parent)
        return result


def create_destinations_tools(
    service: DestinationsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a DestinationsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_destinations(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """List the Google tag destinations linked to a container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            Each destination's path, destinationId, name and destinationLinkId.
        """
        return cast(
            Dict[str, Any],
            await service.list_destinations(ctx, account_id, container_id),
        )

    async def get_destination(
        ctx: Context, account_id: str, container_id: str, destination_id: str
    ) -> Dict[str, Any]:
        """Get one destination linked to a container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            destination_id: Destination ID, e.g. AW-123456789 or G-ABC123.

        Returns:
            The destination's path, destinationId, name and fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_destination(
                ctx, account_id, container_id, destination_id
            ),
        )

    async def link_destination(
        ctx: Context,
        account_id: str,
        container_id: str,
        destination_id: str,
        allow_user_permission_feature_update: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Link a Google tag destination to a container.

        The destination is taken from whichever container currently holds it,
        so this moves rather than copies.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID to link the destination to.
            destination_id: Destination ID, e.g. AW-123456789 or G-ABC123.
            allow_user_permission_feature_update: Must be true if the link would
                turn the user-permissions feature on.

        Returns:
            The linked destination.
        """
        return cast(
            Dict[str, Any],
            await service.link_destination(
                ctx,
                account_id,
                container_id,
                destination_id,
                allow_user_permission_feature_update,
            ),
        )

    return [list_destinations, get_destination, link_destination]


def register_destinations_tools(mcp: FastMCP[Any]) -> DestinationsService:
    """Register the destinations tools with an MCP server."""
    service = DestinationsService()
    for tool in create_destinations_tools(service):
        mcp.tool(tool)
    return service
