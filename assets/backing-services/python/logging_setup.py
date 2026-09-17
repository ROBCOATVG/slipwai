"""How this process logs, decided in one place and from the environment alone.

Structured and on from the first run, because the alternative is a service whose only
account of itself is whatever `print` somebody reached for: a projection that dies, a
request that 500s and a start-up that fails all have to leave a line somebody can find,
and a line nobody can parse is a line nobody greps twice.

JSON is the default, because that is what a log shipper reads. ``LOG_FORMAT=pretty`` —
which ``make dev`` sets — gives the same records as one readable line each, for a person
watching a terminal. ``LOG_LEVEL`` names the level either way, and defaults to ``info``.

No dependency: a JSON formatter is a dozen lines of the standard library, and a starter
should not spend a project's first dependency on choosing its logging library for it.
Moving to structlog later is a change to this module and to nothing else, which is the
whole reason it is a module the entry point calls rather than a call inside the entry
point.
"""

from __future__ import annotations

import json
import logging
import sys
from os import environ

from .tracing import trace_context

#: The attributes `logging` puts on every record itself. Anything else came from a
#: caller's ``extra=``, and is what makes a structured line worth reading — so the
#: formatter below copies exactly what is *not* in here into the JSON object.
_STANDARD = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per record, with whatever the caller passed as ``extra``."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # The request this line happened inside, where there is one. A log line nobody can tie
        # back to a request is the reason an incident takes an afternoon; `tracing.py` says
        # where the ids come from and why they are these two spellings.
        payload.update(trace_context())
        for key, value in record.__dict__.items():
            if key not in _STANDARD:
                payload[key] = value
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str | None = None, log_format: str | None = None) -> None:
    """Install the one handler this process logs through.

    Both arguments default to the environment, and are parameters at all so that a test
    can ask for a format without setting a variable the rest of the suite then runs under.
    """
    resolved_level = (level or environ.get("LOG_LEVEL", "info")).upper()
    resolved_format = log_format or environ.get("LOG_FORMAT", "json")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
        if resolved_format == "pretty"
        else JsonFormatter()
    )
    root = logging.getLogger()
    # Replace what is installed rather than adding to it: calling this twice — a test,
    # then the entry point — would otherwise leave two handlers and double every line.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(resolved_level)
