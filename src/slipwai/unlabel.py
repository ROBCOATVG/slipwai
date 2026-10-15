"""The adoption label's respell: what `slipwai migrate` takes off the files no merge reaches.

slipwai 1.3.x wrote "experimental" into four places a merge never carries (the `AGENTS.md` block, two survey
pages, the installed constitution copy). This release spells none of it, so a migration takes the old label off
exactly where 1.3.x put it and nowhere else, leaving every other byte of each file, line endings included, as
it is. `migrate.refresh` calls `unlabel` before it re-derives the projections, and `Refresh` is the record of
both: what was respelled, what was projected, what was left alone.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .layout import Layout

# What slipwai 1.3.x wrote as the adoption label, in the files no merge carries (`replay` regenerates only what
# `<delivery>/.written` lists; the `AGENTS.md` block and the survey pages are the repository's from the day they were
# written). Exactly these strings and nothing near them, so a person's own words are never touched; each right-hand
# side is byte for byte what this release writes, so a later `/survey` rewrites nothing. A survey label is taken
# off only where 1.3.x wrote it: in the page's header, before its first `## ` line, straight after the sentence
# it followed (the anchor). A copy anywhere else, or one left after the keel's is gone, is the person's.
BLOCK_BEGIN = "<!-- extension:delivery:begin -->\n"
HEADING = re.compile(r"(?m)^(## Delivery method \(installed by slipwai [^;\n)]+); experimental\)$")
UNLABELLED = (
    ("survey/survey.md", "file that said so.", " Experimental: see `../docs/adoption.md`."),
    ("survey/structure.md", "the graph holds the edge.", "\nExperimental: see `../docs/adoption.md`."),
)
SECTION = re.compile(r"(?m)^## ")
# The keel's sentence is the paragraph that opens "Written by `slipwai adopt` (": the label is taken off only inside
# it, so a person's exact quote of the sentence elsewhere in the header is theirs on the first run and on every one
# after the keel's own copy is gone.
FACTORY_PARAGRAPH = re.compile(r"(?ms)^Written by `slipwai adopt` \(.*?(?=(?:\r?\n){2}|\Z)")
CONSTITUTION = ".specify/memory/constitution.md"
CONSTITUTION_ANCHOR = (
    "     a principle marked `journey:` is a target, not yet in force, and check-constitution holds it to the\n"
    "     map."
)
CONSTITUTION_LABEL = " Experimental, with the rest of adoption."


@dataclass(frozen=True)
class Refresh:
    """Re-deriving the project's own projections after the merge: what moved, or why it could not run."""

    changed: tuple[str, ...] = ()
    # The files the adoption label was taken off, in the commit that carries them: not projections, not in `changed`.
    respelled: tuple[str, ...] = ()
    # Whether the projector ran and wrote: the projections are ignored by Git, so a re-derivation that changed every
    # one of them stages nothing, and `changed` is only what a project still tracks from before they were ignored.
    written: bool = False
    # Why the projector could not be run to completion, for a report that says so rather than swallowing it.
    failed: str | None = None
    # A commit git refused (a hook, a missing identity): what it said. `uncommitted` is what is left staged or modified.
    refused: str | None = None
    uncommitted: tuple[str, ...] = ()
    # The pages the respell left alone, each with why: a symbolic link is never written through.
    skipped: tuple[str, ...] = ()
    # Whether this checkout was pointed at the project's own git hooks, and the sentence where it was not —
    # a path somebody else owns is reported and never taken. Empty where there was nothing to say.
    hooked: bool = False
    hooks: str = ""


def read_page(page: Path) -> str | None:
    """A page's text with its line endings exactly as they are on disk (`read_text` would turn CRLF into LF and
    the write back would keep it that way). None where it cannot be read as UTF-8."""
    try:
        return page.read_bytes().decode("utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def write_page(page: Path, text: str) -> None:
    page.write_bytes(text.encode("utf-8"))


def endings(text: str) -> tuple[str, ...]:
    """The line endings to try against `text`, its own first: the strings this release matches spell `\n`, and a
    file a person's editor or `core.autocrlf` gave CRLF spells every one `\r\n`."""
    return ("\r\n", "\n") if "\r\n" in text else ("\n", "\r\n")


def unlabel(root: Path, layout: Layout) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Take the label 1.3.x wrote off the four places no merge reaches, leaving the rest of each file as it is,
    byte for byte, line endings included. Nothing is written where the string is not, so a repository adopted by
    this release, and a generated project, which has none of these files, come out untouched. Never writes through
    a symbolic link, and never a byte outside `root`: such a page is left alone and named. Returns the files it
    wrote, root-relative, and the ones it left alone, each with why."""
    written: list[str] = []
    skipped: list[str] = []
    real = root.resolve()

    def load(page: Path, name: str) -> str | None:
        if not page.is_file():
            return None
        if page.is_symlink() or not page.resolve().is_relative_to(real):
            if b"xperimental" in page.read_bytes():
                skipped.append(f"{name} (a symbolic link, so the label in what it points to is not this command's "
                               "to write)")
            return None
        text = read_page(page)
        if text is None and b"xperimental" in page.read_bytes():
            skipped.append(f"{name} (not UTF-8, so it is read as nothing and left as it is)")
        return text

    agents = root / "AGENTS.md"
    text = load(agents, "AGENTS.md")
    if text is not None:
        for eol in endings(text):
            begin = text.find(BLOCK_BEGIN.replace("\n", eol))
            if begin < 0:
                continue
            # Only the heading on the line after the marker: the same words further down are the person's.
            start = begin + len(BLOCK_BEGIN.replace("\n", eol))
            end = text.find("\n", start)
            line = text[start:] if end < 0 else text[start:end]
            carriage = "\r" if line.endswith("\r") else ""
            bare = line[:len(line) - len(carriage)]
            respelled = HEADING.sub(r"\1)", bare)
            if respelled != bare:
                write_page(agents, text[:start] + respelled + carriage + text[start + len(line):])
                written.append("AGENTS.md")
            break
    for name, anchor, label in UNLABELLED:
        page = root / layout.under(name)
        text = load(page, layout.under(name))
        if text is None:
            continue
        for eol in endings(text):
            spelled = label.replace("\n", eol)
            section = SECTION.search(text)
            header = text[:section.start()] if section else text
            paragraph = FACTORY_PARAGRAPH.search(header)
            if paragraph is None:
                continue
            base = paragraph.start()
            header = paragraph.group()
            at = header.find(anchor + spelled)
            # A label straight after the keel's own is a repeated copy: which of the two is the person's cannot
            # be told once written, so both stay, and a second migration cannot take the one the first left.
            if at >= 0 and not header.startswith(spelled, at + len(anchor) + len(spelled)):
                cut = base + at + len(anchor)
                write_page(page, text[:cut] + text[cut + len(spelled):])
                written.append(layout.under(name))
                break
    # The installed constitution copy, which `./init` made from the template 1.3.x labelled: the label sits in the
    # template's closing note, straight after the sentence it followed. Taken off only there, and only when that
    # note appears once; the same words anywhere else are the person's.
    constitution = root / CONSTITUTION
    text = load(constitution, CONSTITUTION)
    if text is not None:
        for eol in endings(text):
            anchor = CONSTITUTION_ANCHOR.replace("\n", eol)
            if text.count(anchor + CONSTITUTION_LABEL) == 1:
                write_page(constitution, text.replace(anchor + CONSTITUTION_LABEL, anchor))
                written.append(CONSTITUTION)
                break
    return tuple(written), tuple(skipped)
