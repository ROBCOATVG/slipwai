"""A page of the board's as one file a person can send to somebody who is not at this board.

A prototype and a storyboard are both served from `127.0.0.1`, so neither can be linked to, and a storyboard
is a folder: its file alone, sent, is a page of empty frames. The copy made here is one HTML file with
everything the page shows inside it — its stylesheets and scripts written in, its pictures as data, each
page it frames as that frame's `srcdoc` (with whatever `sandbox` the frame had), and each page it only links
to drawn at the end with the link pointed there. It opens from a mail attachment with no board, no project
and no connection.

Three things a copy is held to:

- **It carries only what the board would have served.** `allowed` is the caller's own rule for which files
  a page may reach, and a file must also be of a kind a page is made of (`KINDS`): the pages are drawn by an
  agent, and a picture whose address is the project's configuration is not a picture.
- **It says what it is.** A strip the page did not draw says it is a copy, of what and from when, what it
  could not carry, and what it still fetches from the internet. The caller adds what only it knows: where a
  storyboard's verdict stood.
- **Nothing is written.** The copy is made on the way out, like the prototype's reporter.
"""
from __future__ import annotations

import base64
import html
import mimetypes
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import unquote

#: Where the Voyage serves a copy of a mock-up page: `/mockups/`'s own remainder, seat and all.
ROUTE = "/copy/"
#: What a page is made of. Nothing else is read into a copy, whatever a page's address for it says.
KINDS = frozenset({".html", ".htm", ".css", ".js", ".mjs", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                   ".ico", ".woff", ".woff2", ".ttf", ".otf"})
PAGES = frozenset({".html", ".htm"})
#: One file larger than this stays out and is named in the strip: a copy is something a person mails.
LIMIT = 8_000_000
#: A page framing a page framing a page is as deep as a storyboard goes; past this a frame is left as it was.
DEEP = 3

_TAG = re.compile(r"<(link|img|source|iframe|a)\b[^>]*>", re.IGNORECASE)
_SCRIPT = re.compile(r"<script\b([^>]*)>\s*</script>", re.IGNORECASE)
_STYLE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.IGNORECASE | re.DOTALL)
_URL = re.compile(r"""url\(\s*(["']?)([^"')]+)\1\s*\)""", re.IGNORECASE)
_IMPORT = re.compile(r"""@import\s+(?:url\(\s*)?["']([^"']+)["']\s*\)?\s*;""", re.IGNORECASE)
_REMOTE = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
_ELSEWHERE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_BODY = re.compile(r"<body\b[^>]*>", re.IGNORECASE)


