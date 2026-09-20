# Google Tag Manager MCP Server

An MCP server covering the **entire Google Tag Manager API v2** — all 106
published methods, plus task-shaped tools on top for the workflows people
actually run against a container.

## Overview

This project provides a Model Context Protocol server that wraps the Google Tag
Manager API v2, letting LLMs read and write accounts, containers, workspaces,
tags, triggers, variables, versions and permissions through a standardised
interface.

Tag Manager ships no official SDK in any language, so this is built on the
generic `google-api-python-client` with complete static types supplied by
`google-api-python-client-stubs`. See
[Why there is no Tag Manager SDK](#why-there-is-no-tag-manager-sdk).

## Features

- **Complete API Coverage**: all 106 published API methods, enforced by a test rather than claimed
- **Full Type Safety**: strict `pyright` with 0 errors
- **100% Test Coverage**: 383 tests, 100% statement and branch coverage, floor enforced in config
- **Task-Shaped Tools**: 6 convenience tools on top of the raw API
- **ID-Based Addressing**: tools take account/container/workspace IDs; relative paths are assembled and validated for you
- **MCP Compliant**: FastMCP 4, stdio transport
- **Async Throughout**: the synchronous Google client is dispatched off the event loop
- **Read-Only Mode**: an opt-in switch that refuses every mutating call

## Installation

```bash
git clone https://github.com/rgellis/google-tag-manager-mcp.git
cd google-tag-manager-mcp

# Install dependencies using uv
uv sync
```

Requires Python 3.12+.

### 1. Enable the API

The Tag Manager API must be enabled on the Google Cloud project that owns your
OAuth client:

```bash
gcloud services enable tagmanager.googleapis.com --project=<project>
```

### 2. Create an OAuth client

In the Google Cloud console, create an OAuth 2.0 client of type **Desktop app**
(or **Web application** with `http://localhost` as an authorised redirect URI).
Note the client ID and secret.

### 3. Mint a refresh token

```bash
GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." \
  uv run scripts/get_refresh_token.py

# or, if this server will only ever read:
GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." \
  uv run scripts/get_refresh_token.py --read-only
```

Sign in as an account with access to the Tag Manager containers you need. The
script prints the refresh token.

Scope the token to this server alone rather than reusing one minted for other
Google APIs — re-consenting a shared token to add the Tag Manager scopes rotates
a secret everything else using it depends on.

### 4. Set credentials

```bash
export GOOGLE_CLIENT_ID="your_client_id"
export GOOGLE_CLIENT_SECRET="your_client_secret"
export GOOGLE_TAG_MANAGER_REFRESH_TOKEN="token_from_step_3"

# optional: request only the readonly scope and refuse all mutations
export TAG_MANAGER_READ_ONLY=false
```

If those three are not all set, the client falls back to Application Default
Credentials, which covers a service account via `GOOGLE_APPLICATION_CREDENTIALS`
as well as local `gcloud` auth.

### 5. Verify

```bash
uv run main.py --groups accounts
```

Then call `check_client_status`, which reports whether credentials resolve, the
scopes in use, and whether read-only mode is active — without spending API quota.

## Usage

```bash
uv run main.py                          # all 112 tools, over stdio
uv run main.py --groups web             # the web-container subset
uv run main.py --groups tags,triggers   # a specific subset
```

Groups: `accounts`, `user-permissions`, `containers`, `destinations`,
`environments`, `versions`, `workspaces`, `tags`, `triggers`, `variables`,
`built-in-variables`, `folders`, `templates`, `clients`, `transformations`,
`zones`, `gtag-config`, `insights`.

`--groups` matters more here than on a small API. An MCP client pays for every
tool description in its context on every request, and 112 of them is a lot to
carry when the task is "read the tags in this container". `web` is a useful
default for web containers: accounts, containers, workspaces, versions, tags,
triggers, variables, built-in variables, folders and the task-shaped tools,
leaving out the server-side (`clients`, `transformations`) and 360-only
(`zones`) resources.

### With an MCP client

```json
{
  "mcpServers": {
    "tag-manager": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/google-tag-manager-mcp", "main.py", "--groups", "web"],
      "env": {
        "GOOGLE_CLIENT_ID": "...",
        "GOOGLE_CLIENT_SECRET": "...",
        "GOOGLE_TAG_MANAGER_REFRESH_TOKEN": "..."
      }
    }
  }
}
```

### Identifiers

Every Tag Manager resource is addressed by a relative path such as
`accounts/6000000000/containers/7000000/workspaces/3/tags/42`, and the API
validates each one against a regex — a path of the wrong shape is rejected
before any permission check, so a malformed ID surfaces as a confusing 400 or
404 rather than "you got the shape wrong".

Tools therefore take the individual IDs and assemble the path for you:

```
get_tag(account_id="6000000000", container_id="7000000",
        workspace_id="3", tag_id="42")
```

The API's own `collection/id` spelling is accepted too (`account_id="accounts/6000000000"`),
since that is what you have to hand when copying an ID out of a previous
response. A longer path is rejected rather than silently truncated — guessing
which segment was meant is how you end up writing to the wrong container.

Starting from a `GTM-XXXXXXX` off a website with no account ID? Call
`lookup_container`, the one read that needs no account.

### The Tag Manager model, in four sentences

An **account** holds **containers**; a container is what a site loads. Edits
happen in a **workspace**, which is a draft branch — nothing in one affects the
live site. Turning a workspace into a **version** freezes its entities and
consumes the workspace. Publishing a version is what reaches production, and it
does so immediately, for every visitor.

`publish_workspace` performs the last two steps and defaults `publish` to
`false`, so creating a version is never silently a release.

## Feature Parity Table

Implementation status of Google Tag Manager API v2 methods (discovery revision
20260916). All 106 methods are implemented; the table groups them by resource.

| Tools | Category | API Methods | Implemented | Test Coverage | Notes |
| --- | --- | --- | --- | --- | --- |
| `list_accounts`, `get_account`, `update_account` | Accounts | `accounts.*` (3) | ✅ Yes | ✅ Yes | Start here for account IDs |
| `list_user_permissions`, `get_user_permission`, `create_user_permission`, `update_user_permission`, `delete_user_permission` | User Permissions | `accounts.user_permissions.*` (5) | ✅ Yes | ✅ Yes | Update takes no fingerprint |
| `list_containers`, `get_container`, `lookup_container`, `get_container_snippet`, `create_container`, `update_container`, `delete_container`, `combine_containers`, `move_tag_id` | Containers | `accounts.containers.*` (9) | ✅ Yes | ✅ Yes | `lookup_container` needs no account ID |
| `list_destinations`, `get_destination`, `link_destination` | Destinations | `...destinations.*` (3) | ✅ Yes | ✅ Yes | Linking moves, it does not copy |
| `list_environments`, `get_environment`, `create_environment`, `update_environment`, `delete_environment`, `reauthorize_environment` | Environments | `...environments.*` (6) | ✅ Yes | ✅ Yes | Reauthorize rotates the preview code |
| `list_version_headers`, `get_latest_version_header` | Version Headers | `...version_headers.*` (2) | ✅ Yes | ✅ Yes | Cheap history, no entity payload |
| `get_version`, `get_live_version`, `update_version`, `delete_version`, `undelete_version`, `publish_version`, `set_latest_version` | Versions | `...versions.*` (7) | ✅ Yes | ✅ Yes | ⚠️ `publish_version` hits production |
| `list_workspaces`, `get_workspace`, `get_workspace_status`, `create_workspace`, `update_workspace`, `delete_workspace`, `sync_workspace`, `resolve_workspace_conflict`, `quick_preview_workspace`, `create_version`, `bulk_update_workspace` | Workspaces | `...workspaces.*` (11) | ✅ Yes | ✅ Yes | `create_version` consumes the workspace |
| `list_tags`, `get_tag`, `create_tag`, `update_tag`, `delete_tag`, `revert_tag` | Tags | `...tags.*` (6) | ✅ Yes | ✅ Yes | Update replaces, it does not merge |
| `list_triggers`, `get_trigger`, `create_trigger`, `update_trigger`, `delete_trigger`, `revert_trigger` | Triggers | `...triggers.*` (6) | ✅ Yes | ✅ Yes | Referenced by tag `firingTriggerId` |
| `list_variables`, `get_variable`, `create_variable`, `update_variable`, `delete_variable`, `revert_variable` | Variables | `...variables.*` (6) | ✅ Yes | ✅ Yes | User-defined variables only |
| `list_built_in_variables`, `create_built_in_variable`, `delete_built_in_variable`, `revert_built_in_variable` | Built-In Variables | `...built_in_variables.*` (4) | ✅ Yes | ✅ Yes | Addressed by type, not ID; three distinct paths |
| `list_folders`, `get_folder`, `get_folder_entities`, `create_folder`, `update_folder`, `delete_folder`, `revert_folder`, `move_entities_to_folder` | Folders | `...folders.*` (8) | ✅ Yes | ✅ Yes | `get_folder_entities` is a POST that reads |
| `list_templates`, `get_template`, `create_template`, `update_template`, `delete_template`, `revert_template`, `import_template_from_gallery` | Templates | `...templates.*` (7) | ✅ Yes | ✅ Yes | Gallery import needs explicit permission ack |
| `list_clients`, `get_client`, `create_client`, `update_client`, `delete_client`, `revert_client` | Clients | `...clients.*` (6) | ✅ Yes | ✅ Yes | Server containers only |
| `list_transformations`, `get_transformation`, `create_transformation`, `update_transformation`, `delete_transformation`, `revert_transformation` | Transformations | `...transformations.*` (6) | ✅ Yes | ✅ Yes | Server containers only |
| `list_zones`, `get_zone`, `create_zone`, `update_zone`, `delete_zone`, `revert_zone` | Zones | `...zones.*` (6) | ✅ Yes | ✅ Yes | Tag Manager 360 only |
| `list_gtag_configs`, `get_gtag_config`, `create_gtag_config`, `update_gtag_config`, `delete_gtag_config` | Google Tag Config | `...gtag_config.*` (5) | ✅ Yes | ✅ Yes | The only entity with no revert method |
| `list_workspace_entities`, `find_entities_by_name`, `summarize_container`, `list_all_containers`, `publish_workspace` | Task-Shaped | *(compose several methods)* | ✅ Yes | ✅ Yes | See below |
| `check_client_status` | Diagnostics | *(no API call)* | ✅ Yes | ✅ Yes | Credential state; spends no quota |

### Task-shaped tools

Nothing here maps one-to-one onto an API method. Each exists because the raw API
makes a common task take several round trips that have to be sequenced
correctly.

| Tool | Composes | Why |
| --- | --- | --- |
| `list_workspace_entities` | `tags.list`, `triggers.list`, `variables.list`, `folders.list`, each paged to exhaustion | Reading a container's setup is four paginated calls |
| `find_entities_by_name` | the same four, filtered by name | The API has no search; turns "the purchase tag" into an ID |
| `summarize_container` | `containers.get`, `workspaces.list`, `versions.live` | "What is this container and what is it running" |
| `list_all_containers` | `accounts.list`, then `containers.list` per account | "What do I have access to", in one call |
| `publish_workspace` | `workspaces.create_version`, then `versions.publish` | The release flow, with `publish` defaulting to false |

### Summary Statistics

- **API Methods Implemented**: 106 out of 106 Tag Manager API v2 methods (**100%**)
- **Total Tools**: 112 (106 API methods + 6 convenience tools)
- **Tools with Tests**: 112 (**100% tool coverage**, enforced end to end)
- **Line & Branch Coverage**: **100%** across `src` (1,471 statements, 94 branches), enforced by `fail_under = 100`
- **Test Count**: 383
- **Type Safety**: `pyright` strict, 0 errors

### Implementation Highlights

1. ✅ **Complete API Surface**: every published method across all 18 resources
2. ✅ **Coverage Enforced, Not Claimed**: `tests/test_api_coverage.py` diffs the implementation against the vendored discovery document in both directions
3. ✅ **End-to-End Tool Tests**: every one of the 112 tools is invoked through a real MCP client, and `test_every_registered_tool_is_exercised` fails if a tool is added without one
4. ✅ **Paths Built, Not Pasted**: relative paths are assembled from IDs in one place and validated, so a malformed identifier fails with a clear message instead of a 404
5. ✅ **Publishing Is Explicit**: `publish_workspace` will not release unless asked, and never publishes a version that failed to compile

### Key Features

- **Typed Discovery Client**: complete static types from `google-api-python-client-stubs`
- **Off-Loop Execution**: the synchronous Google client is dispatched via `asyncio.to_thread`, so it never blocks the MCP event loop
- **Uniform Error Translation**: one `execute()` helper turns `HttpError` into a readable message, with per-status hints — a 400 usually means a stale fingerprint, a 404 usually means the wrong ID
- **Lazy Client Initialisation**: credentials resolve on first use, so the server starts even when misconfigured and `check_client_status` can say why
- **Read-Only Mode**: `TAG_MANAGER_READ_ONLY=true` requests the readonly scope and refuses every mutation

### Scopes

Tag Manager splits write access six ways, so a token covering the whole API has
to carry all of them. `TAG_MANAGER_READ_ONLY=true` requests only the first.

| Scope | Needed for |
| --- | --- |
| `tagmanager.readonly` | Every read |
| `tagmanager.edit.containers` | Editing containers and workspace entities |
| `tagmanager.edit.containerversions` | Creating, editing and deleting versions |
| `tagmanager.delete.containers` | Deleting containers and workspaces |
| `tagmanager.manage.accounts` | Updating account settings |
| `tagmanager.manage.users` | User permissions |
| `tagmanager.publish` | Publishing versions, reauthorizing environments |

A 403 from a call whose read equivalent works usually means the token is missing
one of these, not that the user lacks permission.

### API quirks worth knowing

These are published behaviours, implemented as published and documented in
`src/coverage.py` under `QUIRKS` rather than worked around:

- **`built_in_variables`** is addressed by type rather than ID, takes a list of
  types on create and delete but a single type on revert, and uses three
  different paths across its four methods.
- **`folders.entities`** is a POST that reads. It is not gated by read-only mode.
- **`environments.reauthorize`** and **`folders.move_entities_to_folder`**
  require a request body they make no use of; an empty object is sent when you
  supply none.
- **`gtag_config`** is the only workspace entity with no revert method.
- **Fingerprints** are Tag Manager's optimistic concurrency control. Every entity
  carries one, and passing it to an update rejects the write if the entity
  changed since you read it. A 400 mentioning a fingerprint means re-read and
  retry, not malformed input.

## Why there is no Tag Manager SDK

Tag Manager is a *discovery-document* API. Google ships no dedicated client
library for it in any language — no equivalent of `google-ads` or
`google-analytics-data`. It is one of ~300 APIs served by the generic
`google-api-python-client`, whose resources are built dynamically at runtime and
are entirely untyped.

Other languages fare better, because their generic clients generate code at build
time into per-API packages: Go has `google.golang.org/api/tagmanager/v2`, Java
has `google-api-services-tagmanager`, .NET has `Google.Apis.TagManager.v2`, and
Node's `googleapis` ships `Schema$*` TypeScript interfaces. Python is the
outlier — its client parses the discovery document at runtime, so there is
nothing to type-check.

That would normally rule out strict type checking. The way out is
`google-api-python-client-stubs`, which covers `tagmanager/v2` completely, with a
`build()` overload keyed on the literal service name. It is a dev-only
dependency — stubs never ship at runtime, so if it goes stale the cost is
type-checking, not functionality.

Three consequences to know before editing:

- `src/client.py` imports `TagManagerResource` under `if TYPE_CHECKING:`. The
  `googleapiclient._apis` package **does not exist at runtime**; that guard must stay.
- FastMCP resolves tool annotations at runtime, so tool signatures use
  `Dict[str, Any]` while the service layer beneath stays precisely typed.
  Annotating a tool with a stub type raises `NameError` at registration.
- The stubs are not always right. They type `built_in_variables`' `type`
  parameter as a single `Literal` where the discovery document marks it
  repeated. The discovery document is authoritative at runtime, so lists are
  sent.

## Testing

```bash
# Run tests
uv run pytest

# Run tests with coverage (must stay at 100%)
.venv/bin/python -m pytest --cov --cov-report=term-missing

# Run type checking
uv run pyright

# Run code formatting
uv run ruff format .

# Everything at once
./scripts/typecheck.sh
```

Coverage is invoked as `.venv/bin/python -m pytest` rather than `uv run pytest`
for one reason, documented in `pyproject.toml`: constructing a FastMCP instance
inside a coverage-instrumented module trips a type check in `cryptography`'s Rust
bindings, so `main.py` is excluded from the measured source set and covered
end-to-end by `tests/test_api_coverage.py` and `tests/test_tools.py` instead.

### Development without a local toolchain

`uv` and Python 3.12 are not required on the workstation. The whole toolchain
runs in Docker:

```bash
docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  bash -c 'apt-get update -qq && apt-get install -y -qq libatomic1 \
           && pip install -q uv && uv sync --extra dev && ./scripts/typecheck.sh'
```

`libatomic1` is needed by the Node binary `pyright` downloads; without it
`pyright` fails with a shared-library error rather than a type error.

### Test layout

| File | Covers |
| --- | --- |
| `test_tools.py` | Every one of the 112 tools invoked through a real MCP client, end to end |
| `test_api_coverage.py` | The API coverage contract, both directions, plus group selection |
| `test_workspace_entities.py` | The six resources sharing the CRUD+revert shape, parametrised |
| `test_special_entities.py` | Templates, folders, gtag config and built-in variables |
| `test_accounts_service.py` | Accounts and user permissions |
| `test_containers_service.py` | Containers and destinations |
| `test_environments_service.py` | Environments |
| `test_versions_service.py` | Versions and version headers |
| `test_workspaces_service.py` | Workspaces, sync, conflicts, version creation |
| `test_insights_service.py` | Pagination, name search, container summary, the release flow |
| `test_client.py` | Credential resolution, scopes, read-only gate, lifecycle |
| `test_base.py` | Error translation, status hints, off-loop dispatch |
| `test_paths.py` | Relative path construction and identifier validation |
| `test_utils.py` | Logging, dotenv, env flags, optional-parameter handling |

### When Google revises the API

```bash
uv run scripts/refresh_discovery.py
uv run pytest tests/test_api_coverage.py
```

`refresh_discovery.py` prints exactly which methods were added or removed. A new
method fails `test_every_api_method_is_declared` until it is implemented and
mapped in `src/coverage.py`. A removed one fails
`test_no_declared_method_has_been_removed`. That failure is the intended alarm —
do not weaken the test.

## Repository layout

```
src/client.py            credentials, typed discovery client, read-only gate
src/coverage.py          API method -> tool mapping; the coverage contract
src/paths.py             relative path construction and identifier validation
src/services/            one module per API resource
src/services/base.py     off-loop dispatch and error translation
src/services/insights_service.py   the task-shaped tools
refs/                    vendored discovery document
scripts/                 token minting, discovery refresh, checks
tests/                   383 tests, 100% coverage
main.py                  stdio MCP server
```

## Contributing

Contributions are welcome. Please ensure:

1. All code has proper type annotations
2. Tests are added for new functionality — coverage must stay at 100%
3. Code passes `uv run pyright` with no errors
4. Code is formatted with `uv run ruff format`
5. Any new API method is mapped in `src/coverage.py`

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This is an unofficial integration and is not affiliated with or endorsed by
Google. Tag Manager API quotas apply. Publishing a container version takes effect
on the live site immediately — `TAG_MANAGER_READ_ONLY=true` exists for a reason.
