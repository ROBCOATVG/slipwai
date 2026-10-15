"""The interview of 3.x as a page: the same questions, in the same order, from the same catalogue.

**One interview, two faces.** The terminal asks these questions one at a time (`cli.generate_main`, with the
prompts in `cli_prompts`); this asks them all at once on a form. Neither writes the questions down: both
read `catalog.json` — which profiles there are, which targets a loaded backend declares, which families are
offered under the chosen target, which axes apply to the profile and backend chosen, what each option is
called and what its description says. An axis added to the catalogue is asked here with no edit to this
module, and that is the point of reading rather than writing.

**The gate is the two trees.** Agreeing prose is not evidence. `tests/test_interview_page.py` drives the
terminal interview with every question answered by its default, generates from the board with every question
left at the default this page shows, and diffs the trees file for file. Where the two faces disagree about a
default, that is where it shows.

**Generation itself is the verb, run as a child.** The answers become the flags `slipwai generate` already
takes and this runs that command — the non-interactive form of the interview, which is the same code the
terminal reaches through the same assembly. A second path into `write_project` would be a second thing to
keep in step, and the first one to drift.

A question the catalogue cannot answer is asked nowhere here: the quickstarts of phase 13 are to be offered
first, the way 13.2 has the terminal offer them, and they are not in the keel yet. The place they go is the
head of `asked`, and the gate above is what will hold them to the terminal's wording.
"""
from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .assets import DEFAULT_OUTPUT, relaunch
from .browser_app import frontend_menu
from .catalog import (
    CATALOG,
    axis_applies,
    axis_default,
    axis_options,
    axis_required,
    default_language,
    families,
    framework_of,
    resolve_backend,
)
from .cli_offered import not_installed_frameworks, not_installed_languages
from .cli_prompts import PROFILE_GUIDANCE
from .errors import GenerationError
from .harness import detect, keys, name_of
from .page_shell import document, esc
from .services import FIRST_SERVICE, FIRST_WEB
from .shell_environment import login_environment
from .targets import managed, offered_backends

# budget: 400 — this is the interview's one list of questions, held in step with the terminal question for
# question (`InStepTest` walks it), and the half that turns the answers back into the flags `generate` takes.
# Split, the question and the flag it becomes would be in two files, which is the drift the pairing exists
# to prevent.


@dataclass(frozen=True)
class Question:
    """One question, as both faces have it: what it is called, what it offers and what it proposes.

    `name` is the flag the generator takes, so the form's field names and `slipwai generate --help` are the
    same vocabulary; `unavailable` is the catalogue's refusal shown where the answer would be, which is the
    terminal's rule too — an option that cannot be chosen is named with the line that makes it choosable.
    """

    name: str
    label: str
    default: str = ""
    choices: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    #: `text`, or `file` for the one answer that is a document rather than a word — the browser reads it and
    #: sends its text, and `run` writes that back to a file for the flag the terminal takes a path in.
    kind: str = "text"
    why: str = ""
    unavailable: Mapping[str, str] = field(default_factory=dict)
    optional: bool = False


def chosen(answers: Mapping[str, str]) -> dict[str, str]:
    """The three answers every later question is decided by: the profile, the target and the backend.

    Two of them may not be asked at all — a target nothing else is offered under, a family with one
    framework — and the questions after them still have to be filtered by what they are.
    """
    profile = answers.get("profile") or str(CATALOG["default"]["profile"])
    declared = [name for name in CATALOG["targets"] if offered_backends(CATALOG, name)]
    preferred = str(CATALOG["default"]["target"])
    target = answers.get("target") or (preferred if preferred in declared else next(iter(declared), preferred))
    offered = offered_backends(CATALOG, target)
    known = families()
    languages = [family for family, members in known.items() if set(members) & set(offered)]
    first = default_language()
    language = answers.get("language") or (first if first in languages else next(iter(languages), ""))
    members = [name for name in known.get(language, []) if name in offered]
    if len(members) == 1:
        backend = members[0]
    else:
        default = str(CATALOG["default"]["framework"].get(language) or "")
        framework = answers.get("framework") or default or next(
            (found for name in members if (found := framework_of(name))), "")
        backend = resolve_backend(language, framework) if framework else next(iter(members), "")
    return {"profile": profile, "target": target, "language": language, "backend": backend}


