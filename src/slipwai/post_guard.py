"""Whether a POST came from the board's own pages: checked once, before any route reads it.

The board answers on the loopback address, and every control on it is a POST — and since the conversations,
a POST can stop a slice's session, interrupt its turn or tell every captain something, signed as from the
person. A page on any other origin a browser has open could send one: a `text/plain` POST is a "simple"
request a browser sends cross-site without asking first. So a POST is refused when

- it says where it came from (`Origin`, or `Referer` without one) and that is not this board;
- the `Host` it was sent to is not an address this board is served on (a name rebound to 127.0.0.1 is not);
- it carries a body that is not `application/json`, which is all any route here reads — and the one kind a
  browser will not send cross-site without asking this server first, which it does not answer.

A request that says nowhere it came from — a script on this machine, the suite — is let through: it is not a
browser carrying a stranger's page, and everything else here already trusts this machine's own user.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}
ANY = {"", "0.0.0.0", "::"}  # noqa: S104 — the names a server bound to every address answers on


def host_of(value: str) -> tuple[str, int | None]:
    """A `Host` or an origin's netloc as (name, port)."""
    try:
        split = urlsplit(f"//{value}")
        return (split.hostname or "").lower(), split.port
    except ValueError:
        return "", None


def ours(handler: Any, value: str) -> bool:
    """Whether `name:port` is an address this board's server answers on."""
    bound, port = handler.server.server_address[:2]
    name, asked = host_of(value)
    if asked != port or not name:
        return False
    if str(bound) in ANY:
        return True
    return name == str(bound).lower() or (str(bound) in LOOPBACK and name in LOOPBACK)


def refusal(handler: Any) -> str:
    """Why this POST is not taken, or `''` where it is the board's own (or no browser's at all)."""
    headers = handler.headers
    host = headers.get("Host") or ""
    if host and not ours(handler, host):
        return f"this board is not served at {host}"
    said = headers.get("Origin") or ""
    if said:
        if said == "null" or urlsplit(said).netloc.lower() != host.lower():
            return "a page on another site cannot change this board"
    elif headers.get("Referer") and urlsplit(headers["Referer"]).netloc.lower() != host.lower():
        return "a page on another site cannot change this board"
    kind = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
    length = int(headers.get("Content-Length") or 0)
    if (kind and kind != "application/json") or (length and not kind):
        return "the board takes JSON, sent by its own pages"
    return ""
