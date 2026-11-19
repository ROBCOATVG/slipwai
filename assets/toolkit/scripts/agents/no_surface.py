# Written by scripts/shared-modules.py from src/slipwai/no_surface.py. Do not edit: edit the keel's module,
# run `make shared`, and commit both. A generated project has no slipwai to import, and both runtimes need
# this one — so there is one source and this copy, and `make check-shared` refuses a copy that has drifted.
"""A feature that adds and changes no surface: the grounds for saying so, and the record of it.

A further feature that touches no screen — a migration, a scheduled job, a change behind an interface — ended
the mock-up stage as a failure: nothing drawn, "nothing to approve", a non-zero exit, and a person sent to
write `surfaces: none` by hand before anything could move. The stage now writes that answer itself and ends
cleanly, **where it has positive grounds**, and only there. Nothing drawn is not grounds: a session that
crashed, ran out of budget or misread its brief draws nothing too, and recording *no surface* for one of those
is a feature built with a screen nobody ever saw.

**The grounds, all of them.** Each is a thing on disk, read without judgement:

1. **The drawing says so, with its reason.** `research.md` carries `Surfaces: none — <why>`: the researcher
   read the specification and found no place a person or another system meets this feature.
2. **The specification's requirements name nothing anybody meets.** Its requirement lines — `FR-…`, `SC-…`,
   a user story, a `Given`/`When`/`Then` — carry none of the words a surface is asked for in: a screen, a
   page, a form, something shown, seen or displayed, an email, a report, a webhook, a command line. A
   specification with no requirement line cannot be read this way, and that is a doubt, not a pass.
3. **No slice of it carries a `ui` frame or names a surface.** Where the feature is split or modelled
   already, its rows in `story-split.md` leave *Surfaces and states* empty and its slices in
   `docs/event-model/model.yaml` hold no frame of `type: ui`. A feature with no slice yet has none that does.
4. **Nothing was drawn and nobody has judged anything.** No surface page of this feature, and no
   `mock-states.md` with a verdict in it.
5. **Where the hand-over suggested surfaces, the drawing has answered it.** The conversation that handed the
   idea over may have named surfaces it thought the feature touches (`surface_hint.py`). That is a suggestion
   and decides nothing; but a drawing that ends at *no surface* against it says so, with its reason:
   `Suggested surfaces: not touched — <why>` in `research.md`. Then the record names the suggestion and the
   answer. Without that line the stage stops and says the two disagree. A feature nobody suggested a surface
   for is read as it always was.

**Where any of them fails, the stage still stops, and says which.** A reading that errs stops: a requirement
that says "the job reports its failures to the log" names a report, and a person settles it with `/mockups`.

The keel carries this for the board, which checks a stage it ran over the protocol; `scripts/agents/` carries
the same file for `surfaces.py` (`scripts/shared-modules.py`). It imports nothing but the standard library.
"""
from __future__ import annotations

import re
from pathlib import Path

MOCKUPS = "mockups"
#: What `mock-states.md` says for a feature with nothing to draw; `check-surfaces.py` and the board read it.
NONE = "surfaces: none"
#: The drawing's own line in `research.md`, read past a list marker, bold or backticks.
SAID = re.compile(r"^[\s>*_`+-]*surfaces[*_` \t]*:[*_` \t]*none\b[*_` \t.]*(?:[—–:-]+[ \t]*)?(?P<why>.*)$",
                  re.IGNORECASE | re.MULTILINE)
#: A line a requirement begins on: an id, a user story, or a step of an acceptance scenario.
REQUIREMENT = re.compile(r"\b(?:FR|NFR|SC|US|AC)-?\d+[a-z]?\b|^[\s>*_\d.+-]*(?:Given|When|Then|As an?)\b",
                         re.IGNORECASE)
