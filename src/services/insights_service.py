"""Task-shaped tools composed from several API calls.

Nothing here maps one-to-one onto an API method. Each tool exists because the
raw API makes a common Tag Manager task take several round trips that an agent
has to sequence correctly, and getting the sequence wrong is expensive -- the
release flow in particular ends in a publish to a live site.

Everything in this module is declared in ``src/coverage.py`` under
``CONVENIENCE_TOOLS``, and the coverage test fails if a tool appears here
without being declared there.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from fastmcp import Context, FastMCP

from src.services.accounts_service import AccountsService
from src.services.containers_service import ContainersService
from src.services.folders_service import FoldersService
from src.services.tags_service import TagsService
from src.services.triggers_service import TriggersService
from src.services.variables_service import VariablesService
from src.services.versions_service import VersionsService
from src.services.workspaces_service import WorkspacesService
from src.utils import get_logger

logger = get_logger(__name__)

#: Response key holding the rows for each collection these tools read.
ENTITY_KEYS: Dict[str, str] = {
    "tags": "tag",
    "triggers": "trigger",
    "variables": "variable",
    "folders": "folder",
}

#: Entity collections find_entities_by_name searches, and the ID field on each.
SEARCHABLE: Dict[str, str] = {
    "tags": "tagId",
    "triggers": "triggerId",
    "variables": "variableId",
}


class InsightsService:
    """Multi-call workflows over the Tag Manager API."""

    def __init__(self) -> None:
        self.accounts = AccountsService()
        self.containers = ContainersService()
        self.workspaces = WorkspacesService()
        self.versions = VersionsService()
        self.tags = TagsService()
        self.triggers = TriggersService()
        self.variables = VariablesService()
        self.folders = FoldersService()

    async def _collect(
        self,
        fetch: Callable[[Optional[str]], Awaitable[Any]],
        key: str,
        max_pages: int = 50,
    ) -> List[Dict[str, Any]]:
        """Page through a list method and return every row.

        Args:
            fetch: Callable taking a page token and returning one page.
            key: Response field holding the rows, e.g. ``"tag"``.
            max_pages: Stop after this many pages. A guard against an API that
                keeps returning a token, not a limit anyone should need to
                raise.

        Returns:
            Every row across all pages.
        """
        rows: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        for _ in range(max_pages):
            page = cast(Dict[str, Any], await fetch(page_token))
            rows.extend(cast(List[Dict[str, Any]], page.get(key) or []))
            page_token = cast(Optional[str], page.get("nextPageToken"))
            if not page_token:
                break

        return rows

    async def _workspace_collections(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Read a workspace's tags, triggers, variables and folders in full."""
        return {
            "tags": await self._collect(
                lambda token: self.tags.list_tags(
                    ctx, account_id, container_id, workspace_id, token
                ),
                ENTITY_KEYS["tags"],
            ),
            "triggers": await self._collect(
                lambda token: self.triggers.list_triggers(
                    ctx, account_id, container_id, workspace_id, token
                ),
                ENTITY_KEYS["triggers"],
            ),
            "variables": await self._collect(
                lambda token: self.variables.list_variables(
                    ctx, account_id, container_id, workspace_id, token
                ),
                ENTITY_KEYS["variables"],
            ),
            "folders": await self._collect(
                lambda token: self.folders.list_folders(
                    ctx, account_id, container_id, workspace_id, token
                ),
                ENTITY_KEYS["folders"],
            ),
        }

    async def list_workspace_entities(
        self, ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Read a workspace's tags, triggers, variables and folders at once.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            Each collection in full, with a count of each.
        """
        collections = await self._workspace_collections(
            ctx, account_id, container_id, workspace_id
        )
        counts = {name: len(rows) for name, rows in collections.items()}
        logger.info("Read workspace entities: %s", counts)
        return {
            "accountId": account_id,
            "containerId": container_id,
            "workspaceId": workspace_id,
            "counts": counts,
            **collections,
        }

    async def find_entities_by_name(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """Find tags, triggers and variables whose name contains a string.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            query: Case-insensitive substring to match against entity names.

        Returns:
            The matching entities per collection, with a total count.
        """
        if not query.strip():
            raise ValueError("query must not be empty")

        needle = query.strip().lower()
        collections = await self._workspace_collections(
            ctx, account_id, container_id, workspace_id
        )

        matches: Dict[str, List[Dict[str, Any]]] = {}
        for collection, id_field in SEARCHABLE.items():
            matches[collection] = [
                {
                    "id": row.get(id_field),
                    "name": row.get("name"),
                    "type": row.get("type"),
                    "path": row.get("path"),
                }
                for row in collections[collection]
                if needle in str(row.get("name", "")).lower()
            ]

        total = sum(len(rows) for rows in matches.values())
        logger.info("Found %d entities matching %r", total, query)
        return {"query": query, "total": total, **matches}

    async def summarize_container(
        self, ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Describe a container: its settings, workspaces and published state.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The container, its workspaces, and a summary of the live version.
            ``live`` is None when nothing has been published, which the API
            reports as an error rather than an empty result.
        """
        container = cast(
            Dict[str, Any],
            await self.containers.get_container(ctx, account_id, container_id),
        )
        workspaces = await self._collect(
            lambda token: self.workspaces.list_workspaces(
                ctx, account_id, container_id, token
            ),
            "workspace",
        )

        live: Optional[Dict[str, Any]]
        try:
            version = cast(
                Dict[str, Any],
                await self.versions.get_live_version(ctx, account_id, container_id),
            )
            live = {
                "containerVersionId": version.get("containerVersionId"),
                "name": version.get("name"),
                "counts": {
                    "tags": len(cast(List[Any], version.get("tag") or [])),
                    "triggers": len(cast(List[Any], version.get("trigger") or [])),
                    "variables": len(cast(List[Any], version.get("variable") or [])),
                    "builtInVariables": len(
                        cast(List[Any], version.get("builtInVariable") or [])
                    ),
                },
            }
        except Exception as e:
            # A container that has never been published has no live version,
            # and the API says so with an error. That is a fact about the
            # container, not a failure of this tool.
            logger.info("No live version for container %s: %s", container_id, e)
            live = None

        return {
            "container": container,
            "workspaces": [
                {
                    "workspaceId": workspace.get("workspaceId"),
                    "name": workspace.get("name"),
                    "description": workspace.get("description"),
                }
                for workspace in workspaces
            ],
            "workspaceCount": len(workspaces),
            "live": live,
        }

    async def list_all_containers(
        self, ctx: Context, include_google_tags: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List every container this user can reach, across every account.

        Args:
            ctx: FastMCP context.
            include_google_tags: Also include Google tag-only accounts.

        Returns:
            One entry per account with its containers. An account whose
            containers cannot be listed is reported with an error rather than
            failing the whole call.
        """
        accounts = await self._collect(
            lambda token: self.accounts.list_accounts(ctx, token, include_google_tags),
            "account",
        )

        results: List[Dict[str, Any]] = []
        total = 0
        for account in accounts:
            account_id = str(account.get("accountId", ""))
            entry: Dict[str, Any] = {
                "accountId": account_id,
                "name": account.get("name"),
            }
            try:
                containers = await self._collect(
                    lambda token, aid=account_id: self.containers.list_containers(
                        ctx, aid, token
                    ),
                    "container",
                )
            except Exception as e:
                entry["error"] = str(e)
                entry["containers"] = []
            else:
                entry["containers"] = [
                    {
                        "containerId": container.get("containerId"),
                        "publicId": container.get("publicId"),
                        "name": container.get("name"),
                        "usageContext": container.get("usageContext"),
                    }
                    for container in containers
                ]
                total += len(containers)
            results.append(entry)

        logger.info("Listed %d containers across %d accounts", total, len(results))
        return {
            "accountCount": len(results),
            "containerCount": total,
            "accounts": results,
        }

    async def publish_workspace(
        self,
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        publish: bool = False,
    ) -> Dict[str, Any]:
        """Turn a workspace into a version and, if asked, publish it.

        Args:
            ctx: FastMCP context.
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            name: Name for the new version.
            notes: Notes for the new version.
            publish: Publish the version to production once created. Defaults
                to False so that creating a version is not silently a release.

        Returns:
            The created version, whether it was published, and any compiler
            error. A compiler error stops the publish.
        """
        version_options: Dict[str, Any] = {}
        if name is not None:
            version_options["name"] = name
        if notes is not None:
            version_options["notes"] = notes

        created = cast(
            Dict[str, Any],
            await self.workspaces.create_version(
                ctx, account_id, container_id, workspace_id, version_options
            ),
        )

        compiler_error = created.get("compilerError")
        version = cast(Dict[str, Any], created.get("containerVersion") or {})
        version_id = version.get("containerVersionId")

        result: Dict[str, Any] = {
            "containerVersion": version,
            "compilerError": compiler_error,
            "newWorkspacePath": created.get("newWorkspacePath"),
            "published": False,
        }

        if not publish:
            result["skippedPublishReason"] = (
                "publish was not requested; call publish_version, or this tool "
                "again with publish=true, to release it"
            )
            return result

        if compiler_error:
            result["skippedPublishReason"] = (
                "the version failed to compile, so it was not published"
            )
            return result

        if not version_id:
            result["skippedPublishReason"] = (
                "the API returned no containerVersionId, so there was nothing "
                "to publish"
            )
            return result

        published = cast(
            Dict[str, Any],
            await self.versions.publish_version(
                ctx, account_id, container_id, str(version_id)
            ),
        )
        result["published"] = True
        result["publishResult"] = published
        logger.info("Published version %s of container %s", version_id, container_id)
        return result


def create_insights_tools(
    service: InsightsService,
) -> List[Callable[..., Awaitable[Any]]]:
    """Build the MCP tool functions backed by an InsightsService instance."""
    # FastMCP resolves tool annotations at runtime; see accounts_service.py.

    async def list_workspace_entities(
        ctx: Context, account_id: str, container_id: str, workspace_id: str
    ) -> Dict[str, Any]:
        """Read everything configured in a workspace in one call.

        Fetches tags, triggers, variables and folders, following pagination on
        each. Prefer this over four separate list calls when you want to
        understand or audit a container's setup.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.

        Returns:
            The full tags, triggers, variables and folders lists, plus counts.
        """
        return await service.list_workspace_entities(
            ctx, account_id, container_id, workspace_id
        )

    async def find_entities_by_name(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        query: str,
    ) -> Dict[str, Any]:
        """Find tags, triggers and variables by name.

        The API has no search, so this reads each collection and filters. Use
        it to turn a name a human used ("the purchase tag") into the ID the
        other tools need.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            query: Case-insensitive substring to match against names.

        Returns:
            Matching tags, triggers and variables as id/name/type/path, and a
            total count.
        """
        return await service.find_entities_by_name(
            ctx, account_id, container_id, workspace_id, query
        )

    async def summarize_container(
        ctx: Context, account_id: str, container_id: str
    ) -> Dict[str, Any]:
        """Summarise a container: settings, workspaces and what is live.

        The quickest answer to "what is this container and what is it running".

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.

        Returns:
            The container, its workspaces, and the live version with entity
            counts. live is null when the container has never been published.
        """
        return await service.summarize_container(ctx, account_id, container_id)

    async def list_all_containers(
        ctx: Context, include_google_tags: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List every container this user can reach, across every account.

        Answers "what do I have access to" in one call instead of one
        list_containers per account. An account that cannot be read is reported
        with its error rather than failing the whole call.

        Args:
            include_google_tags: Also include Google tag-only accounts.

        Returns:
            Accounts with their containers, plus account and container counts.
        """
        return await service.list_all_containers(ctx, include_google_tags)

    async def publish_workspace(
        ctx: Context,
        account_id: str,
        container_id: str,
        workspace_id: str,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        publish: bool = False,
    ) -> Dict[str, Any]:
        """Create a container version from a workspace, optionally publishing it.

        This is the Tag Manager release flow: a workspace becomes a version,
        and a version is published. Creating the version consumes the
        workspace either way.

        publish defaults to false. Passing true releases to the live site
        immediately, for every visitor -- confirm that is intended before
        setting it. A version that fails to compile is never published.

        Args:
            account_id: Numeric Tag Manager account ID.
            container_id: Numeric container ID.
            workspace_id: Numeric workspace ID.
            name: Name for the new version, e.g. "Release 2026-09-20".
            notes: Notes describing what changed.
            publish: Publish the version to production once created.

        Returns:
            The created containerVersion, any compilerError, whether it was
            published, and skippedPublishReason when it was not.
        """
        return await service.publish_workspace(
            ctx, account_id, container_id, workspace_id, name, notes, publish
        )

    return [
        list_workspace_entities,
        find_entities_by_name,
        summarize_container,
        list_all_containers,
        publish_workspace,
    ]


def register_insights_tools(mcp: FastMCP[Any]) -> InsightsService:
    """Register the task-shaped tools with an MCP server."""
    service = InsightsService()
    for tool in create_insights_tools(service):
        mcp.tool(tool)
    return service