def asked(answers: Mapping[str, str], root: Path | None = None) -> list[Question]:
    """Every question this set of answers makes askable, in the order the terminal asks them.

    The order is `generate`'s: the name, the delivery foundation, where it goes to production, the language
    and its framework, the first service and what it owns, the browser app, one question per applicable
    axis, and where the project is written. An answer changes what comes after it — the target decides the
    menus, the backend decides the axes — so this is called again whenever one changes rather than rendered
    once and patched.

    `root` is where the board is looking, and is what the last question proposes: the terminal proposes the
    directory it was run in, and the board's equivalent is the harbour it serves rather than the directory
    its process happens to hold — a board started at login holds `/`, and a project staged there was a
    traceback on a read-only filesystem.
    """
    held = chosen(answers)
    target, backend, language = held["target"], held["backend"], held["language"]
    offered = offered_backends(CATALOG, target)
    known = families()
    said = [Question("name", "Project name", answers.get("name", ""),
                     why="lowercase letters, numbers, '.', '_' or '-'; it is the repository's name too")]
    recommended = str(CATALOG["default"]["profile"])
    profiles = (recommended, *(name for name in CATALOG["profiles"] if name != recommended))
    said.append(Question("profile", "Delivery foundation", held["profile"], profiles,
                         {name: str(CATALOG["profiles"][name]["label"]) for name in profiles},
                         why=PROFILE_GUIDANCE))
    declared = tuple(name for name in CATALOG["targets"] if offered_backends(CATALOG, name))
    # One answer is not a choice — the terminal's rule, and offering it would teach the reader that it is.
    if len(declared) > 1:
        said.append(Question("target", "Production target", target, declared,
                             {name: str(CATALOG["targets"][name]["label"]) for name in declared}))
    languages = tuple(family for family, members in known.items() if set(members) & set(offered))
    uninstalled, _unreachable = not_installed_languages()
    said.append(Question("language", "Language", language, languages, unavailable=uninstalled))
    members = [name for name in known.get(language, []) if name in offered]
    if len(members) > 1:
        labels = {found: str(CATALOG["backends"][name]["label"])
                  for name in members if (found := framework_of(name))}
        said.append(Question("framework", "Application framework", framework_of(backend) or "",
                             tuple(labels), labels, unavailable=not_installed_frameworks(language),
                             why="the framework that owns startup"))
    service = answers.get("service-name") or FIRST_SERVICE
    said.append(Question("service-name", "Service name", service, why=f"apps/{service}"))
    said.append(Question("purpose", f"What does {service} own?", answers.get("purpose", ""), optional=True,
                         why="a sentence or two, recorded in project.json; leave it empty to decide later"))
    said.append(Question("context", f"Bounded contexts {service} holds", answers.get("context", ""),
                         optional=True, why=f"comma-separated; {service} itself unless you say otherwise"))
    frontends, first_frontend, unavailable = frontend_menu()
    frontend = answers.get("frontend") or first_frontend
    said.append(Question("frontend", "Frontend", frontend, tuple(frontends), unavailable=unavailable))
    if frontend != "none":
        said.append(Question("frontend-name", "Browser app name",
                             answers.get("frontend-name") or FIRST_WEB))
    for axis, spec in CATALOG["axes"].items():
        if not axis_applies(axis, held["profile"], backend, target):
            continue
        options = axis_options(axis, backend, target)
        # A target that deploys this axis's answer takes the no-infrastructure one off the menu rather than
        # offering it and refusing it a moment later.
        if axis_required(axis, target):
            options = [name for name in options if name != spec["absent"]]
        said.append(Question(axis, str(spec["prompt"]), answers.get(axis) or axis_default(axis, backend, target),
                             tuple(options), {name: str(spec["options"][name]["label"]) for name in options},
                             why=str(spec["description"])))
    said.append(Question("output", "Output parent",
                         answers.get("output") or str(root.resolve() if root is not None else DEFAULT_OUTPUT),
                         why="the directory the project's own directory is made in"))
    said.append(Question("prd", "Product requirements document", "", optional=True, kind="file",
                         why="optional: a PRD, copied into the project as docs/prd.md. After ./init the agent "
                             "drafts the constitution and the first specification from it and stops; the "
                             "build continues when you have read the specification and said so"))
    return said


