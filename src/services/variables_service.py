"""Variables service -- the user-defined variables a container resolves.

Covers ``accounts.containers.workspaces.variables`` in full: list, get,
create, update, delete, revert.

These are the user-defined variables only. The variables Tag Manager
supplies itself are enabled per workspace through the built-in
variables resource, which has its own module.
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
        ListVariablesResponse,
        RevertVariableResponse,
        Variable,
    )

logger = get_logger(__name__)


def _variable_path(
    account_id: str, container_id: str, workspace_id: str, variable_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "variables",
        variable_id,
        "variable_id",
    )


class VariablesService:
    """Manage the variables in a workspace."""

    def list_variables(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListVariablesResponse]:
        """List the variables in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().variables()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing variables in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
    ) -> Awaitable[Variable]:
        """Retrieve one variable.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.
        """
        resource = get_client().service.accounts().containers().workspaces().variables()
        path = _variable_path(account_id, container_id, workspace_id, variable_id)
        return execute(
            ctx,
            f"getting variable {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable: Dict[str, Any],
    ) -> Variable:
        """Create a variable in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable: Variable resource to create.
        """
        client = get_client()
        client.require_write("create_variable")
        resource = client.service.accounts().containers().workspaces().variables()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a variable in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("Variable", variable)
            ).execute(),
        )
        logger.info("Created variable in %s", parent)
        return result

    async def update_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
        variable: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Variable:
        """Update a variable.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.
            variable: Variable resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the variable.
        """
        client = get_client()
        client.require_write("update_variable")
        resource = client.service.accounts().containers().workspaces().variables()
        path = _variable_path(account_id, container_id, workspace_id, variable_id)
        result = await execute(
            ctx,
            f"updating variable {path}",
            lambda: resource.update(
                path=path,
                body=cast("Variable", variable),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated variable %s", path)
        return result

    async def delete_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
    ) -> Dict[str, Any]:
        """Delete a variable from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_variable")
        resource = client.service.accounts().containers().workspaces().variables()
        path = _variable_path(account_id, container_id, workspace_id, variable_id)
        await execute(
            ctx,
            f"deleting variable {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted variable %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_variable(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertVariableResponse:
        """Discard a workspace's changes to one variable.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the variable.
        """
        client = get_client()
        client.require_write("revert_variable")
        resource = client.service.accounts().containers().workspaces().variables()
        path = _variable_path(account_id, container_id, workspace_id, variable_id)
        result = await execute(
            ctx,
            f"reverting variable {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted variable %s", path)
        return result


def create_variables_tools(
    service: VariablesService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a VariablesService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_variables(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the variables in a workspace.

        Other entities reference these by name in {{double braces}}, so the
        names here are what tag and trigger parameters point at.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each variable's variableId, name, type and parameter list.
        """
        return cast(
            Dict[str, Any],
            await service.list_variables(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
    ) -> Dict[str, Any]:
        """Get one variable from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.

        Returns:
            The variable's full configuration, including its fingerprint --
            which update_variable and revert_variable need.
        """
        return cast(
            Dict[str, Any],
            await service.get_variable(
                ctx, account_id, container_id, workspace_id, variable_id
            ),
        )

    async def create_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a variable in a workspace.

        Variable types are Tag Manager's internal codes: "v" is a data
        layer variable, "c" a constant, "jsm" custom JavaScript, "k" a
        first-party cookie, "u" a URL variable. Copy the shape from an
        existing variable via get_variable when unsure.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable: Variable resource. Requires name and type, e.g.
                {"name": "DL - transaction ID",
                 "type": "v",
                 "parameter": [
                   {"type": "integer", "key": "dataLayerVersion",
                    "value": "2"},
                   {"type": "template", "key": "name",
                    "value": "ecommerce.transaction_id"}]}.

        Returns:
            The created variable, including its new variableId.
        """
        return cast(
            Dict[str, Any],
            await service.create_variable(
                ctx, account_id, container_id, workspace_id, variable
            ),
        )

    async def update_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
        variable: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a variable in a workspace.

        The variable you send replaces the stored one, so read it with
        get_variable first and send the whole thing back with your edits
        applied. Omitted fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.
            variable: Complete Variable resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the variable changed in the meantime.

        Returns:
            The updated variable.
        """
        return cast(
            Dict[str, Any],
            await service.update_variable(
                ctx,
                account_id,
                container_id,
                workspace_id,
                variable_id,
                variable,
                fingerprint,
            ),
        )

    async def delete_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
    ) -> Dict[str, Any]:
        """Delete a variable from a workspace.

        This affects the workspace only. The variable stays in production until
        a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_variable(
            ctx, account_id, container_id, workspace_id, variable_id
        )

    async def revert_variable(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        variable_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one variable.

        Restores the variable to the state of the container version the
        workspace was branched from, leaving the workspace's other changes
        alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            variable_id: Numeric variable ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored variable, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_variable(
                ctx,
                account_id,
                container_id,
                workspace_id,
                variable_id,
                fingerprint,
            ),
        )

    return [
        list_variables,
        get_variable,
        create_variable,
        update_variable,
        delete_variable,
        revert_variable,
    ]


def register_variables_tools(mcp: FastMCP[Any]) -> VariablesService:
    """Register the variables tools with an MCP server."""
    service = VariablesService()
    for tool in create_variables_tools(service):
        mcp.tool(tool)
    return service
