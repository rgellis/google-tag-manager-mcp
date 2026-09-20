"""Entry point for the Google Tag Manager MCP server.

Two deliberate differences from the Google Ads MCP server this mirrors:

1. Tools are registered directly onto a single FastMCP instance rather than
   mounted as prefixed sub-servers. Prefixed mounts exist there to keep hundreds
   of same-named service tools apart; every tool name here is already unique, so
   that indirection would only turn `list_tags` into `tags_list_tags`.
2. Nothing happens at import time. Registration, credential loading and argument
   parsing all sit behind ``main()``, so the test suite can import this module
   and assert against the real server.

The API is large -- 106 methods, 112 tools -- so ``--groups`` matters more here
than on the smaller servers: an MCP client pays for every tool description in
its context on every request. Register the groups the task needs.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import threading
from types import FrameType
from typing import Any, Callable, Dict, List, Optional

from fastmcp import Context, FastMCP

from src.client import TagManagerClient, get_client, set_client
from src.services.accounts_service import register_accounts_tools
from src.services.built_in_variables_service import register_built_in_variables_tools
from src.services.clients_service import register_clients_tools
from src.services.containers_service import register_containers_tools
from src.services.destinations_service import register_destinations_tools
from src.services.environments_service import register_environments_tools
from src.services.folders_service import register_folders_tools
from src.services.gtag_config_service import register_gtag_config_tools
from src.services.insights_service import register_insights_tools
from src.services.tags_service import register_tags_tools
from src.services.templates_service import register_templates_tools
from src.services.transformations_service import register_transformations_tools
from src.services.triggers_service import register_triggers_tools
from src.services.user_permissions_service import register_user_permissions_tools
from src.services.variables_service import register_variables_tools
from src.services.versions_service import register_versions_tools
from src.services.workspaces_service import register_workspaces_tools
from src.services.zones_service import register_zones_tools
from src.utils import get_logger, load_dotenv

logger = get_logger(__name__)

mcp: FastMCP[Any] = FastMCP("Tag Manager MCP")

TOOL_GROUPS: Dict[str, Callable[[FastMCP[Any]], Any]] = {
    "accounts": register_accounts_tools,
    "user-permissions": register_user_permissions_tools,
    "containers": register_containers_tools,
    "destinations": register_destinations_tools,
    "environments": register_environments_tools,
    "versions": register_versions_tools,
    "workspaces": register_workspaces_tools,
    "tags": register_tags_tools,
    "triggers": register_triggers_tools,
    "variables": register_variables_tools,
    "built-in-variables": register_built_in_variables_tools,
    "folders": register_folders_tools,
    "templates": register_templates_tools,
    "clients": register_clients_tools,
    "transformations": register_transformations_tools,
    "zones": register_zones_tools,
    "gtag-config": register_gtag_config_tools,
    "insights": register_insights_tools,
}

#: A useful default for web containers: everything needed to read and edit a
#: container without the server-side and 360-only resources.
WEB_GROUPS: List[str] = [
    "accounts",
    "containers",
    "workspaces",
    "versions",
    "tags",
    "triggers",
    "variables",
    "built-in-variables",
    "folders",
    "insights",
]

shutdown_event = asyncio.Event()


@mcp.tool
async def check_client_status(ctx: Context) -> Dict[str, Any]:  # noqa: ARG001
    """Check that the Tag Manager client is configured and can authenticate.

    Returns:
        Whether credentials resolve, whether the server is in read-only mode,
        and the OAuth scopes in use.
    """
    try:
        client = get_client()
    except RuntimeError as e:
        return {"status": "not_initialized", "error": str(e)}

    try:
        _ = client.service
    except Exception as e:
        return {
            "status": "error",
            "readOnly": client.read_only,
            "scopes": client.scopes,
            "error": str(e),
        }

    return {"status": "ready", "readOnly": client.read_only, "scopes": client.scopes}


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Google Tag Manager MCP server")
    parser.add_argument(
        "--groups",
        default="all",
        help=(
            "Comma-separated tool groups to register, 'all', or 'web' for the "
            f"web-container subset. Available: {', '.join(TOOL_GROUPS)}"
        ),
    )
    return parser.parse_args(argv)


def resolve_groups(groups_arg: str = "all") -> List[str]:
    """Expand a --groups argument into a list of group names."""
    if groups_arg == "all":
        return list(TOOL_GROUPS)
    if groups_arg == "web":
        return list(WEB_GROUPS)
    return [group.strip() for group in groups_arg.split(",") if group.strip()]


def register_groups(groups_arg: str = "all") -> int:
    """Register the requested tool groups onto the server.

    Args:
        groups_arg: Comma-separated group names, "all", or "web".

    Returns:
        The number of groups successfully registered.
    """
    requested = resolve_groups(groups_arg)

    registered = 0
    for group in requested:
        register = TOOL_GROUPS.get(group)
        if register is None:
            logger.warning("Unknown tool group: %s", group)
            continue
        register(mcp)
        registered += 1

    logger.info("Registered tool groups: %s", ", ".join(requested))
    return registered


def signal_handler(signum: int, frame: Optional[FrameType]) -> None:  # noqa: ARG001
    """Handle shutdown signals gracefully."""
    logger.info("Received signal %s, shutting down...", signum)
    shutdown_event.set()

    def force_exit() -> None:
        logger.warning("Force exiting after timeout...")
        os._exit(0)

    threading.Timer(2.0, force_exit).start()


async def run_with_shutdown(group_count: int) -> None:
    """Run the MCP server over stdio with graceful shutdown support."""
    tools = await mcp.list_tools()
    logger.info("Registered %d tools from %d group(s)", len(tools), group_count)

    server_task = asyncio.create_task(mcp.run_async(transport="stdio"))
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    _, pending = await asyncio.wait(
        [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("Server stopped gracefully")


def main(argv: Optional[List[str]] = None) -> int:
    """Configure and run the server."""
    args = parse_arguments(argv)

    load_dotenv()
    set_client(TagManagerClient())
    group_count = register_groups(args.groups)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        asyncio.run(run_with_shutdown(group_count))
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt during startup")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
