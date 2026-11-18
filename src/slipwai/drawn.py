"""The surfaces a storyboard shows, and the states on each page, read from the page and nothing else.

A surface is one HTML page; `<title>` names it and each `<article class="state">`'s first `<h2>` names a
state. That is the whole of what the board reads from a drawing, whether the stage drew it or a person
handed it over under `docs/design/`, and it is the contract `docs/reference/the-brief.md` states for a
folder at the front door. It is read here, in one place, so the Voyage window's approve button, the
upstream stop that approves without a person, and `slipwai brief check` cannot each read a page their own
way: two readings of "drawn" were once a storyboard the board offered to approve and then could not.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
from pathlib import Path

_FEATURE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
_ARTICLE = re.compile(r'<article\b(?P<tag>[^>]*\bclass="[^"]*\bstate\b[^"]*"[^>]*)>(?P<body>.*?)</article>',
                      re.IGNORECASE | re.DOTALL)
#: Who chose a state, where the page says: `person` or `proposed` as the reference page spells them, or a name.
_DECIDED = re.compile(r'\bdata-decided="([^"]*)"', re.IGNORECASE)
_HEADING = re.compile(r"<h2>(.*?)</h2>", re.IGNORECASE | re.DOTALL)
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_NOT_A_SURFACE = frozenset({"storyboard.html", "index.html"})
#: A page the storyboard embeds or links: where the surfaces are when they were handed over rather than drawn.
_EMBEDDED = re.compile(r"""(?:src|href)=["']([^"'#?]+\.html)["']""", re.IGNORECASE)
#: What a page with no state article is: one state, the page as shown.
SHOWN = "shown"
#: What a storyboard says a surface is, on the frame or link that shows it (`data-surface`). `built` is the
#: project's own, framed from where it lies and never put up for a verdict; `changed` and `new` are this
#: feature's pages. An unmarked page is read as it always was.
KINDS = ("built", "changed", "new")
_TAG = re.compile(r"<[a-zA-Z][^<>]*>")
_KIND = re.compile(r"""\bdata-surface=["'](built|changed|new)["']""", re.IGNORECASE)


def _plain(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _surface_name(title: str, stem: str) -> str:
    title = re.sub(r"^\s*mock(-?up)?:\s*", "", _plain(title), flags=re.IGNORECASE)
    for mark in ("—", " - "):
        if mark in title:
            title = title.split(mark)[-1].strip()
    return title or stem


def decided_states(page: Path) -> tuple[str, list[tuple[str, str]]]:
    """One page as the board reads it: the surface its title names, and each state its articles name with
    who decided it — `data-decided` on the article, or `""` where the page does not say.

    A page with no article is one state, `shown` — a plain page is still a drawing somebody can approve.
    Two articles with the same heading are one state, and the first says who decided it.
    """
    text = page.read_text(encoding="utf-8", errors="replace")
    title = _TITLE.search(text)
    name = _surface_name(title.group(1) if title else "", page.stem)
    states: list[tuple[str, str]] = []
    for article in _ARTICLE.finditer(text):
        heading = _HEADING.search(article.group("body"))
        label = _plain(heading.group(1)) if heading else ""
        if label and label not in [state for state, _ in states]:
            who = _DECIDED.search(article.group("tag"))
            states.append((label, who.group(1).strip() if who else ""))
    return name, states or [(SHOWN, "")]


def page_states(page: Path) -> tuple[str, list[str]]:
    """The surface and its states, without who decided each: what every reader before `data-decided` reads."""
    name, states = decided_states(page)
    return name, [state for state, _ in states]


def decided(who: str) -> str:
    """The suffix a verdict line carries for who chose the state, or nothing where the page did not say.

    After the verdict, so the three readers of the line — `check-surfaces.py`, the surfaces agent and the
    feedback reader — which match `approved` and `parked` at a word boundary, read it as they always did.
    """
    if not who:
        return ""
    if who.lower() == "proposed":
        return " (proposed)"
    return " (decided by a person)" if who.lower() == "person" else f" (decided by {who})"


def surface_kinds(home: Path) -> dict[Path, str]:
    """Each page the storyboard marks, by its resolved path, with what it says the page is; in its order."""
    board = home / "storyboard.html"
    found: dict[Path, str] = {}
    if not board.is_file():
        return found
    for tag in _TAG.findall(board.read_text(encoding="utf-8", errors="replace")):
        kind, target = _KIND.search(tag), _EMBEDDED.search(tag)
        if kind and target:
            found.setdefault((home / target.group(1)).resolve(), kind.group(1).lower())
    return found


def built_pages(home: Path) -> list[Path]:
    """The pages a storyboard frames as built — inside the project, and there — in the order it shows them."""
    project = home.parents[2].resolve()
    return [page for page, kind in surface_kinds(home).items()
            if kind == "built" and page.is_file() and page.is_relative_to(project)]


def titled(page: Path) -> str:
    """A built page's own title, whole: a preview's is `<surface> — <state>`, and both halves are the name."""
    title = _TITLE.search(page.read_text(encoding="utf-8", errors="replace")[:8192])
    return (_plain(title.group(1)) if title else "") or page.stem


def surface_pages(home: Path) -> list[Path]:
    """The surfaces of one feature's mock-ups: the pages beside the storyboard, else the pages it embeds or links.

    Every page but the storyboard and the contents page, where the stage drew them. Where it drew none, because
    a person handed the mock-ups over (`docs/design/`) and the stage storyboarded those instead of redrawing
    them, the surfaces are the pages the storyboard shows — inside the project, and there. Never a page the
    storyboard marks `built`: that is the project's own, shown for the flow, and nobody is asked about it. The
    one reading of "drawn" for every question that asks it: two readings were a storyboard the board offered
    to approve and then could not.
    """
    kinds = surface_kinds(home)
    beside = sorted(page for page in home.glob("*.html")
                    if page.name not in _NOT_A_SURFACE and kinds.get(page.resolve()) != "built")
    board = home / "storyboard.html"
    if beside or not board.is_file():
        return beside
    project, shown = home.parents[2].resolve(), []
    for target in _EMBEDDED.findall(board.read_text(encoding="utf-8", errors="replace")):
        page = (home / target).resolve()
        if page.is_file() and page.is_relative_to(project) and page.name not in _NOT_A_SURFACE \
                and page not in shown and kinds.get(page) != "built":
            shown.append(page)
    return shown


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


def drawn_states(root: Path, feature: str) -> list[tuple[str, list[str]]]:
    """Each drawn surface and the states on its page. The storyboard and the contents page are not surfaces."""
    if not _FEATURE.fullmatch(feature):
        raise ValueError(f"no feature {feature}")
    home = (root / "specs" / feature / "mockups").resolve()
    if not home.is_dir() or not home.is_relative_to((root / "specs").resolve()):
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    found = [page_states(page) for page in surface_pages(home)]
    if not found:
        raise ValueError(f"nothing drawn under specs/{feature}/mockups")
    return found


def record_verdict(root: Path, feature: str, verdict: str, reason: str = "", by: str = "") -> str:
    """Write `mock-states.md` from the drawings a person has just approved or disapproved.

    Approving marks every drawn state approved. Disapproving parks them, and a park with no reason is a
    blank, which is the one mark this file refuses. `by` is a first line saying who gave the verdict, where
    it was not a person. A surface the storyboard frames as built gets a line saying so and no verdict: it
    was shown for the flow, and a state marked approved here is a state the split then has to deliver.
    """
    if verdict not in ("approved", "parked"):
        raise ValueError("approve or disapprove the storyboard")
    why = re.sub(r"\s+", " ", reason).strip()
    if verdict == "parked" and not why:
        raise ValueError("say why you disapprove, so the next drawing knows what to change")
    lines: list[str] = [by, ""] if by else []
    # The same pages `drawn_states` reads, with who decided each state kept: the refusals above are its.
    drawn_states(root, feature)
    built = built_pages(root / "specs" / feature / "mockups")
    lines += [f"<!-- built: {titled(page)} — {where_in(root, page)} (shown as built: no verdict was asked "
              "or given) -->" for page in built] + ([""] if built else [])
    for page in surface_pages(root / "specs" / feature / "mockups"):
        name, states = decided_states(page)
        # Which page, and what it said, when the verdict was given: a page that says something else since —
        # changed in a conversation, by hand, or gone — is a page nobody has given this verdict on.
        lines.append(f"<!-- page: {where_in(root, page)} {digest(page)} -->")
        lines.append(f"## Surface: {name}")
        mark = "approved" if verdict == "approved" else f"parked: {why}"
        lines.extend(f"- {state} — {mark}{decided(who)}" for state, who in states)
        lines.append("")
    (root / "specs" / feature / "mockups" / "mock-states.md").write_text("\n".join(lines), encoding="utf-8")
    return "approved" if verdict == "approved" else "disapproved"


# A verdict stands for the pages it was given on. `record_verdict` writes, above each surface's block, the page
# and a digest of what it said; a page that no longer says that is a verdict nobody gave. A conversation that
# changes a page takes its block out and leaves a `withdrawn` line in its place, once per page; a page changed
# any other way is read as withdrawn all the same. `storyboard.html` is the flow between the surfaces, not one:
# a change to it withdraws nothing.
PAGE = re.compile(r"^<!-- page: (?P<path>\S+) (?P<digest>[0-9a-f]{8,40}) -->$")
WITHDRAWN = re.compile(r"^<!-- withdrawn: (?P<surface>.+?) — (?P<states>.*?) \((?:page (?P<path>\S+); )?changed ",
                       re.MULTILINE)
STATE_LINE = re.compile(r"^-\s*(?P<state>.+?)\s*—\s*(?:approved|parked|n/a)\b")


def where_in(root: Path, page: Path) -> str:
    try:
        return page.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return page.as_posix()


def digest(page: Path, raw: bool = False) -> str:
    """What a page says, as a short digest — of its lines with their endings and trailing spaces let go of, so a
    page saved with CRLF or a newline more says what it said. `raw` is the bytes as they are, which a verdict
    recorded before this reading carries."""
    try:
        data = page.read_bytes()
    except OSError:
        return "0" * 16
    if not raw:
        lines = data.decode("utf-8", "replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        data = "\n".join(line.rstrip() for line in lines).strip("\n").encode("utf-8")
    return hashlib.sha1(data).hexdigest()[:16]


def fingerprints(root: Path) -> dict[str, str]:
    """Every surface page of every feature, by its path in the project, with a digest of what it says now:
    taken before a conversation turn and again after it, so what the turn changed is known by its pages."""
    specs = root / "specs"
    homes = sorted(specs.glob("*/mockups")) if specs.is_dir() else []
    return {where_in(root, page): digest(page) for home in homes for page in surface_pages(home)}


def blocks(text: str) -> list[dict]:
    """`mock-states.md` as its surface blocks: the name, the page and digest written above it (where the verdict
    carried one), the states, and the lines it spans."""
    found: list[dict] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("## Surface: "):
            continue
        above = PAGE.match(lines[index - 1]) if index else None
        end = next((at for at in range(index + 1, len(lines)) if lines[at].startswith(("## ", "<!-- page: "))),
                   len(lines))
        states = [match.group("state") for match in map(STATE_LINE.match, lines[index:end]) if match]
        found.append({"name": line.removeprefix("## Surface: ").strip(), "states": states,
                      "path": above.group("path") if above else "", "digest": above.group("digest") if above else "",
                      "start": index - 1 if above else index, "end": end})
    return found


def stale(root: Path, block: dict) -> bool:
    """Whether a block's page no longer says what it said when the verdict was given — or is gone."""
    page = root / block["path"]
    return bool(block["path"]) and block["digest"] not in (digest(page), digest(page, raw=True))


def withdraw(root: Path, before: dict[str, str]) -> list[str]:
    """After a conversation turn: every verdict on a page that changed — in the turn, or since the verdict — is
    taken out of its feature's `mock-states.md` and said there as withdrawn, once, so the file approves nothing
    nobody has seen. A verdict written before pages were recorded beside it is matched by its surface's name,
    where exactly one page has that name. Answers `<surface> — <states>` for each, for the board to say which."""
    after = fingerprints(root)
    changed = {path for path, one in after.items() if before.get(path) != one}
    said: list[str] = []
    for verdicts in sorted((root / "specs").glob("*/mockups/mock-states.md")) if (root / "specs").is_dir() else []:
        try:
            text = verdicts.read_text(encoding="utf-8")
        except OSError:
            continue
        if "surfaces: none" in text:
            continue
        pages = [(where_in(root, page), decided_states(page)[0]) for page in surface_pages(verdicts.parent)]
        titles = [title for _, title in pages]
        named = {title for path, title in pages if path in changed and titles.count(title) == 1}
        dropping = [one for one in blocks(text) if stale(root, one) or (not one["path"] and one["name"] in named)]
        if not dropping:
            continue
        lines, gone = text.splitlines(), {at for one in dropping for at in range(one["start"], one["end"])}
        had = {(found.group("surface"), found.group("path") or "") for found in WITHDRAWN.finditer(text)}
        when = time.strftime("%Y-%m-%d %H:%M")
        # "In a conversation" only where the board saw the turn change the page; a change it did not see is not one.
        marks = [f"<!-- withdrawn: {one['name']} — {', '.join(one['states'])} ("
                 + (f"page {one['path']}; " if one["path"] else "") + "changed "
                 + ("in a conversation " if one["path"] in changed or not one["path"] else "")
                 + f"at {when}, after this verdict: approve or disapprove the storyboard again) -->"
                 for one in dropping if (one["name"], one["path"]) not in had]
        kept = [line for at, line in enumerate(lines) if at not in gone]
        verdicts.write_text("\n".join([*marks, *kept]) + "\n", encoding="utf-8")
        said += [f"{one['name']} — {', '.join(one['states'])}" for one in dropping]
    return said


def withdrawn_parts(root: Path, feature: str) -> tuple[list[str], list[str]]:
    """The surfaces whose verdict no longer stands, `<surface> — <states>`, in two lists: those a conversation the
    board saw changed, and those changed any other way — by hand, renamed, gone. Empty until something is judged."""
    try:
        text = (root / "specs" / feature / "mockups" / "mock-states.md").read_text(encoding="utf-8")
    except OSError:
        return [], []
    seen: list[str] = []
    since: list[str] = []
    for found in WITHDRAWN.finditer(text):
        line = text[found.start():text.find("\n", found.start())]
        (seen if "changed in a conversation" in line else since).append(
            f"{found.group('surface')} — {found.group('states')}")
    since += [f"{one['name']} — {', '.join(one['states'])}" for one in blocks(text) if stale(root, one)]
    return list(dict.fromkeys(seen)), [one for one in dict.fromkeys(since) if one not in seen]


def withdrawn(root: Path, feature: str) -> list[str]:
    """Every surface whose verdict no longer stands, however it changed (`withdrawn_parts`)."""
    seen, since = withdrawn_parts(root, feature)
    return [*seen, *since]