def settled(answers: Mapping[str, str], root: Path | None = None) -> dict[str, str]:
    """Every question's answer, the shown default standing in wherever nobody said otherwise."""
    return {**{one.name: answers.get(one.name) or one.default for one in asked(answers, root)}, **chosen(answers)}


def flags(answers: Mapping[str, str], root: Path | None = None) -> list[str]:
    """The answers as the flags `slipwai generate` takes — which is the interview's own other half.

    Only what was actually asked becomes a flag: an axis this profile and backend cannot be given a choice
    about is left to the generator's own default, exactly as a terminal run that never asked it is.
    """
    held = settled(answers, root)
    names = {question.name for question in asked(answers, root)}
    argv = [held["name"], "--profile", held["profile"], "--target", held["target"],
            "--backend", held["backend"], "--frontend", held["frontend"],
            "--service-name", held["service-name"], "--output", held["output"]]
    if held.get("purpose"):
        argv += ["--purpose", held["purpose"]]
    contexts = [name.strip() for name in held.get("context", "").split(",") if name.strip()]
    # A service that holds itself is what the terminal records as nothing: `prompt_context` returns None
    # for that answer, and passing it as a flag would be the one difference between the two trees.
    if contexts != [held["service-name"]]:
        for context in contexts:
            argv += ["--context", context]
    if "frontend-name" in names:
        argv += ["--frontend-name", held["frontend-name"]]
    for axis in CATALOG["axes"]:
        if axis in names:
            argv += [f"--{axis}", held[axis]]
    return argv


#: The row that hands the new project to nobody, which is the only answer a board can offer that leaves
#: `./init` where it has always been — the next step, for a person with a terminal.
NO_INIT = "none"


def destination(answers: Mapping[str, str], root: Path | None = None) -> Path:
    """Where this set of answers puts the project. `flags` carries the two halves to the verb separately and
    the verb prints the join; the board needs it before it reads a word of what the verb said."""
    held = settled(answers, root)
    return (Path(held["output"]).expanduser() / held["name"]).resolve()


def init_asked(answers: Mapping[str, str], root: Path) -> Question:
    """Which coding agent the new project is handed to as soon as it exists.

    The terminal does not ask this because it cannot ask it well — `./init` has thirty-six answers, so
    there it stays Spec Kit's own question, put to the person sitting in front of it. Nobody is sitting in
    front of this, and a child with no terminal that stops on a menu is a board that hangs, so the board
    asks first, with a list, which is the one shape of question a browser is better at. Declining is the
    first row. Neither this nor the repository below is in `asked`: that list is the flags `generate` takes,
    held in step with the terminal question for question, and these are the board's own.
    """
    found = detect(root)
    rows = (NO_INIT, *keys())
    return Question("init", "Then", answers.get("init") or found.harness or NO_INIT, rows,
                    {NO_INIT: "leave ./init as the next step, to be run in a terminal",
                     **{key: f"run ./init here and project into {name_of(key)}" for key in keys()}},
                    why="`./init` installs Spec Kit and projects the skills and commands into one agent. It "
                        "is the step nothing in the new tree works without, and the only one that needs the "
                        "network" + (f" — {found.evidence}" if found.harness else ""))


