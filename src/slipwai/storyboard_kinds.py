"""Built, planned, changed and new, apart, on the storyboard's card: what a person is asked about, and what not.

The card's verdict covers what this feature changes and adds. What the storyboard frames beside those — the
project's own surfaces, and an earlier feature's that are approved and not built yet — is shown for the flow,
and the card says so in counts and by name, so that "Approve storyboard" is never read as approving a screen
nobody was asked about. A built surface nothing shows is counted with the built and named as having no picture.
"""
from __future__ import annotations

from pathlib import Path

from .drawn import decided_states, surface_pages
from .framed import built_pages, planned_pages, surface_kinds, titled, unseen
from .page_shell import esc


def framed_count(home: Path) -> tuple[int, int]:
    """How many surfaces the storyboard shows as built — framed, or boxed with no picture — and as planned."""
    return len(built_pages(home)) + len(unseen(home)), len(planned_pages(home))


def not_asked(home: Path) -> str:
    """The sentence saying which surfaces a verdict leaves alone, or `""` where the storyboard frames none."""
    built, planned = framed_count(home)
    parts = [f"{count} {word} surface{'' if count == 1 else 's'}" for count, word in ((built, "built"),
                                                                                   (planned, "planned")) if count]
    if not parts:
        return ""
    one = built + planned == 1
    return (f"the {' and '.join(parts)} {'is' if one else 'are'} shown for the flow and "
            f"{'is' if one else 'are'} not asked about")


def kinds_html(root: Path, feature: str) -> str:
    """The four apart, where the storyboard says which each surface is: what is the project's already, what an
    earlier feature has coming, and the two a verdict is asked about. Nothing where it marks none, as before
    there were kinds."""
    home = root / "specs" / feature / "mockups"
    marked = surface_kinds(home)
    boxed = unseen(home)
    if not marked and not boxed:
        return ""
    judged = surface_pages(home)
    named = {"built": [titled(page) for page in built_pages(home)] + [f"{one} (no picture)" for one in boxed],
             "planned": [titled(page) for page in planned_pages(home)],
             "changed": [decided_states(page)[0] for page in judged if marked.get(page.resolve()) == "changed"],
             "new": [decided_states(page)[0] for page in judged if marked.get(page.resolve()) != "changed"]}
    rows = "".join(f'<li><span class="chip {kind}">{kind.capitalize()} · {len(names)}</span> '
                   f'{esc(", ".join(names))}</li>' for kind, names in named.items() if names)
    return f'<ul class="kinds" id="kinds-{esc(feature)}">{rows}</ul>'
