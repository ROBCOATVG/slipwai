"""Adoption from the board: a directory somebody picks, what it holds, and what would be written in it.

Adoption's whole risk is a file changed in a repository somebody already has. The terminal verb manages that
by printing — the survey's findings, then a report of what it wrote — and a page can do far better, because
the list of what *would* be written can be shown before anything is.

**Nothing here writes.** `found` runs the same `check_repository` the verb does and the same `survey`, and
`would_write` assembles the same files `adopt` assembles and then throws them away. Adopting is a separate
press, and it runs the verb as a child of this copy, so there is one path into somebody's repository.

**The preview is held to the adoption, not to a description of it.** `tests/test_adopt_page.py` previews a
fixture repository, adopts it for real, and compares the preview against the paths the adoption commit added
and the files of theirs it appended to. A preview that is nearly right is worse than none: it is believed.
"""
from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

from .adopt import (
    AGENTS,
    GITIGNORE,
    PINNED,
    STRUCTURE_PAGE,
    SURVEY_PAGE,
    Answers,
    candidates_of,
    check_repository,
    facts,
    proposed,
)
from .adopt_report import MAKEFILE, SETTINGS
from .assets import relaunch
from .big_picture import big_picture
from .ecosystems import prefixed
from .errors import GenerationError
from .folder_field import SCRIPT as CHOOSING
from .folder_field import folder_field
from .layout import Layout
from .page_shell import document, esc
from .platform import with_platform
from .project.big_picture_page import big_picture_files
from .project.run_skill import RUNNING
from .project.strangle_command import RETIREMENT
from .scaffold import FACTORY_IDENTITY, project_files
from .strategy import with_recommendation
from .structure import structure
from .survey import survey
from .wrappers import WRAPPERS, missing_wrapper

#: The one refusal a person meets most, and the only one worth matching on: `git init` is day zero.
NOT_A_REPOSITORY = "is not a Git repository"


def name_of(root: Path) -> str:
    """What the project would be called: the directory's own name, as the verb takes it."""
    return root.name.lower()


def found(root: Path, delivery: str = "delivery") -> dict:
    """What the survey read here, or the reason this is not a repository to adopt.

    The refusal comes first and before the survey, because that is where it belongs: finding out after
    twelve thousand files were read is the refusal arriving after the work it refuses.
    """
    try:
        if not root.is_dir():
            raise GenerationError(f"{root} {NOT_A_REPOSITORY}: there is no such directory")
        check_repository(root)
    except (GenerationError, OSError) as refused:
        return {"root": str(root), "refused": str(refused), "candidates": [], "proposal": {}}
    read = survey(root)
    forge, evidence = read.forge
    return {
        "root": str(root),
        "name": name_of(root),
        "delivery": delivery,
        "refused": "",
        "candidates": candidates_of(read, name_of(root)),
        "proposal": {
            "CI forge": f"{forge} — {evidence}",
            "Where the schema is versioned": read.schema_home,
            "Where the infrastructure is described": read.infrastructure_home,
            "How a change reaches production": read.release_path or "nothing here says",
            "Default branch": read.default_branch,
        },
        "quick wins": [str(win.get("what", "")) for win in read.quick_wins],
    }


def would_write(root: Path, delivery: str = "delivery") -> dict[str, list[str]]:
    """Every path adoption would add here, and every file of theirs it would add to. Nothing is written.

    Assembled by the same calls `adopt` makes — the layout, the record the survey proposes, and
    `scaffold.project_files` over them — and then dropped. The gate that keeps the two in step is the one
    that adopts a repository for real and compares, because this list and that adoption are two readings of
    one thing and only a comparison can say they agree.

    `proposed` rather than `candidates_of`, because `--yes` is what the board runs: every directory the
    survey found is wrapped as an application, unlooked-at. The page says so where the list is shown.
    """
    read = survey(root)
    name = name_of(root)
    layout = Layout(delivery)
    apps = proposed(read, name)
    answers = Answers(name, applications=apps)
    adoption = with_recommendation(root, layout, with_platform(root, facts(read, answers, layout), apps), apps)
    written = [*project_files(name, answers.profile, answers.target, apps, layout, adoption)]
    shape = structure(root, apps, layout.delivery, FACTORY_IDENTITY["GIT_AUTHOR_EMAIL"])
    written += big_picture_files(big_picture(root, apps, shape, layout.delivery), layout)
    written += [layout.under(page) for page in (SURVEY_PAGE, STRUCTURE_PAGE, PINNED, RETIREMENT, RUNNING)]
    # Written only where there is none: adoption never writes over what a repository already has.
    if not (root / SETTINGS).exists():
        written.append(SETTINGS)
    appended = [AGENTS, GITIGNORE]
    # No root Makefile means nothing of theirs to clash with, so `make verify` can be one word from day one.
    if not read.makefile:
        appended.append(MAKEFILE)
    # A Maven or Gradle build with no wrapper of its own gets one, and those files are theirs from then on.
    for app in apps:
        ecosystem = missing_wrapper(root, app)
        if ecosystem is not None:
            written += [prefixed(app.path, relative) for relative, _, _ in WRAPPERS[ecosystem][2]]
    # A managed block creates a new file where the repository has none; the preview
    # calls a file appended only when there is already a person's file to add to.
    written += [path for path in appended if not (root / path).exists()]
    appended = [path for path in appended if (root / path).exists()]
    return {"written": sorted(set(written)), "appended": sorted(set(appended))}


