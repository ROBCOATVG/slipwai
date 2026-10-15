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

Two questions are not the catalogue's. The quickstart is offered first, the way the terminal offers it
(`cli_generate.offer_quickstart`), from the same menu and with the same rows greyed out; choosing one fills
in every answer it gives and leaves all of them changeable, which is what a default is. And who signs in is
asked once in place of the two identity axes (`identity`), because the page is read by the same person the
terminal's version of that question was rewritten for. Both are in `asked` rather than beside it, so the
gate above holds them to the terminal's wording too.
"""
from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from . import identity, quickstart
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
from .cli_generate import DECLINE, quickstart_menu, unavailable_quickstarts
from .cli_offered import not_installed_frameworks, not_installed_languages
from .cli_prompts import PROFILE_GUIDANCE
from .errors import GenerationError
from .extension_install import catalogue
from .harness import detect, keys, name_of
from .language_directory import directory as extension_directory
from .services import FIRST_SERVICE, FIRST_WEB
from .shell_environment import login_environment
from .targets import managed, offered_backends

# budget: 460 — this is the interview's one list of questions, held in step with the terminal question for
# question (`InStepTest` walks it), and the half that turns the answers back into the flags `generate` takes.
# Split, the question and the flag it becomes would be in two files, which is the drift the pairing exists
# to prevent — and the two questions that are not one flag each, the quickstart that fills in many and the
# one that stands in for the identity pair, are exactly the two whose answers must be turned into flags
# within sight of the rows that asked for them.


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


#: The hidden field carrying the quickstart the form in front of the reader was rendered from. Without it
#: a quickstart chosen on the board would be overruled by the page's own last answers, which arrive with
#: every re-ask: the browser posts what is on the form, and what is on the form is the previous quickstart's
#: answers, or the catalogue's. With it, `given` can tell the one case where the quickstart must win — the
#: press that chose it — from every re-ask afterwards, where what the reader has since changed must.
WAS = "quickstart-was"


def given(answers: Mapping[str, str]) -> dict[str, str]:
    """`answers`, with the chosen quickstart's own answers filled in.

    Every answer, where the quickstart has just been chosen; only the ones nothing has answered yet,
    afterwards. That is the difference between a default and a decision made on somebody's behalf, and it
    is the same rule `quickstart.applied` holds the flags to — a person who changes the persistence a
    quickstart proposed has changed it, and a form that snapped back on the next re-ask would be the board
    arguing with them.

    A name that no longer reads is passed through rather than raised on: the menu greys it out and says
    why, and a half-rendered page is a worse answer to a file somebody edited by hand than a page asking
    its own questions.
    """
    name = (answers.get("quickstart") or "").strip()
    if not name or name == DECLINE:
        return dict(answers)
    try:
        said = quickstart.answered(quickstart.find(name))
    except GenerationError:
        return dict(answers)
    taken = dict(answers)
    fresh = answers.get(WAS) != name
    for flag, value in said.items():
        if fresh or not taken.get(flag):
            taken[flag] = value
    return taken


def chosen(answers: Mapping[str, str]) -> dict[str, str]:
    """The three answers every later question is decided by: the profile, the target and the backend.

    Two of them may not be asked at all — a target nothing else is offered under, a family with one
    framework — and the questions after them still have to be filtered by what they are.
    """
    answers = given(answers)
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
    answers = given(answers)
    target, backend, language = held["target"], held["backend"], held["language"]
    offered = offered_backends(CATALOG, target)
    known = families()
    said = [Question("name", "Project name", answers.get("name", ""),
                     why="lowercase letters, numbers, '.', '_' or '-'; it is the repository's name too")]
    said += starting_from(answers)
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
    # The two identity axes are one question and then whichever of them that answer leaves to ask, emitted
    # at the first of the pair the catalogue offers so the order the terminal asks in is kept.
    asking_identity = True
    for axis in CATALOG["axes"]:
        if not axis_applies(axis, held["profile"], backend, target):
            continue
        if axis in identity.AXES:
            said += signing_in(answers, held["profile"], backend, target) if asking_identity else []
            asking_identity = False
            continue
        said.append(axis_asked(axis, answers, backend, target))
    said.append(Question("output", "Output parent",
                         answers.get("output") or str(root.resolve() if root is not None else DEFAULT_OUTPUT),
                         why="the directory the project's own directory is made in"))
    said.append(Question("prd", "Product requirements document", "", optional=True, kind="file",
                         why="optional: a PRD, copied into the project as docs/prd.md. After ./init the agent "
                             "drafts the constitution and the first specification from it and stops; the "
                             "build continues when you have read the specification and said so"))
    said.append(Question("brief", "Everything else", answers.get("brief", ""), optional=True, kind="path",
                         why="optional: the path to the folder your brief is in — wireframes, a brand "
                             "sheet, a stylesheet, screenshots, and the requirements document itself if "
                             "you have not picked it above. It is read from where it already is, and "
                             "sorted: whichever file reads as the requirements document becomes "
                             "docs/prd.md and everything else lands under docs/design/, which the mock-up "
                             "stage reads before it draws a surface — where it finds a direction there, "
                             "it follows it rather than inventing one"))
    return said


def starting_from(answers: Mapping[str, str]) -> list[Question]:
    """The quickstart offer, where this machine has one that can be carried out.

    Nothing at all where it has none: a board that gained a question for people with no quickstart would
    have made the common path worse to serve the uncommon one, which is the terminal's rule for the same
    offer. The rows that cannot be carried out here are named under it with the line that fetches what
    they want, rather than being left out — somebody who wrote one should see it is still theirs.
    """
    rows, describe = quickstart_menu()
    if len(rows) == 1:
        return []
    return [Question("quickstart", "Preset", answers.get("quickstart") or DECLINE, tuple(rows),
                     {name: describe(name) for name in rows},
                     unavailable=unavailable_quickstarts(),
                     why="optional: a set of answers somebody already settled — which languages, how the "
                         "project is laid out, which optional tooling it switches on. Picking one fills in "
                         "the questions below, and every answer it fills in stays yours to change. None is "
                         "picked for you")]


def axis_asked(axis: str, answers: Mapping[str, str], backend: str, target: str,
               label: str = "", why: str = "") -> Question:
    """One axis as a row of the form. `label` and `why` are the words of a question that led here, where
    one did, exactly as `cli_prompts.prompt_axis` takes them."""
    spec = CATALOG["axes"][axis]
    options = axis_options(axis, backend, target)
    # A target that deploys this axis's answer takes the no-infrastructure one off the menu rather than
    # offering it and refusing it a moment later.
    if axis_required(axis, target):
        options = [name for name in options if name != spec["absent"]]
    return Question(axis, label or str(spec["prompt"]), answers.get(axis) or axis_default(axis, backend, target),
                    tuple(options), {name: str(spec["options"][name]["label"]) for name in options},
                    why=why or str(spec["description"]))


def signing_in(answers: Mapping[str, str], profile: str, backend: str, target: str) -> list[Question]:
    """Who signs in, and the provider question that answer leads to — the terminal's `ask_identity`, as rows.

    Where the catalogue can only be given one of the two axes, the question standing in for both would be
    standing in for one, so that axis is asked on its own terms instead.
    """
    if not identity.applies(profile, backend, target):
        return [axis_asked(axis, answers, backend, target) for axis in identity.AXES
                if axis_applies(axis, profile, backend, target)]
    who = answers.get(identity.WHO) or identity.implied(answers)
    asking = [Question(identity.WHO, identity.LABEL, who, tuple(name for name, _ in identity.ROWS),
                       dict(identity.ROWS), why=identity.WHY)]
    return asking + [axis_asked(axis, answers, backend, target,
                                identity.label(who, axis), identity.says(who, axis))
                     for axis in identity.asks(who)]


def settled(answers: Mapping[str, str], root: Path | None = None) -> dict[str, str]:
    """Every question's answer, the shown default standing in wherever nobody said otherwise.

    Read off the answers a chosen quickstart has already filled in, so that a question this page did not
    ask — an axis the quickstart answered and the catalogue does not offer here — is still its answer and
    not the generator's.
    """
    taken = given(answers)
    return {**{one.name: taken.get(one.name) or one.default for one in asked(answers, root)}, **chosen(answers)}


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
        if axis in names and axis not in identity.AXES:
            argv += [f"--{axis}", held[axis]]
    # Both identity axes, always, where the one question stood in for them: the axis nobody was asked about
    # is the one this answer said has nobody on it, and leaving it to the generator's default would be the
    # page deciding less than the reader was shown it had.
    if identity.WHO in names:
        for axis, answer in identity.settled(held[identity.WHO], held).items():
            argv += [f"--{axis}", answer]
    else:
        argv += [word for axis in identity.AXES if axis in names for word in (f"--{axis}", held[axis])]
    # The quickstart is given to the verb as well as read here: it is what writes `.slipwai/quickstart.json`
    # and elects the extensions it names, neither of which is an answer to a question on this form.
    if (name := held.get("quickstart", DECLINE)) != DECLINE:
        argv += ["--quickstart", name]
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


def extensions_offered() -> list[tuple[str, str, str]]:
    """Every extension installed on this machine: its key, its name and what it is for.

    Read here rather than written out, because an extension is a third-party package somebody installed
    and the keel ships none of them.
    """
    return [(key, str(manifest.get("name", key)), str(manifest.get("description", "")))
            for key, manifest in catalogue(extension_directory())]


def extensions_asked(answers: Mapping[str, str]) -> Question | None:
    """Which optional dev tooling this project adopts — `./init`'s third `/dev/tty` question.

    The one the board was not asking at all, and the omission was silent rather than visible: `./init`'s
    menu reads `/dev/tty` and **prints nothing where there is none**, so a board that runs `./init` as a
    child — which is every `./init` the board runs — elected nothing and said nothing about it. A person
    who generated here got a project with no extensions and no sign they had been offered any.

    Nothing where this machine has none installed, which is the same rule the settings box follows: a
    question whose every answer is unavailable is a question not worth asking.
    """
    found = extensions_offered()
    if not found:
        return None
    return Question("extensions", "Dev tooling", answers.get("extensions", ""),
                    tuple(key for key, _, _ in found),
                    {key: f"{name} — {says}" if says else name for key, name, says in found},
                    kind="checks", optional=True,
                    why="optional: elected in the new project by `./init`. Check any, or none — "
                        "`./init --extension <key>` adds one later just the same")


def elected_in(answers: Mapping[str, str]) -> tuple[str, ...]:
    """The extensions checked on the form, as `./init` takes them. Only ones this machine has: a key typed
    into a payload by hand is not an election, and `./init` would refuse it anyway."""
    offered = {key for key, _, _ in extensions_offered()}
    checked = (one.strip() for one in str(answers.get("extensions") or "").split(","))
    return tuple(one for one in checked if one in offered)


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
        # The brief is a path and not an upload. This board binds this machine only and generates on it,
        # so the folder is already where the verb can read it: carrying its bytes through a browser and
        # writing them back would be a copy nobody asked for, with a size limit nobody needs.
        if (folder := str(answers.get("brief") or "").strip()):
            argv += ["--brief", folder]
        done = subprocess.run([*relaunch(), "generate", *argv], cwd=str(root),
                              capture_output=True, text=True, env=login_environment())
    return done.returncode == 0, (done.stdout + done.stderr).strip()
