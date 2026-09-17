"""What the service's log lines actually look like, in both formats.

Worth a suite because the failure it guards against is silent: a formatter that drops
the ``extra`` a caller passed, or a second ``configure_logging`` that leaves two handlers
and doubles every line, is invisible until the day somebody is reading production logs to
find out what went wrong.
"""

from __future__ import annotations

import json
import logging

from delivery_starter.logging_setup import configure_logging


def _emit(capsys, **kwargs: str) -> str:
    logging.getLogger("test").info("a thing happened", extra={"view": "orders"})
    return capsys.readouterr().out


def test_the_default_line_is_one_json_object_carrying_what_the_caller_passed(capsys) -> None:
    configure_logging(level="info", log_format="json")

    record = json.loads(_emit(capsys))

    assert record["level"] == "info"
    assert record["logger"] == "test"
    assert record["message"] == "a thing happened"
    # The whole point of structured logging: the caller's own fields survive to the reader.
    assert record["view"] == "orders"
    assert "time" in record


def test_pretty_is_the_same_record_as_one_readable_line(capsys) -> None:
    configure_logging(level="info", log_format="pretty")

    line = _emit(capsys)

    assert line.count("\n") == 1
    assert "a thing happened" in line
    assert "INFO" in line


def test_configuring_twice_leaves_one_handler_rather_than_two(capsys) -> None:
    configure_logging(level="info", log_format="json")
    configure_logging(level="info", log_format="json")

    assert len(_emit(capsys).strip().splitlines()) == 1


def test_an_exception_is_reported_with_the_record_rather_than_beside_it(capsys) -> None:
    configure_logging(level="info", log_format="json")

    try:
        raise ValueError("the pass failed")
    except ValueError:
        logging.getLogger("test").exception("catching up failed")

    record = json.loads(capsys.readouterr().out)
    assert record["message"] == "catching up failed"
    assert "ValueError: the pass failed" in record["error"]


def test_the_level_is_honoured(capsys) -> None:
    configure_logging(level="warning", log_format="json")

    logging.getLogger("test").info("not this one")

    assert capsys.readouterr().out == ""
