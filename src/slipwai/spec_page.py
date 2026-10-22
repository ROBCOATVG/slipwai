"""The specification, read on the board rather than downloaded from it.

**Continue the build is a person's word that the specification is good**, and the button beside it that
opens the file served the file: `text/plain`, a wall of hashes and asterisks in a browser window, which is
the format for a machine. Somebody being asked to agree to a document should be shown the document.

A renderer of about sixty lines, deliberately. The keel reads no YAML and it carries no markdown library
either, and what has to be rendered here is not the whole of CommonMark: it is what `/draft` and `/mockups`
write, which is Spec Kit's shape — headings, the two kinds of list, tables, rules, fenced code, and bold,
italic and code inside a line. Anything it does not know is shown as the paragraph it came from, which is
the failure the file is readable under. Nothing here follows a link to another file or runs anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

from .page_shell import document, esc

#: One line's worth of markup, in the order it has to be applied: code spans first, because what is inside
#: one is not markup, and the escape has already happened so a `<b>` here is this module's own.
CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")
#: A `*` with space after it opens nothing — "2 * 3" is arithmetic — and one with space before its
#: closer closes nothing either.
ITALIC = re.compile(r"(?<![*\w])\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^\s*[-*+]\s+(.*)$")
NUMBER = re.compile(r"^\s*(\d+)\.\s+(.*)$")
RULE = re.compile(r"^\s*([-*_])\s*\1\s*\1[\s\-*_]*$")
ROW = re.compile(r"^\s*\|(.+)\|\s*$")
#: A cell boundary: a pipe nothing escaped.
CELL = re.compile(r"(?<!\\)\|")
DIVIDER = re.compile(r"^[\s|:-]+$")

STYLE = """
/* A document, not a dashboard: a measure somebody can read without losing the line. The card stays the
   board's width so the page matches every other one; what is held is the text inside it. */
.doc>*{max-width:78ch}
.doc table{max-width:100%}
.doc h1{font-size:1.5rem;margin:0 0 4px}
.doc h2{font-size:1.1rem;margin:26px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--rule)}
.doc h3{font-size:.98rem;margin:20px 0 6px}.doc h4,.doc h5,.doc h6{font-size:.9rem;margin:16px 0 6px}
.doc p{margin:0 0 10px;line-height:1.55}
.doc ul,.doc ol{margin:0 0 12px;padding-left:22px;display:grid;gap:5px;line-height:1.5}
.doc hr{border:0;border-top:1px solid var(--rule-2);margin:22px 0}
.doc table{margin:0 0 14px}
.doc pre{background:var(--paper-2,var(--paper));border:1px solid var(--rule);border-radius:7px;padding:10px 12px;
  overflow-x:auto;font-size:.82rem;margin:0 0 12px}
