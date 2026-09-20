"""Built-in variables service -- the variables Tag Manager supplies itself.

Covers ``accounts.containers.workspaces.built_in_variables`` in full: list,
create, delete, revert.

This resource does not behave like the other workspace collections:

- there is no get or update, because a built-in variable is either enabled or
  not -- there is nothing to configure;
- entities are addressed by ``type`` rather than by ID, and create and delete
  take several types per call;
- the three paths differ. create and list hang off the workspace, delete off
  ``{workspace}/built_in_variables``, and revert off the workspace again.

One divergence to know about: the discovery document marks ``type`` as repeated
for create and delete, while ``google-api-python-client-stubs`` types it as a
single Literal. The discovery document is authoritative at runtime, so lists are
sent; they reach the API through ``optional()``, whose ``Dict[str, Any]`` return
keeps pyright from checking them against the narrower stub.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import built_in_variables_path, workspace_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        CreateBuiltInVariableResponse,
        ListEnabledBuiltInVariablesResponse,
        RevertBuiltInVariableResponse,
    )

logger = get_logger(__name__)


class BuiltInVariablesService:
    """Enable and disable a workspace's built-in variables."""

    def list_built_in_variables(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListEnabledBuiltInVariablesResponse]:
        """List the built-in variables enabled in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = (
            get_client()
            .service.accounts()
            .containers()
            .workspaces()
            .built_in_variables()
        )
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing enabled built-in variables in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    async def create_built_in_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        types: List[str],
    ) -> CreateBuiltInVariableResponse:
        """Enable one or more built-in variables in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            types: Built-in variable type names to enable, e.g.
                ``["pageUrl", "clickText"]``.
        """
        client = get_client()
        client.require_write("create_built_in_variable")
        resource = (
            client.service.accounts().containers().workspaces().built_in_variables()
        )
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"enabling built-in variables {types} in {parent}",
            lambda: resource.create(parent=parent, **optional(type=types)).execute(),
        )
        logger.info("Enabled built-in variables %s in %s", types, parent)
        return result

    async def delete_built_in_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        types: List[str],
    ) -> Dict[str, Any]:
        """Disable one or more built-in variables in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            types: Built-in variable type names to disable.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_built_in_variable")
        resource = (
            client.service.accounts().containers().workspaces().built_in_variables()
        )
        path = built_in_variables_path(account_id, container_id, workspace_id)
        await execute(
            ctx,
            f"disabling built-in variables {types} in {path}",
            lambda: resource.delete(path=path, **optional(type=types)).execute(),
        )
        logger.info("Disabled built-in variables %s in %s", types, path)
        return {"path": path, "status": "deleted", "type": list(types)}

    async def revert_built_in_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_type: Optional[str] = None,
    ) -> RevertBuiltInVariableResponse:
        """Discard a workspace's change to one built-in variable.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_type: The single built-in variable type to revert. Unlike
                create and delete, this method takes one type, not a list.
        """
        client = get_client()
        client.require_write("revert_built_in_variable")
        resource = (
            client.service.accounts().containers().workspaces().built_in_variables()
        )
        path = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"reverting built-in variable {variable_type} in {path}",
            lambda: resource.revert(
                path=path, **optional(type=variable_type)
            ).execute(),
        )
        logger.info("Reverted built-in variable %s in %s", variable_type, path)
        return result


def create_built_in_variables_tools(
    service: BuiltInVariablesService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a BuiltInVariablesService."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_built_in_variables(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the built-in variables enabled in a workspace.

        Built-in variables (Page URL, Click Text, and so on) are supplied by
        Tag Manager and only need enabling. They are separate from the
        user-defined variables in list_variables.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each enabled variable's type and display name. Variables that are
            not enabled are absent rather than listed as disabled.
        """
        return cast(
            Dict[str, Any],
            await service.list_built_in_variables(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def create_built_in_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        types: List[str],
    ) -> Dict[str, Any]:
        """Enable built-in variables in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            types: Type names to enable, e.g. ["pageUrl", "pagePath",
                "referrer", "clickText", "formId", "event"]. Several may be
                enabled in one call. Names are camelCase codes, not the
                display names shown in the Tag Manager UI.

        Returns:
            The built-in variables that were enabled.
        """
        return cast(
            Dict[str, Any],
            await service.create_built_in_variable(
                ctx, account_id, container_id, workspace_id, types
            ),
        )

    async def delete_built_in_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        types: List[str],
    ) -> Dict[str, Any]:
        """Disable built-in variables in a workspace.

        Anything referencing a disabled variable stops resolving, so check for
        uses first.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            types: Type names to disable, e.g. ["clickClasses"].

        Returns:
            Confirmation listing the types that were disabled.
        """
        return await service.delete_built_in_variable(
            ctx, account_id, container_id, workspace_id, types
        )

    async def revert_built_in_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's change to one built-in variable.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_type: The one type to revert, e.g. "clickText". This
                method takes a single type, not a list.

        Returns:
            The built-in variable as it stands in the base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_built_in_variable(
                ctx, account_id, container_id, workspace_id, variable_type
            ),
        )

    return [
        list_built_in_variables,
        create_built_in_variable,
        delete_built_in_variable,
        revert_built_in_variable,
    ]


def register_built_in_variables_tools(mcp: FastMCP[Any]) -> BuiltInVariablesService:
    """Register the built-in variables tools with an MCP server."""
    service = BuiltInVariablesService()
    for tool in create_built_in_variables_tools(service):
        mcp.tool(tool)
    return service
