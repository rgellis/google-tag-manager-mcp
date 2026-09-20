"""Tests for the workspace entity services that share one shape.

Six resources -- tags, triggers, variables, clients, transformations and zones
-- expose the same list/get/create/update/delete/revert surface over the same
paths. They are tested together here so that a divergence in any one of them
shows up as a failure rather than as an untested special case.

The resources that do not share the shape (templates, folders, gtag_config and
built_in_variables) have their own modules.
"""

from __future__ import annotations

from typing import Any, Callable, List, NamedTuple
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.clients_service import ClientsService, register_clients_tools
from src.services.tags_service import TagsService, register_tags_tools
from src.services.transformations_service import (
    TransformationsService,
    register_transformations_tools,
)
from src.services.triggers_service import TriggersService, register_triggers_tools
from src.services.variables_service import VariablesService, register_variables_tools
from src.services.zones_service import ZonesService, register_zones_tools
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    ENTITY_ID,
    WORKSPACE_ID,
    WORKSPACE_PATH,
    workspace_child,
)


class Entity(NamedTuple):
    collection: str  # resource accessor and path segment
    singular: str  # noun in method names
    plural: str  # plural in method names
    service: Callable[[], Any]
    register: Callable[[FastMCP[Any]], Any]


ENTITIES: List[Entity] = [
    Entity("tags", "tag", "tags", TagsService, register_tags_tools),
    Entity("triggers", "trigger", "triggers", TriggersService, register_triggers_tools),
    Entity(
        "variables", "variable", "variables", VariablesService, register_variables_tools
    ),
    Entity("clients", "client", "clients", ClientsService, register_clients_tools),
    Entity(
        "transformations",
        "transformation",
        "transformations",
        TransformationsService,
        register_transformations_tools,
    ),
    Entity("zones", "zone", "zones", ZonesService, register_zones_tools),
]

IDS = [entity.collection for entity in ENTITIES]

ENTITY_PATH = f"{WORKSPACE_PATH}/{{collection}}/{ENTITY_ID}"


def entity_path(entity: Entity) -> str:
    return ENTITY_PATH.format(collection=entity.collection)


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_list_without_a_page_token(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    expected = {entity.singular: [{"name": "example"}]}
    resource.list.return_value.execute.return_value = expected
    service = entity.service()

    result = await getattr(service, f"list_{entity.plural}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == expected
    resource.list.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_list_passes_a_page_token_through(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.list.return_value.execute.return_value = {}
    service = entity.service()

    await getattr(service, f"list_{entity.plural}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "next-page"
    )

    resource.list.assert_called_once_with(parent=WORKSPACE_PATH, pageToken="next-page")


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_get(entity: Entity, mock_api: Mock, mock_ctx: AsyncMock) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.get.return_value.execute.return_value = {"name": "example"}
    service = entity.service()

    result = await getattr(service, f"get_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"name": "example"}
    resource.get.assert_called_once_with(path=entity_path(entity))


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_create(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock, install_client: Mock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.create.return_value.execute.return_value = {"name": "made"}
    body = {"name": "made", "type": "example"}
    service = entity.service()

    result = await getattr(service, f"create_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, body
    )

    assert result == {"name": "made"}
    install_client.require_write.assert_called_once_with(f"create_{entity.singular}")
    resource.create.assert_called_once_with(parent=WORKSPACE_PATH, body=body)


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_update_without_a_fingerprint(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock, install_client: Mock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.update.return_value.execute.return_value = {"name": "changed"}
    body = {"name": "changed"}
    service = entity.service()

    result = await getattr(service, f"update_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, body
    )

    assert result == {"name": "changed"}
    install_client.require_write.assert_called_once_with(f"update_{entity.singular}")
    resource.update.assert_called_once_with(path=entity_path(entity), body=body)


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_update_sends_a_fingerprint_when_given(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.update.return_value.execute.return_value = {}
    body = {"name": "changed"}
    service = entity.service()

    await getattr(service, f"update_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, body, "fp-1"
    )

    resource.update.assert_called_once_with(
        path=entity_path(entity), body=body, fingerprint="fp-1"
    )


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_delete_confirms_because_the_api_returns_nothing(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock, install_client: Mock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.delete.return_value.execute.return_value = ""
    service = entity.service()

    result = await getattr(service, f"delete_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"path": entity_path(entity), "status": "deleted"}
    install_client.require_write.assert_called_once_with(f"delete_{entity.singular}")
    resource.delete.assert_called_once_with(path=entity_path(entity))


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_revert(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock, install_client: Mock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.revert.return_value.execute.return_value = {entity.singular: {}}
    service = entity.service()

    result = await getattr(service, f"revert_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {entity.singular: {}}
    install_client.require_write.assert_called_once_with(f"revert_{entity.singular}")
    resource.revert.assert_called_once_with(path=entity_path(entity))


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_revert_sends_a_fingerprint_when_given(
    entity: Entity, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = workspace_child(mock_api, entity.collection)
    resource.revert.return_value.execute.return_value = {}
    service = entity.service()

    await getattr(service, f"revert_{entity.singular}")(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, "fp-2"
    )

    resource.revert.assert_called_once_with(
        path=entity_path(entity), fingerprint="fp-2"
    )


@pytest.mark.parametrize("entity", ENTITIES, ids=IDS)
@pytest.mark.asyncio
async def test_registers_exactly_the_expected_tools(entity: Entity) -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    entity.register(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        f"list_{entity.plural}",
        f"get_{entity.singular}",
        f"create_{entity.singular}",
        f"update_{entity.singular}",
        f"delete_{entity.singular}",
        f"revert_{entity.singular}",
    }
