"""Templates service -- custom tag and variable templates.

Covers ``accounts.containers.workspaces.templates`` in full: list, get, create,
update, delete, revert, import_from_gallery.

A custom template defines a new tag or variable type in the container's own
sandboxed JavaScript, so it is the one workspace entity whose body is code
rather than configuration.
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
        CustomTemplate,
        ListTemplatesResponse,
        RevertTemplateResponse,
    )

logger = get_logger(__name__)


def _template_path(
    account_id: str, container_id: str, workspace_id: str, template_id: str
) -> str:
    return workspace_child_path(
        account_id, container_id, workspace_id, "templates", template_id, "template_id"
    )


class TemplatesService:
    """Manage the custom templates in a workspace."""

    def list_templates(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Awaitable[ListTemplatesResponse]:
        """List the custom templates in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.
        """
        resource = get_client().service.accounts().containers().workspaces().templates()
        parent = workspace_path(account_id, container_id, workspace_id)
        return execute(
            ctx,
            f"listing templates in {parent}",
            lambda: resource.list(
                parent=parent, **optional(pageToken=page_token)
            ).execute(),
        )

    def get_template(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
    ) -> Awaitable[CustomTemplate]:
        """Retrieve one custom template, including its source.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.
        """
        resource = get_client().service.accounts().containers().workspaces().templates()
        path = _template_path(account_id, container_id, workspace_id, template_id)
        return execute(
            ctx,
            f"getting template {path}",
            lambda: resource.get(path=path).execute(),
        )

    async def create_template(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template: Dict[str, Any],
    ) -> CustomTemplate:
        """Create a custom template in a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template: CustomTemplate resource, carrying the template source in
                ``templateData``.
        """
        client = get_client()
        client.require_write("create_template")
        resource = client.service.accounts().containers().workspaces().templates()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"creating a template in {parent}",
            lambda: resource.create(
                parent=parent, body=cast("CustomTemplate", template)
            ).execute(),
        )
        logger.info("Created template in %s", parent)
        return result

    async def update_template(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
        template: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> CustomTemplate:
        """Update a custom template.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.
            template: CustomTemplate resource replacing the stored one.
            fingerprint: When given, the update is rejected unless it matches
                the fingerprint currently stored for the template.
        """
        client = get_client()
        client.require_write("update_template")
        resource = client.service.accounts().containers().workspaces().templates()
        path = _template_path(account_id, container_id, workspace_id, template_id)
        result = await execute(
            ctx,
            f"updating template {path}",
            lambda: resource.update(
                path=path,
                body=cast("CustomTemplate", template),
                **optional(fingerprint=fingerprint),
            ).execute(),
        )
        logger.info("Updated template %s", path)
        return result

    async def delete_template(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
    ) -> Dict[str, Any]:
        """Delete a custom template from a workspace.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.

        Returns:
            A confirmation dict -- the API itself returns an empty body.
        """
        client = get_client()
        client.require_write("delete_template")
        resource = client.service.accounts().containers().workspaces().templates()
        path = _template_path(account_id, container_id, workspace_id, template_id)
        await execute(
            ctx,
            f"deleting template {path}",
            lambda: resource.delete(path=path).execute(),
        )
        logger.info("Deleted template %s", path)
        return {"path": path, "status": "deleted"}

    async def revert_template(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
        fingerprint: Optional[str] = None,
    ) -> RevertTemplateResponse:
        """Discard a workspace's changes to one custom template.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.
            fingerprint: When given, must match the fingerprint currently
                stored for the template.
        """
        client = get_client()
        client.require_write("revert_template")
        resource = client.service.accounts().containers().workspaces().templates()
        path = _template_path(account_id, container_id, workspace_id, template_id)
        result = await execute(
            ctx,
            f"reverting template {path}",
            lambda: resource.revert(
                path=path, **optional(fingerprint=fingerprint)
            ).execute(),
        )
        logger.info("Reverted template %s", path)
        return result

    async def import_template_from_gallery(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gallery_owner: Optional[str] = None,
        gallery_repository: Optional[str] = None,
        gallery_sha: Optional[str] = None,
        acknowledge_permissions: Optional[bool] = None,
    ) -> CustomTemplate:
        """Import a template from the Community Template Gallery.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gallery_owner: GitHub owner of the gallery template.
            gallery_repository: GitHub repository of the gallery template.
            gallery_sha: Commit SHA to import; defaults to the latest.
            acknowledge_permissions: Must be true, acknowledging the
                permissions the template requests, or the import fails.
        """
        client = get_client()
        client.require_write("import_template_from_gallery")
        resource = client.service.accounts().containers().workspaces().templates()
        parent = workspace_path(account_id, container_id, workspace_id)
        result = await execute(
            ctx,
            f"importing gallery template {gallery_owner}/{gallery_repository} "
            f"into {parent}",
            lambda: resource.import_from_gallery(
                parent=parent,
                **optional(
                    galleryOwner=gallery_owner,
                    galleryRepository=gallery_repository,
                    gallerySha=gallery_sha,
                    acknowledgePermissions=acknowledge_permissions,
                ),
            ).execute(),
        )
        logger.info("Imported a gallery template into %s", parent)
        return result


def create_templates_tools(
    service: TemplatesService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by a TemplatesService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_templates(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List the custom templates in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            page_token: Continuation token from a previous response.

        Returns:
            Each template's templateId, name, galleryReference when it came
            from the gallery, and templateData source.
        """
        return cast(
            Dict[str, Any],
            await service.list_templates(
                ctx, account_id, container_id, workspace_id, page_token
            ),
        )

    async def get_template(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
    ) -> Dict[str, Any]:
        """Get one custom template, including its sandboxed JavaScript source.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.

        Returns:
            The template's templateData source, galleryReference and
            fingerprint.
        """
        return cast(
            Dict[str, Any],
            await service.get_template(
                ctx, account_id, container_id, workspace_id, template_id
            ),
        )

    async def create_template(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a custom template in a workspace.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template: CustomTemplate resource, e.g.
                {"name": "My pixel", "templateData": "___INFO___\\n..."}.
                templateData is the full template definition in Tag Manager's
                sandboxed JavaScript format, including its ___INFO___,
                ___TEMPLATE_PARAMETERS___ and ___SANDBOXED_JS_FOR_WEB_TEMPLATE___
                sections.

        Returns:
            The created template, including its new templateId.
        """
        return cast(
            Dict[str, Any],
            await service.create_template(
                ctx, account_id, container_id, workspace_id, template
            ),
        )

    async def update_template(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
        template: Dict[str, Any],
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a custom template in a workspace.

        The template you send replaces the stored one, so read it with
        get_template first and send the whole thing back with your edits
        applied.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.
            template: Complete CustomTemplate resource.
            fingerprint: Fingerprint from a previous read. When given, the
                update fails if the template changed in the meantime.

        Returns:
            The updated template.
        """
        return cast(
            Dict[str, Any],
            await service.update_template(
                ctx,
                account_id,
                container_id,
                workspace_id,
                template_id,
                template,
                fingerprint,
            ),
        )

    async def delete_template(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
    ) -> Dict[str, Any]:
        """Delete a custom template from a workspace.

        Tags and variables using the template stop working, so check for uses
        before deleting.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.

        Returns:
            Confirmation of the deletion.
        """
        return await service.delete_template(
            ctx, account_id, container_id, workspace_id, template_id
        )

    async def revert_template(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        template_id: str,
        fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Undo a workspace's changes to one custom template.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            template_id: Numeric template ID.
            fingerprint: Fingerprint from a previous read.

        Returns:
            The restored template, or an empty object if it did not exist in
            the base version.
        """
        return cast(
            Dict[str, Any],
            await service.revert_template(
                ctx, account_id, container_id, workspace_id, template_id, fingerprint
            ),
        )

    async def import_template_from_gallery(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        gallery_owner: Optional[str] = None,
        gallery_repository: Optional[str] = None,
        gallery_sha: Optional[str] = None,
        acknowledge_permissions: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Import a template from the Community Template Gallery.

        Gallery templates are third-party code that runs on the site, and the
        import declares the permissions the template asks for --
        acknowledge_permissions must be true or the call fails. Review what it
        requests before importing.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            gallery_owner: GitHub owner, e.g. "gtm-templates-simo-ahava".
            gallery_repository: GitHub repository name.
            gallery_sha: Commit SHA to import; defaults to the latest.
            acknowledge_permissions: Must be true to accept the template's
                requested permissions.

        Returns:
            The imported template, including its galleryReference.
        """
        return cast(
            Dict[str, Any],
            await service.import_template_from_gallery(
                ctx,
                account_id,
                container_id,
                workspace_id,
                gallery_owner,
                gallery_repository,
                gallery_sha,
                acknowledge_permissions,
            ),
        )

    return [
        list_templates,
        get_template,
        create_template,
        update_template,
        delete_template,
        revert_template,
        import_template_from_gallery,
    ]


def register_templates_tools(mcp: FastMCP[Any]) -> TemplatesService:
    """Register the templates tools with an MCP server."""
    service = TemplatesService()
    for tool in create_templates_tools(service):
        mcp.tool(tool)
    return service
