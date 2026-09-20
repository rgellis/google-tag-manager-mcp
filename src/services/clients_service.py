"""Clients service -- request handlers in a server-side container.

Covers ``accounts.containers.workspaces.clients`` in full: list, get,
create, update, delete, revert.

A Tag Manager Client claims an incoming HTTP request and turns it into
events the container's tags can act on. Clients exist only in server
containers (usageContext "server"); a web container has none.

Unrelated to the API client in src/client.py, which is this server's
own credentialed connection to Google.
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
        Client,
        ListClientsResponse,
        RevertClientResponse,
    )

logger = get_logger(__name__)


def _client_path(
    account_id: str, container_id: str, workspace_id: str, client_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "clients",
        client_id,
        "client_id",
    )


class ClientsService:
    """Manage the clients in a workspace."""

    def list_clients(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListClientsResponse]:
        """List the clients in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().clients()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing clients in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_client(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
    ) -> Awaitable[Client]:
        """Retrieve one client.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.
        """
        resource = get_client().service.accounts().containers().workspaces().clients()
        path = _client_path(account_id, container_id, workspace_id, client_id)
        return execute(
            ctx,
            f"getting client {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_client(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client: Dict[str, Any],
    ) -> Client:
        """Create a client in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client: Client resource to create.
        """
        api_client = get_client()
        api_client.require_write("create_client")
        resource = api_client.service.accounts().containers().workspaces().clients()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a client in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("Client", client)
            ).execute(),
        )
        logger.info("Created client in %s", parent)
        return result

    async def update_client(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
        client: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Client:
        """Update a client.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.
            client: Client resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the client.
        """
        api_client = get_client()
        api_client.require_write("update_client")
        resource = api_client.service.accounts().containers().workspaces().clients()
        path = _client_path(account_id, container_id, workspace_id, client_id)
        result = await execute(
            ctx,
            f"updating client {path}",
            lambda: resource.update(
                path=path,
                body=cast("Client", client),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated client %s", path)
        return result

    async def delete_client(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """Delete a client from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        api_client = get_client()
        api_client.require_write("delete_client")
        resource = api_client.service.accounts().containers().workspaces().clients()
        path = _client_path(account_id, container_id, workspace_id, client_id)
        await execute(
            ctx,
            f"deleting client {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted client %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_client(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertClientResponse:
        """Discard a workspace's changes to one client.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the client.
        """
        api_client = get_client()
        api_client.require_write("revert_client")
        resource = api_client.service.accounts().containers().workspaces().clients()
        path = _client_path(account_id, container_id, workspace_id, client_id)
        result = await execute(
            ctx,
            f"reverting client {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted client %s", path)
        return result


def create_clients_tools(
    service: ClientsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a ClientsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_clients(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the clients in a workspace.

        A web container returns an empty list; clients exist only in server
        containers.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each client's clientId, name, type, priority and parameter list.
        """
        return cast(
            Dict[str, Any],
            await service.list_clients(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_client(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """Get one client from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.

        Returns:
            The client's full configuration, including its fingerprint --
            which update_client and revert_client need.
        """
        return cast(
            Dict[str, Any],
            await service.get_client(
                ctx, account_id, container_id, workspace_id, client_id
            ),
        )

    async def create_client(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a client in a workspace.

        Only server containers accept clients. Creating one in a web
        container fails.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client: Client resource. Requires name and type, e.g.
                {"name": "GA4 client", "type": "gaaw_client",
                 "priority": 0,
                 "parameter": [{"type": "boolean",
                                "key": "activateGa4Support",
                                "value": "true"}]}.

        Returns:
            The created client, including its new clientId.
        """
        return cast(
            Dict[str, Any],
            await service.create_client(
                ctx, account_id, container_id, workspace_id, client
            ),
        )

    async def update_client(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
        client: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a client in a workspace.

        The client you send replaces the stored one, so read it with
        get_client first and send the whole thing back with your edits
        applied. Omitted fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.
            client: Complete Client resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the client changed in the meantime.

        Returns:
            The updated client.
        """
        return cast(
            Dict[str, Any],
            await service.update_client(
                ctx,
                account_id,
                container_id,
                workspace_id,
                client_id,
                client,
                fingerprint,
            ),
        )

    async def delete_client(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
    ) -> Dict[str, Any]:
        """Delete a client from a workspace.

        This affects the workspace only. The client stays in production until
        a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_client(
            ctx, account_id, container_id, workspace_id, client_id
        )

    async def revert_client(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        client_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one client.

        Restores the client to the state of the container version the
        workspace was branched from, leaving the workspace's other changes
        alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            client_id: Numeric client ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored client, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_client(
                ctx,
                account_id,
                container_id,
                workspace_id,
                client_id,
                fingerprint,
            ),
        )

    return [
        list_clients,
        get_client,
        create_client,
        update_client,
        delete_client,
        revert_client,
    ]


def register_clients_tools(mcp: FastMCP[Any]) -> ClientsService:
    """Register the clients tools with an MCP server."""
    service = ClientsService()
    for tool in create_clients_tools(service):
        mcp.tool(tool)
    return service
