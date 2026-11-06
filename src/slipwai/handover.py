"""Hand-over from a brief: what the start page settles from the folder, and what it says before asking anything.

A person who has just finished a brief on the first page has answered everything in plain words. The start
page used to meet them with the same seventeen questions it asks anyone, language and store and write
model among them. What the brief settles is read off the folder here: the project's name from the sketch's,
a browser app from whether the brief drew surfaces, who signs in from *Who runs it*, the service's purpose
from the brief's own first paragraph, the agent from the Settings tab. What the brief cannot settle is the
builder's — language, store, write model, where it runs — and those take the smallest start, the laptop
quickstart's answers: one service on this machine, a real store in one file, nothing to install. The page
says all of it in a few lines, with one button to make it and one to change something.
"""
from __future__ import annotations

import re
from pathlib import Path

from .board_settings import chosen as agent_chosen
from .board_settings import read
from .brief_check import runs_line, sections, service
from .design_docs import briefed
from .harness import name_of
from .identity import EVERYONE, STAFF, WHO
from .interview_page import extensions_offered
from .quickstart import answered, find

#: The builder's defaults for a project that starts from a brief: the smallest start there is.
BASE = "laptop-trial"
SLUG = re.compile(r"[^a-z0-9._-]+")
#: What the quickstart's answers are called, in a person's words, for the lines the page says.
STORES = {"sqlite": "a real store in one file", "memory": "no store kept between runs", "postgres": "Postgres"}
TRUTH = {"events": "keeping every change as its history", "state": "keeping current state"}
PLACES = {"none": "on this machine, deployed nowhere", "existing": "on infrastructure somebody else runs",
          "aws": "on AWS", "azure": "on Azure"}


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
    """Every answer the start page can give itself from this brief, over the smallest start's own."""
    held = dict(answered(find(BASE)))
    held["brief"] = str(folder)
    held["name"] = slug_of(folder)
    try:
        document, rest = briefed(folder)
    except Exception:  # noqa: BLE001 — a folder that will not sort is still one the form can be given
        document, rest = None, []
    pages = [one for one in rest if one.parent.name == "surfaces" and one.suffix.lower() == ".html"]
    held["frontend"] = "react-vite" if pages else "none"
    found = service(document) if document else {}
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
    runs = runs_line(found)
    lines.append(runs.replace("runs for: ", "For ", 1).capitalize() if not runs.startswith("runs for: not said")
                 else "Who runs it is not said yet; the first build starts small, one environment.")
    lines.append(f"A browser app, drawn from the brief's {len(pages)} surface{'s' if len(pages) != 1 else ''}."
                 if held.get("frontend", "none") != "none" else "No browser app: the brief draws no surfaces.")
    store = STORES.get(held.get("persistence", ""), held.get("persistence", ""))
    place = PLACES.get(held.get("target", ""), held.get("target", ""))
    lines.append(f"One service, {held.get('service-name', 'service')}, in {held.get('language', '')} with {store}, "
                 f"{TRUTH.get(held.get('write-model', ''), '')}, {place}.")
    lines.append("Signed in by the people who work here, and nobody else." if held.get(WHO) == STAFF
                 else "Signed in by everyone it is for, through one identity provider.")
    lines.append(f"Built with {name_of(held['init'])}: ./init runs here and projects into it."
                 if held.get("init") else "./init is left for you to run in a terminal.")
    return lines