def repository_asked(answers: Mapping[str, str]) -> Question:
    """Where the project is pushed — `./init`'s other `/dev/tty` question, asked where somebody can answer.

    Asked whatever the target is, rather than appearing and disappearing with the one above it: a person
    with a repository in mind has it in mind now. What the target changes is the line under it, and whether
    `./init` is handed the answer at all.
    """
    return Question(
        "repository", "Repository to push to", answers.get("repository", ""), optional=True,
        why="a URL on GitHub or Gitea, created if it is missing. This target configures its pipeline on the "
            "repository the project is pushed to, so `./init` pushes there as its last step; left empty, "
            "`./init --repository <url>` picks it up whenever you like."
            if managed(CATALOG, chosen(answers)["target"]) else
            "this target bootstraps no pipeline, so `./init` is not given this and nothing is pushed. The "
            "repository is yours to make when you want one; a target that deploys uses it the moment it has it.")


def repository_for(answers: Mapping[str, str]) -> str | None:
    """The repository to hand `./init`, and nothing where this project's `./init` has no flag to take it:
    a target that bootstraps nothing never had one, and the flag would reach Spec Kit and be refused."""
    named = (answers.get("repository") or "").strip()
    return named if named and managed(CATALOG, chosen(answers)["target"]) else None


def run(answers: Mapping[str, str], root: Path) -> tuple[bool, str]:
    """Generate, by running the verb. Whether it worked, and what it said either way.

    A child rather than a call: `generate` owns a parser, a refusal shape and an exit status, and a server
    thread that imported its way into the middle of it would be a second entry point to the same work. The
    child is this copy and no other (`assets.relaunch`), so the board cannot generate with a different keel
    from the one serving it; it is given the login shell's environment (`shell_environment`).
    """
    with tempfile.TemporaryDirectory(prefix=".prd-") as held:
        argv = flags(answers, root)
        # The document arrived as text, because a browser hands a page a file's contents and never its
        # path; the verb takes a path, so it is written back to one for the length of the run.
        if (text := str(answers.get("prd") or "")).strip():
            document = Path(held) / (Path(str(answers.get("prd-name") or "")).name or "prd.md")
            document.write_text(text, encoding="utf-8")
            argv += ["--prd", str(document)]
        done = subprocess.run([*relaunch(), "generate", *argv], cwd=str(root),
                              capture_output=True, text=True, env=login_environment())
    return done.returncode == 0, (done.stdout + done.stderr).strip()


def field_html(question: Question) -> str:
    """One question, as a row of the form. The `id` is the name: the label has always said `for` and had
    nothing to point at, so clicking one focused nothing and the browser reported fifteen of them."""
    if question.choices:
        options = "".join(
            f'<option value="{esc(name)}"{" selected" if name == question.default else ""}>'
            f"{esc(question.labels.get(name, name))}</option>" for name in question.choices)
        asking = f'<select id="{esc(question.name)}" name="{esc(question.name)}" data-asks>{options}</select>'
    elif question.kind == "file":
        asking = (f'<input id="{esc(question.name)}" name="{esc(question.name)}" type="file" '
                  f'accept=".md,.markdown,.txt,text/markdown,text/plain">')
    else:
        asking = (f'<input id="{esc(question.name)}" name="{esc(question.name)}" value="{esc(question.default)}"'
                  f'{"" if question.optional else " required"}>')
    why = f'<div class="why">{esc(question.why)}</div>' if question.why else ""
    no = "".join(f'<div class="no">{esc(name)} — {esc(line)}</div>'
                 for name, line in question.unavailable.items())
    return (f'<div class="q"><label for="{esc(question.name)}">{esc(question.label)}</label>'
            f"{asking}{why}{no}</div>")


