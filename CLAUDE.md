## Objective

This is `google-tag-manager-mcp`: an MCP server wrapping the **entire** Google
Tag Manager API v2.

## About the Tag Manager API

Tag Manager is a **discovery-document API**, not an SDK product. Google ships no
dedicated client library for it in any language — nothing equivalent to
`google-ads` or `google-analytics-data`. It is one of ~300 APIs served by the
generic `google-api-python-client`, whose resources are constructed dynamically
at runtime and are entirely untyped.

Static typing comes from `google-api-python-client-stubs` (dev-only), which
covers `tagmanager/v2` and supplies a `build()` overload keyed on the literal
service name.

The API is large — 106 methods across 18 resources — and consequential: a
container holds the tracking code of a live website, and publishing a version
reaches production immediately, for every visitor, with no staged rollout.

## RULES

1. `uv` for package management; see `pyproject.toml`.
2. After changes run `./scripts/typecheck.sh` (ruff + pyright + pytest). It must
   be clean: pyright is in **strict** mode and currently reports 0 errors.
3. **`uv` and Python 3.12 are not installed on this workstation.** Run the
   toolchain in Docker — the exact command is in README.md under Development.
   The image needs `libatomic1` or the Node binary pyright downloads will not
   start.
4. **Two coverage contracts, both enforced. Neither is aspirational — do not
   weaken either to land a change.**
   - *API coverage:* `src/coverage.py` maps every API method to its tool, and
     `tests/test_api_coverage.py` checks it in both directions against the
     vendored discovery document in `refs/`.
   - *Test coverage:* `src` sits at 100% statement and branch coverage, with
     `fail_under = 100` in `pyproject.toml`. Every tool also has an end-to-end
     test in `tests/test_tools.py`, and
     `test_every_registered_tool_is_exercised` fails if a tool is registered
     without one.

## Traps that have already bitten this codebase

These are not hypothetical; each one caused a failure during the initial build.

1. **`googleapiclient._apis` does not exist at runtime.** It is a stubs-only
   package. Every import of a schema type must sit under `if TYPE_CHECKING:`.

2. **FastMCP resolves tool annotations at runtime.** Annotating a tool function
   with a stub type raises `NameError` when the tool is registered. Tool
   signatures use `Dict[str, Any]`; the service layer beneath them stays
   precisely typed. The boundary is deliberate — see the comment at the top of
   each `create_*_tools` function.

3. **The Clients resource shadows the API client.** `clients_service.py` takes a
   payload argument named `client`, which collided with the usual
   `client = get_client()` and sent a `TagManagerClient` as the request body.
   That module names its local `api_client`. The end-to-end tests caught it; do
   not "tidy" it back.

4. **`google-api-python-client` serialises whatever it is handed.** Passing
   `pageToken=None` puts a literal `pageToken=None` on the query string instead
   of omitting it. Every optional parameter goes through `src.utils.optional`,
   which drops `None` while keeping `False` and `""` — both meaningful values to
   this API.

5. **The stubs are not always right.** They type `built_in_variables`' `type`
   parameter as a single `Literal` where the discovery document marks it
   repeated. The discovery document wins at runtime, so lists are sent; they
   pass pyright because `optional()` returns `Dict[str, Any]`.

6. **An empty response serialises to `data=None`.** A tool returning `{}` comes
   back from an MCP client as `structured_content={}` with `data` unset, so
   end-to-end assertions check `is_error` rather than `data`.

7. **Registration accumulates on the module-level `mcp`.** A test asserting that
   a group did *not* register something must monkeypatch `main.mcp` with a fresh
   `FastMCP` — see the `isolated_server` fixture.

8. **Coverage cannot instrument `main.py`.** Constructing a FastMCP instance
   inside a coverage-instrumented module makes `cryptography`'s Rust bindings
   reject a `SHA256` that Python-level `isinstance` accepts. Hence
   `source = ["src"]` in `pyproject.toml`, and coverage runs as
   `.venv/bin/python -m pytest`, not `uv run pytest`. `main.py` is covered
   end-to-end by `tests/test_api_coverage.py` and `tests/test_tools.py`.

## Design decisions worth preserving

- **Tools take IDs, not paths.** Tag Manager validates relative paths against a
  regex before any permission check, so a malformed identifier surfaces as a
  confusing 400 or 404. `src/paths.py` assembles and validates every path in one
  place. It accepts the API's own `collection/id` spelling but refuses a longer
  path rather than guessing which segment was meant.

- **No prefixed sub-server mounts.** The Ads server mounts prefixed sub-servers
  because it has hundreds of same-named service tools. Every tool name here is
  already unique, so that indirection would only turn `list_tags` into
  `tags_list_tags`. `test_every_method_maps_to_a_distinct_tool` keeps it that
  way.

- **`--groups` is load-bearing, not a nicety.** An MCP client pays for every tool
  description in its context on every request, and there are 112. The `web`
  preset exists because most containers are web containers and never touch
  `clients`, `transformations` or `zones`.

- **Nothing executes at import time in `main.py`.** Argument parsing, credential
  loading and registration all sit behind `main()`, so tests can import the
  module and assert against the real server.

- **Blocking calls go through `asyncio.to_thread`.** The discovery client is
  synchronous; `src/services/base.py::execute` keeps it off the event loop and
  centralises error handling, including the per-status hints in `STATUS_HINTS`.

- **`publish_workspace` defaults `publish` to false.** Creating a version and
  releasing it are two different decisions, and the tool refuses to publish a
  version that failed to compile.

- **`TAG_MANAGER_READ_ONLY`** requests only the readonly scope and refuses every
  mutation. It matters more here than on most Google APIs, because the blast
  radius of a mistaken write is a live site's tracking.

- **The five same-shaped entity modules are generated from one template.**
  `tags_service.py` is the hand-written reference; `triggers`, `variables`,
  `clients`, `transformations` and `zones` were emitted from a spec so the
  plumbing cannot drift between them. The output is ordinary committed source —
  edit it directly, and keep the six in step, which
  `tests/test_workspace_entities.py` checks by parametrising over all of them.

## Where things live

- `src/coverage.py` — the API-method-to-tool map, plus `CONVENIENCE_TOOLS` and
  `QUIRKS`. Any new tool must be declared here or the coverage test fails.
- `src/services/insights_service.py` — the six task-shaped tools. Everything
  here composes several API calls; nothing maps 1:1.
- `refs/tagmanager.v2.discovery.json` — the vendored contract. Refresh with
  `scripts/refresh_discovery.py`, which prints exactly which methods changed.
