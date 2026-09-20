"""Workspaces service -- the editable draft layer of a container.

Covers ``accounts.containers.workspaces``' own methods in full: list, get,
create, update, delete, getStatus, sync, resolve_conflict, quick_preview,
create_version and bulk_update. The entities inside a workspace live in their
own resources and have their own service modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.client import get_client
from src.paths import container_path, workspace_path
from src.services.base import execute
from src.utils import get_logger, optional

if TYPE_CHECKING:
    from googleapiclient._apis.tagmanager.v2 import (
        BulkUpdateWorkspaceResponse,
        CreateContainerVersionRequestVersionOptions,
        CreateContainerVersionResponse,
        Entity,
        GetWorkspaceStatusResponse,
        ListWorkspacesResponse,
        ProposedChange,
        QuickPreviewResponse,
        SyncWorkspaceResponse,
        Workspace,
    )

logger = get_logger(__name__)


class WorkspacesService:
    """Manage a container's workspaces and turn them into versions."""

    def list_workspaces(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListWorkspacesResponse]:
        """List a container's workspaces.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            page_token: Continuation token from a previous response.
        """
        client = get_client()
        parent = container_path(account_id, container_id)
        return execute(
            ctx,
            f"listing workspaces in {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .list(parent=parent, **optional(pageToken=page_token))
                .execute()
            ),
        )

    def get_workspace(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Awaitable[Workspace]:
        """Retrieve one workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
        """
        client = get_client()
        path = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"getting workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .get(path=path)
                .execute()
            ),
        )

    def get_workspace_status(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Awaitable[GetWorkspaceStatusResponse]:
        """Retrieve a workspace's modified and conflicting entities.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
        """
        client = get_client()
        path = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"getting the status of workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .getStatus(path=path)
                .execute()
            ),
        )

    async def create_workspace(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace: Dict[str, Any],
    ) -> Workspace:
        """Create a workspace in a container.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace: Workspace resource, e.g. ``{"name": "Consent mode"}``.
        """
        client = get_client()
        client.require_write("create_workspace")
        parent = container_path(account_id, container_id)
        result = await execute(
            ctx,
            f"creating a workspace in {parent}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .create(parent=parent, body=cast("Workspace", workspace))
                .execute()
            ),
        )
        logger.info("Created workspace in %s", parent)
        return result

    async def update_workspace(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        workspace: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Workspace:
        """Update a workspace's name or description.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            workspace: Workspace resource with the fields to change.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the workspace.
        """
        client = get_client()
        client.require_write("update_workspace")
        path = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"updating workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .update(
                    path=path,
                    body=cast("Workspace", workspace),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Updated workspace %s", path)
        return result

    async def delete_workspace(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Delete a workspace and discard its unversioned changes.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_workspace")
        path = workspace_path(account_id, container_id, workspace_id)
        await execute(
            ctx,
            f"deleting workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .delete(path=path)
                .execute()
            ),
        )
        logger.info("Deleted workspace %s", path)
        return {"path": path, "status": "deleted"}

    async def sync_workspace(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> SyncWorkspaceResponse:
        """Sync a workspace to the latest container version.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
        """
        client = get_client()
        client.require_write("sync_workspace")
        path = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"syncing workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .sync(path=path)
                .execute()
            ),
        )
        logger.info("Synced workspace %s", path)
        return result

    async def resolve_workspace_conflict(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        entity: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve one merge conflict by supplying the resolved entity.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            entity: Entity resource holding the resolved tag, trigger or
                variable, e.g. ``{"tag": {...}, "changeStatus": "updated"}``.
            fingerprint: When given, must match the fingerprint of the
                conflicting entity in the workspace.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("resolve_workspace_conflict")
        path = workspace_path(account_id, container_id, workspace_id)
        await execute(
            ctx,
            f"resolving a conflict in workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .resolve_conflict(
                    path=path,
                    body=cast("Entity", entity),
                    **optional(fingerprint=fingerprint),
                )
                .execute()
            ),
        )
        logger.info("Resolved a conflict in workspace %s", path)
        return {"path": path, "status": "resolved"}

    async def quick_preview_workspace(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> QuickPreviewResponse:
        """Build a throwaway version from a workspace to check it compiles.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
        """
        client = get_client()
        client.require_write("quick_preview_workspace")
        path = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"quick previewing workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .quick_preview(path=path)
                .execute()
            ),
        )
        logger.info("Quick previewed workspace %s", path)
        return result

    async def create_version(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        version_options: Optional[Dict[str, Any]] = None,
    ) -> CreateContainerVersionResponse:
        """Turn a workspace into a container version.

        The workspace is consumed: the API deletes it and sets the new version
        as the container's latest.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            version_options: Version options, e.g.
                ``{"name": "Release 2026-09", "notes": "Adds consent mode"}``.
        """
        client = get_client()
        client.require_write("create_version")
        path = workspace_path(account_id, container_id, workspace_id)
        body = cast(
            "CreateContainerVersionRequestVersionOptions",
            version_options if version_options is not None else {},
        )
        result = await execute(
            ctx,
            f"creating a container version from workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .create_version(path=path, body=body)
                .execute()
            ),
        )
        logger.info("Created a container version from workspace %s", path)
        return result

    async def bulk_update_workspace(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        proposed_change: Dict[str, Any],
    ) -> BulkUpdateWorkspaceResponse:
        """Apply many entity changes to a workspace in one call.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            proposed_change: ProposedChange resource listing the changes. New
                entities must carry IDs of the form ``new_1``, ``new_2`` and so
                on, unique within the request.
        """
        client = get_client()
        client.require_write("bulk_update_workspace")
        path = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"bulk updating workspace {path}",
            lambda: (
                client.service.accounts()
                .containers()
                .workspaces()
                .bulk_update(path=path, body=cast("ProposedChange", proposed_change))
                .execute()
            ),
        )
        logger.info("Bulk updated workspace %s", path)
        return result


