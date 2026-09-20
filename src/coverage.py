"""Declared mapping from Tag Manager API methods to MCP tools.

This module is the contract behind the claim that the server covers the API
completely. ``tests/test_api_coverage.py`` checks it in both directions against
the vendored discovery document:

- every method Google publishes appears here, so a method added in a future API
  revision fails the test suite rather than passing unnoticed;
- every tool named here is actually registered on the server.

Refresh the vendored document with ``scripts/refresh_discovery.py``.
"""

from __future__ import annotations

from typing import Dict, Final

#: API method path (as it appears in the discovery document) -> MCP tool name.
API_COVERAGE: Final[Dict[str, str]] = {
    # accounts
    "accounts.list": "list_accounts",
    "accounts.get": "get_account",
    "accounts.update": "update_account",
    # accounts.user_permissions
    "accounts.user_permissions.list": "list_user_permissions",
    "accounts.user_permissions.get": "get_user_permission",
    "accounts.user_permissions.create": "create_user_permission",
    "accounts.user_permissions.update": "update_user_permission",
    "accounts.user_permissions.delete": "delete_user_permission",
    # accounts.containers
    "accounts.containers.list": "list_containers",
    "accounts.containers.get": "get_container",
    "accounts.containers.lookup": "lookup_container",
    "accounts.containers.snippet": "get_container_snippet",
    "accounts.containers.create": "create_container",
    "accounts.containers.update": "update_container",
    "accounts.containers.delete": "delete_container",
    "accounts.containers.combine": "combine_containers",
    "accounts.containers.move_tag_id": "move_tag_id",
    # accounts.containers.destinations
    "accounts.containers.destinations.list": "list_destinations",
    "accounts.containers.destinations.get": "get_destination",
    "accounts.containers.destinations.link": "link_destination",
    # accounts.containers.environments
    "accounts.containers.environments.list": "list_environments",
    "accounts.containers.environments.get": "get_environment",
    "accounts.containers.environments.create": "create_environment",
    "accounts.containers.environments.update": "update_environment",
    "accounts.containers.environments.delete": "delete_environment",
    "accounts.containers.environments.reauthorize": "reauthorize_environment",
    # accounts.containers.version_headers
    "accounts.containers.version_headers.list": "list_version_headers",
    "accounts.containers.version_headers.latest": "get_latest_version_header",
    # accounts.containers.versions
    "accounts.containers.versions.get": "get_version",
    "accounts.containers.versions.live": "get_live_version",
    "accounts.containers.versions.update": "update_version",
    "accounts.containers.versions.delete": "delete_version",
    "accounts.containers.versions.undelete": "undelete_version",
    "accounts.containers.versions.publish": "publish_version",
    "accounts.containers.versions.set_latest": "set_latest_version",
    # accounts.containers.workspaces
    "accounts.containers.workspaces.list": "list_workspaces",
    "accounts.containers.workspaces.get": "get_workspace",
    "accounts.containers.workspaces.getStatus": "get_workspace_status",
    "accounts.containers.workspaces.create": "create_workspace",
    "accounts.containers.workspaces.update": "update_workspace",
    "accounts.containers.workspaces.delete": "delete_workspace",
    "accounts.containers.workspaces.sync": "sync_workspace",
    "accounts.containers.workspaces.resolve_conflict": "resolve_workspace_conflict",
    "accounts.containers.workspaces.quick_preview": "quick_preview_workspace",
    "accounts.containers.workspaces.create_version": "create_version",
    "accounts.containers.workspaces.bulk_update": "bulk_update_workspace",
    # accounts.containers.workspaces.built_in_variables
    "accounts.containers.workspaces.built_in_variables.list": (
        "list_built_in_variables"
    ),
    "accounts.containers.workspaces.built_in_variables.create": (
        "create_built_in_variable"
    ),
    "accounts.containers.workspaces.built_in_variables.delete": (
        "delete_built_in_variable"
    ),
    "accounts.containers.workspaces.built_in_variables.revert": (
        "revert_built_in_variable"
    ),
    # accounts.containers.workspaces.clients
    "accounts.containers.workspaces.clients.list": "list_clients",
    "accounts.containers.workspaces.clients.get": "get_client",
    "accounts.containers.workspaces.clients.create": "create_client",
    "accounts.containers.workspaces.clients.update": "update_client",
    "accounts.containers.workspaces.clients.delete": "delete_client",
    "accounts.containers.workspaces.clients.revert": "revert_client",
    # accounts.containers.workspaces.folders
    "accounts.containers.workspaces.folders.list": "list_folders",
    "accounts.containers.workspaces.folders.get": "get_folder",
    "accounts.containers.workspaces.folders.entities": "get_folder_entities",
    "accounts.containers.workspaces.folders.create": "create_folder",
    "accounts.containers.workspaces.folders.update": "update_folder",
    "accounts.containers.workspaces.folders.delete": "delete_folder",
    "accounts.containers.workspaces.folders.revert": "revert_folder",
    "accounts.containers.workspaces.folders.move_entities_to_folder": (
        "move_entities_to_folder"
    ),
    # accounts.containers.workspaces.gtag_config
    "accounts.containers.workspaces.gtag_config.list": "list_gtag_configs",
    "accounts.containers.workspaces.gtag_config.get": "get_gtag_config",
    "accounts.containers.workspaces.gtag_config.create": "create_gtag_config",
    "accounts.containers.workspaces.gtag_config.update": "update_gtag_config",
    "accounts.containers.workspaces.gtag_config.delete": "delete_gtag_config",
    # accounts.containers.workspaces.tags
    "accounts.containers.workspaces.tags.list": "list_tags",
    "accounts.containers.workspaces.tags.get": "get_tag",
    "accounts.containers.workspaces.tags.create": "create_tag",
    "accounts.containers.workspaces.tags.update": "update_tag",
    "accounts.containers.workspaces.tags.delete": "delete_tag",
    "accounts.containers.workspaces.tags.revert": "revert_tag",
    # accounts.containers.workspaces.templates
    "accounts.containers.workspaces.templates.list": "list_templates",
    "accounts.containers.workspaces.templates.get": "get_template",
    "accounts.containers.workspaces.templates.create": "create_template",
    "accounts.containers.workspaces.templates.update": "update_template",
    "accounts.containers.workspaces.templates.delete": "delete_template",
    "accounts.containers.workspaces.templates.revert": "revert_template",
    "accounts.containers.workspaces.templates.import_from_gallery": (
        "import_template_from_gallery"
    ),
    # accounts.containers.workspaces.transformations
    "accounts.containers.workspaces.transformations.list": "list_transformations",
    "accounts.containers.workspaces.transformations.get": "get_transformation",
    "accounts.containers.workspaces.transformations.create": "create_transformation",
    "accounts.containers.workspaces.transformations.update": "update_transformation",
    "accounts.containers.workspaces.transformations.delete": "delete_transformation",
    "accounts.containers.workspaces.transformations.revert": "revert_transformation",
    # accounts.containers.workspaces.triggers
    "accounts.containers.workspaces.triggers.list": "list_triggers",
    "accounts.containers.workspaces.triggers.get": "get_trigger",
    "accounts.containers.workspaces.triggers.create": "create_trigger",
    "accounts.containers.workspaces.triggers.update": "update_trigger",
    "accounts.containers.workspaces.triggers.delete": "delete_trigger",
    "accounts.containers.workspaces.triggers.revert": "revert_trigger",
    # accounts.containers.workspaces.variables
    "accounts.containers.workspaces.variables.list": "list_variables",
    "accounts.containers.workspaces.variables.get": "get_variable",
    "accounts.containers.workspaces.variables.create": "create_variable",
    "accounts.containers.workspaces.variables.update": "update_variable",
    "accounts.containers.workspaces.variables.delete": "delete_variable",
    "accounts.containers.workspaces.variables.revert": "revert_variable",
    # accounts.containers.workspaces.zones
    "accounts.containers.workspaces.zones.list": "list_zones",
    "accounts.containers.workspaces.zones.get": "get_zone",
    "accounts.containers.workspaces.zones.create": "create_zone",
    "accounts.containers.workspaces.zones.update": "update_zone",
    "accounts.containers.workspaces.zones.delete": "delete_zone",
    "accounts.containers.workspaces.zones.revert": "revert_zone",
}

