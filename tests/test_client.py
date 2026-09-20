"""Tests for credential resolution, scopes and the read-only gate."""

from __future__ import annotations

import os
from typing import Iterator
from unittest.mock import Mock, patch

import pytest

from src.client import (
    SCOPE_READONLY,
    SCOPES_FULL,
    ReadOnlyError,
    TagManagerClient,
    get_client,
    set_client,
)

OAUTH_VARS = (
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_TAG_MANAGER_REFRESH_TOKEN",
    "TAG_MANAGER_READ_ONLY",
)


@pytest.fixture
def clean_env() -> Iterator[None]:
    """Run with none of the client's environment variables set."""
    saved = {name: os.environ.pop(name, None) for name in OAUTH_VARS}
    yield
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_read_only_defaults_to_false(clean_env: None) -> None:
    assert TagManagerClient().read_only is False


def test_read_only_reads_the_environment(clean_env: None) -> None:
    os.environ["TAG_MANAGER_READ_ONLY"] = "true"
    assert TagManagerClient().read_only is True


def test_read_only_argument_beats_the_environment(clean_env: None) -> None:
    os.environ["TAG_MANAGER_READ_ONLY"] = "true"
    assert TagManagerClient(read_only=False).read_only is False


def test_scopes_narrow_to_readonly_in_read_only_mode(clean_env: None) -> None:
    assert TagManagerClient(read_only=True).scopes == [SCOPE_READONLY]


def test_scopes_cover_every_write_scope_otherwise(clean_env: None) -> None:
    scopes = TagManagerClient(read_only=False).scopes
    assert scopes == SCOPES_FULL
    # Tag Manager splits write access six ways; a token missing any of these
    # cannot reach part of the API.
    assert len(scopes) == 7


def test_scopes_are_a_copy_callers_cannot_mutate(clean_env: None) -> None:
    client = TagManagerClient(read_only=False)
    client.scopes.append("https://example.com/extra")
    assert "https://example.com/extra" not in client.scopes


def test_resolve_credentials_prefers_an_oauth_refresh_token(clean_env: None) -> None:
    os.environ["GOOGLE_CLIENT_ID"] = "id"
    os.environ["GOOGLE_CLIENT_SECRET"] = "secret"
    os.environ["GOOGLE_TAG_MANAGER_REFRESH_TOKEN"] = "refresh"

    credentials = TagManagerClient(read_only=True).resolve_credentials()

    assert credentials.refresh_token == "refresh"  # type: ignore[attr-defined]
    assert credentials.client_id == "id"  # type: ignore[attr-defined]


def test_resolve_credentials_falls_back_to_adc(clean_env: None) -> None:
    os.environ["GOOGLE_CLIENT_ID"] = "id"
    # Secret and refresh token are absent, so the OAuth path must not be taken.
    sentinel = Mock()
    with patch("google.auth.default", return_value=(sentinel, "project")) as default:
        credentials = TagManagerClient(read_only=True).resolve_credentials()

    assert credentials is sentinel
    default.assert_called_once_with(scopes=[SCOPE_READONLY])


def test_service_is_built_once_and_cached(clean_env: None) -> None:
    client = TagManagerClient(read_only=True)
    built = Mock()
    with (
        patch("src.client.build", return_value=built) as build,
        patch.object(client, "resolve_credentials", return_value=Mock()),
    ):
        assert client.service is built
        assert client.service is built

    build.assert_called_once()
    assert build.call_args.args == ("tagmanager", "v2")
    assert build.call_args.kwargs["cache_discovery"] is False


def test_require_write_passes_when_writable() -> None:
    TagManagerClient(read_only=False).require_write("create_tag")


def test_require_write_refuses_in_read_only_mode() -> None:
    with pytest.raises(ReadOnlyError, match="TAG_MANAGER_READ_ONLY"):
        TagManagerClient(read_only=True).require_write("create_tag")


def test_close_releases_the_service_and_the_next_use_rebuilds(
    clean_env: None,
) -> None:
    client = TagManagerClient(read_only=True)
    built = Mock()
    with (
        patch("src.client.build", return_value=built) as build,
        patch.object(client, "resolve_credentials", return_value=Mock()),
    ):
        _ = client.service
        client.close()
        built.close.assert_called_once()

        # The next access must build afresh rather than hand back a client
        # whose transport has been closed.
        _ = client.service
        assert build.call_count == 2


def test_close_is_a_no_op_when_nothing_was_built() -> None:
    client = TagManagerClient(read_only=True)
    with patch("src.client.build") as build:
        client.close()
    build.assert_not_called()


def test_get_client_requires_initialization() -> None:
    set_client(None)
    with pytest.raises(RuntimeError, match="Client not initialized"):
        get_client()


def test_set_and_get_client_round_trip() -> None:
    client = TagManagerClient(read_only=True)
    set_client(client)
    assert get_client() is client
    set_client(None)