def create_workspaces_tools(
    service: WorkspacesService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a WorkspacesService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_workspaces(
        ctx: Context,
        account_id: str,
        container_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List a container's workspaces.

        A workspace is the draft layer: tags, triggers and variables are edited
        in one, and nothing reaches production until it becomes a version and
        that version is published. Every container has a "Default Workspace".

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each workspace's path, workspaceId, name and description.
        """
        return cast(
            Dict[str, Any],
            await service.list_workspaces(ctx, account_id, container_id, page_token),
        )

    async def get_workspace(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Get one workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            The workspace's path, workspaceId, name, description and
            fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_workspace(ctx, account_id, container_id, workspace_id),
        )

    async def get_workspace_status(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """List what a workspace has changed, and what conflicts with the base.

        Run this before creating a version: it is the diff between the
        workspace and the container version it was branched from.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            workspaceChange entries for every modified entity, and
            mergeConflict entries for any that also changed in the base version.
        """
        return cast(
            Dict[str, Any],
            await service.get_workspace_status(
                ctx, account_id, container_id, workspace_id
            ),
        )

    async def create_workspace(
        ctx: Context, account_id: str, container_id: str, workspace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a workspace in a container.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace: Workspace resource. Requires name, e.g.
                {"name": "Consent mode", "description": "GDPR banner work"}.

        Returns:
            The created workspace, including its new workspaceId.
        """
        return cast(
            Dict[str, Any],
            await service.create_workspace(ctx, account_id, container_id, workspace),
        )

    async def update_workspace(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        workspace: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a workspace's name or description.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            workspace: Workspace resource with the fields to change.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the workspace changed in the meantime.

        Returns:
            The updated workspace.
        """
        return cast(
            Dict[str, Any],
            await service.update_workspace(
                ctx, account_id, container_id, workspace_id, workspace, fingerprint
            ),
        )

    async def delete_workspace(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Delete a workspace, discarding every change in it.

        Changes that were never turned into a version are lost. Check
        get_workspace_status first.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_workspace(
            ctx, account_id, container_id, workspace_id
        )

    async def sync_workspace(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Bring a workspace up to date with the latest container version.

        Unmodified entities are updated in place; anything the workspace also
        changed comes back as a merge conflict to resolve with
        resolve_workspace_conflict.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            syncStatus, plus a mergeConflict entry per entity needing a decision.
        """
        return cast(
            Dict[str, Any],
            await service.sync_workspace(ctx, account_id, container_id, workspace_id),
        )

    async def resolve_workspace_conflict(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        entity: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve one merge conflict raised by sync_workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            entity: Entity resource holding the resolved version, with exactly
                one of tag, trigger, variable, client, folder or
                transformation set, e.g.
                {"tag": {"tagId": "12", "name": "GA4 config", ...},
                 "changeStatus": "updated"}.
            fingerprint: Fingerprint of the conflicting entity in the workspace.

        Returns:
            Confirmation that the conflict was resolved.
        """
        return await service.resolve_workspace_conflict(
            ctx, account_id, container_id, workspace_id, entity, fingerprint
        )

    async def quick_preview_workspace(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Compile a workspace into a throwaway version to check it is valid.

        Nothing is saved and nothing is published; this is the cheap way to
        find compiler errors before create_version.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            The provisional containerVersion, compilerError, and
            syncStatus when the workspace is out of date.
        """
        return cast(
            Dict[str, Any],
            await service.quick_preview_workspace(
                ctx, account_id, container_id, workspace_id
            ),
        )

    async def create_version(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        version_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Turn a workspace into a container version.

        The workspace is consumed by this call -- the API deletes it and makes
        the new version the container's latest. Creating a version does not
        publish it; use publish_version for that.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            version_options: Name and notes for the version, e.g.
                {"name": "Release 2026-09", "notes": "Adds consent mode"}.

        Returns:
            The created containerVersion, compilerError if it failed to
            compile, and newWorkspacePath when the API created a replacement
            workspace.
        """
        return cast(
            Dict[str, Any],
            await service.create_version(
                ctx, account_id, container_id, workspace_id, version_options
            ),
        )

    async def bulk_update_workspace(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        proposed_change: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply many entity changes to a workspace in a single call.

        Use this when creating entities that reference each other -- a tag and
        the trigger that fires it, say -- since one call keeps them consistent.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            proposed_change: ProposedChange resource, e.g.
                {"change": [{"changeStatus": "added",
                             "tag": {"tagId": "new_1", "name": "GA4 event",
                                     "type": "gaawe", ...}}]}.
                IDs for new entities must be "new_" followed by a number and
                unique within the request; reference them from other new
                entities by the same string.

        Returns:
            The bulk update result, including any compilerError.
        """
        return cast(
            Dict[str, Any],
            await service.bulk_update_workspace(
                ctx, account_id, container_id, workspace_id, proposed_change
            ),
        )

    return [
        list_workspaces,
        get_workspace,
        get_workspace_status,
        create_workspace,
        update_workspace,
        delete_workspace,
        sync_workspace,
        resolve_workspace_conflict,
        quick_preview_workspace,
        create_version,
        bulk_update_workspace,
    ]


def register_workspaces_tools(mcp: FastMCP[Any]) -> WorkspacesService:
    """Register the workspaces tools with an MCP server."""
    service = WorkspacesService()
    for tool in create_workspaces_tools(service):
        mcp.tool(tool)
    return service