def run(answers: Mapping[str, str], here: Path) -> tuple[bool, str]:
    """Adopt, by running the verb in the directory that was picked. Whether it worked, and what it said.

    `--yes` because every question the terminal would ask has been shown on the page already, and `--no-init`
    because `./init` reaches the network and is the next step a person takes themselves, as it is under
    `--yes` in a terminal.
    """
    root = Path(str(answers.get("root") or here)).expanduser()
    seen = found(root, str(answers.get("delivery") or "delivery"))
    if seen["refused"]:
        return False, seen["refused"]
    done = subprocess.run([*relaunch(), "adopt", "--yes", "--no-init",
                           "--delivery", str(answers.get("delivery") or "delivery")],
                          cwd=str(root), capture_output=True, text=True)
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def listing(title: str, paths: list[str], empty: str) -> str:
    if not paths:
        return f'<h3>{esc(title)}</h3><p class="empty">{esc(empty)}</p>'
    rows = "".join(f'<li>{esc(path)}</li>' for path in paths)
    return f'<h3>{esc(title)} ({len(paths)})</h3><ol class="lines">{rows}</ol>'


def report(seen: dict, plan: dict[str, list[str]] | None, fault: str = "") -> str:
    """What was found and what would be written, as the card a person reads before pressing anything.

    `fault` is what stopped the list being assembled, where something did. The findings still stand — they
    were read first — and the refusal goes where the list would have been, with nothing to press.
    """
    if seen["refused"]:
        return f'<div class="card"><h2>Nothing to adopt here</h2><p class="no">{esc(seen["refused"])}</p></div>'
    rows = "".join(f"<tr><td><b>{esc(row['path'])}</b></td><td>{esc(row['language'])}</td>"
                   f"<td>{esc(row['evidence'])}</td></tr>" for row in seen["candidates"])
    facts_said = "".join(f"<dt>{esc(name)}</dt><dd>{esc(value)}</dd>"
                         for name, value in seen["proposal"].items())
    if fault:
        would = (f'<div class="card"><h2>What would be written</h2>'
                 f'<p class="no">This cannot be worked out here, so nothing is offered: {esc(fault)}</p>'
                 f'</div>')
    else:
        listed = plan or {"written": [], "appended": []}
        would = (f'<div class="card"><h2>What would be written</h2>'
                 f'<p class="empty">Nothing below exists yet, and nothing is written until you press '
                 f'Adopt.</p>'
                 f'{listing("New files", listed["written"], "nothing")}'
                 f'{listing("Files of yours added to, between markers", listed["appended"], "none")}'
                 f'<div class="ask"><button class="go" id="adopt">Adopt {esc(seen.get("name", ""))}'
                 f'</button></div><pre class="said" id="said" hidden></pre></div>')
    return (
        f'<div class="card"><h2>What is in {esc(seen["root"])}</h2>'
        f'<p class="empty">Every one of these is wrapped as an application, as found and looked at by '
        f'nobody — which is what the terminal\'s own unattended run does. What each is really for is a '
        f'question the code answers: an agent reading it settles them afterwards, and '
        f'<code>slipwai adopt --decline &lt;name&gt;</code> drops one that is not an application.</p>'
        f"<table><tr><th>Directory</th><th>Language</th><th>Found by</th></tr>{rows}</table>"
        f"<dl>{facts_said}</dl></div>{would}"
    )


def picker(root: str) -> str:
    """The directory, asked for with this machine's folder dialog, where it has one."""
    return (
        '<div class="card" id="pick"><h2>Adopt a repository you already have</h2>'
        '<form class="ask-page"><div class="q"><label for="root">The repository\'s directory</label>'
        + folder_field("root", root, required=True) +
        '<div class="why">A clean Git repository with no project.json of its own. Nothing in it is read '
        'until you press Look, and nothing is written until you press Adopt.</div></div>'
        '<div class="q"><label for="delivery">Where the method\'s files go</label>'
        '<input name="delivery" id="delivery" value="delivery"></div></form>'
        '<div class="ask"><button class="go" id="look">Look</button></div></div>'
    )


SCRIPT = CHOOSING + """
const answers = () => Object.fromEntries(
  new FormData(document.querySelector('#pick form.ask-page')).entries());

document.addEventListener('click', async event => {
  if (event.target.id === 'look') {
    const where = document.getElementById('report');
    where.innerHTML = '<div class="card"><p class="empty">Reading the tree…</p></div>';
    const answer = await fetch('/adopt/look', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(answers())});
    where.innerHTML = await answer.text();
  }
  if (event.target.id === 'adopt') {
    const said = document.getElementById('said');
    said.hidden = false;
    said.className = 'said';
    said.textContent = 'adopting…';
    const answer = await fetch('/adopt/run', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(answers())});
    said.textContent = await answer.text();
    if (!answer.ok) said.className = 'said bad';
  }
});
"""


def page(answers: Mapping[str, str], title: str = "Adopt a repository") -> str:
    """The adoption tab: pick a directory, look at it, and only then adopt it."""
    body = picker(str(answers.get("root") or "")) + '<div id="report"></div>'
    return document(title, "what it found, and what it would write, before it writes it",
                    body, SCRIPT, now="/adopt")


def looked(answers: Mapping[str, str], here: Path) -> str:
    """One look at a directory: the findings and the list, rendered. Still nothing written."""
    root = Path(str(answers.get("root") or here)).expanduser()
    delivery = str(answers.get("delivery") or "delivery")
    seen = found(root, delivery)
    if seen["refused"]:
        return report(seen, None)
    try:
        return report(seen, would_write(root, delivery))
    except (GenerationError, OSError) as refused:
        # The findings still stand — they were read before the assembly was attempted — and what cannot be
        # listed is said where the list would have been. A partial list is the thing this tab exists to
        # prevent: it would be believed.
        return report(seen, None, str(refused))
