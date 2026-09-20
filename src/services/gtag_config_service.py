"""Google tag config service -- gtag.js settings held in a workspace.

Covers ``accounts.containers.workspaces.gtag_config`` in full: list, get,
create, update, delete.

Alone among the workspace entity resources this one has no revert method, so a
change here can only be undone by editing it back or discarding the workspace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import workspace_child_path, workspace_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import GtagConfig, ListGtagConfigResponse

logger = get_logger(__name__)


def _gtag_config_path(
    account_id: str, container_id: str, workspace_id: str, gtag_config_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "gtag_config",
        gtag_config_id,
        "gtag_config_id",
    )


class GtagConfigService:
    """Manage the Google tag configurations in a workspace."""

    def list_gtag_configs(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListGtagConfigResponse]:
        """List the Google tag configs in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = (
            get_client().service.accounts().containers().workspaces().gtag_config()
        )
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing Google tag configs in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_gtag_config(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
    ) -> Awaitable[GtagConfig]:
        """Retrieve one Google tag config.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.
        """
        resource = (
            get_client().service.accounts().containers().workspaces().gtag_config()
        )
        path = _gtag_config_path(account_id, container_id, workspace_id, gtag_config_id)
        return execute(
            ctx,
            f"getting Google tag config {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_gtag_config(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config: Dict[str, Any],
    ) -> GtagConfig:
        """Create a Google tag config in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config: GtagConfig resource to create.
        """
        client = get_client()
        client.require_write("create_gtag_config")
        resource = client.service.accounts().containers().workspaces().gtag_config()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a Google tag config in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("GtagConfig", gtag_config)
            ).execute(),
        )
        logger.info("Created Google tag config in %s", parent)
        return result

    async def update_gtag_config(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
        gtag_config: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> GtagConfig:
        """Update a Google tag config.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.
            gtag_config: GtagConfig resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the config.
        """
        client = get_client()
        client.require_write("update_gtag_config")
        resource = client.service.accounts().containers().workspaces().gtag_config()
        path = _gtag_config_path(account_id, container_id, workspace_id, gtag_config_id)
        result = await execute(
            ctx,
            f"updating Google tag config {path}",
            lambda: resource.update(
                path=path,
                body=cast("GtagConfig", gtag_config),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated Google tag config %s", path)
        return result

    async def delete_gtag_config(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
    ) -> Dict[str, Any]:
        """Delete a Google tag config from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_gtag_config")
        resource = client.service.accounts().containers().workspaces().gtag_config()
        path = _gtag_config_path(account_id, container_id, workspace_id, gtag_config_id)
        await execute(
            ctx,
            f"deleting Google tag config {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted Google tag config %s", path)
        return {"path": path, "status": "deleted"}


def create_gtag_config_tools(
    service: GtagConfigService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a GtagConfigService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_gtag_configs(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the Google tag configurations in a workspace.

        These are the gtag.js settings a Google tag applies to its
        destinations -- the API equivalent of the "Configuration settings"
        panel on a Google tag.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each config's gtagConfigId, type and parameter list.
        """
        return cast(
            Dict[str, Any],
            await service.list_gtag_configs(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_gtag_config(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
    ) -> Dict[str, Any]:
        """Get one Google tag configuration from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.

        Returns:
            The config's type, parameter list and fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_gtag_config(
                ctx, account_id, container_id, workspace_id, gtag_config_id
            ),
        )

    async def create_gtag_config(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a Google tag configuration in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config: GtagConfig resource, e.g.
                {"type": "googtag",
                 "parameter": [{"type": "template", "key": "tagId",
                                "value": "G-ABC123"}]}.

        Returns:
            The created config, including its new gtagConfigId.
        """
        return cast(
            Dict[str, Any],
            await service.create_gtag_config(
                ctx, account_id, container_id, workspace_id, gtag_config
            ),
        )

    async def update_gtag_config(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
        gtag_config: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a Google tag configuration.

        The config you send replaces the stored one, so read it with
        get_gtag_config first and send the whole thing back with your edits
        applied.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.
            gtag_config: Complete GtagConfig resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the config changed in the meantime.

        Returns:
            The updated config.
        """
        return cast(
            Dict[str, Any],
            await service.update_gtag_config(
                ctx,
                account_id,
                container_id,
                workspace_id,
                gtag_config_id,
                gtag_config,
                fingerprint,
            ),
        )

    async def delete_gtag_config(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gtag_config_id: str,
    ) -> Dict[str, Any]:
        """Delete a Google tag configuration from a workspace.

        Unlike every other workspace entity, Google tag configs have no revert
        method, so this cannot be undone short of discarding the workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gtag_config_id: Numeric Google tag config ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_gtag_config(
            ctx, account_id, container_id, workspace_id, gtag_config_id
        )

    return [
        list_gtag_configs,
        get_gtag_config,
        create_gtag_config,
        update_gtag_config,
        delete_gtag_config,
    ]


def register_gtag_config_tools(mcp: FastMCP[Any]) -> GtagConfigService:
    """Register the Google tag config tools with an MCP server."""
    service = GtagConfigService()
    for tool in create_gtag_config_tools(service):
        mcp.tool(tool)
    return service
