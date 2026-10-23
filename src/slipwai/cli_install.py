"""`slipwai install <name>...`: install whatever the index says each name is, by that kind's own verb.

The short form is what a reader types after a search result tells them a package exists, and what a package's CI
types to put its siblings beside it — and a sibling is not always a language. A language proved against a cloud
needs the cloud's target package beside it, and the verb refused it with `aws is a target, not a language`, which
named the right command and left the reader to type it. The index already says what each name is (every release
entry has its `kind`), so this asks it and hands each name to its own verb: targets to `target install`, the rest
to `language install`, which keeps its own refusals for a name the index has under another kind, or not at all.
"""
from __future__ import annotations

from .cli_language import language_main
from .cli_target import target_main
from .index_schema import TARGET
from .language_index import Unreachable, read_index


def kinds_of(names: list[str]) -> dict[str, str]:
    """Each name's kind as the index lists it, for the names it lists; nothing where it cannot be read, so the
    language verb meets the name and says what it says about an index it cannot reach."""
    try:
        index = read_index()
    except Unreachable:
        return {}
    return {name: sorted({release.kind for release in index.releases[name]})[0]
            for name in names if index.releases.get(name)}


def install_main(argv: list[str]) -> None:
    """Targets by `target install`, everything else by `language install`, each with the flags given."""
    names = [word for word in argv if not word.startswith("-")]
    flags = [word for word in argv if word.startswith("-")]
    kinds = kinds_of(names)
    targets = [name for name in names if kinds.get(name) == TARGET]
    rest = [name for name in names if name not in targets]
    if targets:
        target_main(["install", *targets, *flags])
    if rest or not targets:
        language_main(["install", *rest, *(flag for flag in flags if flag != "--accept-publisher")])
