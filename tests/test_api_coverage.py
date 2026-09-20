"""Verifies the claim that this server covers the Tag Manager API completely.

Checked in both directions against the vendored discovery document:

- every method Google publishes is declared in src/coverage.py and registered as
  a tool, so a method added in a future revision breaks the build;
- every registered tool is accounted for as either an API method or a declared
  convenience tool, so nothing undocumented creeps in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Set

import pytest
from fastmcp import FastMCP

import main
from src.coverage import API_COVERAGE, CONVENIENCE_TOOLS, QUIRKS

DISCOVERY_PATH = (
    Path(__file__).resolve().parent.parent / "refs" / "tagmanager.v2.discovery.json"
)


def discovery_document() -> Dict[str, Any]:
    return json.loads(DISCOVERY_PATH.read_text())


def discovery_methods() -> Set[str]:
    """Every method path in the discovery document, e.g. 'accounts.list'."""
    found: Set[str] = set()

    def walk(resources: Dict[str, Any], prefix: str = "") -> None:
        for name, resource in resources.items():
            path = f"{prefix}{name}"
            for method in resource.get("methods") or {}:
                found.add(f"{path}.{method}")
            walk(resource.get("resources") or {}, f"{path}.")

    walk(discovery_document().get("resources") or {})
    return found


async def registered_tool_names() -> Set[str]:
    main.register_groups("all")
    return {tool.name for tool in await main.mcp.list_tools()}


@pytest.fixture
def isolated_server(monkeypatch: pytest.MonkeyPatch) -> FastMCP[Any]:
    """Swap main.mcp for an empty server.

    Registration accumulates on the module-level instance, so asserting that a
    group did NOT register something needs a server nothing else has touched.
    """
    server: FastMCP[Any] = FastMCP("isolated")
    monkeypatch.setattr(main, "mcp", server)
    return server


def test_discovery_document_is_present_and_current() -> None:
    document = discovery_document()
    assert document["name"] == "tagmanager"
    assert document["version"] == "v2"
    assert document["revision"]


def test_every_api_method_is_declared() -> None:
    """A method added by Google fails here until it is mapped and implemented."""
    undeclared = discovery_methods() - set(API_COVERAGE)
    assert not undeclared, (
        f"Tag Manager API methods with no declared tool: {sorted(undeclared)}. "
        "Implement them, map them in src/coverage.py, then re-run."
    )


def test_no_declared_method_has_been_removed() -> None:
    """A mapping left behind after Google drops a method fails here."""
    stale = set(API_COVERAGE) - discovery_methods()
    assert not stale, (
        f"Declared methods no longer in the API: {sorted(stale)}. "
        "Remove them from src/coverage.py."
    )


def test_coverage_is_exactly_one_hundred_percent() -> None:
    assert discovery_methods() == set(API_COVERAGE)
    assert len(API_COVERAGE) == 106


def test_every_method_maps_to_a_distinct_tool() -> None:
    """Two methods sharing a tool name would hide one of them."""
    names = list(API_COVERAGE.values())
    assert len(names) == len(set(names))


def test_api_tools_and_convenience_tools_do_not_overlap() -> None:
    assert not set(API_COVERAGE.values()) & set(CONVENIENCE_TOOLS)


@pytest.mark.asyncio
async def test_every_declared_method_is_registered_as_a_tool() -> None:
    tools = await registered_tool_names()
    missing = {
        method: tool for method, tool in API_COVERAGE.items() if tool not in tools
    }
    assert not missing, f"Declared tools that are not registered: {missing}"


@pytest.mark.asyncio
async def test_no_undocumented_tools() -> None:
    tools = await registered_tool_names()
    documented = set(API_COVERAGE.values()) | set(CONVENIENCE_TOOLS)
    undocumented = tools - documented
    assert not undocumented, (
        f"Tools missing from src/coverage.py: {sorted(undocumented)}"
    )


@pytest.mark.asyncio
async def test_convenience_tools_all_exist() -> None:
    tools = await registered_tool_names()
    missing = set(CONVENIENCE_TOOLS) - tools
    assert not missing, f"Declared convenience tools not registered: {sorted(missing)}"


@pytest.mark.asyncio
async def test_the_full_tool_count_is_what_the_readme_claims() -> None:
    tools = await registered_tool_names()
    assert len(tools) == len(API_COVERAGE) + len(CONVENIENCE_TOOLS) == 112


def test_documented_quirks_refer_to_real_methods() -> None:
    """A quirk describing a method that no longer exists is stale documentation."""
    for method in QUIRKS:
        assert method in API_COVERAGE


@pytest.mark.asyncio
async def test_group_selection_registers_only_that_group(
    isolated_server: FastMCP[Any],
) -> None:
    assert main.register_groups("tags") == 1
    tools = {tool.name for tool in await isolated_server.list_tools()}
    assert "list_tags" in tools
    assert "list_zones" not in tools


@pytest.mark.asyncio
async def test_the_web_preset_registers_the_web_container_groups(
    isolated_server: FastMCP[Any],
) -> None:
    main.register_groups("web")
    tools = {tool.name for tool in await isolated_server.list_tools()}
    assert {"list_tags", "list_triggers", "list_variables"} <= tools
    # Server-side and 360-only resources are deliberately left out.
    assert "list_clients" not in tools
    assert "list_zones" not in tools


def test_resolve_groups_expands_the_presets() -> None:
    assert main.resolve_groups("all") == list(main.TOOL_GROUPS)
    assert main.resolve_groups("web") == main.WEB_GROUPS
    assert main.resolve_groups("tags, triggers ") == ["tags", "triggers"]
    assert main.resolve_groups(",,") == []


def test_every_web_preset_group_exists() -> None:
    unknown = set(main.WEB_GROUPS) - set(main.TOOL_GROUPS)
    assert not unknown, f"WEB_GROUPS names a group that does not exist: {unknown}"


def test_unknown_group_is_ignored() -> None:
    assert main.register_groups("nonsense") == 0


def test_parse_arguments_defaults_to_all() -> None:
    assert main.parse_arguments([]).groups == "all"
    assert main.parse_arguments(["--groups", "tags"]).groups == "tags"
