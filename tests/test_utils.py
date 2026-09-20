"""Tests for the shared helpers."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from src.utils import env_flag, get_logger, load_dotenv, optional


def test_get_logger_adds_a_stderr_handler_when_there_is_none() -> None:
    """The handler-adding branch, with the root logger's own handlers removed.

    pytest attaches handlers to the root logger, and `hasHandlers()` walks up
    to it, so without this the branch never runs under the test suite.
    """
    root = logging.getLogger()
    saved = root.handlers[:]
    root.handlers = []
    try:
        logger = get_logger("tests.utils.fresh")
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        # stdout is the MCP stdio transport; logs must never go there.
        assert handler.stream is sys.stderr
    finally:
        root.handlers = saved
        logging.getLogger("tests.utils.fresh").handlers = []


def test_get_logger_does_not_add_a_second_handler() -> None:
    root = logging.getLogger()
    saved = root.handlers[:]
    root.handlers = []
    try:
        logger = get_logger("tests.utils.repeat")
        again = get_logger("tests.utils.repeat")
        assert again is logger
        assert len(again.handlers) == 1
    finally:
        root.handlers = saved
        logging.getLogger("tests.utils.repeat").handlers = []


def test_load_dotenv_ignores_a_missing_file(tmp_path: Path) -> None:
    load_dotenv(str(tmp_path / "absent.env"))


def test_load_dotenv_reads_values_without_overwriting(
    tmp_path: Path, monkeypatch: object
) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                "# a comment",
                "",
                "NOT_A_PAIR",
                'GTM_TEST_QUOTED="quoted value"',
                "GTM_TEST_PLAIN = plain ",
                "GTM_TEST_EXISTING=from_file",
            ]
        )
    )
    os.environ["GTM_TEST_EXISTING"] = "from_environment"
    try:
        load_dotenv(str(env))
        assert os.environ["GTM_TEST_QUOTED"] == "quoted value"
        assert os.environ["GTM_TEST_PLAIN"] == "plain"
        assert os.environ["GTM_TEST_EXISTING"] == "from_environment"
        assert "NOT_A_PAIR" not in os.environ
    finally:
        for key in (
            "GTM_TEST_QUOTED",
            "GTM_TEST_PLAIN",
            "GTM_TEST_EXISTING",
        ):
            os.environ.pop(key, None)


def test_env_flag_defaults_when_unset_or_blank() -> None:
    os.environ.pop("GTM_TEST_FLAG", None)
    assert env_flag("GTM_TEST_FLAG") is False
    assert env_flag("GTM_TEST_FLAG", default=True) is True

    os.environ["GTM_TEST_FLAG"] = ""
    try:
        assert env_flag("GTM_TEST_FLAG", default=True) is True
    finally:
        os.environ.pop("GTM_TEST_FLAG", None)


def test_env_flag_reads_truthy_and_falsy_spellings() -> None:
    try:
        for raw in ("1", "true", "TRUE", " yes ", "on"):
            os.environ["GTM_TEST_FLAG"] = raw
            assert env_flag("GTM_TEST_FLAG") is True
        for raw in ("0", "false", "no", "off", "maybe"):
            os.environ["GTM_TEST_FLAG"] = raw
            assert env_flag("GTM_TEST_FLAG") is False
    finally:
        os.environ.pop("GTM_TEST_FLAG", None)


def test_optional_drops_none_and_keeps_falsy_values() -> None:
    assert optional(a=None) == {}
    assert optional(a=1, b=None, c="x") == {"a": 1, "c": "x"}
    # False and empty string are meaningful API values, not absences.
    assert optional(includeDeleted=False, name="") == {
        "includeDeleted": False,
        "name": "",
    }
    assert optional(type=["a", "b"]) == {"type": ["a", "b"]}