#: The words a surface is asked for in: any place a person or another system meets the feature.
MET = re.compile(
    r"\b(screens?|pages?|buttons?|forms?|dialogs?|modals?|menus?|tabs?|dashboards?|banners?|wizards?|clicks?|"
    r"clicked|taps?|tapped|displays?|displayed|shows?|shown|showed|sees?|seen|views?|viewed|navigat\w*|"
    r"sign(?:s|ed)?[ -]in|log(?:s|ged)?[ -]in|browsers?|ui|user interface|e-?mails?|notif\w*|reports?|"
    r"webhooks?|command line|cli|prints?|printed)\b", re.IGNORECASE)
#: The drawing's answer to a hand-over that named surfaces, where it found the feature touches none of them.
ANSWERED = re.compile(r"^[\s>*_`+-]*suggested surfaces[*_` \t]*:[*_` \t]*not touched\b[*_` \t.]*"
                      r"(?:[—–:-]+[ \t]*)?(?P<why>.*)$", re.IGNORECASE | re.MULTILINE)
VERDICT = re.compile(r"^-\s*.+?\s*—\s*(approved|parked|n/a)\b", re.MULTILINE)
#: A reason shorter than this is a word, not a reason.
SHORTEST = 12


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def declared(research: str) -> str | None:
    """The reason the drawing gave for no surface: `None` where it never said so, `""` where it gave none."""
    found = SAID.search(research)
    return None if found is None else re.sub(r"[*_`]", "", found.group("why")).strip().rstrip(".").strip()


def requirements(spec: str) -> list[tuple[int, str]]:
    """Each requirement of a specification with the line it begins on: the line that names it and the lines
    it runs on to, up to a blank line, a heading or the next list item."""
    found: list[tuple[int, str]] = []
    open_ = False
    for at, line in enumerate(spec.replace("\r", "").split("\n"), 1):
        if REQUIREMENT.search(line) and not line.lstrip().startswith("#"):
            found.append((at, line.strip()))
            open_ = True
        elif open_ and line.strip() and line[:1] in " \t" and not re.match(r"\s*([-*+]|\d+[.)])\s", line):
            found[-1] = (found[-1][0], f"{found[-1][1]} {line.strip()}")
        else:
            open_ = False
    return found


def slices_of(home: Path) -> list[str]:
    """The slices a feature has already: the directories under `slices/`, and the rows of its split."""
    found = [path.name for path in (home / "slices").glob("*") if path.is_dir()] if (home / "slices").is_dir() else []
    for line in read(home / "story-split.md").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if cells and cells[0] and cells[0].lower() != "slice" and not set("".join(cells)) <= set("-: "):
            found.append(cells[0])
    return sorted(set(found))


def surfaced(home: Path, model: str) -> list[str]:
    """Why a feature's own slices say it has a surface after all: a split row that names one, a `ui` frame."""
    found: list[str] = []
    column = None
    for line in read(home / "story-split.md").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
        if column is None:
            column = next((at for at, cell in enumerate(cells) if cell.lower().startswith("surfaces and states")), None)
        elif len(cells) > column and "·" in cells[column]:
            found.append(f"story-split.md has {cells[0]} deliver `{cells[column]}`")
    lines = model.replace("\r", "").split("\n")
    for name in slices_of(home):
        opened = re.compile(rf"""^\s*-\s*id:\s*["']?{re.escape(name)}["']?\s*(?:#.*)?$""")
        start = next((at for at, line in enumerate(lines) if opened.match(line)), None)
        if start is None:
            continue
        end = next((at for at in range(start + 1, len(lines)) if re.match(r"^\s*-\s*id:\s", lines[at])), len(lines))
        if any(re.search(r"\btype:\s*[\"']?ui\b", line.split("#")[0]) for line in lines[start:end]):
            found.append(f"docs/event-model/model.yaml gives slice {name} a `ui` frame")
    return found


