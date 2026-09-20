"""End-to-end tests that invoke every registered tool through an MCP client.

The per-service tests exercise the service layer directly. These go through the
real FastMCP tool surface instead -- argument coercion, Context injection and
result serialisation included -- which is what an MCP client actually touches.

`test_every_registered_tool_is_exercised` holds the whole thing together: it
fails if a tool is registered without a call in CALLS below, so a new tool
cannot be added without an end-to-end test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Tuple
from unittest.mock import Mock

import pytest
import pytest_asyncio
from fastmcp import Client

import main
from tests.conftest import ACCOUNT_ID, CONTAINER_ID, ENTITY_ID, WORKSPACE_ID

DISCOVERY_PATH = (
    Path(__file__).resolve().parent.parent / "refs" / "tagmanager.v2.discovery.json"
)

#: Stand-in response for every endpoint whose shape no tool reads. Every Tag
#: Manager entity carries a fingerprint, so this is a shape the API really
#: returns -- and unlike {} it serialises to a non-empty structured result,
#: which keeps the end-to-end assertions meaningful.
DEFAULT_RESPONSE: Dict[str, Any] = {"fingerprint": "fp-stub"}

#: Responses for the endpoints whose shape a tool actually reads.
SPECIFIC_RESPONSES: Dict[str, Dict[str, Any]] = {
    "accounts.list": {"account": [{"accountId": ACCOUNT_ID, "name": "Acme"}]},
    "accounts.containers.list": {
        "container": [
            {"containerId": CONTAINER_ID, "publicId": "GTM-ABC123", "name": "web"}
        ]
    },
    "accounts.containers.get": {
        "containerId": CONTAINER_ID,
        "name": "web",
        "publicId": "GTM-ABC123",
    },
    "accounts.containers.snippet": {"snippet": "<script>...</script>"},
    "accounts.containers.versions.live": {
        "containerVersionId": "8",
        "name": "Release",
        "tag": [{}],
    },
    "accounts.containers.workspaces.list": {
        "workspace": [{"workspaceId": WORKSPACE_ID, "name": "Default Workspace"}]
    },
    "accounts.containers.workspaces.create_version": {
        "containerVersion": {"containerVersionId": "9"}
    },
    "accounts.containers.workspaces.tags.list": {
        "tag": [{"tagId": "1", "name": "GA4 - purchase", "type": "gaawe"}]
    },
    "accounts.containers.workspaces.triggers.list": {
        "trigger": [{"triggerId": "2", "name": "All Pages", "type": "pageview"}]
    },
    "accounts.containers.workspaces.variables.list": {
        "variable": [{"variableId": "3", "name": "DL - id", "type": "v"}]
    },
    "accounts.containers.workspaces.folders.list": {
        "folder": [{"folderId": "4", "name": "GA4"}]
    },
}

#: Every tool, with arguments that reach it. Keep in step with the registered
#: surface -- test_every_registered_tool_is_exercised enforces that.
A: Dict[str, Any] = {"account_id": ACCOUNT_ID}
AC: Dict[str, Any] = {**A, "container_id": CONTAINER_ID}
ACW: Dict[str, Any] = {**AC, "workspace_id": WORKSPACE_ID}

CALLS: List[Tuple[str, Dict[str, Any]]] = [
    # diagnostics
    ("check_client_status", {}),
    # accounts
    ("list_accounts", {}),
    ("get_account", A),
    ("update_account", {**A, "account": {"name": "Acme"}}),
    # user permissions
    ("list_user_permissions", A),
    ("get_user_permission", {**A, "permission_id": "88"}),
    ("create_user_permission", {**A, "user_permission": {"emailAddress": "a@b.com"}}),
    (
        "update_user_permission",
        {**A, "permission_id": "88", "user_permission": {"emailAddress": "a@b.com"}},
    ),
    ("delete_user_permission", {**A, "permission_id": "88"}),
    # containers
    ("list_containers", A),
    ("get_container", AC),
    ("lookup_container", {"tag_id": "GTM-ABC123"}),
    ("get_container_snippet", AC),
    ("create_container", {**A, "container": {"name": "web", "usageContext": ["web"]}}),
    ("update_container", {**AC, "container": {"name": "web"}}),
    ("delete_container", AC),
    ("combine_containers", {**AC, "other_container_id": "999"}),
    ("move_tag_id", {**AC, "tag_id": "GTM-ABC123"}),
    # destinations
    ("list_destinations", AC),
    ("get_destination", {**AC, "destination_id": "AW-1"}),
    ("link_destination", {**AC, "destination_id": "AW-1"}),
    # environments
    ("list_environments", AC),
    ("get_environment", {**AC, "environment_id": "5"}),
    ("create_environment", {**AC, "environment": {"name": "Staging"}}),
    ("update_environment", {**AC, "environment_id": "5", "environment": {"name": "S"}}),
    ("delete_environment", {**AC, "environment_id": "5"}),
    ("reauthorize_environment", {**AC, "environment_id": "5"}),
    # versions
    ("list_version_headers", AC),
    ("get_latest_version_header", AC),
    ("get_version", {**AC, "version_id": "9"}),
    ("get_live_version", AC),
    (
        "update_version",
        {**AC, "version_id": "9", "container_version": {"name": "Release"}},
    ),
    ("delete_version", {**AC, "version_id": "9"}),
    ("undelete_version", {**AC, "version_id": "9"}),
    ("publish_version", {**AC, "version_id": "9"}),
    ("set_latest_version", {**AC, "version_id": "9"}),
    # workspaces
    ("list_workspaces", AC),
    ("get_workspace", ACW),
    ("get_workspace_status", ACW),
    ("create_workspace", {**AC, "workspace": {"name": "Consent mode"}}),
    ("update_workspace", {**ACW, "workspace": {"name": "W"}}),
    ("delete_workspace", ACW),
    ("sync_workspace", ACW),
    ("resolve_workspace_conflict", {**ACW, "entity": {"tag": {"tagId": "1"}}}),
    ("quick_preview_workspace", ACW),
    ("create_version", ACW),
    ("bulk_update_workspace", {**ACW, "proposed_change": {"change": []}}),
    # built-in variables
    ("list_built_in_variables", ACW),
    ("create_built_in_variable", {**ACW, "types": ["pageUrl"]}),
    ("delete_built_in_variable", {**ACW, "types": ["pageUrl"]}),
    ("revert_built_in_variable", {**ACW, "variable_type": "pageUrl"}),
    # tags
    ("list_tags", ACW),
    ("get_tag", {**ACW, "tag_id": ENTITY_ID}),
    ("create_tag", {**ACW, "tag": {"name": "GA4", "type": "gaawe"}}),
    ("update_tag", {**ACW, "tag_id": ENTITY_ID, "tag": {"name": "GA4"}}),
    ("delete_tag", {**ACW, "tag_id": ENTITY_ID}),
    ("revert_tag", {**ACW, "tag_id": ENTITY_ID}),
    # triggers
    ("list_triggers", ACW),
    ("get_trigger", {**ACW, "trigger_id": ENTITY_ID}),
    ("create_trigger", {**ACW, "trigger": {"name": "All Pages", "type": "pageview"}}),
    ("update_trigger", {**ACW, "trigger_id": ENTITY_ID, "trigger": {"name": "t"}}),
    ("delete_trigger", {**ACW, "trigger_id": ENTITY_ID}),
    ("revert_trigger", {**ACW, "trigger_id": ENTITY_ID}),
    # variables
    ("list_variables", ACW),
    ("get_variable", {**ACW, "variable_id": ENTITY_ID}),
    ("create_variable", {**ACW, "variable": {"name": "DL - id", "type": "v"}}),
    ("update_variable", {**ACW, "variable_id": ENTITY_ID, "variable": {"name": "v"}}),
    ("delete_variable", {**ACW, "variable_id": ENTITY_ID}),
    ("revert_variable", {**ACW, "variable_id": ENTITY_ID}),
    # folders
    ("list_folders", ACW),
    ("get_folder", {**ACW, "folder_id": ENTITY_ID}),
    ("get_folder_entities", {**ACW, "folder_id": ENTITY_ID}),
    ("create_folder", {**ACW, "folder": {"name": "GA4"}}),
    ("update_folder", {**ACW, "folder_id": ENTITY_ID, "folder": {"name": "GA4"}}),
    ("delete_folder", {**ACW, "folder_id": ENTITY_ID}),
    ("revert_folder", {**ACW, "folder_id": ENTITY_ID}),
    ("move_entities_to_folder", {**ACW, "folder_id": ENTITY_ID, "tag_ids": ["1"]}),
    # templates
    ("list_templates", ACW),
    ("get_template", {**ACW, "template_id": ENTITY_ID}),
    ("create_template", {**ACW, "template": {"name": "My pixel"}}),
    ("update_template", {**ACW, "template_id": ENTITY_ID, "template": {"name": "t"}}),
    ("delete_template", {**ACW, "template_id": ENTITY_ID}),
    ("revert_template", {**ACW, "template_id": ENTITY_ID}),
    (
        "import_template_from_gallery",
        {**ACW, "gallery_owner": "owner", "gallery_repository": "repo"},
    ),
    # clients
    ("list_clients", ACW),
    ("get_client", {**ACW, "client_id": ENTITY_ID}),
    ("create_client", {**ACW, "client": {"name": "GA4 client", "type": "gaaw_client"}}),
    ("update_client", {**ACW, "client_id": ENTITY_ID, "client": {"name": "c"}}),
    ("delete_client", {**ACW, "client_id": ENTITY_ID}),
    ("revert_client", {**ACW, "client_id": ENTITY_ID}),
    # transformations
    ("list_transformations", ACW),
    ("get_transformation", {**ACW, "transformation_id": ENTITY_ID}),
    ("create_transformation", {**ACW, "transformation": {"name": "Redact"}}),
    (
        "update_transformation",
        {**ACW, "transformation_id": ENTITY_ID, "transformation": {"name": "t"}},
    ),
    ("delete_transformation", {**ACW, "transformation_id": ENTITY_ID}),
    ("revert_transformation", {**ACW, "transformation_id": ENTITY_ID}),
    # zones
    ("list_zones", ACW),
    ("get_zone", {**ACW, "zone_id": ENTITY_ID}),
    ("create_zone", {**ACW, "zone": {"name": "Marketing"}}),
    ("update_zone", {**ACW, "zone_id": ENTITY_ID, "zone": {"name": "z"}}),
    ("delete_zone", {**ACW, "zone_id": ENTITY_ID}),
    ("revert_zone", {**ACW, "zone_id": ENTITY_ID}),
    # google tag config
    ("list_gtag_configs", ACW),
    ("get_gtag_config", {**ACW, "gtag_config_id": ENTITY_ID}),
    ("create_gtag_config", {**ACW, "gtag_config": {"type": "googtag"}}),
    (
        "update_gtag_config",
        {**ACW, "gtag_config_id": ENTITY_ID, "gtag_config": {"type": "googtag"}},
    ),
    ("delete_gtag_config", {**ACW, "gtag_config_id": ENTITY_ID}),
    # task-shaped tools
    ("list_workspace_entities", ACW),
    ("find_entities_by_name", {**ACW, "query": "purchase"}),
    ("summarize_container", AC),
    ("list_all_containers", {}),
    ("publish_workspace", {**ACW, "name": "Release"}),
]

CALL_IDS = [name for name, _ in CALLS]


def stub_every_endpoint(mock_api: Mock) -> Mock:
    """Give every method in the discovery document a serialisable response.

    Driven by the vendored document rather than a hand-written list, so a
    method added upstream is stubbed here as soon as it is implemented.
    """
    document: Dict[str, Any] = json.loads(DISCOVERY_PATH.read_text())

    def walk(resources: Dict[str, Any], accessor: Any, prefix: str) -> None:
        for name, resource in resources.items():
            child = getattr(accessor, name).return_value
            path = f"{prefix}{name}"
            for method in resource.get("methods") or {}:
                response = SPECIFIC_RESPONSES.get(f"{path}.{method}", DEFAULT_RESPONSE)
                getattr(child, method).return_value.execute.return_value = response
            walk(resource.get("resources") or {}, child, f"{path}.")

    walk(document.get("resources") or {}, mock_api, "")
    return mock_api


@pytest.fixture
def api(mock_api: Mock) -> Mock:
    return stub_every_endpoint(mock_api)


@pytest_asyncio.fixture
async def client(api: Mock, install_client: Mock) -> AsyncIterator[Client[Any]]:
    """An in-memory MCP client connected to the fully registered server."""
    main.register_groups("all")
    async with Client(main.mcp) as connected:
        yield connected


@pytest.mark.parametrize(("name", "args"), CALLS, ids=CALL_IDS)
@pytest.mark.asyncio
async def test_tool_returns_a_result(
    client: Client[Any], name: str, args: Dict[str, Any]
) -> None:
    result = await client.call_tool(name, args)
    # The point is that the call round-tripped: arguments coerced, the service
    # ran, and the result serialised. What comes back is asserted per tool in
    # the service-level tests.
    assert not result.is_error
    assert result.structured_content is not None


@pytest.mark.asyncio
async def test_every_registered_tool_is_exercised(client: Client[Any]) -> None:
    """A tool added without an end-to-end call fails here."""
    registered = {tool.name for tool in await client.list_tools()}
    exercised = {name for name, _ in CALLS}

    assert not registered - exercised, (
        f"Tools with no end-to-end call: {sorted(registered - exercised)}"
    )
    assert not exercised - registered, (
        f"Calls naming a tool that is not registered: {sorted(exercised - registered)}"
    )


@pytest.mark.asyncio
async def test_check_client_status_reports_a_ready_client(
    client: Client[Any],
) -> None:
    data = (await client.call_tool("check_client_status", {})).data
    assert data["status"] == "ready"
    assert data["readOnly"] is False


@pytest.mark.asyncio
async def test_lookup_container_surfaces_a_validation_error(
    client: Client[Any],
) -> None:
    """A ValueError from the service layer must reach the caller as an error."""
    with pytest.raises(Exception, match="exactly one"):
        await client.call_tool("lookup_container", {})


@pytest.mark.asyncio
async def test_a_bad_identifier_is_rejected_before_the_api_is_called(
    client: Client[Any], api: Mock
) -> None:
    with pytest.raises(Exception, match="bare identifier"):
        await client.call_tool(
            "get_tag",
            {
                "account_id": "accounts/1/containers/2",
                "container_id": CONTAINER_ID,
                "workspace_id": WORKSPACE_ID,
                "tag_id": ENTITY_ID,
            },
        )


@pytest.mark.asyncio
async def test_find_entities_by_name_filters_through_the_tool_surface(
    client: Client[Any],
) -> None:
    data = (
        await client.call_tool("find_entities_by_name", {**ACW, "query": "purchase"})
    ).data
    assert data["total"] == 1
    assert data["tags"][0]["name"] == "GA4 - purchase"


@pytest.mark.asyncio
async def test_summarize_container_through_the_tool_surface(
    client: Client[Any],
) -> None:
    data = (await client.call_tool("summarize_container", AC)).data
    assert data["container"]["publicId"] == "GTM-ABC123"
    assert data["workspaceCount"] == 1
    assert data["live"]["containerVersionId"] == "8"


@pytest.mark.asyncio
async def test_publish_workspace_does_not_publish_unless_asked(
    client: Client[Any], api: Mock
) -> None:
    data = (await client.call_tool("publish_workspace", ACW)).data

    assert data["published"] is False
    versions = api.accounts.return_value.containers.return_value.versions.return_value
    versions.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_workspace_publishes_when_asked(
    client: Client[Any], api: Mock
) -> None:
    data = (await client.call_tool("publish_workspace", {**ACW, "publish": True})).data

    assert data["published"] is True
    versions = api.accounts.return_value.containers.return_value.versions.return_value
    versions.publish.assert_called_once()
