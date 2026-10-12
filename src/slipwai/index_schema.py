"""What a chandlery index document says, in both the formats a published one may be written in.

Version 1 listed languages: a `languages` object, a list of releases under each name, each release carrying
its file, the file's digest and its `language.json`. Nothing else was publishable, so nothing else was
described.

**Version 2 lists packages.** An extension is a package the way a language is, and a target — the place a
project is deployed to — is a third; an index that could only list one of them would make the others things
people pass paths around for. So the block is `packages`, each entry declares its `kind`, and the manifest
is under the key that names it — `language`, `extension` or `target` — which is also how a reader with no
`kind` field still knows what it is holding. A kind is added here rather than branched on at each reader:
the three differ only in which few fields a line can be built from.

**Four fields arrive with it, and each answers a question a person asked of version 1.** `publisher`, because
"who published this?" had no answer. `signature`, because the digest proves the file is the file the index
lists and says nothing about who put it there (6.5 verifies it; this only carries it). `description` and
`tags`, because `slipwai search` could match a name and nothing else, and a person searching for "a code
index" does not know it is called codegraph.

**Both formats are read.** Published v1 indexes exist, and an index is a file on someone else's server: a
keel that could only read the newer one would make upgrading the keel break the index. A v1 document is read
as packages of kind `language`, which is what it was.

This module is the document's shape alone — no fetching, no network, nothing that can fail slowly — so the
shape can be tested without a server and read without one.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from .language_shape import name_fault
from .quickstart import is_document
from .versions import parse

#: Where the channels are named, in order: an organisation's own first, the public one after it. Comma
#: separated, because `PATH`'s separator is a colon on this platform and the third character of every URL.
CHANDLERY = "SLIPWAI_CHANDLERY"
#: The document formats this keel reads. A document declaring anything else is not an index it knows.
FORMATS = (1, 2)
#: Where each format's entries live, and what version 1 called the one kind it had.
BLOCK = {1: "languages", 2: "packages"}
LANGUAGE, EXTENSION, TARGET, QUICKSTART = "language", "extension", "target", "quickstart"
#: In the order a reader meets them, which is the order they were published in. A kind arriving here is a
#: kind every index in the world may already be listing: the block, the manifest key and the `kind` field
#: are one word, so an index written for a keel that reads four kinds still loads on one that reads two —
#: the entries it cannot read are dropped, which is what `entry_of` does with every entry it cannot read.
#: A quickstart is not code and installs nothing into the package directory — it is the set of answers
#: somebody already settled — but it is published, versioned, searched and fetched the way a language is,
#: which is the whole reason it is a package at all rather than a file people send each other.
KINDS = (LANGUAGE, EXTENSION, TARGET, QUICKSTART)
DIGEST = re.compile(r"[0-9a-f]{64}")
#: The declared-never-required family members an entry's `answers` may name: what a verb needs to know a
#: release answers before it is installed (D122, ADR 0010). A value a reader does not know is ignored.
ANSWERS = ("npm_workspace",)
#: How long a field a person wrote may be before the index is not describing a package any more. A tag is a
#: word; a description is a sentence. Held here rather than where they are printed, because a line that
#: wraps a terminal is a cosmetic fault and a field that is a megabyte is a document nobody should have read.
LIMITS = {"publisher": 200, "description": 500, "signature": 8192, "tag": 40}
TAGS = 12


@dataclass(frozen=True)
class Release:
    """One release the index lists.

    `fragment` is the manifest, whichever kind it is: a `language.json`, an `extension.json` or a
    `target.json`. One field rather than three, because every reader of it either knows the kind already or
    does not care — `compatible` reads `core`, which all three carry.
    """

    name: str
    version: str
    url: str
    sha256: str
    fragment: dict[str, Any]
    answers: tuple[str, ...] = ()
    kind: str = LANGUAGE
    publisher: str = ""
    signature: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    #: Which channel listed it, as a line names one, and that channel's document URL as given — credentials
    #: and all, because a private channel's release files are fetched the way its document was. Carried on
    #: the release rather than looked up, because several channels are read into one listing and a release
    #: that could not say where it came from could not be fetched from there either.
    channel: str = ""
    origin: str = ""

    @property
    def is_extension(self) -> bool:
        return self.kind == EXTENSION

    @property
    def is_target(self) -> bool:
        return self.kind == TARGET

    def is_quickstart(self) -> bool:
        return self.kind == QUICKSTART

    @property
    def signed(self) -> bool:
        """Whether the index carries a signature for it. Verifying one is 6.5; carrying it is this."""
        return bool(self.signature)


@dataclass(frozen=True)
class Index:
    """The index document as read: its URL, the index's name (for credentials), and each name's releases."""

    url: str
    name: str
    releases: dict[str, list[Release]] = field(default_factory=dict)
    source: str = field(default="", repr=False)  # the URL as given, credentials and all: only `fetch` reads it
    #: A line for each channel that could not be read, where the others could. A listing says so and still
    #: lists: one channel being down is not a reason a person cannot install from the rest.
    unreachable: tuple[str, ...] = ()


def names_of(name: str, fragment: dict[str, Any]) -> list[Any]:
    """Every name a language entry supplies besides its key: its `name`, `family`, `default_framework`, and each
    backend's key and `framework`, so none is printed or joined into a path before `name_fault` has held it."""
    found: list[Any] = [fragment.get("name"), name]
    found += [fragment[k] for k in ("family", "default_framework") if k in fragment]
    rows = fragment.get("backends")
    for key_, row in (rows.items() if isinstance(rows, dict) else []):
        found.append(key_)
        if isinstance(row, dict) and "framework" in row:
            found.append(row["framework"])
    return found


