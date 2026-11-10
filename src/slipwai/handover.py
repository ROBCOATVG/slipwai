"""Hand-over from a brief: what the start page settles from the folder, and what it says before asking anything.

A person who has just finished a brief on the first page has answered everything in plain words. The start
page used to meet them with the same seventeen questions it asks anyone, language and store and write
model among them. What the brief settles is read off the folder here: the project's name from the sketch's,
a browser app from whether the brief drew surfaces, who signs in from *Who runs it*, the service's purpose
from the brief's own first paragraph, the agent from the Settings tab. What the brief cannot settle is the
builder's — language, store, write model — and those come from a quickstart: the one *Where it runs* names,
where this machine can reach it, and otherwise the smallest start, the laptop quickstart's answers: one
service on this machine, a real store in one file, nothing to install. The page says all of it in a few
lines, with one button to make it and one to change something.

Where it runs has to be settled here. A deployment's shape can be moved after generation; the place it
deploys to cannot, so a brief that said AWS and was generated on the laptop would have to start again.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .board_settings import chosen as agent_chosen
from .board_settings import read
from .brief_check import runs_line, sections, service, shape_of
from .browser_app import frontend_menu
from .catalog import CATALOG, families
from .design_docs import briefed, played
from .harness import name_of
from .identity import EVERYONE, STAFF, WHO
from .interview_page import extensions_offered
from .language_directory import directory
from .language_install import builtin, installed
from .loaded_targets import answer, loaded
from .quickstart import Quickstart, answered, find
from .shell_environment import login_environment
from .target_protocol import TOOLS
from .targets import managed

#: The builder's defaults for a project that starts from a brief: the smallest start there is.
BASE = "laptop-trial"
SLUG = re.compile(r"[^a-z0-9._-]+")
#: What the quickstart's answers are called, in a person's words, for the lines the page says.
STORES = {"sqlite": "a real store in one file", "memory": "no store kept between runs", "postgres": "Postgres"}
TRUTH = {"events": "keeping every change as its history", "state": "keeping current state"}
PLACES = {"none": "on this machine, deployed nowhere", "existing": "on infrastructure somebody else runs"}
#: Where it runs, in the brief's words, as the quickstart that starts there. Nowhere, or not said, is `BASE`.
STARTS = {"aws": "aws-customer-product", "azure": "azure-staff-service", "platform": "existing-platform-service"}
SAID = {"aws": "AWS", "azure": "Azure", "platform": "a platform another team runs"}


def short_of(one: Quickstart) -> list[str]:
    """What this machine lacks to start where a quickstart does, in plain words; nothing where it lacks nothing.

    Its languages and its target installed, and the target's own tools on the PATH a login shell has — the
    board is started at login, with less of a PATH than a terminal. Signing in is the target's to check,
    which its setup script does when `./init` runs."""
    have = {*families(), *installed(directory()), *builtin()}
    lacking = [f"the {each.name} language" for each in one.languages if each.name not in have]
    target = answered(one).get("target", "")
    if not managed(CATALOG, target):
        return lacking
    if target not in loaded():
        return [*lacking, f"the {target} target"]
    path = login_environment().get("PATH")
    return [*lacking, *(str(why).split(" — ")[0] for command, why, _where in answer(target, TOOLS, ())
                        if shutil.which(command, path=path) is None)]


def destination(found: dict, pages: bool) -> tuple[str, str]:
    """The quickstart to start from, and the line saying why it is not the one the brief named, or `""`.

    Another team's platform is a service joining it — or, for a staff screen, the internal tool. A place
    this machine cannot reach yet starts on the laptop and says what it needs, rather than generating a
    project that cannot be bootstrapped from here; that line is what the board installs from, later."""
    place = str(found.get("runs_on") or "")
    if place not in STARTS:
        return BASE, ""
    name = "internal-tool" if place == "platform" and found.get("used_by") == "staff" and pages else STARTS[place]
    lacking = short_of(find(name))
    if not lacking:
        return name, ""
    needs = lacking[0] if len(lacking) == 1 else ", ".join(lacking[:-1]) + " and " + lacking[-1]
    return BASE, (f"You said {SAID[place]}. This machine cannot start there yet: it needs {needs}. "
                  f"Starting on this machine for now.")


def slug_of(folder: Path) -> str:
    """The project's name, from the sketch's: the folder is `<sketch>/brief`, or named for the product."""
    name = folder.parent.name if folder.name == "brief" and folder.parent.name else folder.name
    return SLUG.sub("-", name.lower()).strip("-.") or "product"


def purpose_of(document: Path | None) -> str:
    """The brief's own first paragraph after its title: the one sentence, as the service's purpose."""
    if document is None:
        return ""
    head = next((text for title, text in sections(document) if title == ""), "")
    body = re.sub(r"^#.*$", "", head, flags=re.MULTILINE).strip()
    paragraph = re.split(r"\n\s*\n", body)[0].replace("\n", " ").strip() if body else ""
    return paragraph[:300]


def answers(folder: Path) -> dict[str, str]:
    """Every answer the start page can give itself from this brief, over the quickstart's it starts from."""
    try:
        document, rest = briefed(folder)
    except Exception:  # noqa: BLE001 — a folder that will not sort is still one the form can be given
        document, rest = None, []
    pages = [one for one in rest if one.parent.name == "surfaces" and one.suffix.lower() == ".html"]
    found = service(document) if document else {}
    held = dict(answered(find(destination(found, bool(pages))[0])))
    held["brief"] = str(folder)
    held["name"] = slug_of(folder)
    # The browser app is the catalogue's own default frontend: which family ships it is the catalogue's to say.
    held["frontend"] = frontend_menu()[1] if pages else "none"
    held[WHO] = STAFF if found.get("used_by") == "staff" else EVERYONE
    words = held["name"].split("-")
    held["service-name"] = words[-1] if len(words) > 1 and len(words[-1]) > 2 else held["name"]
    held["purpose"] = purpose_of(document)
    agent = agent_chosen(read())
    if agent is not None and agent.able:
        held["init"] = agent.key
    # Every extension this machine has, ticked: the hand-over is the one start where nobody has read a menu,
    # and a project that quietly had none was the omission `./init`'s silent menu used to make.
    held["extensions"] = ",".join(key for key, _, _ in extensions_offered())
    return held


