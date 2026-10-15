"""The chandlery as a page: what this copy has, what the channels offer, and a button that installs one.

Finding out that a package exists is the question version 1 had no answer to, and version 2's answer was
`slipwai search` — which is the right answer for somebody already in a terminal and no answer at all for
the person who typed one word and got a board. This is that listing, as a tab of the same page.

**It is `search` and the install verbs, rendered.** The rows are the same `offered()` over the same index
`install` fetches from, so what this shows is what installing would fetch; the button calls the function
the verb calls, per kind. A second path that fetched or staged its own way would be a second thing to keep
in step and the first one to drift, which is the bridge's rule and this is the bridge.

**Every kind, a table each.** A language, an extension, a target and a quickstart are all packages — the
index lists them in one block and tells them apart by `kind` — so the page tells them apart the same way,
and a fifth kind is a row in `SECTIONS` rather than a section written out here.

**A publisher is accepted on the page, deliberately.** `trust.admitted` refuses a named publisher this
machine has not agreed to, and the terminal's answer to that is `--accept-publisher`. A page cannot pass a
flag, and installing without one would be the board quietly deciding the thing the terminal makes a person
say out loud. So a row whose publisher this machine has not accepted carries a tick-box naming them, and
the install is refused until it is ticked — the same question, asked where the person already is.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from . import quickstart
from .assets import this_command
from .catalog import reread
from .cli_language import reach, snapshots
from .cli_search import summary
from .errors import GenerationError
from .extension_install import catalogue as extensions_here
from .extension_install import install as put_extension
from .index_schema import EXTENSION, LANGUAGE, QUICKSTART, TARGET
from .language_directory import directory
from .language_index import Index, Release
from .language_install import builtin, installed
from .language_plan import install as put_language
from .page_shell import WORKS, document, esc
from .quickstart_install import install as put_quickstart
from .target_install import catalogue as targets_here
from .target_install import install as put_target
from .trust import trusted
from .versions import key

WHERE = "/packages"
#: What each kind is called here and the sentence under it. Plain words and the install verb's own: a reader
#: on this page is choosing what their project is written in, not learning the index's vocabulary — but the
#: command named under each is the one they will type the second time, from a script or from habit.
SECTIONS: tuple[tuple[str, str, str], ...] = (
    (LANGUAGE, "Languages", "what a service is written in — a project needs one"),
    (EXTENSION, "Extensions", "optional dev tooling, elected in a project with `./init --extension <key>`"),
    (TARGET, "Targets", "where a project is deployed to"),
    (QUICKSTART, "Quickstarts", "a settled set of answers to start from, offered before `generate`'s "
                 "first question and given by `generate --quickstart <name>`"),
)
#: The kinds whose install asks about the publisher, which is the only place the tick-box means anything.
#: A language's install does not ask — nothing on the language path calls `trust.admitted` — and a box that
#: did nothing would be the page claiming to have asked a question it never put.
ASKS_PUBLISHER = (EXTENSION, TARGET, QUICKSTART)
BUILT_IN = "built in"


@dataclass(frozen=True)
class Row:
    """One package, as the table has it: here already, or offered and installable in one press."""

    name: str
    kind: str
    version: str
    what: str
    here: bool
    newer: str = ""
    publisher: str = ""
    accepted: bool = True

    @property
    def asked(self) -> bool:
        """Whether this row has a publisher to accept before it can be installed."""
        return not self.here and bool(self.publisher) and not self.accepted and self.kind in ASKS_PUBLISHER


def listed(found: Index | None, kind: str) -> int:
    """How many packages of this kind the channels list at all, whatever keel they were built for.

    Told apart from what this keel can load, because the two are different answers and an empty table that
    gave the wrong one would be the page inventing a compatibility problem. A channel that lists no
    extension at all is not a channel whose extensions are too new.
    """
    if found is None:
        return 0
    return len({name for name, releases in found.releases.items()
                if any(release.kind == kind for release in releases)})


def chandlery(prerelease: bool | None = None) -> tuple[dict[str, Release], str, list[str], Index | None]:
    """What the channels offer this keel, which channel said so, and the lines saying one could not be read.

    The reaching is here and the rendering is below it, the way `search` has it: a page that fetched inside
    its own render could not be tested without a server, and the half worth testing is the render.
    """
    found, offer, unreachable = reach(snapshots() if prerelease is None else prerelease, kind=None)
    return offer, found.name if found is not None else "", [line.strip() for line in unreachable], found


def here() -> dict[str, dict[str, tuple[str, str]]]:
    """Every package installed on this machine, by kind, each with its version and its own sentence.

    Four readers because a kind is a manifest: the three directory kinds are told apart by the file each
    carries, and a quickstart is a document in a directory of its own rather than a package directory at all.
    """
    place = directory()
    files = installed(place)
    said: dict[str, dict[str, tuple[str, str]]] = {kind: {} for kind, _, _ in SECTIONS}
    for name, family in builtin().items():
        said[LANGUAGE][name] = (BUILT_IN, f"the {family} family, carried by this keel")
    for name, one in files.items():
        if (one.root / "language.json").is_file():
            said[LANGUAGE][name] = (one.version, str((one.fragment or {}).get("description", "")))
    for name, manifest in extensions_here(place):
        said[EXTENSION][name] = (version_of(files, name), str(manifest.get("description", "")
                                                              or manifest.get("name", "")))
    for name, manifest in targets_here(place):
        said[TARGET][name] = (version_of(files, name), str(manifest.get("label", "")))
    carried = quickstart.carried()
    for name in quickstart.names():
        said[QUICKSTART][name] = (BUILT_IN if name in carried else "", suits(name))
    return said


def suits(name: str) -> str:
    """A quickstart's own sentence about the product it suits — the one thing worth putting in its row.

    Nothing where the document cannot be read, which is a file somebody edited by hand: it is still listed,
    because the table says what this machine has and a row that vanished when its file went wrong would
    leave a person looking for a quickstart they can see in the directory.
    """
    try:
        return quickstart.find(name).suits
    except GenerationError:
        return ""


def version_of(files: Mapping[str, object], name: str) -> str:
    """The `VERSION` beside a package directory, or nothing where it carries none."""
    return str(getattr(files.get(name), "version", ""))


def sections(offer: Mapping[str, Release]) -> dict[str, list[Row]]:
    """Every package this page shows, by kind: what is here first, then what the chandlery offers that is not.

    An installed package the index does not list is shown all the same — a local install is an install, and a
    listing that dropped it would be a page disagreeing with the directory it is about.
    """
    mine = here()
    found: dict[str, list[Row]] = {}
    for kind, _, _ in SECTIONS:
        rows = [installed_row(kind, name, version, what, offer.get(name))
                for name, (version, what) in sorted(mine[kind].items())]
        rows += [offered_row(kind, name, release) for name, release in sorted(offer.items())
                 if release.kind == kind and name not in mine[kind]]
        found[kind] = rows
    return found


def installed_row(kind: str, name: str, version: str, what: str, release: Release | None) -> Row:
    """A package that is here. The index's sentence about it first, because a publisher writes that one for
    people browsing and a manifest's `description` is written for the keel."""
    newer = release.version if release is not None and version not in ("", BUILT_IN) and key(
        release.version) > key(version) else ""
    return Row(name, kind, version, (summary(release) if release is not None else "") or what, True, newer)


