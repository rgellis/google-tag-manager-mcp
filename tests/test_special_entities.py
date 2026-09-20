"""Tests for the workspace resources that break the common CRUD shape.

Templates add a gallery import, folders add entity listing and moving,
gtag_config has no revert, and built_in_variables is addressed by type across
three different paths.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastmcp import FastMCP

from src.services.built_in_variables_service import (
    BuiltInVariablesService,
    register_built_in_variables_tools,
)
from src.services.folders_service import FoldersService, register_folders_tools
from src.services.gtag_config_service import (
    GtagConfigService,
    register_gtag_config_tools,
)
from src.services.templates_service import (
    TemplatesService,
    register_templates_tools,
)
from tests.conftest import (
    ACCOUNT_ID,
    CONTAINER_ID,
    ENTITY_ID,
    WORKSPACE_ID,
    WORKSPACE_PATH,
    workspace_child,
)

TEMPLATE_PATH = f"{WORKSPACE_PATH}/templates/{ENTITY_ID}"
FOLDER_PATH = f"{WORKSPACE_PATH}/folders/{ENTITY_ID}"
GTAG_PATH = f"{WORKSPACE_PATH}/gtag_config/{ENTITY_ID}"
BUILT_IN_PATH = f"{WORKSPACE_PATH}/built_in_variables"


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------


@pytest.fixture
def templates() -> TemplatesService:
    return TemplatesService()


@pytest.fixture
def templates_api(mock_api: Mock) -> Any:
    return workspace_child(mock_api, "templates")


@pytest.mark.asyncio
async def test_list_templates(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.list.return_value.execute.return_value = {"template": []}

    result = await templates.list_templates(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"template": []}
    templates_api.list.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_list_templates_pages(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.list.return_value.execute.return_value = {}

    await templates.list_templates(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "token"
    )

    templates_api.list.assert_called_once_with(parent=WORKSPACE_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_get_template(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.get.return_value.execute.return_value = {"templateData": "x"}

    result = await templates.get_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"templateData": "x"}
    templates_api.get.assert_called_once_with(path=TEMPLATE_PATH)


@pytest.mark.asyncio
async def test_create_template(
    templates: TemplatesService,
    templates_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"name": "My pixel", "templateData": "___INFO___"}
    templates_api.create.return_value.execute.return_value = body

    result = await templates.create_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, body
    )

    assert result == body
    install_client.require_write.assert_called_once_with("create_template")
    templates_api.create.assert_called_once_with(parent=WORKSPACE_PATH, body=body)


@pytest.mark.asyncio
async def test_update_template(
    templates: TemplatesService,
    templates_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    templates_api.update.return_value.execute.return_value = {}

    await templates.update_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"name": "t"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_template")
    templates_api.update.assert_called_once_with(
        path=TEMPLATE_PATH, body={"name": "t"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_template_without_a_fingerprint(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.update.return_value.execute.return_value = {}

    await templates.update_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"name": "t"}
    )

    templates_api.update.assert_called_once_with(path=TEMPLATE_PATH, body={"name": "t"})


@pytest.mark.asyncio
async def test_delete_template(
    templates: TemplatesService,
    templates_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    templates_api.delete.return_value.execute.return_value = ""

    result = await templates.delete_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"path": TEMPLATE_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_template")


@pytest.mark.asyncio
async def test_revert_template(
    templates: TemplatesService,
    templates_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    templates_api.revert.return_value.execute.return_value = {"template": {}}

    result = await templates.revert_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, "fp"
    )

    assert result == {"template": {}}
    install_client.require_write.assert_called_once_with("revert_template")
    templates_api.revert.assert_called_once_with(path=TEMPLATE_PATH, fingerprint="fp")


@pytest.mark.asyncio
async def test_revert_template_without_a_fingerprint(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.revert.return_value.execute.return_value = {}

    await templates.revert_template(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    templates_api.revert.assert_called_once_with(path=TEMPLATE_PATH)


@pytest.mark.asyncio
async def test_import_template_from_gallery(
    templates: TemplatesService,
    templates_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    templates_api.import_from_gallery.return_value.execute.return_value = {}

    await templates.import_template_from_gallery(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "owner", "repo", "sha", True
    )

    install_client.require_write.assert_called_once_with("import_template_from_gallery")
    templates_api.import_from_gallery.assert_called_once_with(
        parent=WORKSPACE_PATH,
        galleryOwner="owner",
        galleryRepository="repo",
        gallerySha="sha",
        acknowledgePermissions=True,
    )


@pytest.mark.asyncio
async def test_import_template_omits_unset_options(
    templates: TemplatesService, templates_api: Any, mock_ctx: AsyncMock
) -> None:
    templates_api.import_from_gallery.return_value.execute.return_value = {}

    await templates.import_template_from_gallery(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    templates_api.import_from_gallery.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_templates_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_templates_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_templates",
        "get_template",
        "create_template",
        "update_template",
        "delete_template",
        "revert_template",
        "import_template_from_gallery",
    }


# --------------------------------------------------------------------------
# Folders
# --------------------------------------------------------------------------


@pytest.fixture
def folders() -> FoldersService:
    return FoldersService()


@pytest.fixture
def folders_api(mock_api: Mock) -> Any:
    return workspace_child(mock_api, "folders")


@pytest.mark.asyncio
async def test_list_folders(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.list.return_value.execute.return_value = {"folder": []}

    result = await folders.list_folders(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"folder": []}
    folders_api.list.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_list_folders_pages(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.list.return_value.execute.return_value = {}

    await folders.list_folders(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "token"
    )

    folders_api.list.assert_called_once_with(parent=WORKSPACE_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_get_folder(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.get.return_value.execute.return_value = {"name": "GA4"}

    result = await folders.get_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"name": "GA4"}
    folders_api.get.assert_called_once_with(path=FOLDER_PATH)


@pytest.mark.asyncio
async def test_get_folder_entities_is_a_read_despite_being_a_post(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.entities.return_value.execute.return_value = {"tag": []}

    result = await folders.get_folder_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"tag": []}
    folders_api.entities.assert_called_once_with(path=FOLDER_PATH)
    # A POST that reads, so it must not be gated by read-only mode.
    install_client.require_write.assert_not_called()


@pytest.mark.asyncio
async def test_get_folder_entities_pages(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.entities.return_value.execute.return_value = {}

    await folders.get_folder_entities(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, "token"
    )

    folders_api.entities.assert_called_once_with(path=FOLDER_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_create_folder(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.create.return_value.execute.return_value = {"name": "GA4"}

    result = await folders.create_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, {"name": "GA4"}
    )

    assert result == {"name": "GA4"}
    install_client.require_write.assert_called_once_with("create_folder")
    folders_api.create.assert_called_once_with(
        parent=WORKSPACE_PATH, body={"name": "GA4"}
    )


@pytest.mark.asyncio
async def test_update_folder(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.update.return_value.execute.return_value = {}

    await folders.update_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"name": "f"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_folder")
    folders_api.update.assert_called_once_with(
        path=FOLDER_PATH, body={"name": "f"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_folder_without_a_fingerprint(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.update.return_value.execute.return_value = {}

    await folders.update_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"name": "f"}
    )

    folders_api.update.assert_called_once_with(path=FOLDER_PATH, body={"name": "f"})


@pytest.mark.asyncio
async def test_delete_folder(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.delete.return_value.execute.return_value = ""

    result = await folders.delete_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"path": FOLDER_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_folder")


@pytest.mark.asyncio
async def test_revert_folder(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.revert.return_value.execute.return_value = {"folder": {}}

    result = await folders.revert_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, "fp"
    )

    assert result == {"folder": {}}
    install_client.require_write.assert_called_once_with("revert_folder")
    folders_api.revert.assert_called_once_with(path=FOLDER_PATH, fingerprint="fp")


@pytest.mark.asyncio
async def test_revert_folder_without_a_fingerprint(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.revert.return_value.execute.return_value = {}

    await folders.revert_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    folders_api.revert.assert_called_once_with(path=FOLDER_PATH)


@pytest.mark.asyncio
async def test_move_entities_to_folder(
    folders: FoldersService,
    folders_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    folders_api.move_entities_to_folder.return_value.execute.return_value = ""

    result = await folders.move_entities_to_folder(
        mock_ctx,
        ACCOUNT_ID,
        CONTAINER_ID,
        WORKSPACE_ID,
        ENTITY_ID,
        None,
        ["1", "2"],
        ["3"],
        ["4"],
    )

    assert result == {
        "path": FOLDER_PATH,
        "status": "moved",
        "moved": {"tagId": ["1", "2"], "triggerId": ["3"], "variableId": ["4"]},
    }
    install_client.require_write.assert_called_once_with("move_entities_to_folder")
    folders_api.move_entities_to_folder.assert_called_once_with(
        path=FOLDER_PATH,
        body={},
        tagId=["1", "2"],
        triggerId=["3"],
        variableId=["4"],
    )


@pytest.mark.asyncio
async def test_move_entities_to_folder_with_nothing_to_move(
    folders: FoldersService, folders_api: Any, mock_ctx: AsyncMock
) -> None:
    folders_api.move_entities_to_folder.return_value.execute.return_value = ""

    result = await folders.move_entities_to_folder(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"name": "f"}
    )

    assert result["moved"] == {"tagId": [], "triggerId": [], "variableId": []}
    folders_api.move_entities_to_folder.assert_called_once_with(
        path=FOLDER_PATH, body={"name": "f"}
    )


@pytest.mark.asyncio
async def test_folders_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_folders_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_folders",
        "get_folder",
        "get_folder_entities",
        "create_folder",
        "update_folder",
        "delete_folder",
        "revert_folder",
        "move_entities_to_folder",
    }


# --------------------------------------------------------------------------
# Google tag config
# --------------------------------------------------------------------------


@pytest.fixture
def gtag() -> GtagConfigService:
    return GtagConfigService()


@pytest.fixture
def gtag_api(mock_api: Mock) -> Any:
    return workspace_child(mock_api, "gtag_config")


@pytest.mark.asyncio
async def test_list_gtag_configs(
    gtag: GtagConfigService, gtag_api: Any, mock_ctx: AsyncMock
) -> None:
    gtag_api.list.return_value.execute.return_value = {"gtagConfig": []}

    result = await gtag.list_gtag_configs(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"gtagConfig": []}
    gtag_api.list.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_list_gtag_configs_pages(
    gtag: GtagConfigService, gtag_api: Any, mock_ctx: AsyncMock
) -> None:
    gtag_api.list.return_value.execute.return_value = {}

    await gtag.list_gtag_configs(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "token"
    )

    gtag_api.list.assert_called_once_with(parent=WORKSPACE_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_get_gtag_config(
    gtag: GtagConfigService, gtag_api: Any, mock_ctx: AsyncMock
) -> None:
    gtag_api.get.return_value.execute.return_value = {"type": "googtag"}

    result = await gtag.get_gtag_config(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"type": "googtag"}
    gtag_api.get.assert_called_once_with(path=GTAG_PATH)


@pytest.mark.asyncio
async def test_create_gtag_config(
    gtag: GtagConfigService,
    gtag_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    body = {"type": "googtag"}
    gtag_api.create.return_value.execute.return_value = body

    result = await gtag.create_gtag_config(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, body
    )

    assert result == body
    install_client.require_write.assert_called_once_with("create_gtag_config")
    gtag_api.create.assert_called_once_with(parent=WORKSPACE_PATH, body=body)


@pytest.mark.asyncio
async def test_update_gtag_config(
    gtag: GtagConfigService,
    gtag_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    gtag_api.update.return_value.execute.return_value = {}

    await gtag.update_gtag_config(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"type": "g"}, "fp"
    )

    install_client.require_write.assert_called_once_with("update_gtag_config")
    gtag_api.update.assert_called_once_with(
        path=GTAG_PATH, body={"type": "g"}, fingerprint="fp"
    )


@pytest.mark.asyncio
async def test_update_gtag_config_without_a_fingerprint(
    gtag: GtagConfigService, gtag_api: Any, mock_ctx: AsyncMock
) -> None:
    gtag_api.update.return_value.execute.return_value = {}

    await gtag.update_gtag_config(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID, {"type": "g"}
    )

    gtag_api.update.assert_called_once_with(path=GTAG_PATH, body={"type": "g"})


@pytest.mark.asyncio
async def test_delete_gtag_config(
    gtag: GtagConfigService,
    gtag_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    gtag_api.delete.return_value.execute.return_value = ""

    result = await gtag.delete_gtag_config(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ENTITY_ID
    )

    assert result == {"path": GTAG_PATH, "status": "deleted"}
    install_client.require_write.assert_called_once_with("delete_gtag_config")


@pytest.mark.asyncio
async def test_gtag_config_registers_no_revert_tool() -> None:
    """This resource is the one with no revert method in the API."""
    mcp: FastMCP[Any] = FastMCP("test")
    register_gtag_config_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_gtag_configs",
        "get_gtag_config",
        "create_gtag_config",
        "update_gtag_config",
        "delete_gtag_config",
    }
    assert "revert_gtag_config" not in names


# --------------------------------------------------------------------------
# Built-in variables
# --------------------------------------------------------------------------


@pytest.fixture
def built_in() -> BuiltInVariablesService:
    return BuiltInVariablesService()


@pytest.fixture
def built_in_api(mock_api: Mock) -> Any:
    return workspace_child(mock_api, "built_in_variables")


@pytest.mark.asyncio
async def test_list_built_in_variables(
    built_in: BuiltInVariablesService, built_in_api: Any, mock_ctx: AsyncMock
) -> None:
    built_in_api.list.return_value.execute.return_value = {"builtInVariable": []}

    result = await built_in.list_built_in_variables(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    assert result == {"builtInVariable": []}
    built_in_api.list.assert_called_once_with(parent=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_list_built_in_variables_pages(
    built_in: BuiltInVariablesService, built_in_api: Any, mock_ctx: AsyncMock
) -> None:
    built_in_api.list.return_value.execute.return_value = {}

    await built_in.list_built_in_variables(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "token"
    )

    built_in_api.list.assert_called_once_with(parent=WORKSPACE_PATH, pageToken="token")


@pytest.mark.asyncio
async def test_create_built_in_variable_sends_a_list_of_types(
    built_in: BuiltInVariablesService,
    built_in_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    """'type' is repeated in the discovery document, whatever the stubs say."""
    built_in_api.create.return_value.execute.return_value = {"builtInVariable": []}

    result = await built_in.create_built_in_variable(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ["pageUrl", "clickText"]
    )

    assert result == {"builtInVariable": []}
    install_client.require_write.assert_called_once_with("create_built_in_variable")
    built_in_api.create.assert_called_once_with(
        parent=WORKSPACE_PATH, type=["pageUrl", "clickText"]
    )


@pytest.mark.asyncio
async def test_delete_built_in_variable_uses_the_collection_path(
    built_in: BuiltInVariablesService,
    built_in_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    """Delete hangs off {workspace}/built_in_variables, not the workspace."""
    built_in_api.delete.return_value.execute.return_value = ""

    result = await built_in.delete_built_in_variable(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, ["clickClasses"]
    )

    assert result == {
        "path": BUILT_IN_PATH,
        "status": "deleted",
        "type": ["clickClasses"],
    }
    install_client.require_write.assert_called_once_with("delete_built_in_variable")
    built_in_api.delete.assert_called_once_with(
        path=BUILT_IN_PATH, type=["clickClasses"]
    )


@pytest.mark.asyncio
async def test_revert_built_in_variable_uses_the_workspace_path(
    built_in: BuiltInVariablesService,
    built_in_api: Any,
    mock_ctx: AsyncMock,
    install_client: Mock,
) -> None:
    """Revert takes the workspace path and a single type, unlike delete."""
    built_in_api.revert.return_value.execute.return_value = {"enabled": True}

    result = await built_in.revert_built_in_variable(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID, "clickText"
    )

    assert result == {"enabled": True}
    install_client.require_write.assert_called_once_with("revert_built_in_variable")
    built_in_api.revert.assert_called_once_with(path=WORKSPACE_PATH, type="clickText")


@pytest.mark.asyncio
async def test_revert_built_in_variable_without_a_type(
    built_in: BuiltInVariablesService, built_in_api: Any, mock_ctx: AsyncMock
) -> None:
    built_in_api.revert.return_value.execute.return_value = {}

    await built_in.revert_built_in_variable(
        mock_ctx, ACCOUNT_ID, CONTAINER_ID, WORKSPACE_ID
    )

    built_in_api.revert.assert_called_once_with(path=WORKSPACE_PATH)


@pytest.mark.asyncio
async def test_built_in_variables_register_expected_tools() -> None:
    mcp: FastMCP[Any] = FastMCP("test")
    register_built_in_variables_tools(mcp)

    names = {tool.name for tool in await mcp.list_tools()}
    assert names == {
        "list_built_in_variables",
        "create_built_in_variable",
        "delete_built_in_variable",
        "revert_built_in_variable",
    }