.doc code{font-family:ui-monospace,Menlo,monospace;font-size:.86em}
.doc :not(pre)>code{background:var(--teal-soft);border-radius:4px;padding:0 3px}
.doc blockquote{margin:0 0 12px;padding:2px 0 2px 14px;border-left:3px solid var(--rule);color:var(--ink-2)}
"""


def inline(text: str) -> str:
    """One line's markup, over text that is already escaped. Code spans first: a `**` inside backticks is
    two asterisks somebody meant to type, and every renderer that applies bold first gets it wrong."""
    held: list[str] = []

    def keep(match: re.Match[str]) -> str:
        held.append(match.group(1))
        return f"\x00{len(held) - 1}\x00"

    text = CODE.sub(keep, text)
    text = LINK.sub(lambda m: f'<a href="{m.group(2)}" rel="noopener">{m.group(1)}</a>', text)
    text = BOLD.sub(r"<b>\1</b>", text)
    text = ITALIC.sub(r"<i>\1</i>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{held[int(m.group(1))]}</code>", text)


def table(rows: list[str]) -> str:
    """A pipe table. The divider row says which line was the header; a table without one is all body."""
    def split(line: str) -> list[str]:
        found = ROW.match(line)
        # On unescaped pipes only: `\|` is a pipe inside a cell, which is how every settings table in
        # this project spells the choice between two values.
        return [one.strip().replace("\\|", "|") for one in CELL.split(found.group(1) if found else line)]

    cells = [split(line) for line in rows]
    head = ""
    if len(cells) > 1 and DIVIDER.match(rows[1]):
        head = "<thead><tr>" + "".join(f"<th>{inline(esc(one))}</th>" for one in cells[0]) + "</tr></thead>"
        cells = cells[2:]
    body = "".join("<tr>" + "".join(f"<td>{inline(esc(one))}</td>" for one in row) + "</tr>" for row in cells)
    return f"<table>{head}<tbody>{body}</tbody></table>"


@dataclass(frozen=True)
class Item:
    """One list item: how far in it sits, what it says, and which of the two kinds of list it is in."""

    indent: int
    text: str
    kind: str


def nested(items: list[Item]) -> str:
    """A run of list items, as the lists their indents and markers say they are.

    A sub-point flattened to a sibling reads as a peer, which changes what the document says; so does a
    bulleted point under a numbered step, which is the shape every acceptance scenario is written in.
    """
    out = ""
    at = 0
    while at < len(items):
        one = items[at]
        under: list[Item] = []
        while at + 1 < len(items) and items[at + 1].indent > one.indent:
            at += 1
            under.append(items[at])
        out += f"<li>{inline(esc(one.text))}{nested(under) if under else ''}</li>"
        if at + 1 < len(items) and items[at + 1].kind != one.kind:
            # Two kinds at one indent are two lists, not one with a changed marker.
            return f"<{one.kind}>{out}</{one.kind}>" + nested(items[at + 1:])
        at += 1
    return f"<{items[0].kind}>{out}</{items[0].kind}>" if items else ""


def rendered(text: str) -> str:
    """The document as HTML. A block at a time, because every construct here is a line or a run of them."""
    out: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    at = 0
    while at < len(lines):
        line = lines[at]
        if line.startswith("```") or line.startswith("~~~"):
            fence = line[:3]
            held: list[str] = []
            at += 1
            while at < len(lines) and not lines[at].startswith(fence):
                held.append(lines[at])
                at += 1
            out.append(f"<pre><code>{esc(chr(10).join(held))}</code></pre>")
        elif RULE.match(line):
            out.append("<hr>")
        elif HEADING.match(line):
            found = HEADING.match(line)
            assert found is not None
            level = min(len(found.group(1)), 6)
            out.append(f"<h{level}>{inline(esc(found.group(2).strip()))}</h{level}>")
        elif ROW.match(line):
            held = []
            while at < len(lines) and ROW.match(lines[at]):
                held.append(lines[at])
                at += 1
            at -= 1
            out.append(table(held))
        elif BULLET.match(line) or NUMBER.match(line):
            items: list[Item] = []
            # One run, whichever marker each line carries: an acceptance scenario is numbered and the
            # points under it are bulleted, and reading the second kind as a continuation of the first
            # ran them into the sentence above. A wrapped item *is* a continuation, though, and most
            # lines here are one — a drafted specification is hard-wrapped at ninety-odd columns.
            while at < len(lines) and lines[at].strip():
                numbered = NUMBER.match(lines[at])
                found = numbered or BULLET.match(lines[at])
                if found is not None:
                    items.append(Item(len(lines[at]) - len(lines[at].lstrip()),
                                      found.group(2 if numbered else 1), "ol" if numbered else "ul"))
                elif items and lines[at].startswith((" ", "\t")):
                    items[-1] = replace(items[-1], text=items[-1].text + " " + lines[at].strip())
                else:
                    break
                at += 1
            at -= 1
            out.append(nested(items))
        elif line.strip().startswith(">"):
            held = []
            while at < len(lines) and lines[at].strip().startswith(">"):
                held.append(lines[at].strip().lstrip(">").strip())
                at += 1
            at -= 1
            out.append(f"<blockquote>{inline(esc(' '.join(held)))}</blockquote>")
        elif line.strip():
            held = []
            while at < len(lines) and lines[at].strip() and not (
                    HEADING.match(lines[at]) or BULLET.match(lines[at]) or NUMBER.match(lines[at])
                    or ROW.match(lines[at]) or RULE.match(lines[at]) or lines[at].startswith("```")):
                held.append(lines[at].strip())
                at += 1
            at -= 1
            out.append(f"<p>{inline(esc(' '.join(held)))}</p>")
        at += 1
    return "".join(out)


def titled(text: str, fallback: str) -> str:
    """The document's own first heading, which is what it calls itself, or the path's feature name."""
    for line in text.split("\n"):
        found = HEADING.match(line)
        if found and len(found.group(1)) == 1 and found.group(2).strip():
            return found.group(2).strip()
    return fallback


def page(where: str, text: str, back: str = "/voyage") -> str:
    """The document, in the board's own shell, with the way back to the window that opened it.

    `now` is a route and not a tab, so the bar is the one link back to the voyage \u2014 and the page is
    still served rather than published, which is what carries the seat onto both links back: this window is
    a view of one project, and the voyage it returns to is that project's.
    """
    body = (f'<style>{STYLE}</style><div class="card doc">{rendered(text)}</div>'
            f'<p class="empty"><a href="{esc(back)}">\u2190 the voyage</a></p>')
    return document(titled(text, where.rsplit("/", 2)[-2] if "/" in where else where), where, body,
                    now="/spec")