def offered_row(kind: str, name: str, release: Release) -> Row:
    return Row(name, kind, release.version, summary(release), False, publisher=release.publisher,
               accepted=not release.publisher or trusted(release.publisher))


def put(kind: str, name: str, accept: bool) -> list[str]:
    """Install one package, by the verb's own function, and read the directory again. What it said, a line
    each, or its refusal.

    **The re-read is the half a verb does not need.** A command installs and exits, and the process that
    generates next is a new one that reads the directory as it now is. The board is one process: without
    this, a language installed from the page is on disk and in the packages tab, which re-reads, and absent
    from the interview's menus, which read the catalogue built when the server started — and the person this
    page is for is exactly the person who cannot restart a server to fix that.

    `language_plan.install` takes no publisher: nothing on that path calls `trust.admitted`, so there is
    nothing for the page to accept on its behalf and a parameter here would imply there was.
    """
    if not name:
        raise GenerationError("an install needs a package to install")
    place = directory()
    if kind == LANGUAGE:
        said = put_language([name], place, prerelease=snapshots())
    elif kind == EXTENSION:
        said = put_extension([name], place, accept)
    elif kind == TARGET:
        said = put_target([name], place, accept)
    elif kind == QUICKSTART:
        # A quickstart is answers and installs no code, so it changes nothing the catalogue holds.
        return put_quickstart([name], quickstart.directory(), accept)
    else:
        raise GenerationError(f"{kind or 'nothing'} is not a kind of package this board installs")
    reread()
    return said


def action(row: Row) -> str:
    """The right-hand cell: what an installed package is, or what it takes to have one that is not."""
    if row.here:
        return ('<span class="chip">installed</span>' if not row.newer else
                f'<span class="chip" data-state="waiting on you">{esc(row.newer)} available</span>')
    accept = (f'<label class="accept"><input type="checkbox" id="accept-{esc(row.name)}">'
              f"accept {esc(row.publisher)}</label>") if row.asked else ""
    return (f'{accept}<button class="go" data-install="{esc(row.name)}" '
            f'data-kind="{esc(row.kind)}">Install</button>')


