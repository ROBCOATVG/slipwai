"""Standing text as an asset: the tokens it may name, the sections a module may select, and the refusals.

Three kinds of text live in `src/slipwai/project/`, and only one of them may become an asset. The page that
says which is [docs/generated-prose.md](../../../docs/generated-prose.md); this module is the mechanism it
describes, and the rules below are the ones that page is enforcing.

**Tokens.** The substitution is a closed set, deliberately, and not `str.format`: `format` reads every `{` in
a page as a field, which turns a shell `${VAR}` or a JSON example into an escaping question a person writing
prose should never have to think about, and answers a misspelt name with a `KeyError` from the middle of a
generation instead of a line naming the file and the token. The doubled-brace marker is the one the toolkit
already used for language examples, so a placeholder in a page looks like every other placeholder under
`assets/`. `briefs.py` piloted this; everything here is that mechanism with the pilot's brief-only parts left
behind.

**Sections.** The conditional question phase 16 had to answer. A page's text branches two ways and they are
not the same thing:

- A **whole section** appears or it does not — `AGENTS.md` grows a "Browser frontends" heading when the
  project has a browser app. The words inside are standing text; only whether they are there is decided. That
  is a section: the asset carries it behind a marker and the module names the sections it wants.
- A **sentence agrees with a declaration** — "Each consumes" against "It consumes", a plural `s`, a list of
  paths joined into a clause. Those are not prose a person edits a paragraph at a time; they are rendered from
  the count, and an asset that hand-wrote them would be a second answer to a question the declaration already
  answers. They stay in Python, which is case 2 of the page's three.

The test a contributor applies is the paragraph boundary: if you can point at where the branch begins and
ends and it is a whole paragraph or more, it is a section; if the branch is inside a sentence, it is
rendering and it stays. That rule is why there is no `{% if %}` here and never will be — a template language
with conditionals would make every one of those agreements expressible in an asset, and then the asset and
the declaration would be two places that answer "how many browser apps does this project have".

A marker is an HTML comment because an asset is copied into a generated project verbatim before the resolved
one is written over it, and a marker that leaked would be invisible in rendered Markdown rather than a
stray word in somebody's `AGENTS.md`.
"""
from __future__ import annotations

import re

from ..errors import GenerationError

#: A placeholder, in the spelling `examples.py` already uses under `assets/`. Lower case and hyphenated so
#: the marker cannot be mistaken for the prose around it.
MARKER = re.compile(r"\{\{([a-z][a-z0-9-]*)\}\}")
#: A section's two markers. An HTML comment, so one that leaked is invisible rather than wrong.
OPEN = re.compile(r"^[ \t]*<!-- section: ([a-z][a-z0-9-]*) -->[ \t]*\n", re.M)
CLOSE = re.compile(r"^[ \t]*<!-- end section -->[ \t]*\n", re.M)


def resolve(name: str, text: str, named: dict[str, str]) -> str:
    """`text` with each `{{placeholder}}` replaced, or a refusal naming the file and the token it invented.

    The refusal matters more than the substitution. An unresolved `{{make}}` is a page that ships the marker
    into somebody's repository, where it reads as a typo in the method rather than as a bug in the keel, and
    nothing downstream would notice: the file is valid markdown either way.
    """
    def value(match: re.Match[str]) -> str:
        token = match.group(1)
        if token not in named:
            raise GenerationError(
                f"{name} names {{{{{token}}}}}, which no value provides; the whole set is "
                f"{', '.join(sorted(named))}"
            )
        return named[token]

    return MARKER.sub(value, text)


def sections(name: str, text: str) -> dict[str, str]:
    """Every section the page carries, in the order it carries them, keyed by the name on its marker."""
    found: dict[str, str] = {}
    position = 0
    while (start := OPEN.search(text, position)) is not None:
        key = start.group(1)
        end = CLOSE.search(text, start.end())
        if end is None:
            raise GenerationError(
                f"{name} opens section {key} and never closes it; a section ends with `<!-- end section -->`"
            )
        if key in found:
            raise GenerationError(
                f"{name} carries section {key} twice; a section is named once, and a module selecting it "
                "would otherwise get whichever came first"
            )
        found[key] = text[start.end():end.start()]
        position = end.end()
    return found


def render(name: str, text: str, named: dict[str, str], wanted: tuple[str, ...] | None = None) -> str:
    """The page as a project receives it: the sections `wanted` kept, the rest dropped, the tokens resolved.

    `wanted` of None keeps every section, which is what a page with no sections wants and what a module that
    has no branch to make asks for. A name in `wanted` the page has not got is refused rather than ignored,
    because a module selecting a section that is no longer there is a paragraph silently gone from a file
    somebody receives — the one failure the digest gate exists to catch, found here instead.
    """
    carried = sections(name, text)
    if wanted is not None and (invented := [one for one in wanted if one not in carried]):
        raise GenerationError(
            f"{name} has no section {', '.join(invented)}; it carries {', '.join(carried) or 'none'}"
        )
    kept = carried if wanted is None else {key: body for key, body in carried.items() if key in wanted}
    out, position = [], 0
    while (start := OPEN.search(text, position)) is not None:
        end = CLOSE.search(text, start.end())
        assert end is not None  # `sections` has already refused an unclosed one
        out.append(text[position:start.start()])
        if start.group(1) in kept:
            out.append(carried[start.group(1)])
        position = end.end()
    out.append(text[position:])
    return resolve(name, "".join(out), named)


def unresolved(text: str) -> list[str]:
    """Every placeholder still in `text`. A generated file carrying one is a file that shipped the marker."""
    return sorted({match.group(0) for match in MARKER.finditer(text)})