#: Tools that exist for ergonomics and map onto no single API method.
CONVENIENCE_TOOLS: Final[Dict[str, str]] = {
    "list_workspace_entities": (
        "tags.list, triggers.list, variables.list and folders.list, each paged "
        "to exhaustion"
    ),
    "find_entities_by_name": (
        "the same four list methods, filtered by name -- the API has no search"
    ),
    "summarize_container": (
        "containers.get, workspaces.list and versions.live, with counts"
    ),
    "list_all_containers": ("accounts.list, then containers.list once per account"),
    "publish_workspace": (
        "workspaces.create_version, then versions.publish when asked and when "
        "the version compiled"
    ),
    "check_client_status": "no API call; reports local credential state",
}

#: Methods whose runtime behaviour does not match the published discovery
#: document. Implemented as published; the divergence is documented, not
#: worked around.
QUIRKS: Final[Dict[str, str]] = {
    "accounts.containers.workspaces.built_in_variables.create": (
        "'type' is repeated in the discovery document but typed as a single "
        "Literal by google-api-python-client-stubs. A list is sent, per the "
        "discovery document."
    ),
    "accounts.containers.workspaces.built_in_variables.delete": (
        "'type' is repeated in the discovery document but typed as a single "
        "Literal by google-api-python-client-stubs. A list is sent, per the "
        "discovery document."
    ),
    "accounts.containers.workspaces.folders.entities": (
        "A POST that reads rather than writes, so it is not gated by read-only mode."
    ),
    "accounts.containers.environments.reauthorize": (
        "Requires a request body it makes no use of; an empty object is sent "
        "when the caller supplies none."
    ),
    "accounts.containers.workspaces.folders.move_entities_to_folder": (
        "Requires a Folder body it makes no use of; an empty object is sent "
        "when the caller supplies none."
    ),
}