def nothing_here(kind: str, where: str, found: Index | None) -> str:
    """The sentence an empty table gets: which of the three reasons it is empty for."""
    if not where:
        return "Nothing installed here, and no channel could be read."
    total = listed(found, kind)
    if not total:
        return f"Nothing installed, and {esc(where)} lists none yet."
    return (f"Nothing installed. {esc(where)} lists {total}, and this keel can load none of them: "
            f"<code>{esc(this_command())} upgrade</code> moves the keel.")


def table(rows: list[Row], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{empty}</p>'
    head = "<tr><th>Package</th><th>Version</th><th>What it is</th><th>Publisher</th><th></th></tr>"
    body = "".join(
        f"<tr><td><b>{esc(row.name)}</b></td><td class=\"mono\">{esc(row.version or '—')}</td>"
        f"<td>{esc(row.what)}</td><td>{esc(row.publisher or '—')}</td>"
        f'<td class="doing">{action(row)}</td></tr>' for row in rows)
    return f"<table>{head}{body}</table>"


def card(kind: str, title: str, why: str, rows: list[Row], empty: str) -> str:
    command = f"{this_command()} {kind} install <name>"
    return (f'<div class="card"><h2>{esc(title)}</h2><p class="empty">{esc(why)} · <code>'
            f"{esc(command)}</code></p>{table(rows, empty)}</div>")


#: The one thing the page does that a link could not: install without leaving it. A press, the report, and
#: then the page again — every control on the board reloads, because the board is a fold of what is on disk
#: and a page that showed a package installed without re-reading the directory would be the one view that
#: was a memory of a click rather than a reading of the machine.
SCRIPT = WORKS + """
const said = () => document.getElementById('said');
document.addEventListener('click', async event => {
  const button = event.target.closest('[data-install]');
  if (!button) return;
  const box = document.getElementById('accept-' + button.dataset.install);
  const out = said();
  out.hidden = false;
  out.className = 'said';
  out.textContent = 'installing ' + button.dataset.install + '…';
  // In the button as well as in the log: an install reaches the network and the log is a card away, so a
  // row that went quiet read as a press that never landed — which is a press somebody makes again.
  const was = working(button, 'Installing…');
  let answer;
  try {
    answer = await fetch('/packages/install', {method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({kind: button.dataset.kind, name: button.dataset.install,
                            accept: !!(box && box.checked)})});
    out.textContent = await answer.text();
  } catch (fault) {
    out.textContent = 'the board could not be reached: ' + fault;
    out.className = 'said bad';
    return;
  } finally { was(); }
  if (answer.ok) {
    out.textContent += '\\n\\nreading the package directory again…';
    working(button, 'Installed');
    setTimeout(() => location.reload(), 1500);
  } else out.className = 'said bad';
});
"""

STYLE = """
td.doing{text-align:right;white-space:nowrap}
label.accept{font-size:.8rem;color:var(--brass);margin-right:10px}
label.accept input{margin-right:4px;vertical-align:middle}
"""


def sub(rows: dict[str, list[Row]], where: str, notes: list[str]) -> str:
    """The line under the title: what is here, what is offered, and by whom — or why nobody could be asked."""
    every = [row for found in rows.values() for row in found]
    have = len([row for row in every if row.here])
    offered = len(every) - have
    if not where:
        return f"{have} installed · {notes[0] if notes else 'no channel could be read'}"
    return f"{have} installed · {offered} more offered by {where}"


def page(offer: Mapping[str, Release], where: str = "", notes: list[str] | None = None,
         found: Index | None = None, title: str = "Packages") -> str:
    """The tab: a card per kind, the installed packages first, and one press to have one that is not."""
    rows = sections(offer)
    said = "".join(f'<p class="empty">{esc(line)}</p>' for line in notes or [])
    unreachable = (f'<div class="card"><h2>A channel could not be read</h2>{said}</div>'
                   if notes and not where else "")
    cards = "".join(card(kind, title_of, why, rows[kind], nothing_here(kind, where, found))
                    for kind, title_of, why in SECTIONS)
    body = (f"<style>{STYLE}</style>{unreachable}{cards}"
            f'<pre class="said" id="said" hidden></pre>')
    return document(title, sub(rows, where, notes or []), body, SCRIPT, now=WHERE)


def served(prerelease: bool | None = None) -> str:
    """The page, having asked the channels. What the board's route calls."""
    return page(*chandlery(prerelease))


__all__ = ["Row", "chandlery", "page", "put", "sections", "served"]
