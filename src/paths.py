"""Construction of Tag Manager API relative paths.

Every Tag Manager resource is addressed by a slash-separated relative path such
as ``accounts/1234/containers/5678/workspaces/9/tags/12``, and the API validates
each one against a regex -- a path of the wrong shape is rejected before any
permission check, so a malformed identifier surfaces as a confusing 400 or 404
rather than "you got the shape wrong".

Tools therefore take the individual numeric IDs, which is what the Tag Manager
UI displays and what a caller actually has, and the paths are assembled here.
Assembling in one place also means the shape is tested once rather than at 106
call sites.
"""

from __future__ import annotations

from typing import Optional

#: Path segment for each workspace-scoped entity collection.
WORKSPACE_COLLECTIONS: frozenset[str] = frozenset(
    {
        "built_in_variables",
        "clients",
        "folders",
        "gtag_config",
        "tags",
        "templates",
        "transformations",
        "triggers",
        "variables",
        "zones",
    }
)


def segment(value: str, field: str, collection: Optional[str] = None) -> str:
    """Validate one path component and return it.

    A bare identifier is what is expected. The API's own ``collection/id``
    spelling is accepted too, because it is what a caller copying an identifier
    out of a previous response will have to hand -- but a longer path is
    rejected rather than silently truncated, since guessing which segment was
    meant is how you end up writing to the wrong container.

    Args:
        value: The identifier to validate.
        field: Name of the argument, used in error messages.
        collection: Collection name to strip if ``value`` is given as
            ``collection/id``.

    Returns:
        The bare identifier.

    Raises:
        ValueError: If the value is empty or is a path this cannot unambiguously
            reduce to a single component.
    """
    cleaned = value.strip().strip("/")
    if not cleaned:
        raise ValueError(f"{field} must not be empty")

    if "/" in cleaned:
        parts = cleaned.split("/")
        if collection is not None and len(parts) == 2 and parts[0] == collection:
            return parts[1]
        raise ValueError(
            f"{field} must be a bare identifier such as '123', not a path "
            f"({value!r}). Pass each level of the hierarchy as its own argument."
        )

    return cleaned


def account_path(account_id: str) -> str:
    """``accounts/{account_id}``."""
    return f"accounts/{segment(account_id, 'account_id', 'accounts')}"


def container_path(account_id: str, container_id: str) -> str:
    """``accounts/{a}/containers/{c}``."""
    container = segment(container_id, "container_id", "containers")
    return f"{account_path(account_id)}/containers/{container}"


def workspace_path(account_id: str, container_id: str, workspace_id: str) -> str:
    """``accounts/{a}/containers/{c}/workspaces/{w}``."""
    workspace = segment(workspace_id, "workspace_id", "workspaces")
    return f"{container_path(account_id, container_id)}/workspaces/{workspace}"


def container_child_path(
    account_id: str, container_id: str, collection: str, entity_id: str, field: str
) -> str:
    """``accounts/{a}/containers/{c}/{collection}/{entity_id}``."""
    entity = segment(entity_id, field, collection)
    return f"{container_path(account_id, container_id)}/{collection}/{entity}"


def workspace_child_path(
    account_id: str,
    container_id: str,
    workspace_id: str,
    collection: str,
    entity_id: str,
    field: str,
) -> str:
    """``accounts/{a}/containers/{c}/workspaces/{w}/{collection}/{entity_id}``."""
    if collection not in WORKSPACE_COLLECTIONS:
        raise ValueError(f"Unknown workspace collection: {collection}")
    entity = segment(entity_id, field, collection)
    workspace = workspace_path(account_id, container_id, workspace_id)
    return f"{workspace}/{collection}/{entity}"


def built_in_variables_path(
    account_id: str, container_id: str, workspace_id: str
) -> str:
    """``accounts/{a}/containers/{c}/workspaces/{w}/built_in_variables``.

    Built-in variables are the one workspace collection addressed without a
    trailing entity ID: several are enabled or deleted per call, identified by
    type rather than by ID.
    """
    workspace = workspace_path(account_id, container_id, workspace_id)
    return f"{workspace}/built_in_variables"


def destination_path(account_id: str, container_id: str, destination_id: str) -> str:
    """``accounts/{a}/containers/{c}/destinations/{d}``."""
    return container_child_path(
        account_id, container_id, "destinations", destination_id, "destination_id"
    )


def environment_path(account_id: str, container_id: str, environment_id: str) -> str:
    """``accounts/{a}/containers/{c}/environments/{e}``."""
    return container_child_path(
        account_id, container_id, "environments", environment_id, "environment_id"
    )


def version_path(account_id: str, container_id: str, version_id: str) -> str:
    """``accounts/{a}/containers/{c}/versions/{v}``."""
    return container_child_path(
        account_id, container_id, "versions", version_id, "version_id"
    )


def user_permission_path(account_id: str, permission_id: str) -> str:
    """``accounts/{a}/user_permissions/{p}``."""
    permission = segment(permission_id, "permission_id", "user_permissions")
    return f"{account_path(account_id)}/user_permissions/{permission}"
