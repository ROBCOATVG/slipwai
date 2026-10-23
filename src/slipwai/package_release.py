"""Building a release of either kind of package, and putting it in a channel.

A release is three things: a file, a digest of that file, and an entry in a channel's index saying where the
file is and what is in it. Version 1 had the first two and a person wrote the third by hand, into one
`index.json` that every publisher edited — which is the shared line every other part of this method has
already removed once, and it goes the same way here.

**One file per entry.** A channel repository holds `entries/<name>-<version>.json`, and its index is built
from them. Two publishers releasing on one afternoon touch two files and never meet; the index is a
regeneration rather than a resolution, which is `changelog.d/`'s shape and `render-fairways`' and the
events index's.

**The entry is written from the package, never typed.** Its manifest, its version, its digest: all of it is
read off the thing being released. What a publisher writes is the description and the tags, in the manifest,
where they are also what the keel reads — so there is one place to get them wrong rather than two places to
get them out of step.

**Registering is a file operation, and that is deliberate.** A channel is a directory of JSON, served as a
static site. `register` writes into a checkout of one; whether that checkout is pushed, reviewed or merged
is the channel's own business, which is what makes a private channel and the public one the same shape.

**The release file does not have to live in the channel, and should not.** An entry's `file` may be an
absolute URL, which the client joins against nothing and fetches anonymously — the channel's credentials
go only to the channel's own origin, and the digest proves the bytes either way. So the ordinary
arrangement is the tarball on the tag that built it and the channel holding JSON alone: git keeps every
version of every file for ever, and a channel that stored its own tarballs would grow without bound while
GitHub already hosts the same bytes for nothing.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import tempfile
from pathlib import Path

from . import ed25519
from .assets import this_command
from .errors import GenerationError
from .index_schema import BLOCK, EXTENSION, LANGUAGE, QUICKSTART, TARGET
from .language_release import ReleaseError, pack, read_package
from .trust import ED25519

#: Where a channel keeps one file per release, and the document built from them.
ENTRIES = "entries"
#: What a channel calls itself and where it is served from, written once by `channel new`. Read here
#: rather than passed around: `register` rebuilds a channel too, and a page titled after whatever
#: directory it happened to be cloned into is the kind of thing nobody notices until it is published.
SETTINGS = "channel.json"
DOCUMENT = "slipwai-languages/index.json"
FORMAT = 2
#: What an entry declares about itself beyond the manifest. Read off the package or given by the publisher;
#: none of it is typed twice.
CARRIED = ("publisher", "description", "tags")


def settings(channel: Path) -> dict:
    """What a channel calls itself and where it is served from, or nothing where it says neither."""
    try:
        held = json.loads((channel / SETTINGS).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return {}
    return held if isinstance(held, dict) else {}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


#: Each kind against the manifest that declares it. The manifest's name is how a reader and the loader both
#: tell the kinds apart without being told which they are holding.
MANIFESTS = {EXTENSION: "extension.json", LANGUAGE: "language.json", TARGET: "target.json",
             QUICKSTART: "quickstart.json"}


def kind_of(root: Path) -> str:
    """Which kind of package this directory is, by the manifest it holds."""
    for kind, manifest in MANIFESTS.items():
        if (root / manifest).is_file():
            return kind
    raise GenerationError(f"{root} holds none of {', '.join(sorted(MANIFESTS.values()))}, so it is no package")


def signing_key(path: Path) -> bytes:
    """A publisher's Ed25519 seed, read from a file. Base64 on one line, or the raw thirty-two bytes.

    Two spellings because a key is made in two places: `package key` writes the base64 a person can paste
    into a secret store, and a CI runner writing a secret to a file gets whatever that store hands back.
    Nothing else is accepted — a passphrase-wrapped key would be a key format this keel has to understand,
    and the thing to hold a key in is the secret store, not a file on a runner.
    """
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise GenerationError(f"{path} cannot be read ({error}), and it is the key this release is signed "
                              f"with") from None
    if len(raw) == ed25519.KEY_BYTES:
        return raw
    try:
        decoded = base64.b64decode(raw.strip(), validate=True)
    except (binascii.Error, ValueError):
        decoded = b""
    if len(decoded) != ed25519.KEY_BYTES:
        raise GenerationError(f"{path} is not an Ed25519 secret key: {ed25519.KEY_BYTES} bytes, raw or "
                              f"base64, as `{this_command()} package key` writes it")
    return decoded


def signature_for(archive: Path, key: Path | None) -> str:
    """The `signature` field for a release signed with this key, or `''` where there is none to sign with.

    Over the release file's bytes, which is what a client has when it asks: the index's digest proves the
    bytes are the bytes listed, and this proves the publisher put them there. Prefixed `ed25519:` so a
    reader knows what it is holding without being told which channel it came from (`trust.py`).
    """
    if key is None:
        return ""
    raw = ed25519.sign(signing_key(key), archive.read_bytes())
    return ED25519 + base64.b64encode(raw).decode("ascii")


def entry_for(root: Path, archive: Path, publisher: str = "", file_url: str = "",
              signature: str = "") -> dict:
    """The index entry for a built release: where the file is, what is in it, and who says so.

    `file_url` is where the bytes actually are, where that is not beside the index — the release asset on
    the tag that built them, usually. Absent, the file is named relative to the index, which is the
    arrangement a `file:` channel and a first try both want. It is the only field in an entry that is about
    *where* rather than about *what*, and the digest is what makes either safe.
    """
    source = read_package(root)
    if source.version == "unknown":
        raise GenerationError(f"{root} has no VERSION, and a release is a version of something. Write one: "
                              f"`echo 0.1.0 > {root / 'VERSION'}`")
    kind = kind_of(root)
    manifest = source.fragment
    entry = {
        "version": source.version,
        "file": file_url or archive.name,
        "sha256": digest(archive),
        "kind": kind,
        kind: manifest,
    }
    if publisher:
        entry["publisher"] = publisher
    if signature:
        entry["signature"] = signature
    for field in ("description", "tags"):
        if manifest.get(field):
            entry[field] = manifest[field]
    # What a verb needs to know a release answers before it is installed (`index_schema.ANSWERS`): a release
    # that ships a browser app answers both members a browser app is written through, and its `frontends`
    # block is what says it ships one. Written here so no publisher has to remember to, which nobody did.
    if kind == "language" and manifest.get("frontends"):
        entry["answers"] = ["npm_workspace", "browser_apps"]
    return entry


def written_entry(name: str, entry: dict, into: Path) -> Path:
    """One entry file, `<name>-<version>.json`, which is the only file a release adds to a channel's listing."""
    into.mkdir(parents=True, exist_ok=True)
    path = into / f"{name}-{entry['version']}.json"
    path.write_text(json.dumps({"name": name, **entry}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def release(root: Path, out: Path, publisher: str = "", file_url: str = "",
            key: Path | None = None) -> tuple[Path, Path, dict]:
    """Build the release file and its entry under `out`. (file, entry file, entry). Writes nowhere else.

    `key` signs it, which is what a private channel's releases carry. The public channel's are signed
    keyless from CI instead and the bundle arrives in the entry the workflow writes; signing is never done
    at install time and never on behalf of somebody who did not ask for it, so no key means no signature
    and an entry that honestly says it has none.
    """
    try:
        archive = pack(root, out)
    except ReleaseError as error:
        raise GenerationError(str(error)) from None
    entry = entry_for(root, archive, publisher, file_url, signature_for(archive, key))
    return archive, written_entry(read_package(root).name, entry, out / ENTRIES), entry


def entries_in(channel: Path) -> list[dict]:
    """Every entry file a channel holds, in name then file order, each with the name it is listed under."""
    place = channel / ENTRIES
    found: list[dict] = []
    for path in sorted(place.glob("*.json")) if place.is_dir() else []:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as error:
            raise GenerationError(f"{path} cannot be read as an entry: {error}") from None
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise GenerationError(f"{path} names no package, so nothing can be listed under it")
        found.append(entry)
    return found


def document(entries: list[dict]) -> dict:
    """The index document those entries render to. Deterministic, because it is checked rather than trusted."""
    packages: dict[str, list[dict]] = {}
    for entry in entries:
        body = {key: value for key, value in entry.items() if key != "name"}
        packages.setdefault(entry["name"], []).append(body)
    for listed in packages.values():
        listed.sort(key=lambda body: str(body.get("version")))
    return {"index": FORMAT, BLOCK[FORMAT]: dict(sorted(packages.items()))}


def rebuild(channel: Path, name: str = "", base: str = "") -> Path:
    """Write the channel's index and its front page from its entry files. Returns where the index went.

    Both, because a channel is a static site and the root of one was a 404: the machine's answer was
    there and the person's was not, which is the wrong way round for a URL somebody is sent to. Generated
    together so a release that changes one changes the other, and neither is edited by hand.
    """
    from .channel_page import page
    held = settings(channel)
    name, base = name or str(held.get("name") or channel.name), base or str(held.get("base") or "")
    entries = entries_in(channel)
    path = channel / DOCUMENT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document(entries), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (channel / "index.html").write_text(page(name or channel.name, entries, base), encoding="utf-8")
    return path


def register(root: Path, channel: Path, publisher: str = "",
             file_url: str = "", key: Path | None = None) -> tuple[Path | None, Path, Path]:
    """Build a release of `root` and add it to `channel`. (file or None, entry file, index).

    With `file_url` the tarball is built into a temporary place and only its digest is kept: the channel
    gets the entry and nothing else, which is what keeps it from growing a copy of every version for ever.

    Refuses a version the channel already lists with different bytes. A release file is immutable by the
    time anyone has installed it, and replacing one silently is how a digest somebody checked stops meaning
    anything. Re-registering the same bytes is allowed and does nothing new, so a publisher who ran this
    twice has not got a problem to solve.
    """
    name = read_package(root).name
    serving = channel / DOCUMENT.rsplit("/", 1)[0]
    kept: Path | None = None
    with tempfile.TemporaryDirectory() as elsewhere:
        try:
            archive = pack(root, Path(elsewhere) if file_url else serving)
        except ReleaseError as error:
            raise GenerationError(str(error)) from None
        entry = entry_for(root, archive, publisher, file_url, signature_for(archive, key))
        kept = None if file_url else archive
    standing = channel / ENTRIES / f"{name}-{entry['version']}.json"
    if standing.is_file():
        held = json.loads(standing.read_text(encoding="utf-8"))
        if held.get("sha256") != entry["sha256"]:
            raise GenerationError(f"{channel} already lists {name} {entry['version']}, with a different file. "
                                  f"A release is immutable once anybody has installed it: release a new "
                                  f"version rather than replacing this one")
    return kept, written_entry(name, entry, channel / ENTRIES), rebuild(channel)