def said(held: dict[str, str]) -> list[str]:
    """What the page says it will make, in a few lines a person reads before pressing."""
    folder = Path(held.get("brief") or ".")
    try:
        document, rest = briefed(folder)
    except Exception:  # noqa: BLE001
        document, rest = None, []
    pages = [one for one in rest if one.parent.name == "surfaces" and one.suffix.lower() == ".html"]
    found = service(document) if document else {}
    lines = []
    target = held.get("target", "")
    shape = shape_of(found)
    if not shape:
        lines.append("Who runs it is not said yet; the first build starts small, one environment.")
    elif managed(CATALOG, target):
        # Not `capitalize`, which lowers everything after the first letter: "your aws account".
        lines.append(runs_line(found).replace("runs for: ", "For ", 1) + ".")
    else:
        # Sized only where something is deployed: on the laptop, the size is what it will be when it goes live.
        down = "an annoyance" if found["when_down"] == "annoyance" else "an emergency"
        size = "one environment" if shape == "skiff" else "the full stack, with a staging environment"
        lines.append(f"For {found['used_by']}, {down} when it is down: when it goes live it will be {size}.")
    note = destination(found, bool(pages))[1]
    if note:
        lines.append(note)
    play = " and the prototype you played, which the surfaces follow" if played(folder) else ""
    lines.append(f"A browser app, drawn from the brief's {len(pages)} surface{'s' if len(pages) != 1 else ''}{play}."
                 if held.get("frontend", "none") != "none" else "No browser app: the brief draws no surfaces.")
    store = STORES.get(held.get("persistence", ""), held.get("persistence", ""))
    target = held.get("target", "")
    # A place that is a package says its own name: the catalogue's label for it, never a word of this keel's.
    place = PLACES.get(target) or f"on {CATALOG['targets'].get(target, {}).get('label', target)}"
    lines.append(f"One service, {held.get('service-name', 'service')}, in {held.get('language', '')} with {store}, "
                 f"{TRUTH.get(held.get('write-model', ''), '')}, {place}.")
    lines.append("Signed in by the people who work here, and nobody else." if held.get(WHO) == STAFF
                 else "Signed in by everyone it is for, through one identity provider.")
    lines.append(f"Built with {name_of(held['init'])}: ./init runs here and projects into it."
                 if held.get("init") else "./init is left for you to run in a terminal.")
    return lines