def grounds(root: Path, feature: str, drawn: int = 0,
            hinted: tuple[str, ...] = ()) -> tuple[str | None, list[str], list[str]]:
    """The reason the drawing gave (`None` where it gave no word of it), the grounds that hold, and what stands
    against recording it. Recorded only where there is a reason and nothing against. `hinted` are the surfaces
    the hand-over suggested the feature touches (`surface_hint.read`), which the drawing has to have answered."""
    home = root / "specs" / feature
    research = read(home / MOCKUPS / "research.md")
    why = declared(research)
    held: list[str] = []
    against: list[str] = []
    if why is None:
        return None, held, [f"specs/{feature}/{MOCKUPS}/research.md does not say `Surfaces: none — <why>`"]
    if len(why) < SHORTEST:
        against.append(f"specs/{feature}/{MOCKUPS}/research.md says `Surfaces: none` and gives no reason")
    else:
        held.append("the drawing's research note says so")
    asked = requirements(read(home / "spec.md"))
    meets = [(at, text, found.group(0)) for at, text in asked if (found := MET.search(text))]
    if not asked:
        against.append(f"specs/{feature}/spec.md has no requirement line (`FR-…`, a user story, a "
                       "Given/When/Then) to read for a surface")
    elif meets:
        against += [f"specs/{feature}/spec.md:{at} asks for something a person or another system meets "
                    f"(`{word}`): {text[:140]}" for at, text, word in meets[:3]]
        against += [f"and {len(meets) - 3} more requirement(s) like those"] if len(meets) > 3 else []
    else:
        held.append(f"none of the specification's {len(asked)} requirement(s) names anything a person or "
                    "another system meets")
    shown = surfaced(home, read(root / "docs/event-model/model.yaml"))
    against += shown
    if not shown:
        named = slices_of(home)
        held.append(f"none of its {len(named)} slice(s) carries a `ui` frame or names a surface" if named
                    else "it has no slice yet, so none carries a `ui` frame")
    if hinted:
        suggested = ", ".join(f"`{one}`" for one in hinted)
        answer = ANSWERED.search(research)
        reason = re.sub(r"[*_`]", "", answer.group("why")).strip().rstrip(".").strip() if answer else ""
        if len(reason) < SHORTEST:
            against.append(f"the hand-over conversation suggested it touches {suggested} — a suggestion, and the "
                           f"drawing disagrees with it without saying why: say `Suggested surfaces: not touched "
                           f"— <why>` in specs/{feature}/{MOCKUPS}/research.md, or draw them")
        else:
            held.append(f"the hand-over conversation suggested it touches {suggested}, and the drawing answers "
                        f"that it does not: {reason}")
    states = read(home / MOCKUPS / "mock-states.md")
    if drawn:
        against.append(f"{drawn} surface page(s) of it are drawn under specs/{feature}/{MOCKUPS}/")
    if VERDICT.search(states) and NONE not in states:
        against.append(f"specs/{feature}/{MOCKUPS}/mock-states.md already holds a verdict")
    return why, held, against


def settle(root: Path, feature: str, drawn: int = 0, hinted: tuple[str, ...] = ()) -> tuple[bool, str]:
    """Record `surfaces: none` where the grounds are positive, and answer whether it stands and what to say.
    `(False, "")` where the drawing never said it had no surface: the stage's ordinary refusals are the answer."""
    path = root / "specs" / feature / MOCKUPS / "mock-states.md"
    if NONE in read(path) and not drawn:
        return True, f"{feature} has no surface: specs/{feature}/{MOCKUPS}/mock-states.md says `{NONE}` already"
    why, held, against = grounds(root, feature, drawn, hinted)
    if why is None:
        return False, ""
    if against:
        return False, (f"the drawing says {feature} has no surface, and that is not recorded on its word: "
                       + "; ".join(against) + f". Nothing was written. Settle it in the agent: /mockups {feature}")
    path.parent.mkdir(parents=True, exist_ok=True)
    record = (f"{NONE} — {why}\n\n<!-- recorded by the mock-up stage, not by a person, on these grounds: "
              f"{'; '.join(held)}. To draw a surface after all, delete this file and run /mockups {feature}. -->\n")
    path.write_text(record, encoding="utf-8")
    return True, (f"{feature} adds and changes no surface — {why}. Recorded as `{NONE}` in "
                  f"specs/{feature}/{MOCKUPS}/mock-states.md ({'; '.join(held)}); there is nothing to approve, "
                  "and the feature moves on")
