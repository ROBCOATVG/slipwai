"""Where the chandlery is, how its document is fetched, and the release a verb installs from it.

The index is a tree of files under a base URL, found the way `slipwai upgrade` finds its own (`upgrade.index_of`):
`SLIPWAI_INDEX`, else the uv receipt's index, else a documented default. Its document,
`<base>/slipwai-languages/index.json`, lists each release with its file, the file's `sha256` and the release's own
manifest, so a verb can say which releases speak this keel, which family a framework needs and which framework
a family brings without fetching one (`contracts/language-index.md`).

What a document *says* is `index_schema.py`'s; this is how it is reached. The split is the one every network
client wants: a shape that can be tested without a server, and a fetch that can be tested without a shape.

An index that cannot be read is `Unreachable`, said with its URL and the reason, and never an empty list: a project
maker is not told "nothing available" when the truth is "could not ask". Nothing is published at the default
yet, so until a person publishes there every verb that needs it says so.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import replace
from pathlib import Path
from typing import Any

from .assets import VERSION, this_command
from .errors import GenerationError
from .index_schema import CHANDLERY, FORMATS, LANGUAGE, Index, Release, format_of, releases_of
from .upgrade import INDEX, RECEIPT, credentials, following_snapshots, index_of, refusal
from .versions import is_prerelease, key, satisfies

# The published chandlery. Written out rather than derived from `FORGE`, which is where the *keel* lives and
# is a different thing: deriving one from the other pointed every default install at a Gitea path that has
# never served an index, so `slipwai search` and `slipwai install` failed for anybody who had not set
# `SLIPWAI_INDEX` — including the package repositories' own CI, which cannot fetch a sibling without it.
# `upgrade.index_of`'s own default is PyPI's simple index, which cannot serve this tree either.
DEFAULT = "https://robcoatvg.github.io/slipwai-index"
DOCUMENT = "slipwai-languages/index.json"
#: What `slipwai package release` writes, and the newest format this keel reads. `FORMATS` is both.
FORMAT = max(FORMATS)
TIMEOUT: float = 15
DOCUMENT_LIMIT = 4 * 1024 * 1024  # bytes the index document may be
RELEASE_LIMIT = 64 * 1024 * 1024  # bytes a release file may be


class Unreachable(GenerationError):
    """The index could not be read: not there, not answering, refusing, or not an index. `url` is the document's."""

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(f"the language index at {url} could not be reached ({reason})")
        self.url = url
        #: Why, without the sentence around it. What a caller joining several of these wants: wrapping a
        #: whole message in another one says "could not be reached (could not be reached (…))".
        self.reason = reason


def location(receipt: Path | None = None) -> tuple[str, str]:
    """(index name, document URL): the base `upgrade.index_of` gives, or the documented default where it gives
    PyPI's for want of a variable or a receipt."""
    name, base = index_of(Path(sys.prefix) / RECEIPT if receipt is None else receipt)
    if base == INDEX and not os.environ.get("SLIPWAI_INDEX"):
        base = DEFAULT
    return name, f"{base.rstrip('/')}/{DOCUMENT}"


def bases() -> list[str]:
    """Every channel base this environment names, in the order they are asked.

    `SLIPWAI_CHANDLERY` is the list, comma-separated: an organisation's own channel first and the public one
    after it is the arrangement everybody ends up with, and the order is the whole of the policy — a name an
    earlier channel lists is that channel's, so an organisation can publish its own `python` and have it win
    without anything else being configured.

    Comma rather than `PATH`'s separator, which is a colon on this platform and the third character of every
    URL in the list. Whitespace around each is dropped, so a list broken over lines in a shell profile reads.
    """
    named = os.environ.get(CHANDLERY, "")
    return [base.strip().rstrip("/") for base in named.split(",") if base.strip()]


def channels(receipt: Path | None = None) -> list[tuple[str, str]]:
    """(channel name, document URL) for each channel, in order. The old one-index setting is the last of them.

    `SLIPWAI_INDEX` is kept and kept last: it is the keel's own upgrade index as well as a package channel,
    so a person who set it to a mirror meant "fetch from here", not "and never ask anywhere else".
    """
    found = [(f"channel {number}", f"{base}/{DOCUMENT}") for number, base in enumerate(bases(), start=1)]
    name, url = location(receipt)
    return [*found, (name, url)] if url not in dict(found).values() else found


def bare(url: str) -> str:
    """A URL with any credentials it carries taken out of it, as every line that shows one shows it."""
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(parsed._replace(netloc=parsed.netloc.rpartition("@")[2]))


PORTS = {"http": 80, "https": 443}


def origin_of(url: str) -> tuple[str, str, int | None]:
    """A URL's scheme, host and port, a scheme's default port made explicit, whatever credentials it carries."""
    parsed = urllib.parse.urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        port = -1
    port = port if port is not None else PORTS.get(parsed.scheme)
    return parsed.scheme.lower(), (parsed.hostname or "").lower(), port


