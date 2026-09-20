"""Tests for the task-shaped tools composed from several API calls."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.insights_service import InsightsService, register_insights_tools
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    WORKSPACE_ID,
    accounts_resource,
    container_child,
    containers_resource,
    workspace_child,
    workspaces_resource,
)


@pytest.fixture
def service() -> InsightsService:
    return InsightsService()


def set_workspace_collections(
    mock_api: Mock,
    tags: List[Dict[str, Any]] | None = None,
    triggers: List[Dict[str, Any]] | None = None,
    variables: List[Dict[str, Any]] | None = None,
    folders: List[Dict[str, Any]] | None = None,
) -> None:
    """Wire up single-page responses for the four workspace collections."""
    workspace_child(mock_api, "tags").list.return_value.execute.return_value = {
        "tag": tags or []
    }
    workspace_child(mock_api, "triggers").list.return_value.execute.return_value = {
        "trigger": triggers or []
    }
    workspace_child(mock_api, "variables").list.return_value.execute.return_value = {
        "variable": variables or []
    }
    workspace_child(mock_api, "folders").list.return_value.execute.return_value = {
        "folder": folders or []
    }


@pytest.mark.asyncio
async def test_pagination_is_followed_to_the_last_page(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """A collection spanning several pages comes back whole.

    Exercised through the public tool rather than the paging helper, so the
    thing under test is what a caller actually gets.
    """
    set_workspace_collections(mock_api)
    workspace_child(mock_api, "tags").list.return_value.execute.side_effect = [
        {"tag": [{"name": "a"}], "nextPageToken": "p2"},
        {"tag": [{"name": "b"}], "nextPageToken": "p3"},
        {"tag": [{"name": "c"}]},
    ]

    result = await service.list_workspace_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert [tag["name"] for tag in result["tags"]] == ["a", "b", "c"]
    tokens = [
        call.kwargs.get("pageToken")
        for call in workspace_child(mock_api, "tags").list.call_args_list
    ]
    assert tokens == [None, "p2", "p3"]


@pytest.mark.asyncio
async def test_pagination_stops_at_the_page_guard(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """An API that never stops handing out tokens must not loop forever."""
    set_workspace_collections(mock_api)
    workspace_child(mock_api, "tags").list.return_value.execute.return_value = {
        "tag": [{"name": "x"}],
        "nextPageToken": "always",
    }

    result = await service.list_workspace_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result["counts"]["tags"] == 50
    assert workspace_child(mock_api, "tags").list.call_count == 50


@pytest.mark.asyncio
async def test_a_missing_collection_key_reads_as_empty(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """The API omits the key entirely rather than returning an empty list."""
    for collection in ("tags", "triggers", "variables", "folders"):
        workspace_child(
            mock_api, collection
        ).list.return_value.execute.return_value = {}

    result = await service.list_workspace_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result["counts"] == {
        "tags": 0,
        "triggers": 0,
        "variables": 0,
        "folders": 0,
    }


@pytest.mark.asyncio
async def test_list_workspace_entities(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    set_workspace_collections(
        mock_api,
        tags=[{"tagId": "1", "name": "GA4"}],
        triggers=[{"triggerId": "2", "name": "All Pages"}],
        variables=[{"variableId": "3", "name": "DL - id"}],
        folders=[{"folderId": "4", "name": "GA4"}],
    )

    result = await service.list_workspace_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result["counts"] == {
        "tags": 1,
        "triggers": 1,
        "variables": 1,
        "folders": 1,
    }
    assert result["tags"][0]["name"] == "GA4"
    assert result["accountId"] == ACCOUNT_ID


@pytest.mark.asyncio
async def test_find_entities_by_name_matches_case_insensitively(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    set_workspace_collections(
        mock_api,
        tags=[
            {"tagId": "1", "name": "GA4 - purchase", "type": "gaawe", "path": "p1"},
            {"tagId": "2", "name": "Ads remarketing", "type": "sp", "path": "p2"},
        ],
        triggers=[{"triggerId": "3", "name": "Purchase event", "type": "customEvent"}],
        variables=[{"variableId": "4", "name": "Page URL"}],
    )

    result = await service.find_entities_by_name(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "PURCHASE"
    )

    assert result["total"] == 2
    assert [tag["id"] for tag in result["tags"]] == ["1"]
    assert [trigger["id"] for trigger in result["triggers"]] == ["3"]
    assert result["variables"] == []


@pytest.mark.asyncio
async def test_find_entities_by_name_tolerates_a_nameless_entity(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    set_workspace_collections(mock_api, tags=[{"tagId": "1"}])

    result = await service.find_entities_by_name(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "anything"
    )

    assert result["total"] == 0


@pytest.mark.asyncio
async def test_find_entities_by_name_refuses_an_empty_query(
    service: InsightsService, mock_ctx: AsyncMock
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await service.find_entities_by_name(
            mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "   "
        )


@pytest.mark.asyncio
async def test_summarize_container(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    containers_resource(mock_api).get.return_value.execute.return_value = {
        "containerId": CONTAINER_ID,
        "name": "example.com",
    }
    workspaces_resource(mock_api).list.return_value.execute.return_value = {
        "workspace": [{"workspaceId": "3", "name": "Default", "description": "d"}]
    }
    container_child(mock_api, "versions").live.return_value.execute.return_value = {
        "containerVersionId": "8",
        "name": "Release",
        "tag": [{}, {}],
        "trigger": [{}],
        "variable": [],
        "builtInVariable": [{}, {}, {}],
    }

    result = await service.summarize_container(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result["container"]["name"] == "example.com"
    assert result["workspaceCount"] == 1
    assert result["workspaces"][0]["workspaceId"] == "3"
    assert result["live"]["containerVersionId"] == "8"
    assert result["live"]["counts"] == {
        "tags": 2,
        "triggers": 1,
        "variables": 0,
        "builtInVariables": 3,
    }


@pytest.mark.asyncio
async def test_summarize_container_reports_no_live_version(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """A container that has never been published errors on versions.live."""
    containers_resource(mock_api).get.return_value.execute.return_value = {
        "name": "example.com"
    }
    workspaces_resource(mock_api).list.return_value.execute.return_value = {}
    container_child(
        mock_api, "versions"
    ).live.return_value.execute.side_effect = RuntimeError("not found")

    result = await service.summarize_container(mock_ctx, ACCOUNT_ID, CONTAINER_ID)

    assert result["live"] is None
    assert result["workspaceCount"] == 0


@pytest.mark.asyncio
async def test_list_all_containers(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    accounts_resource(mock_api).list.return_value.execute.return_value = {
        "account": [
            {"accountId": "1", "name": "Acme"},
            {"accountId": "2", "name": "Other"},
        ]
    }
    containers_resource(mock_api).list.return_value.execute.side_effect = [
        {"container": [{"containerId": "10", "publicId": "GTM-A", "name": "a"}]},
        {"container": [{"containerId": "20", "publicId": "GTM-B", "name": "b"}]},
    ]

    result = await service.list_all_containers(mock_ctx)

    assert result["accountCount"] == 2
    assert result["containerCount"] == 2
    assert result["accounts"][0]["containers"][0]["publicId"] == "GTM-A"
    assert result["accounts"][1]["containers"][0]["publicId"] == "GTM-B"


@pytest.mark.asyncio
async def test_list_all_containers_records_a_per_account_failure(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """One unreadable account must not fail the whole call."""
    accounts_resource(mock_api).list.return_value.execute.return_value = {
        "account": [
            {"accountId": "1", "name": "Readable"},
            {"accountId": "2", "name": "Forbidden"},
        ]
    }
    containers_resource(mock_api).list.return_value.execute.side_effect = [
        {"container": [{"containerId": "10"}]},
        RuntimeError("denied"),
    ]

    result = await service.list_all_containers(mock_ctx)

    assert result["containerCount"] == 1
    assert "error" in result["accounts"][1]
    assert "denied" in result["accounts"][1]["error"]
    assert result["accounts"][1]["containers"] == []


@pytest.mark.asyncio
async def test_list_all_containers_passes_include_google_tags(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    accounts_resource(mock_api).list.return_value.execute.return_value = {}

    await service.list_all_containers(mock_ctx, True)

    accounts_resource(mock_api).list.assert_called_once_with(includeGoogleTags=True)


@pytest.mark.asyncio
async def test_publish_workspace_does_not_publish_by_default(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    """Creating a version must not silently be a release."""
    workspaces = workspaces_resource(mock_api)
    workspaces.create_version.return_value.execute.return_value = {
        "containerVersion": {"containerVersionId": "9"}
    }
    versions = container_child(mock_api, "versions")

    result = await service.publish_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "Release", "notes"
    )

    assert result["published"] is False
    assert "publish was not requested" in result["skippedPublishReason"]
    workspaces.create_version.assert_called_once()
    assert workspaces.create_version.call_args.kwargs["body"] == {
        "name": "Release",
        "notes": "notes",
    }
    versions.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_workspace_publishes_when_asked(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    workspaces_resource(mock_api).create_version.return_value.execute.return_value = {
        "containerVersion": {"containerVersionId": "9"}
    }
    versions = container_child(mock_api, "versions")
    versions.publish.return_value.execute.return_value = {"containerVersion": {}}

    result = await service.publish_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, publish=True
    )

    assert result["published"] is True
    assert result["publishResult"] == {"containerVersion": {}}
    versions.publish.assert_called_once_with(
        path=f"accounts/{ACCOUNT_ID}/containers/{CONTAINER_ID}/versions/9"
    )


@pytest.mark.asyncio
async def test_publish_workspace_sends_no_options_when_none_given(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    workspaces = workspaces_resource(mock_api)
    workspaces.create_version.return_value.execute.return_value = {}

    await service.publish_workspace(mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID)

    assert workspaces.create_version.call_args.kwargs["body"] == {}


@pytest.mark.asyncio
async def test_publish_workspace_refuses_to_publish_a_broken_version(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    workspaces_resource(mock_api).create_version.return_value.execute.return_value = {
        "containerVersion": {"containerVersionId": "9"},
        "compilerError": True,
    }
    versions = container_child(mock_api, "versions")

    result = await service.publish_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, publish=True
    )

    assert result["published"] is False
    assert "failed to compile" in result["skippedPublishReason"]
    versions.publish.assert_not_called()


@pytest.mark.asyncio
async def test_publish_workspace_handles_a_missing_version_id(
    service: InsightsService, mock_api: Mock, mock_ctx: AsyncMock
) -> None:
    workspaces_resource(mock_api).create_version.return_value.execute.return_value = {
        "containerVersion": {}
    }
    versions = container_child(mock_api, "versions")

    result = await service.publish_workspace(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, publish=True
    )

    assert result["published"] is False
    assert "no containerVersionId" in result["skippedPublishReason"]
    versions.publish.assert_not_called()


@pytest.mark.asyncio
async def test_insights_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_insights_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_workspace_entities",
        "find_entities_by_name",
        "summarize_container",
        "list_all_containers",
        "publish_workspace",
    }