def _attribute(name: str) -> re.Pattern[str]:
    return re.compile(rf"""(?<![\w-]){name}\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)


_SRC, _HREF, _REL, _MEDIA = (_attribute(name) for name in ("src", "href", "rel", "media"))


def _value(found: re.Match[str] | None) -> str:
    return html.unescape(found.group(1) if found.group(1) is not None else found.group(2)) if found else ""


@dataclass
class Copy:
    """One copy being made: which files it may read, and what it has to say about itself afterwards."""
    allowed: Callable[[Path], bool]
    left: list[str] = field(default_factory=list)       # asked for by the page and not carried
    remote: int = 0                                     # fetched from the internet when the copy is opened
    linked: list[tuple[str, str]] = field(default_factory=list)  # pages only linked to: title, bundled page

    def file(self, page: Path, address: str) -> Path | None:
        """The file a page's own address names, where a copy may carry it; nothing for an address that
        leaves the page (counted where it is fetched) or names what a copy does not carry (named)."""
        address = address.strip()
        if not address or _ELSEWHERE.match(address):
            return None
        name = unquote(re.split(r"[?#]", address, maxsplit=1)[0])
        try:
            path = (page.parent / name).resolve()
            fits = (path.is_file() and path.suffix.lower() in KINDS and path.stat().st_size <= LIMIT
                    and not any(part.startswith(".") for part in path.parts) and self.allowed(path))
        except (OSError, ValueError):
            fits = False
        if not fits:
            if name and name not in self.left:
                self.left.append(name)
            return None
        return path

    def data(self, page: Path, address: str) -> str:
        """A file as the address that is the file, or the address as it was where it is not carried."""
        if _REMOTE.match(address.strip()):
            self.remote += 1
        path = self.file(page, address)
        if path is None:
            return address
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"

    def sheet(self, page: Path, text: str, depth: int = 0) -> str:
        """A stylesheet with what it imports written in and what it points at as data."""
        def imported(found: re.Match[str]) -> str:
            path = self.file(page, found.group(1)) if depth < DEEP else None
            if path is None or path.suffix.lower() != ".css":
                return found.group(0)
            return self.sheet(path, path.read_text(encoding="utf-8", errors="replace"), depth + 1)

        def pointed(found: re.Match[str]) -> str:
            address = found.group(2)
            return found.group(0) if address.startswith("data:") else f'url("{self.data(page, address)}")'

        return _URL.sub(pointed, _IMPORT.sub(imported, text)).replace("</style", "<\\/style")

    def page(self, page: Path, depth: int = 0, seen: frozenset[Path] = frozenset()) -> str:
        """One page with everything it shows inside it."""
        text = page.read_text(encoding="utf-8", errors="replace")
        seen = seen | {page}

        def script(found: re.Match[str]) -> str:
            address = _value(_SRC.search(found.group(1)))
            if _REMOTE.match(address):
                self.remote += 1
            path = self.file(page, address) if address else None
            if path is None:
                return found.group(0)
            code = path.read_text(encoding="utf-8", errors="replace").replace("</script", "<\\/script")
            return f"<script{_SRC.sub('', found.group(1), count=1).rstrip()}>{code}</script>"

        def tag(found: re.Match[str]) -> str:
            whole, name = found.group(0), found.group(1).lower()
            if name == "a":
                return self.link(page, whole) if depth == 0 else whole
            if name == "link":
                address = _value(_HREF.search(whole))
                if "stylesheet" not in _value(_REL.search(whole)).lower():
                    return _HREF.sub(lambda _: f'href="{self.data(page, address)}"', whole, count=1)
                path = self.file(page, address)
                if path is None:
                    self.remote += bool(_REMOTE.match(address))
                    return whole
                media = _MEDIA.search(whole)
                return (f"<style{' ' + media.group(0) if media else ''}>"
                        f"{self.sheet(path, path.read_text(encoding='utf-8', errors='replace'))}</style>")
            address = _value(_SRC.search(whole))
            if not address:
                return whole
            if name == "iframe" and not _REMOTE.match(address):
                path = self.file(page, address)
                if path is None or path.suffix.lower() not in PAGES or path in seen or depth >= DEEP:
                    return whole
                inside = html.escape(self.page(path, depth + 1, seen), quote=True)
                return _SRC.sub(lambda _: f'srcdoc="{inside}"', whole, count=1)
            return _SRC.sub(lambda _: f'src="{html.escape(self.data(page, address), quote=True)}"', whole, count=1)

        text = _SCRIPT.sub(script, text)
        text = _STYLE.sub(lambda found: found.group(1) + self.sheet(page, found.group(2)) + found.group(3), text)
        return _TAG.sub(tag, text)

    def link(self, page: Path, whole: str) -> str:
        """A link to another page of the project's: that page is drawn at the copy's end and the link goes
        there. Any other link is left as the page wrote it."""
        address = _value(_HREF.search(whole))
        if not address or _ELSEWHERE.match(address) or Path(re.split(r"[?#]", address)[0]).suffix.lower() not in PAGES:
            return whole
        path = self.file(page, address)
        if path is None or path == page.resolve():
            return whole
        inside = self.page(path, 1, frozenset({page.resolve()}))
        named = _TITLE.search(inside)
        title = re.sub(r"\s+", " ", html.unescape(named.group(1))).strip() if named else ""
        title = re.sub(r"^mock(-?up)?:\s*", "", title, flags=re.IGNORECASE) or path.stem  # as the board names it
        if (title, inside) not in self.linked:
            self.linked.append((title, inside))
        return _HREF.sub(lambda _: f'href="#slipwai-copy-{self.linked.index((title, inside)) + 1}"', whole, count=1)

    def appended(self) -> str:
        """The pages a copy's links go to, each in a frame of its own, sandboxed: a script on one of them
        has no business with the page that only linked to it."""
        return "".join(
            f'<section id="slipwai-copy-{number}" style="margin:32px 16px"><h2 style="font:600 16px system-ui,'
            f'sans-serif">{html.escape(title)}</h2><iframe title="{html.escape(title, quote=True)}" '
            f'sandbox="allow-scripts" style="width:100%;height:780px;border:1px solid #d8d4c8;border-radius:8px" '
            f'srcdoc="{html.escape(inside, quote=True)}"></iframe></section>'
            for number, (title, inside) in enumerate(self.linked, 1))

    def said(self) -> str:
        """What the strip adds about the copy itself: what it could not carry, and what it still fetches."""
        words = ""
        if self.left:
            words += f" Not in this copy: {', '.join(self.left[:6])}{' and more' if len(self.left) > 6 else ''}."
        if self.remote:
            words += (f" {self.remote} part{' of it loads' if self.remote == 1 else 's of it load'} from the "
                      "internet, and need a connection.")
        return words


def made(when: date | None = None) -> str:
    when = when or date.today()
    return f"{when.day} {when:%B %Y}"


def strip(words: str, fixed: bool = False) -> str:
    """The strip saying a copy is one. In the page's flow for a document; for something a person plays,
    fixed at the foot and dismissed with one press, so the page it sits on is laid out as it was drawn."""
    look = ("all:initial;display:block;box-sizing:border-box;padding:10px 16px;background:#f3f1ea;color:#2b3a42;"
            "font:14px/1.45 system-ui,sans-serif;")
    if not fixed:
        return f'<div id="slipwai-copy" style="{look}border-bottom:1px solid #d8d4c8">{html.escape(words)}</div>'
    return (f'<div id="slipwai-copy" style="{look}position:fixed;left:0;right:0;bottom:0;z-index:2147483647;'
            f'border-top:1px solid #d8d4c8">{html.escape(words)} <button type="button" '
            f'onclick="this.parentNode.remove()" style="font:inherit;margin-left:8px">Hide this</button></div>')


def bundled(page: Path, allowed: Callable[[Path], bool], words: str, fixed: bool = False) -> str:
    """`page` as one file, under a strip that says `words` and then what the copy says of itself."""
    copy = Copy(allowed)
    text = copy.page(page.resolve())
    end = text.lower().rfind("</body>")
    end = len(text) if end < 0 else end
    text = text[:end] + copy.appended() + text[end:]
    said = strip(words + copy.said(), fixed)
    body = _BODY.search(text)
    return text[:body.end()] + said + text[body.end():] if body else said + text


def download(text: str, name: str) -> tuple[bytes, str, tuple[tuple[str, str], ...]]:
    """What a route sends for a copy: bytes, so nothing of the board's own is added to it, and a name to
    save it under."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "copy"
    return (text.encode("utf-8"), "text/html; charset=utf-8",
            (("Content-Disposition", f'attachment; filename="{safe}.html"'),))


def prototype(page: Path, home: Path, slug: str) -> tuple[bytes, str, tuple[tuple[str, str], ...]]:
    """A sketch's prototype as a file to send, reaching nothing outside the sketch's own folder."""
    if not page.is_file():
        raise ValueError("nothing is drawn yet in this sketch, so there is nothing to copy")
    within = home.resolve()
    words = (f"A copy of the prototype “{slug}”, made {made()}. Tap through it: it is a drawing, and nothing "
             "in it is real or saved.")
    return download(bundled(page, lambda path: path.is_relative_to(within), words, fixed=True), f"{slug}-prototype")


def storyboard(page: Path, allowed: Callable[[Path], bool], feature: str,
               standing: str) -> tuple[bytes, str, tuple[tuple[str, str], ...]]:
    """A feature's storyboard — or one page of its mock-ups — as a file to send, with where its verdict stood."""
    what = "the storyboard" if page.name == "storyboard.html" else f"{page.name}, a mock-up"
    words = (f"A copy of {what} for {feature}, made {made()}. {standing} Verdicts are given on the board, "
             "not on this copy.")
    return download(bundled(page, allowed, words), f"{feature}-{page.stem}")