def same_origin(one: str, other: str) -> bool:
    return origin_of(one) == origin_of(other)


class Guarded(urllib.request.HTTPRedirectHandler):
    """Follows a redirect without the credentials where it leaves the origin the request was first sent to."""

    def redirect_request(self, req: Any, fp: Any, code: Any, msg: Any, headers: Any, newurl: str) -> Any:
        found = super().redirect_request(req, fp, code, msg, headers, newurl)
        if found is not None and not same_origin(req.full_url, newurl):
            found.remove_header("Authorization")
        return found


def fetch(url: str, index_name: str, document: str | None = None, limit: int | None = None) -> bytes:
    """The bytes at `url`, or `Unreachable` saying why not. This is the one place the index fetches a URL: the
    index's credentials (the environment's, or the userinfo of `document`, the index document's own URL as given)
    go only to the origin of `document`, never to another host a release entry names, and never across a redirect to
    one. The whole read, headers and body, has `TIMEOUT` seconds, not each socket operation; an answer longer than
    `limit` bytes (`DOCUMENT_LIMIT` unless the caller says a release's) is refused; and a `file:` URL is read only for
    an index that is itself a `file:` tree."""
    shown, home = bare(url), document or url
    limit = DOCUMENT_LIMIT if limit is None else limit
    if urllib.parse.urlsplit(url).scheme == "file" and urllib.parse.urlsplit(home).scheme != "file":
        raise Unreachable(shown, "an index that is not a file: tree may not name a file: release")
    outcome: dict[str, Any] = {}

    def work() -> None:
        try:
            outcome["data"] = read(url, home, index_name, shown, limit, time.monotonic() + TIMEOUT)
        except BaseException as error:  # handed to the caller's thread, which raises it
            outcome["error"] = error

    reader = threading.Thread(target=work, daemon=True)
    reader.start()
    reader.join(TIMEOUT)
    if reader.is_alive():  # a server that drips headers, or a byte a second: the socket's own timeout never fires
        raise Unreachable(shown, f"it did not finish answering within {TIMEOUT:g} seconds")
    if "error" in outcome:
        raise outcome["error"]
    return bytes(outcome["data"])


def read(url: str, home: str, index_name: str, shown: str, limit: int, deadline: float) -> bytes:
    """`fetch`'s read of one URL, in chunks, against the deadline and the size limit."""
    request = urllib.request.Request(shown, headers={"User-Agent": f"slipwai/{VERSION}"})
    secret = credentials(index_name, home) if same_origin(url, home) else None
    if secret is not None:
        request.add_header("Authorization", "Basic " + base64.b64encode(":".join(secret).encode()).decode())
    try:
        with urllib.request.build_opener(Guarded).open(request, timeout=TIMEOUT) as answer:
            length = answer.headers.get("Content-Length", "")
            if length.isdigit() and int(length) > limit:
                raise Unreachable(shown, f"it is larger than {limit} bytes")
            chunks: list[bytes] = []
            total = 0
            while chunk := answer.read1(65536):
                total += len(chunk)
                if total > limit:
                    raise Unreachable(shown, f"it is larger than {limit} bytes")
                if time.monotonic() > deadline:
                    raise Unreachable(shown, f"it did not finish answering within {TIMEOUT:g} seconds")
                chunks.append(chunk)
            if length.isdigit() and total < int(length):
                raise Unreachable(shown, "the answer was cut short")
            return b"".join(chunks)
    except urllib.error.HTTPError as error:
        error.close()
        if error.code == 404:
            raise Unreachable(shown, "nothing is published there") from error
        if error.code in (401, 403):
            raise Unreachable(shown, refusal(error.code, index_name, shown)) from error
        raise Unreachable(shown, f"it answered {error.code}") from error
    except urllib.error.URLError as error:
        raise Unreachable(shown, str(error.reason)) from error
    except http.client.HTTPException as error:  # not HTTP at all, or an invalid URL; a chunked answer cut short
        raise Unreachable(shown, f"it did not answer as HTTP: {error or type(error).__name__}") from error
    except (OSError, ValueError) as error:  # a silent server's bare TimeoutError, a URL urllib cannot open
        raise Unreachable(shown, str(error) or type(error).__name__) from error


def parsed(url: str, index_name: str, body: bytes) -> Index:
    """The document's releases, or `Unreachable` where what answered is not a chandlery index. Each release's URL is
    joined against `url` as given, credentials and all, so a private index's files are fetched as its document was;
    `Index.url`, which lines show, is `bare`."""
    shown = bare(url)
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as error:
        raise Unreachable(shown, "it is not a chandlery index") from error
    document_format = format_of(data)
    if document_format is None:
        raise Unreachable(shown, "it is not a chandlery index")
    return Index(shown, index_name, releases_of(url, data, document_format, index_name), url)


READ: dict[str, Index] = {}