def form(answers: Mapping[str, str], root: Path | None = None) -> str:
    """The whole interview, as one card. Re-rendered when an answer changes what comes after it."""
    rows = "".join(field_html(question) for question in asked(answers, root))
    rows += field_html(init_asked(answers, root or Path(".")))
    rows += field_html(repository_asked(answers))
    return (f'<div class="card" id="interview"><h2>Start a new project</h2>'
            f'<form class="ask-page">{rows}</form>'
            f'<div class="ask"><button class="go" id="generate">Generate</button></div>'
            f'<pre class="said" id="said" data-tail hidden></pre></div>')


#: The two things the page does that a static form cannot. An answer to a question that decides a later one
#: — the target decides which languages are offered, the backend decides which axes apply — is asked again
#: rather than patched, because deciding in the browser which questions follow would be the second reading
#: of the catalogue this slice exists to avoid.
SCRIPT = """
// A file input's entry is a File, which JSON would render as `{}`: it is read here and sent as its text,
// with its name beside it, and only when it is about to be used — a re-ask of the questions is sent the
// name alone.
const answers = async (withFiles) => {
  const held = Object.fromEntries(new FormData(document.querySelector('form.ask-page')).entries());
  for (const [name, value] of Object.entries(held)) {
    if (!(value instanceof File)) continue;
    held[name] = withFiles && value.size ? await value.text() : '';
    if (value.size) held[name + '-name'] = value.name;
  }
  return held;
};

async function post(path, withFiles){
  return fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                      body: JSON.stringify(await answers(withFiles))});
}
document.addEventListener('change', async event => {
  if (!event.target.matches('[data-asks]')) return;
  // The form is rendered again from the catalogue, and a chosen file does not survive that unless carried.
  const chosen = document.getElementById('prd');
  const files = chosen && chosen.files.length ? chosen.files : null;
  const answer = await post('/generate/ask', false);
  if (!answer.ok) return;
  document.getElementById('interview').outerHTML = await answer.text();
  const again = document.getElementById('prd');
  if (again && files) again.files = files;
});
document.addEventListener('click', async event => {
  if (event.target.id !== 'generate') return;
  const said = document.getElementById('said');
  said.hidden = false;
  said.className = 'said';
  said.textContent = 'generating…';
  const answer = await post('/generate/run', true);
  said.textContent = await answer.text();
  said.scrollTop = said.scrollHeight;
  if (!answer.ok) { said.className = 'said bad'; return; }
  // Made. This window is the new project's window from here, and the voyage opens beside it rather than
  // over it: a run is watched for an afternoon and this window is where the next project is started from.
  // `look` and not this window's seat, so the two are genuinely two — a Look here typed in this one later
  // moves this one, and the run goes on being watched where it was opened.
  const receipt = await (await fetch('/init.json')).json();
  window.open('/voyage?look=' + encodeURIComponent(receipt.root), '_blank', 'noopener');
});
"""


def nothing(refused: GenerationError) -> str:
    """The card a board with no language to generate on shows: what is missing, and the tab that fixes it.

    The terminal answers this with `nothing_to_generate`, which prints an install line per language the
    chandlery offers — the right answer for somebody who can type one. Here the install is a tab away, so
    the page says that instead; the refusal itself is still shown, because it is the sentence that says why.

    Before this, the questions were asked of a catalogue with no backend in it and the refusal came out of
    the server as a closed connection — which is what a person met on the first machine they ever installed
    this on, where no language is installed yet by definition.
    """
    return ('<div class="card"><h2>There is no language to generate with yet</h2>'
            f'<p class="empty">{esc(refused)}</p>'
            '<dl><dt><a href="/packages">Install a language</a></dt>'
            "<dd>this page asks its questions the moment there is one</dd></dl></div>")


def page(answers: Mapping[str, str], title: str = "Start a new project", root: Path | None = None) -> str:
    """The interview as a page of its own. 14.4 makes it a tab of the board; the questions do not change."""
    try:
        body, sub = form(answers, root), f"{len(asked(answers))} questions, read from the catalogue"
    except GenerationError as refused:
        return document(title, "nothing to generate yet", nothing(refused), now="/generate")
    return document(title, sub, body, SCRIPT, now="/generate")
