"""`slipwai search` and `slipwai show`: browsing the chandlery from the command line.

A person who wants a language has to find out it exists before they can install it, and version 1 had
no way to ask: `list` says what is installed and what the index happens to offer, in one shape, with no
way to narrow it. These two are the answer to "what is there?" and "what is this one?".

Both read the same index `install` reads, so what `search` shows is what `install` would fetch. Neither
needs a package installed, and neither installs anything.

Every line says whether a package is installed, because the first thing a reader does with a search
result is work out whether they already have it.
"""
from __future__ import annotations

import argparse

from .assets import this_command
from .catalog import families
from .index_schema import KINDS
from .language_directory import directory
from .language_index import Index, Release
from .language_install import installed
from .versions import key


def latest(releases: list[Release]) -> Release | None:
    """The newest release of one package, by version. None for a name the index lists with none."""
    return max(releases, key=lambda release: key(release.version), default=None)


def haystack(release: Release) -> str:
    """Everything about a release a search term may match: its name, what it says about itself, the
    family it belongs to, the frameworks it carries and the axis options it answers.

    A reader searching for "postgres" means "something that will talk to Postgres for me", and the
    thing that knows is the option the package answers — not its name, which is the language's.
    """
    fragment = release.fragment
    # The entry's own description and tags first, then the manifest's: an index entry is what the publisher
    # wrote for people browsing, and a manifest is what the keel reads. Both are searched, because a package
    # published before the entry carried either still has to be findable.
    parts = [release.name, release.description, release.publisher, *release.tags,
             str(fragment.get("description", "")), str(fragment.get("family", "")),
             # A quickstart's own sentence about the product it suits: what somebody searching "a browser
             # app" is actually searching for, and the only prose it has.
             str(fragment.get("suits", ""))]
    for key_, row in (fragment.get("backends") or {}).items():
        parts += [key_, str(row.get("label", "")), str(row.get("framework", ""))]
        for axis, options in (row.get("options") or {}).items():
            parts += [axis, *(str(option) for option in options)]
    parts += [str(tag) for tag in (fragment.get("tags") or [])]
    return " ".join(parts).lower()


def here() -> set[str]:
    """Every package name this copy already has, installed or loaded."""
    return {*families(), *installed(directory())}


def status(name: str, have: set[str]) -> str:
    return "installed" if name in have else "available"


def matches(found: Index, term: str, kind: str | None = None, family: str | None = None) -> list[Release]:
    """The newest release of each package the term matches, narrowed by kind and family, by name."""
    rows: list[Release] = []
    for _, releases in sorted(found.releases.items()):
        release = latest(releases)
        if release is None:
            continue
        if term and term.lower() not in haystack(release):
            continue
        if family is not None and release.fragment.get("family") != family:
            continue
        if kind is not None and release.kind != kind:
            continue
        rows.append(release)
    return rows


def search_lines(found: Index | None, unreachable: list[str], term: str,
                 kind: str | None = None, family: str | None = None) -> list[str]:
    """What `search` prints: one line per package, or why nothing could be asked."""
    if found is None:
        return [*(line.strip() for line in unreachable),
                f"{this_command()} list shows what is installed"]
    rows = matches(found, term, kind, family)
    # A channel that could not be read is said above the results, not instead of them: a short listing that
    # does not say it is short is how a person concludes a package does not exist when a mirror was down.
    said = [f"  {line}" for line in found.unreachable]
    if not rows:
        asked = f" matching {term!r}" if term else ""
        return [*said, f"no package{asked} in {found.name}"]
    have = here()
    width = max(len(release.name) for release in rows)
    kinds = max(len(release.kind) for release in rows)
    return [
        *said,
        *(f"  {release.name:<{width}}  {release.kind:<{kinds}}  {release.version:<12}  "
          f"{status(release.name, have):<9}  {summary(release)}"
          for release in rows),
    ]


def summary(release: Release) -> str:
    """One line about a package: what its entry says, else what its manifest says, else what it offers."""
    return release.description or str(release.fragment.get("description", "")) or describe(release)


def describe(release: Release) -> str:
    """A line for a package that declares no description: what it offers, which is better than nothing."""
    if release.is_quickstart:
        # Its own sentence about the product it suits, which is the row the interview offers it by too.
        return str(release.fragment.get("suits", "")) or "no description"
    if release.is_extension:
        points = ", ".join(sorted(release.fragment.get("hooks") or {}))
        return f"hooks: {points}" if points else "no description"
    backends = list(release.fragment.get("backends") or {})
    return f"backends: {', '.join(backends)}" if backends else "no description"


