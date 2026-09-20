"""Tests for Tag Manager relative path construction."""

from __future__ import annotations

import pytest

from src.paths import (
    account_path,
    built_in_variables_path,
    container_child_path,
    container_path,
    destination_path,
    environment_path,
    segment,
    user_permission_path,
    version_path,
    workspace_child_path,
    workspace_path,
)


def test_segment_accepts_a_bare_identifier() -> None:
    assert segment("123", "account_id") == "123"
    assert segment("  123  ", "account_id") == "123"
    assert segment("/123/", "account_id") == "123"


def test_segment_accepts_the_apis_own_collection_spelling() -> None:
    assert segment("accounts/123", "account_id", "accounts") == "123"
    assert segment("tags/9", "tag_id", "tags") == "9"


def test_segment_rejects_an_empty_value() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        segment("   ", "account_id")


def test_segment_rejects_a_path_it_cannot_reduce() -> None:
    with pytest.raises(ValueError, match="must be a bare identifier"):
        segment("accounts/123/containers/456", "account_id", "accounts")


def test_segment_rejects_a_mismatched_collection() -> None:
    with pytest.raises(ValueError, match="must be a bare identifier"):
        segment("containers/456", "account_id", "accounts")


def test_segment_rejects_a_path_when_no_collection_is_given() -> None:
    with pytest.raises(ValueError, match="must be a bare identifier"):
        segment("accounts/123", "account_id")


def test_account_and_container_paths() -> None:
    assert account_path("123") == "accounts/123"
    assert container_path("123", "456") == "accounts/123/containers/456"
    assert container_path("accounts/123", "containers/456") == (
        "accounts/123/containers/456"
    )


def test_workspace_path() -> None:
    assert workspace_path("1", "2", "3") == "accounts/1/containers/2/workspaces/3"


def test_container_child_path() -> None:
    assert container_child_path("1", "2", "versions", "9", "version_id") == (
        "accounts/1/containers/2/versions/9"
    )


def test_workspace_child_path() -> None:
    assert workspace_child_path("1", "2", "3", "tags", "9", "tag_id") == (
        "accounts/1/containers/2/workspaces/3/tags/9"
    )


def test_workspace_child_path_rejects_an_unknown_collection() -> None:
    with pytest.raises(ValueError, match="Unknown workspace collection"):
        workspace_child_path("1", "2", "3", "widgets", "9", "widget_id")


def test_built_in_variables_path_has_no_entity_id() -> None:
    assert built_in_variables_path("1", "2", "3") == (
        "accounts/1/containers/2/workspaces/3/built_in_variables"
    )


def test_named_container_child_paths() -> None:
    assert destination_path("1", "2", "AW-9") == (
        "accounts/1/containers/2/destinations/AW-9"
    )
    assert environment_path("1", "2", "5") == "accounts/1/containers/2/environments/5"
    assert version_path("1", "2", "7") == "accounts/1/containers/2/versions/7"


def test_user_permission_path() -> None:
    assert user_permission_path("1", "8") == "accounts/1/user_permissions/8"
    assert user_permission_path("1", "user_permissions/8") == (
        "accounts/1/user_permissions/8"
    )
