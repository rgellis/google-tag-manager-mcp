"""Tests for ContainersService and DestinationsService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.containers_service import (
    ContainersService,
    register_containers_tools,
)
from src.services.destinations_service import (
    DestinationsService,
    register_destinations_tools,
)
from tests.conftest import (
    ACCOUNT_ID,
    ACCOUNT_PATH,
    CONTAINER_ID,
    CONTAINER_PATH,
    container_child,
    containers_resource,
)

DESTINATION_ID = "AW-123456789"
DESTINATION_PATH = f"{CONTAINER_PATH}/destinations/{DESTINATION_ID}"


@pytest.fixture
def service() -> ContainersService:
    return ContainersService()


@pytest.fixture
def destinations() -> DestinationsService:
    return DestinationsService()


@pytest.mark.asyncio
async def test_list_containers(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    expected = {"container": [{"containerId": CONTAINER_ID}]}
    containers_resource(mock_api).list.return_value.execute.return_value = expected

    result = await service.list_containers(mock_ctx, ACCOUNT_ID)

    assert result == expected
    containers_resource(mock_api).list.assert_called_once_with(parent=ACCOUNT_PATH)


@pytest.mark.asyncio
async def test_get_container(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).get.return_value.execute.return_value = {"name": "c"}

    result = await service.get_container(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"name": "c"}
    containers_resource(mock_api).get.assert_called_once_with(path=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_lookup_container_by_tag_id(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).lookup.return_value.execute.return_value = {"a": 1}

    result = await service.lookup_container(mock_ctx, tag_id="GTM-ABC123")

    assert result == {"a": 1}
    containers_resource(mock_api).lookup.assert_called_once_with(tagId="GTM-ABC123")


@pytest.mark.asyncio
async def test_lookup_container_by_destination_id(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).lookup.return_value.execute.return_value = {}

    await service.lookup_container(mock_ctx, destination_id=DESTINATION_ID)

    containers_resource(mock_api).lookup.assert_called_once_with(
        destinationId=DESTINATION_ID
    )


@pytest.mark.asyncio
async def test_lookup_container_refuses_both_identifiers(
    service: ContainersService, mock_ctx: AsyncMock
) -> None:
    """The API silently ignores the second, so refuse rather than guess."""
    with pytest.raises(ValueError, match="exactly one"):
        await service.lookup_container(mock_ctx, "GTM-ABC123", DESTINATION_ID)


@pytest.mark.asyncio
async def test_lookup_container_refuses_neither_identifier(
    service: ContainersService, mock_ctx: AsyncMock
) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        await service.lookup_container(mock_ctx)


@pytest.mark.asyncio
async def test_get_container_snippet(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).snippet.return_value.execute.return_value = {
        "snippet": "<script>"
    }

    result = await service.get_container_snippet(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"snippet": "<script>"}
    containers_resource(mock_api).snippet.assert_called_once_with(path=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_create_container(
    service: ContainersService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"name": "example.com", "usageContext": ["web"]}
    containers_resource(mock_api).create.return_value.execute.return_value = body

    result = await service.create_container(mock_ctx, ACCOUNT_ID, body)

    assert result == body
    install_client.require_write.assert_called_once_with("create_container")
    containers_resource(mock_api).create.assert_called_once_with(
        parent=ACCOUNT_PATH, body=body
    )


@pytest.mark.asyncio
async def test_update_container(
    service: ContainersService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    containers_resource(mock_api).update.return_value.execute.return_value = {}

    await service.update_container(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, {"name": "n"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_container")
    containers_resource(mock_api).update.assert_called_once_with(
        path=CONTAINER_PATH, body={"name": "n"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_delete_container(
    service: ContainersService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    containers_resource(mock_api).delete.return_value.execute.return_value = ""

    result = await service.delete_container(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"path": CONTAINER_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_container")


@pytest.mark.asyncio
async def test_combine_containers(
    service: ContainersService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    containers_resource(mock_api).combine.return_value.execute.return_value = {}

    await service.combine_containers(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, "999", "current", True
    )

    install_client.require_write.assert_called_once_with("combine_containers")
    containers_resource(mock_api).combine.assert_called_once_with(
        path=CONTAINER_PATH,
        containerId="999",
        settingSource="current",
        allowUserPermissionFeatureUpdate=True,
    )


@pytest.mark.asyncio
async def test_combine_containers_omits_unset_options(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).combine.return_value.execute.return_value = {}

    await service.combine_containers(mock_ctx, ACCOUNT_ID, CONTAINER_ID, "999")

    containers_resource(mock_api).combine.assert_called_once_with(
        path=CONTAINER_PATH, containerId="999"
    )


@pytest.mark.asyncio
async def test_move_tag_id(
    service: ContainersService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    containers_resource(mock_api).move_tag_id.return_value.execute.return_value = {}

    await service.move_tag_id(
        mock_ctx,
        ACCOUNT_ID,
        CONTAINER_ID,
        "GTM-ABC123",
        "Split out",
        True,
        False,
        True,
        True,
    )

    install_client.require_write.assert_called_once_with("move_tag_id")
    containers_resource(mock_api).move_tag_id.assert_called_once_with(
        path=CONTAINER_PATH,
        tagId="GTM-ABC123",
        tagName="Split out",
        copySettings=True,
        copyUsers=False,
        copyTermsOfService=True,
        allowUserPermissionFeatureUpdate=True,
    )


@pytest.mark.asyncio
async def test_move_tag_id_omits_unset_options(
    service: ContainersService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).move_tag_id.return_value.execute.return_value = {}

    await service.move_tag_id(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    containers_resource(mock_api).move_tag_id.assert_called_once_with(
        path=CONTAINER_PATH
    )


@pytest.mark.asyncio
async def test_containers_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_containers_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_containers",
        "get_container",
        "lookup_container",
        "get_container_snippet",
        "create_container",
        "update_container",
        "delete_container",
        "combine_containers",
        "move_tag_id",
    }


@pytest.mark.asyncio
async def test_list_destinations(
    destinations: DestinationsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = container_child(mock_api, "destinations")
    resource.list.return_value.execute.return_value = {"destination": []}

    result = await destinations.list_destinations(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result == {"destination": []}
    resource.list.assert_called_once_with(parent=CONTAINER_PATH)


@pytest.mark.asyncio
async def test_get_destination(
    destinations: DestinationsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = container_child(mock_api, "destinations")
    resource.get.return_value.execute.return_value = {"destinationId": DESTINATION_ID}

    result = await destinations.get_destination(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, DESTINATION_ID
    )

    assert result == {"destinationId": DESTINATION_ID}
    resource.get.assert_called_once_with(path=DESTINATION_PATH)


@pytest.mark.asyncio
async def test_link_destination(
    destinations: DestinationsService,
    mock_api: Mock,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    resource = container_child(mock_api, "destinations")
    resource.link.return_value.execute.return_value = {}

    await destinations.link_destination(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, DESTINATION_ID, True
    )

    install_client.require_write.assert_called_once_with("link_destination")
    resource.link.assert_called_once_with(
        parent=CONTAINER_PATH,
        destinationId=DESTINATION_ID,
        allowUserPermissionFeatureUpdate=True,
    )


@pytest.mark.asyncio
async def test_link_destination_omits_the_unset_flag(
    destinations: DestinationsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    resource = container_child(mock_api, "destinations")
    resource.link.return_value.execute.return_value = {}

    await destinations.link_destination(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, DESTINATION_ID
    )

    resource.link.assert_called_once_with(
        parent=CONTAINER_PATH, destinationId=DESTINATION_ID
    )


@pytest.mark.asyncio
async def test_destinations_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_destinations_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {"list_destinations", "get_destination", "link_destination"}