def show_lines(found: Index | None, unreachable: list[str], name: str) -> list[str]:
    """What `show` prints for one package: everything the index knows, and how to install it."""
    if found is None:
        return [*(line.strip() for line in unreachable)]
    releases = found.releases.get(name)
    if not releases:
        return [f"{name} is not in {found.name}. {this_command()} search lists what is"]
    release = latest(releases)
    assert release is not None
    fragment = release.fragment
    lines = [f"{release.name} {release.version}  {release.kind}  ({status(release.name, here())})"]
    if summary(release) != describe(release):
        lines.append(f"  {summary(release)}")
    lines += provenance(release)
    lines.append(f"  speaks keel   {fragment.get('core', 'unstated')}")
    if release.is_quickstart:
        lines += quickstart_lines(release)
    else:
        lines += extension_lines(release) if release.is_extension else language_lines(fragment)
    lines.append(f"  releases      {', '.join(r.version for r in sorted(releases, key=lambda r: key(r.version)))}")
    # The verb is the kind: `language install`, `extension install`, `quickstart install`. One word, read
    # off what the entry says it is, rather than a table that grows a row every time a kind is added.
    lines.append(f"  install       {this_command()} {release.kind} install {release.name}")
    return lines


def quickstart_lines(release: Release) -> list[str]:
    """What a quickstart's entry says: what it suits, what it would have installed, and how it is used."""
    fragment = release.fragment
    lines = [f"  suits         {fragment.get('suits', 'unstated')}"]
    for named, label in (("languages", "installs"), ("extensions", "elects")):
        for each in fragment.get(named) or []:
            lines.append(f"  {label:<13} {each.get('name', '?')} {each.get('version', '')}".rstrip())
    lines.append(f"  use it        {this_command()} generate <name> --quickstart {release.name}")
    return lines


def provenance(release: Release) -> list[str]:
    """Who published it and whether the index carries a signature.

    `unsigned` is said rather than left out. A reader who sees nothing about signing cannot tell whether
    this package is unsigned or whether this command does not mention signing — and those are the two
    things it most matters to tell apart.
    """
    from .trust import SAID, state_of, trusted
    state = state_of(release.publisher, release.signature)
    lines = [f"  channel       {release.channel or 'the only one'}"]
    accepted = "accepted here" if trusted(release.publisher) else "not accepted here yet"
    lines.append(f"  publisher     {release.publisher or 'unstated'}"
                 + (f"  ({accepted})" if release.publisher else ""))
    lines.append(f"  signature     {state} — {SAID[state]}")
    if release.tags:
        lines.append(f"  tags          {', '.join(release.tags)}")
    return lines


def language_lines(fragment: dict) -> list[str]:
    lines = [f"  family        {fragment.get('family', 'unstated')}"]
    for backend, row in (fragment.get("backends") or {}).items():
        lines.append(f"  backend       {backend}  {row.get('label', '')}")
        for axis, options in sorted((row.get("options") or {}).items()):
            lines.append(f"      {axis:<12} {', '.join(str(option) for option in options)}")
        if row.get("targets"):
            lines.append(f"      {'targets':<12} {', '.join(str(target) for target in row['targets'])}")
    return lines


def extension_lines(release: Release) -> list[str]:
    """What an extension's entry says: the key a person types, and the moments it attaches to."""
    fragment = release.fragment
    lines = [f"  elect with    ./init --extension {fragment.get('key', release.name)}"]
    points = sorted(fragment.get("hooks") or {})
    lines.append(f"  hooks         {', '.join(points) if points else 'none'}")
    return lines


def search_main(argv: list[str]) -> None:
    from .cli_language import reach, snapshots

    parser = argparse.ArgumentParser(
        prog="slipwai search",
        description="Find a language, an extension or a quickstart in the chandlery",
        epilog="A term matches a package's name, its description, its family, its backends and the axis "
        "options it answers — so `search postgres` finds whatever will talk to Postgres for you, "
        "whichever language it is written in. With no term, everything is listed.",
    )
    parser.add_argument("term", nargs="?", default="", help="what to look for")
    parser.add_argument("--kind", choices=KINDS, default=None)
    parser.add_argument("--family", default=None, help="only packages of this language family")
    parser.add_argument("--pre", action="store_true", help="count snapshots in the index")
    args = parser.parse_args(argv)
    found, _, unreachable = reach(snapshots(args.pre))
    print("\n".join(search_lines(found, unreachable, args.term, args.kind, args.family)))


def show_main(argv: list[str]) -> None:
    from .cli_language import reach, snapshots

    parser = argparse.ArgumentParser(
        prog="slipwai show", description="Everything the chandlery knows about one package")
    parser.add_argument("name", help="the package's name")
    parser.add_argument("--pre", action="store_true", help="count snapshots in the index")
    args = parser.parse_args(argv)
    found, _, unreachable = reach(snapshots(args.pre))
    print("\n".join(show_lines(found, unreachable, args.name)))
