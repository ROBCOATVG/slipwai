"""What a storyboard says each surface is, read from the marks on the frames and links that show them.

A further feature is drawn into the flow the project already has, so its storyboard shows four kinds of
surface and says which each is, on the `<iframe>` or `<a>` that shows it (`data-surface`):

- `built` — the project's own, framed from where it lies;
- `planned` — approved for an earlier feature and not built yet, framed from that feature's page;
- `changed` and `new` — this feature's pages, and the only two a verdict is asked about.

`built` and `planned` are the two that are **framed**: shown for the flow, never put up for a verdict, never
counted as drawn.

An unmarked page is read as it always was, and a storyboard that says three words reads as it did when there
were three. `scripts/agents/existing.py` in a generated project reads the same marks, and says which evidence
makes a surface built or planned; this only reads what the storyboard wrote.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

#: The four words, in the order a reader meets them: what is there, what is coming, what this feature does.
KINDS = ("built", "planned", "changed", "new")
#: The two a storyboard frames and nobody is asked about.
FRAMED = ("built", "planned")
_TAG = re.compile(r"<[a-zA-Z][^<>]*>")
_KIND = re.compile(r"""\bdata-surface=["'](built|planned|changed|new)["']""", re.IGNORECASE)
_TARGET = re.compile(r"""(?:src|href)=["']([^"'#?]+\.html)["']""", re.IGNORECASE)
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _tags(home: Path) -> list[str]:
    board = home / "storyboard.html"
    return _TAG.findall(board.read_text(encoding="utf-8", errors="replace")) if board.is_file() else []


def surface_kinds(home: Path) -> dict[Path, str]:
    """Each page the storyboard marks, by its resolved path, with what it says the page is; in its order."""
    found: dict[Path, str] = {}
    for tag in _tags(home):
        kind, target = _KIND.search(tag), _TARGET.search(tag)
        if kind and target:
            found.setdefault((home / target.group(1)).resolve(), kind.group(1).lower())
    return found


def framed_pages(home: Path, kind: str) -> list[Path]:
    """The pages a storyboard frames as `kind` — inside the project, and there — in the order it shows them."""
    project = home.parents[2].resolve()
    return [page for page, said in surface_kinds(home).items()
            if said == kind and page.is_file() and page.is_relative_to(project)]


def built_pages(home: Path) -> list[Path]:
    return framed_pages(home, "built")


def planned_pages(home: Path) -> list[Path]:
    return framed_pages(home, "planned")


def titled(page: Path) -> str:
    """A framed page's own title, whole: a preview's is `<surface> — <state>`, and both halves are the name."""
    title = _TITLE.search(page.read_text(encoding="utf-8", errors="replace")[:8192])
    plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", title.group(1)))).strip() if title else ""
    return plain or page.stem


def app_look(root: Path, path: Path) -> bool:
    """Whether a resolved path is a browser app's own preview or stylesheet: what a storyboard frames as built,
    and what a new surface links to look like this product. `screens/` and `src/styles/` of a deployable
    `project.json` records as `web`, and nothing else of the app."""
    try:
        held = json.loads((root / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    apps = held.get("deployables") if isinstance(held, dict) else None
    for record in apps.values() if isinstance(apps, dict) else []:
        if isinstance(record, dict) and record.get("kind") == "web" and isinstance(record.get("path"), str):
            home = (root / record["path"]).resolve()
            if path.is_relative_to(home / "screens") or path.is_relative_to(home / "src" / "styles"):
                return True
    return False
