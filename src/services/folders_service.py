"""Folders service -- the folders that organise a workspace's entities.

Covers ``accounts.containers.workspaces.folders`` in full: list, get, create,
update, delete, revert, entities, move_entities_to_folder.

Folders are organisational only: moving a tag into one changes nothing about
when it fires.
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
        Folder,
        FolderEntities,
        ListFoldersResponse,
        RevertFolderResponse,
    )

logger = get_logger(__name__)


def _folder_path(
    account_id: str, container_id: str, workspace_id: str, folder_id: str
) -> str:
    return workspace_child_path(
        account_id, container_id, workspace_id, "folders", folder_id, "folder_id"
    )


class FoldersService:
    """Manage the folders in a workspace."""

    def list_folders(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListFoldersResponse]:
        """List the folders in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().folders()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing folders in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
    ) -> Awaitable[Folder]:
        """Retrieve one folder.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
        """
        resource = get_client().service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        return execute(
            ctx,
            f"getting folder {path}",
            lambda: resource.get(path=path).execute(),
        )

    def get_folder_entities(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[FolderEntities]:
        """List the entities a folder contains.

        Despite being a read, this is a POST in the API; it is not a mutation.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        return execute(
            ctx,
            f"listing the entities in folder {path}",
            lambda: resource.entities(
                path=path, **optional(pageToken=page_token)
            ).execute(),
        )

    async def create_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder: Dict[str, Any],
    ) -> Folder:
        """Create a folder in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder: Folder resource, e.g. ``{"name": "GA4"}``.
        """
        client = get_client()
        client.require_write("create_folder")
        resource = client.service.accounts().containers().workspaces().folders()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a folder in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("Folder", folder)
            ).execute(),
        )
        logger.info("Created folder in %s", parent)
        return result

    async def update_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        folder: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Folder:
        """Update a folder.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            folder: Folder resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the folder.
        """
        client = get_client()
        client.require_write("update_folder")
        resource = client.service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        result = await execute(
            ctx,
            f"updating folder {path}",
            lambda: resource.update(
                path=path,
                body=cast("Folder", folder),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated folder %s", path)
        return result

    async def delete_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
    ) -> Dict[str, Any]:
        """Delete a folder from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_folder")
        resource = client.service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        await execute(
            ctx,
            f"deleting folder {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted folder %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertFolderResponse:
        """Discard a workspace's changes to one folder.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the folder.
        """
        client = get_client()
        client.require_write("revert_folder")
        resource = client.service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        result = await execute(
            ctx,
            f"reverting folder {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted folder %s", path)
        return result

    async def move_entities_to_folder(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        folder: Optional[Dict[str, Any]] = None,
        tag_ids: Optional[List[str]] = None,
        trigger_ids: Optional[List[str]] = None,
        variable_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Move tags, triggers and variables into a folder.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID, or ``0`` to move the entities out of
                whichever folder they are in.
            folder: Folder resource sent as the request body. The API requires
                one, so an empty object is sent when nothing is given.
            tag_ids: Numeric tag IDs to move.
            trigger_ids: Numeric trigger IDs to move.
            variable_ids: Numeric variable IDs to move.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("move_entities_to_folder")
        resource = client.service.accounts().containers().workspaces().folders()
        path = _folder_path(account_id, container_id, workspace_id, folder_id)
        body = cast("Folder", folder if folder is not None else {})
        await execute(
            ctx,
            f"moving entities into folder {path}",
            lambda: resource.move_entities_to_folder(
                path=path,
                body=body,
                **optional(
                    tagId=tag_ids, triggerId=trigger_ids, variableId=variable_ids
                ),
            ).execute(),
        )
        moved = {
            "tagId": list(tag_ids or []),
            "triggerId": list(trigger_ids or []),
            "variableId": list(variable_ids or []),
        }
        logger.info("Moved entities into folder %s", path)
        return {"path": path, "status": "moved", "moved": moved}


def create_folders_tools(
    service: FoldersService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a FoldersService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_folders(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the folders in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each folder's folderId, name and notes.
        """
        return cast(
            Dict[str, Any],
            await service.list_folders(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
    ) -> Dict[str, Any]:
        """Get one folder from a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.

        Returns:
            The folder's folderId, name, notes and fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_folder(
                ctx, account_id, container_id, workspace_id, folder_id
            ),
        )

    async def get_folder_entities(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the tags, triggers and variables inside a folder.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            page_token: Continuation token from a previous response.

        Returns:
            The folder's tag, trigger and variable lists.
        """
        return cast(
            Dict[str, Any],
            await service.get_folder_entities(
                ctx, account_id, container_id, workspace_id, folder_id, page_token
            ),
        )

    async def create_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a folder in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder: Folder resource. Requires name, e.g.
                {"name": "GA4", "notes": "Everything GA4-related"}.

        Returns:
            The created folder, including its new folderId.
        """
        return cast(
            Dict[str, Any],
            await service.create_folder(
                ctx, account_id, container_id, workspace_id, folder
            ),
        )

    async def update_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        folder: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a folder's name or notes.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            folder: Folder resource with the fields to set.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the folder changed in the meantime.

        Returns:
            The updated folder.
        """
        return cast(
            Dict[str, Any],
            await service.update_folder(
                ctx,
                account_id,
                container_id,
                workspace_id,
                folder_id,
                folder,
                fingerprint,
            ),
        )

    async def delete_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
    ) -> Dict[str, Any]:
        """Delete a folder from a workspace.

        The entities inside it are not deleted; they are left unfiled.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_folder(
            ctx, account_id, container_id, workspace_id, folder_id
        )

    async def revert_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one folder.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored folder, or an empty object if it did not exist in the
            base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_folder(
                ctx, account_id, container_id, workspace_id, folder_id, fingerprint
            ),
        )

    async def move_entities_to_folder(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        folder_id: str,
        folder: Optional[Dict[str, Any]] = None,
        tag_ids: Optional[List[str]] = None,
        trigger_ids: Optional[List[str]] = None,
        variable_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Move tags, triggers and variables into a folder.

        Pass folder_id "0" to take the entities out of their current folder
        instead of putting them into one.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            folder_id: Numeric folder ID, or "0" to unfile the entities.
            folder: Optional Folder body. The API requires a body but uses none
                of it, so leaving this unset sends an empty object.
            tag_ids: Numeric tag IDs to move.
            trigger_ids: Numeric trigger IDs to move.
            variable_ids: Numeric variable IDs to move.

        Returns:
            Confirmation listing what was moved.
        """
        return await service.move_entities_to_folder(
            ctx,
            account_id,
            container_id,
            workspace_id,
            folder_id,
            folder,
            tag_ids,
            trigger_ids,
            variable_ids,
        )

    return [
        list_folders,
        get_folder,
        get_folder_entities,
        create_folder,
        update_folder,
        delete_folder,
        revert_folder,
        move_entities_to_folder,
    ]


def register_folders_tools(mcp: FastMCP[Any]) -> FoldersService:
    """Register the folders tools with an MCP server."""
    service = FoldersService()
    for tool in create_folders_tools(service):
        mcp.tool(tool)
    return service