def shaped(fragment: dict[str, Any]) -> bool:
    """Whether the keys a line is made from have their shape: `backends` an object of objects, each `options` an
    object of lists of strings. A fragment the loader would refuse for other reasons is for the loader to say."""
    rows = fragment.get("backends", {})
    if not isinstance(rows, dict) or not all(isinstance(row, dict) for row in rows.values()):
        return False
    for row in rows.values():
        options = row.get("options", {})
        if not isinstance(options, dict) or not all(
                isinstance(found, list) and all(isinstance(each, str) for each in found) for found in options.values()):
            return False
    return True


def text(entry: dict, field_name: str) -> str:
    """One of the fields a publisher writes, or `''` where it is absent, not text, or longer than its limit."""
    said = entry.get(field_name)
    return said if isinstance(said, str) and len(said) <= LIMITS[field_name] else ""


def tags_of(entry: dict) -> tuple[str, ...]:
    """The entry's tags: strings, short, and at most `TAGS` of them. Anything else is dropped, not refused —
    a tag is what a search matches on, and a bad one is a worse search rather than a worse package."""
    said = entry.get("tags")
    if not isinstance(said, list):
        return ()
    return tuple(tag for tag in said if isinstance(tag, str) and 0 < len(tag) <= LIMITS["tag"])[:TAGS]


def kind_of(entry: dict) -> str | None:
    """Which kind this entry is, from its `kind` or from which manifest it carries. None where neither says.

    Reading the manifest's key as a fallback is what lets a v2 document written before `kind` was required
    still load, and what makes a hand-written entry that forgot the field work rather than vanish.
    """
    said = entry.get("kind")
    if isinstance(said, str) and said in KINDS:
        return said
    for kind in KINDS:
        if isinstance(entry.get(kind), dict):
            return kind
    return None


def language_entry(name: str, fragment: Any) -> bool:
    """Whether a language manifest is one a line may be built from without checking it again."""
    if not (isinstance(fragment, dict) and fragment.get("name") == name and isinstance(fragment.get("core"), str)):
        return False
    if not shaped(fragment):
        return False
    return all(isinstance(each, str) and name_fault("language", each) is None for each in names_of(name, fragment))


def extension_entry(name: str, fragment: Any) -> bool:
    """Whether an extension manifest is one a line may be built from. Its `key` is the name it is listed under."""
    if not (isinstance(fragment, dict) and isinstance(fragment.get("core"), str)):
        return False
    if fragment.get("key") != name or name_fault("extension", name) is not None:
        return False
    return isinstance(fragment.get("name"), str) and bool(fragment["name"])


def target_entry(name: str, fragment: Any) -> bool:
    """Whether a target manifest is one a line may be built from. Its `name` is what it is listed under, and
    its `label` is the sentence a prompt shows — an entry with none could be installed and never offered."""
    if not (isinstance(fragment, dict) and isinstance(fragment.get("core"), str)):
        return False
    if fragment.get("name") != name or name_fault("target", name) is not None:
        return False
    return isinstance(fragment.get("label"), str) and bool(fragment["label"])


#: Which reader holds each kind's manifest to the little a line is built from. Everything else a manifest
#: declares is for the loader to refuse, on the machine that installs it, where the package's files are.
READERS = {LANGUAGE: language_entry, EXTENSION: extension_entry, TARGET: target_entry,
           QUICKSTART: is_document}


def entry_of(document: str, name: str, entry: Any, channel: str = "", origin: str = "") -> Release | None:
    """One entry of the document as a `Release`, or None where it is not the contract's shape.

    None rather than a refusal, for every fault: an index is a file on someone else's server, and one bad
    entry in it is not a reason the other forty do not install. What is dropped is said by `slipwai search`
    having nothing to show for that name, which is the truth.
    """
    if not isinstance(entry, dict):
        return None
    kind = kind_of(entry)
    if kind is None:
        return None
    version, file, digest = (entry.get(k) for k in ("version", "file", "sha256"))
    if not (isinstance(version, str) and len(version) <= 64 and parse(version) and isinstance(file, str) and file):
        return None
    if not (isinstance(digest, str) and DIGEST.fullmatch(digest)):
        return None
    fragment = entry.get(kind)
    if not READERS[kind](name, fragment):
        return None
    assert isinstance(fragment, dict)  # every reader above refuses anything else
    said = entry.get("answers")
    answers = tuple(each for each in said if each in ANSWERS) if isinstance(said, list) else ()
    return Release(name, version, urllib.parse.urljoin(document, file), digest, dict(fragment), answers,
                   kind=kind, publisher=text(entry, "publisher"), signature=text(entry, "signature"),
                   description=text(entry, "description"), tags=tags_of(entry),
                   channel=channel, origin=origin or document)


def format_of(data: Any) -> int | None:
    """Which format this document is written in, or None where it is not one this keel reads."""
    if not isinstance(data, dict):
        return None
    declared = data.get("index")
    if declared not in FORMATS or not isinstance(data.get(BLOCK[declared]), dict):
        return None
    return int(declared)


def releases_of(url: str, data: dict, document_format: int, channel: str = "") -> dict[str, list[Release]]:
    """Each name in the document, and the releases of it this keel can read.

    A version 1 entry carries no `kind` and its manifest is under `language`, which is exactly what
    `kind_of` reads — so the two formats differ here in the name of one block and nothing else.
    """
    releases: dict[str, list[Release]] = {}
    for name, entries in data[BLOCK[document_format]].items():
        found = ([entry_of(url, name, entry, channel, url) for entry in entries]
                 if isinstance(entries, list) else [])
        kept = [release for release in found if release is not None]
        if kept:
            releases[name] = kept
    return releases
