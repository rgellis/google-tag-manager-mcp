"""Triggers service -- the conditions under which tags fire.

Covers ``accounts.containers.workspaces.triggers`` in full: list, get,
create, update, delete, revert.
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
        ListTriggersResponse,
        RevertTriggerResponse,
        Trigger,
    )

logger = get_logger(__name__)


def _trigger_path(
    account_id: str, container_id: str, workspace_id: str, trigger_id: str
) -> str:
    return workspace_child_path(
        account_id,
        container_id,
        workspace_id,
        "triggers",
        trigger_id,
        "trigger_id",
    )


class TriggersService:
    """Manage the triggers in a workspace."""

    def list_triggers(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListTriggersResponse]:
        """List the triggers in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().triggers()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing triggers in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_trigger(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
    ) -> Awaitable[Trigger]:
        """Retrieve one trigger.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.
        """
        resource = get_client().service.accounts().containers().workspaces().triggers()
        path = _trigger_path(account_id, container_id, workspace_id, trigger_id)
        return execute(
            ctx,
            f"getting trigger {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_trigger(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger: Dict[str, Any],
    ) -> Trigger:
        """Create a trigger in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger: Trigger resource to create.
        """
        client = get_client()
        client.require_write("create_trigger")
        resource = client.service.accounts().containers().workspaces().triggers()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a trigger in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("Trigger", trigger)
            ).execute(),
        )
        logger.info("Created trigger in %s", parent)
        return result

    async def update_trigger(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
        trigger: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Trigger:
        """Update a trigger.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.
            trigger: Trigger resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the trigger.
        """
        client = get_client()
        client.require_write("update_trigger")
        resource = client.service.accounts().containers().workspaces().triggers()
        path = _trigger_path(account_id, container_id, workspace_id, trigger_id)
        result = await execute(
            ctx,
            f"updating trigger {path}",
            lambda: resource.update(
                path=path,
                body=cast("Trigger", trigger),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated trigger %s", path)
        return result

    async def delete_trigger(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
    ) -> Dict[str, Any]:
        """Delete a trigger from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_trigger")
        resource = client.service.accounts().containers().workspaces().triggers()
        path = _trigger_path(account_id, container_id, workspace_id, trigger_id)
        await execute(
            ctx,
            f"deleting trigger {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted trigger %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_trigger(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertTriggerResponse:
        """Discard a workspace's changes to one trigger.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the trigger.
        """
        client = get_client()
        client.require_write("revert_trigger")
        resource = client.service.accounts().containers().workspaces().triggers()
        path = _trigger_path(account_id, container_id, workspace_id, trigger_id)
        result = await execute(
            ctx,
            f"reverting trigger {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted trigger %s", path)
        return result


def create_triggers_tools(
    service: TriggersService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a TriggersService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_triggers(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the triggers in a workspace.

        Triggers are referenced by tags through firingTriggerId and
        blockingTriggerId, so list these before creating a tag.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each trigger's triggerId, name, type and the filter, customEvent
            and autoEventFilter conditions that decide when it fires.
        """
        return cast(
            Dict[str, Any],
            await service.list_triggers(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_trigger(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
    ) -> Dict[str, Any]:
        """Get one trigger from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.

        Returns:
            The trigger's full configuration, including its fingerprint --
            which update_trigger and revert_trigger need.
        """
        return cast(
            Dict[str, Any],
            await service.get_trigger(
                ctx, account_id, container_id, workspace_id, trigger_id
            ),
        )

    async def create_trigger(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a trigger in a workspace.

        Trigger types are Tag Manager's internal codes: "pageview",
        "domReady", "windowLoaded", "click", "linkClick",
        "formSubmission", "customEvent", "timer" and so on. Copy the
        shape from an existing trigger via get_trigger when unsure.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger: Trigger resource. Requires name and type, e.g.
                {"name": "All Pages", "type": "pageview"}, or with a
                condition:
                {"name": "Checkout page", "type": "pageview",
                 "filter": [{"type": "contains",
                             "parameter": [
                               {"type": "template", "key": "arg0",
                                "value": "{{Page Path}}"},
                               {"type": "template", "key": "arg1",
                                "value": "/checkout"}]}]}.

        Returns:
            The created trigger, including its new triggerId.
        """
        return cast(
            Dict[str, Any],
            await service.create_trigger(
                ctx, account_id, container_id, workspace_id, trigger
            ),
        )

    async def update_trigger(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
        trigger: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a trigger in a workspace.

        The trigger you send replaces the stored one, so read it with
        get_trigger first and send the whole thing back with your edits
        applied. Omitted fields are cleared, not preserved.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.
            trigger: Complete Trigger resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the trigger changed in the meantime.

        Returns:
            The updated trigger.
        """
        return cast(
            Dict[str, Any],
            await service.update_trigger(
                ctx,
                account_id,
                container_id,
                workspace_id,
                trigger_id,
                trigger,
                fingerprint,
            ),
        )

    async def delete_trigger(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
    ) -> Dict[str, Any]:
        """Delete a trigger from a workspace.

        This affects the workspace only. The trigger stays in production until
        a version without it is published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_trigger(
            ctx, account_id, container_id, workspace_id, trigger_id
        )

    async def revert_trigger(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        trigger_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one trigger.

        Restores the trigger to the state of the container version the
        workspace was branched from, leaving the workspace's other changes
        alone.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            trigger_id: Numeric trigger ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored trigger, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_trigger(
                ctx,
                account_id,
                container_id,
                workspace_id,
                trigger_id,
                fingerprint,
            ),
        )

    return [
        list_triggers,
        get_trigger,
        create_trigger,
        update_trigger,
        delete_trigger,
        revert_trigger,
    ]


def register_triggers_tools(mcp: FastMCP[Any]) -> TriggersService:
    """Register the triggers tools with an MCP server."""
    service = TriggersService()
    for tool in create_triggers_tools(service):
        mcp.tool(tool)
    return service