def read_one(index_name: str, url: str) -> Index:
    """One channel, read once per process and URL."""
    if url not in READ:
        READ[url] = parsed(url, index_name, fetch(url, index_name))
    return READ[url]


def merged(found: list[Index]) -> Index:
    """Every channel's releases in one listing, the earlier channel keeping a name the later also lists.

    A name, not a release: a channel that lists `python` owns `python`, versions and all. Merging the version
    lists would make `install python` fetch 2.0 from one channel and 2.1 from another depending on what each
    happened to publish that week, which is the supply-chain shape nobody wants and nobody chose.
    """
    if len(found) == 1:
        return found[0]
    releases: dict[str, list[Release]] = {}
    for index in found:
        for name, listed in index.releases.items():
            releases.setdefault(name, listed)
    named = ", ".join(index.name for index in found)
    return Index(found[0].url, named, releases, found[0].source)


def read_index() -> Index:
    """Every channel this environment names, read once per process and merged into one listing.

    Unreachable only where *every* channel is: one channel being down is not a reason a person cannot install
    from the others, and a listing that vanished because a mirror was slow is worse than one that is short.
    The channels that could not be read are on `Index.unreachable`, so a listing can say so and still list.
    """
    found: list[Index] = []
    refusals: list[str] = []
    reasons: list[str] = []
    for index_name, url in channels():
        try:
            found.append(read_one(index_name, url))
        except Unreachable as error:
            refusals.append(str(error))
            reasons.append(f"{bare(url)}: {error.reason}")
    if not found:
        raise Unreachable(bare(channels()[0][1]), "; ".join(reasons) or "no channel is configured")
    whole = merged(found)
    return replace(whole, unreachable=tuple(refusals)) if refusals else whole


def compatible(release: Release, schema: str) -> bool:
    """Whether the release's `core` range admits this keel's schema; a range that does not parse admits nothing."""
    try:
        return satisfies(schema, release.fragment["core"])
    except ValueError:
        return False


def counted(version: str, prerelease: bool) -> bool:
    """A release, or a snapshot too where snapshots are followed (`upgrade.following_snapshots`)."""
    return prerelease or not is_prerelease(version)


def snapshots(asked: bool = False) -> bool:
    return following_snapshots(asked)


def newest(index: Index, name: str, schema: str, prerelease: bool, where: Any = None) -> Release | None:
    """The newest counted release of `name` that speaks `schema` and that `where` (a predicate) accepts."""
    found = [
        release for release in index.releases.get(name, [])
        if counted(release.version, prerelease) and compatible(release, schema) and (where is None or where(release))
    ]
    return max(found, key=lambda release: key(release.version), default=None)


def offered(index: Index, schema: str, prerelease: bool, kind: str | None = None) -> dict[str, Release]:
    """Each name with a counted release that speaks `schema`, and its newest such release.

    `kind` narrows it to languages or to extensions, which is what the two listings ask for. None is both,
    which is what `slipwai search` wants: a person looking for a package does not first decide what kind it
    is going to turn out to be.
    """
    where = None if kind is None else (lambda release: release.kind == kind)
    found = {name: newest(index, name, schema, prerelease, where) for name in index.releases}
    return {name: release for name, release in found.items() if release is not None}


def must_be_language(index: Index, name: str, local: str) -> None:
    """Refuse a name this index cannot give a language for: one it lists nowhere, or one it lists as another
    kind, which is the wrong verb for a package that exists rather than a package that is broken.

    Both before anything is fetched. The kind was found out by the staging directory instead, which said so
    as `<a temporary path>/<name> has no language.json` — true, and no help at all to somebody who had
    pasted the line a listing gave them. An index has listed four kinds since version 2 and each is
    installed by its own verb, so the refusal names that verb.

    `local` is the local-source form, passed in rather than imported: it is the installer's sentence and
    this module is read by the installer.
    """
    if name not in index.releases:
        raise GenerationError(f"{name} is not in the language index at {index.url}: install from a local "
                              f"source: {local}")
    kinds = {release.kind for release in index.releases[name]}
    if LANGUAGE in kinds or not kinds:
        return
    kind = sorted(kinds)[0]
    article = "an" if kind[0] in "aeiou" else "a"
    raise GenerationError(f"{name} is {article} {kind}, not a language: {this_command()} {kind} install {name}")


def download(index: Index, release: Release) -> bytes:
    """The release file's bytes, refused unless they are the bytes the index publishes a digest of.

    Fetched as the document that listed it was — the release carries its own channel's URL, credentials and
    all, because several channels are read into one listing and the one holding this file is rarely the first.
    """
    data = fetch(release.url, release.channel or index.name, release.origin or index.source or index.url,
                 RELEASE_LIMIT)
    if hashlib.sha256(data).hexdigest() != release.sha256:
        raise GenerationError(
            f"the release file for {release.name} {release.version} does not match the hash the index publishes "
            f"({bare(release.url)}): refusing to install it"
        )
    return data
