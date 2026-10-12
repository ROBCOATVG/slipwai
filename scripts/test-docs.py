#!/usr/bin/env python3
"""Run the guide's first three pages against a freshly generated project, so they cannot drift.

`make test-docs` runs this. It exists because those pages were written from a real session and *still*
shipped six wrong lines — two invented command names, three invented output lines, and a port that was
never bound. Every one of them would have been caught by running the page. So the page is run.

**The gate is a programme, and it reads like the pages.** It generates a project, puts the pages' own model
in it, renders the chart, writes the log lines a captain writes at `BOK-01`'s first stage, and asks the
commands the pages ask, in the order the pages ask them. Each page's commands must appear in exactly the
order the programme has them: a command added to a page, removed from one, or moved is a failure until the
programme is changed with it. That closure rule is the point — a gate that silently covers less than it
claims is the failure this whole file is about.

Each command is checked the strongest way it can be:

  run      The command is run here and every output line the page prints must appear in what it printed.
  capture  It cannot run here — it needs the real chandlery or a different project's run — but
           `docs/captures/` holds its output from a real run (slice 9.3), and the page must match that.
  named    It cannot run and has no capture, so it must print nothing on the page. Its *names* are still
           checked: a make target, a slipwai verb, a script, a `/command` and a skill are held against the
           generation whether they are in a block or in a sentence, because `/speckit-model` — a command
           that has never existed — was written in a sentence.

Nothing about the clock is checked. Two things vary between runs and no page makes a claim about either:
when a line was written, and how long ago. Everything else is compared as written — wildcarding digits
would have let `clearance: 3 of 3` pass against the `1 of 3` this gate found on the page.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guide"
CAPTURES = ROOT / "docs/captures"
FIXTURE = ROOT / "tests/fixtures/docs/model.yaml"
#: Slice 9.4 holds the first three pages. The last two describe a run that cannot be stood up offline and
#: are held by their captures and by the link check.
PAGES = ("start-here.md", "first-feature.md", "a-second-person.md")
#: The pages are written in TypeScript, which comes from the chandlery and is not here. `toy` is the
#: language template's inert placeholder, pinned in `packages/`. The difference reaches exactly one place —
#: the interview's menus — and is handled there, by name.
BACKEND = "toy-plain"
PROJECT = "bookings"
CONTEXTS = ("booking", "availability")


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# Reading the pages
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

BLOCK = re.compile(r"^```(\S*)[^\n]*\n(.*?)^```", re.S | re.M)
#: An inline code span. Names are read from these and from command lines, never from running prose: the
#: pages talk *about* the chandlery and a reader should not have to avoid the word.
CODE = re.compile(r"`([^`\n]+)`")
SLASH = re.compile(r"^/([a-z][a-z0-9-]*)")
#: A `key=value` argument written after a `/command`. The pages assert these — `/sail fairway=booking` is
#: a claim about what the command takes — and a page naming an argument the command does not have is the
#: same class of wrong as naming a command that does not exist.
ARGUMENT = re.compile(r"^/([a-z][a-z0-9-]*)((?:\s+[a-z][a-z0-9-]*=\S+)+)")
SKILL = re.compile(r"skills/([a-z0-9-]+)/SKILL\.md")
MAKE = re.compile(r"^make ([a-z][a-z0-9-]*)")
VERB = re.compile(r"^slipwai ([a-z][a-z0-9-]*)")
SCRIPT = re.compile(r"\b(scripts/[a-z0-9_/-]+\.py)\b")


@dataclass
class Said:
    """One command a page shows being run, and the lines it is shown printing."""
    command: str
    output: list[str] = field(default_factory=list)
    line: int = 0


def blocks(text: str) -> list[tuple[str, str, int]]:
    """Every fenced block as (info string, body, the line its fence is on)."""
    return [(found.group(1), found.group(2), text[: found.start()].count("\n") + 1)
            for found in BLOCK.finditer(text)]


def said(text: str) -> list[Said]:
    """Every command the page shows being run, in the order the page shows them.

    A `console` block is a transcript: `$ ` starts a command and what follows is its output. An `sh` block
    is a command with nothing shown printing. Any other block is something a person types into an agent, or
    a tree, or a file — not a shell.
    """
    found: list[Said] = []
    for info, body, line in blocks(text):
        if info == "console":
            for one in body.splitlines():
                if one.startswith("$ "):
                    found.append(Said(one[2:].strip(), [], line))
                elif found and one.strip():
                    found[-1].output.append(one)
        elif info == "sh":
            found += [Said(stripped.split("  #")[0].strip(), [], line) for one in body.splitlines()
                      if (stripped := one.strip()) and not stripped.startswith("#")]
    return found


def names(text: str) -> list[str]:
    """Every thing the page names as a command: inline code spans, and the lines of its blocks."""
    spans = CODE.findall(re.sub(BLOCK, "", text))
    lines = [one.strip().removeprefix("$ ").strip()
             for _info, body, _line in blocks(text) for one in body.splitlines()]
    return spans + lines + SKILL.findall(text)


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# Comparing what they say with what is printed
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

#: The two things a run says differently every time, and the only two freed. A board drawn twice differs
#: here and nowhere else.
CLOCK = (re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"), re.compile(r"\b\d+[smhd] ago\b"))


def normalised(line: str) -> str:
    """One line ready to compare: column padding collapsed, the clock made free.

    Padding moves when a value changes width, so a board compared character for character fails on a value
    that is right. Comparing cells rather than spacing keeps the check about what the line says.
    """
    for pattern in CLOCK:
        line = pattern.sub("<when>", line)
    return " ".join(line.split())


def missing(documented: list[str], actual: str) -> str | None:
    """Nothing, or the first line the page prints that the command did not.

    The page's lines must appear, in order; the command may print more. That is what lets a page quote the
    first lines of a long answer without reprinting all of it, while still failing on a line that is wrong.
    """
    lines = [normalised(one) for one in actual.splitlines()]
    at = 0
    for one in documented:
        want = normalised(one)
        if not want:
            continue
        while at < len(lines) and lines[at] != want:
            at += 1
        if at == len(lines):
            return one
        at += 1
    return None


#: A pre-release suffix is not drift: the page names the release, and this checkout is on its way there.
RELEASE = re.compile(r"\.(dev|rc|a|b)\d+$")


def same_release(documented: list[str], actual: str) -> str | None:
    return missing([RELEASE.sub("", one) for one in documented], RELEASE.sub("", actual.strip()))


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# The project the pages describe
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

def keel_env() -> dict[str, str]:
    """This checkout's keel and its pinned packages, with an index that is not there to reach."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")
    environment["SLIPWAI_LANGUAGES"] = str(ROOT / "packages")
    environment["SLIPWAI_INDEX"] = (ROOT / "tests/fixtures/no-index").as_uri()
    return environment


def generate(parent: Path, name: str) -> Path:
    """A project, generated the way `slipwai generate <name> [flags]` generates one for a script or CI."""
    subprocess.run(
        [sys.executable, "-m", "slipwai", "generate", name, "--profile", "event-modelling",
         "--backend", BACKEND, "--frontend", "none", "--service-name", PROJECT,
         *[flag for context in CONTEXTS for flag in ("--context", context)],
         "--output", str(parent), "--skip-checks"],
        check=True, cwd=ROOT, env=keel_env(), stdout=subprocess.DEVNULL,
    )
    return parent / name


def when(seconds_ago: int) -> str:
    """A log timestamp that many seconds in the past. Recent, so a berth reads `working` rather than
    `stalled` — which is the state the page is describing, and the clock itself is never compared."""
    return (datetime.now(UTC) - timedelta(seconds=seconds_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_log(project: Path, fairway: str, lines: list[dict]) -> None:
    deck = project / ".slipwai/logs" / "booking"
    deck.mkdir(parents=True, exist_ok=True)
    (deck / f"{fairway}.jsonl").write_text(
        "".join(json.dumps({"v": 1, **line}) + "\n" for line in lines), encoding="utf-8")


def git(project: Path, *argv: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@local", *argv],
                   cwd=project, check=True, capture_output=True)


def model_it(project: Path) -> None:
    """What the modelling conversation and `/speckit-specify` leave behind: the model, and the feature.

    `specs/<feature>/slices/` is what names the feature in flight, which is why it is here and not later:
    without it the chart would be rendered for a feature called `model`, and the pages call it `booking`.
    """
    (project / "docs/event-model/model.yaml").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    (project / "specs/booking/slices").mkdir(parents=True, exist_ok=True)


def sail_bok01(project: Path) -> None:
    """What `/sail BOK-01` leaves behind: its branch, its record, and the five lines its captain wrote.

    The `mark-set` line is the one the pages are about. It is written at the slice's first stage, in its own
    worktree, which is why it is here beside `claimed` and three lines before anything asks to merge.
    """
    git(project, "add", "-A")
    git(project, "commit", "-qm", "the model, and the chart rendered from it")
    git(project, "checkout", "-qb", "slice/BOK-01")
    record = project / "specs/booking/slices/BOK-01"
    record.mkdir(parents=True, exist_ok=True)
    (record / "slice.md").write_text("# BOK-01 — Hold a table\n", encoding="utf-8")
    git(project, "add", "-A")
    git(project, "commit", "-qm", "BOK-01")
    write_log(project, "booking", [
        {"t": when(130), "kind": "claimed", "fairway": "booking", "slice": "BOK-01"},
        {"t": when(130), "kind": "mark-set", "fairway": "booking", "slice": "BOK-01", "mark": "BookingHeld"},
        {"t": when(90), "kind": "heartbeat", "fairway": "booking", "tokens": 42},
        {"t": when(60), "kind": "demo", "fairway": "booking", "slice": "BOK-01", "verdict": "accepted"},
        {"t": when(30), "kind": "request", "fairway": "booking", "id": "merge-BOK-01", "what": "merge",
         "slice": "BOK-01", "detail": "merge slice/BOK-01 into trunk after the full gate"},
        {"t": when(20), "kind": "merged", "fairway": "booking", "slice": "BOK-01",
         "commit": "a1b2c3d4e5f6a7b8"},
    ])


def second_worker(project: Path) -> None:
    """A second person, in the other fairway, with the first slice merged behind them."""
    write_log(project, "booking", [
        {"t": when(130), "kind": "claimed", "fairway": "booking", "slice": "BOK-01"},
        {"t": when(130), "kind": "mark-set", "fairway": "booking", "slice": "BOK-01", "mark": "BookingHeld"},
        {"t": when(60), "kind": "demo", "fairway": "booking", "slice": "BOK-01", "verdict": "accepted"},
        {"t": when(40), "kind": "merged", "fairway": "booking", "slice": "BOK-01", "commit": "a1b2c3d"},
        {"t": when(30), "kind": "claimed", "fairway": "booking", "slice": "BOK-02"},
        {"t": when(12), "kind": "heartbeat", "fairway": "booking", "tokens": 84},
    ])
    write_log(project, "availability", [
        {"t": when(31), "kind": "claimed", "fairway": "availability", "slice": "AVA-01"},
        {"t": when(31), "kind": "heartbeat", "fairway": "availability", "tokens": 42},
    ])


def with_forge(project: Path) -> None:
    """The guide's hand-taken claim is a push, proved against an offline bare forge."""
    forge = project.parent / "forge.git"
    subprocess.run(["git", "init", "--bare", "-q", str(forge)], check=True)
    git(project, "remote", "add", "origin", str(forge))


def claim_pushed(project: Path) -> None:
    """A successful local claim would cover less than the guide promises; require its remote ref."""
    forge = project.parent / "forge.git"
    subprocess.run(["git", "--git-dir", str(forge), "rev-parse", "--verify", "refs/slipwai/claims/booking"],
                   check=True, capture_output=True)


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# The programme
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

KEEL, FRESH, BOOKING = "keel", "fresh", "booking"


@dataclass
class Shown:
    """One command a page shows, however this gate goes on to check it."""
    page: str
    command: str


@dataclass
class Run(Shown):
    """A command this gate runs, and where."""
    where: str = BOOKING


@dataclass
class Named(Shown):
    """A command this gate cannot run, with the reason. It must print nothing on the page."""
    why: str = ""


@dataclass
class Captured(Shown):
    """A command this gate cannot run, whose output a real run already captured."""
    capture: str = ""


@dataclass
class Pinned(Shown):
    """A command this gate cannot run, whose output names a value held in one source file."""
    source: str = ""


@dataclass
class Interview(Shown):
    """`slipwai generate` bare: driven for real, and compared question by question."""
    command: str = "slipwai generate"


@dataclass
class Seed:
    """A stage of the run the pages describe, applied between commands."""
    do: Callable[[Path], None]
    what: str


Step = Shown | Seed


#: The pages' own run, said once. Each page's commands must appear in exactly this order.
PROGRAMME: list[Step] = [
    Named("start-here.md", "uv tool install slipwai",
          "installs from PyPI; `slipwai --version` below is that same command, installed"),
    Run("start-here.md", "slipwai --version", KEEL),
    Captured("start-here.md", "slipwai search", "chandlery-search.txt"),
    Named("start-here.md", "slipwai install typescript",
          "downloads and verifies a signed package from the chandlery"),
    Interview("start-here.md"),
    Interview("start-here.md"),
    Named("start-here.md", "cd bookings", "a shell builtin; the directory it names is the generation below"),
    Named("start-here.md", "./init", "installs Spec Kit over the network, once, into the project"),
    Run("start-here.md", "make verify", FRESH),
    Run("start-here.md", "make verify", FRESH),

    Seed(model_it, "the modelling conversation writes docs/event-model/model.yaml"),
    Run("first-feature.md", "make model"),
    Run("first-feature.md", "make chart"),
    Run("first-feature.md", "make check-chart"),
    Run("first-feature.md", "python3 scripts/agents/clearance.py"),
    Seed(sail_bok01, "/sail BOK-01 claims the slice and sets its mark"),
    Run("first-feature.md", "slipwai fleet booking"),
    Run("first-feature.md", "python3 scripts/agents/clearance.py"),

    Run("a-second-person.md", "make check-slice-scope"),
    Run("a-second-person.md", "slipwai fleet booking"),
    Run("a-second-person.md", "python3 scripts/agents/clearance.py"),
    Seed(second_worker, "a second person claims AVA-01, and BOK-01 is merged"),
    Run("a-second-person.md", "slipwai fleet"),
    Seed(with_forge, "the second person has a bare forge to publish the hand-taken claim to"),
    Run("a-second-person.md", "python3 scripts/agents/claims.py --take booking"),
    Seed(claim_pushed, "the booking claim exists on the forge, rather than only on this machine"),
    Named("a-second-person.md", "slipwai fleet", "the same board, shown once more as a figure"),
    Named("a-second-person.md", "slipwai fleet watch", "redraws until it is interrupted"),
    Captured("a-second-person.md", "slipwai fleet ordering", "stream-log.txt"),
    Pinned("a-second-person.md", "slipwai bridge", "src/slipwai/bridge.py"),
]


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# The interview
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

#: What to answer when a prompt holds this. The first match wins, and a prompt nothing matches is answered
#: with Enter — its own default, which is also how a question added to the interview shows up here instead
#: of silently shifting every answer after it by one.
ANSWERS = (
    ("Project name", PROJECT),
    ("Output parent", None),
    ("Service name", PROJECT),
    ("own?", "Taking and changing a reservation."),
    ("Bounded contexts", ", ".join(CONTEXTS)),
)


def interview(parent: Path) -> str:
    """Drive the real interview through pipes, and return its transcript.

    Pipes rather than a pseudo-terminal, which is not a shortcut: in a terminal `prompt_choice` puts up a
    list to move through with the arrow keys, and anywhere else it is the typed question with its choices
    and its default in the line. The second is what `start-here.md` shows, so the second is what is driven.

    Answered by reading each prompt and matching it, never from a list in order: a positional list shifts
    silently when a question is added, and then this gate answers the wrong one.
    """
    import select  # noqa: PLC0415  - only this function waits on a pipe

    parent.mkdir(parents=True, exist_ok=True)
    answers = [(match, str(parent) if answer is None else answer) for match, answer in ANSWERS]
    # `-u` so a prompt reaches us when it is written: `input()` to a pipe is buffered otherwise, and a
    # reader waiting for a prompt that will never be flushed waits for ever.
    process = subprocess.Popen(
        [sys.executable, "-u", "-m", "slipwai", "generate", "--skip-checks"],
        cwd=parent, env=keel_env(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=False,
    )
    assert process.stdin is not None and process.stdout is not None
    transcript, pending = "", ""
    while True:
        ready, _, _ = select.select([process.stdout], [], [], 120)
        if not ready:
            process.kill()
            raise RuntimeError(f"the interview stopped at {pending.splitlines()[-1:]!r}")
        chunk = os.read(process.stdout.fileno(), 4096).decode("utf-8", "replace")
        if not chunk:
            break
        transcript += chunk
        pending += chunk
        # A prompt is written without a newline and ends in a colon, which is how `input()` leaves it.
        if pending.rstrip(" ").endswith(":"):
            prompt = pending.splitlines()[-1]
            process.stdin.write((next((a for match, a in answers if match in prompt), "") + "\n").encode())
            process.stdin.flush()
            pending = ""
        elif pending.endswith("\n"):
            pending = ""
    process.wait(timeout=120)
    if process.returncode != 0:
        raise RuntimeError(f"the interview exited {process.returncode}:\n{transcript}")
    return transcript


#: The choices and the shown default move with the language and the machine; the words of the question do
#: not, so a documented question is compared without them.
VARIABLE = re.compile(r"\s*[\[(][^\])]*[\])]")


def stem(line: str) -> str | None:
    """The question a line asks, without its answer, its choices or its default."""
    if line.startswith(" ") or not line.strip():
        return None
    body = line.rsplit(": ", 1)[0] if ": " in line else line[:-1] if line.endswith(":") else None
    return VARIABLE.sub("", body).strip() if body else None


def check_interview(parent: Path, documented: list[str]) -> list[str]:
    """Every question the page shows the interview asking must be one the interview can ask.

    One it did not ask here is held against the source that would print it instead. That is not laxness: a
    language with one production target is never asked which target, and the pinned toy language has one,
    so some of the page's questions cannot be reached from any answer this run could give.
    """
    transcript = interview(parent / "interview")
    asked = {stem(line) for line in transcript.replace(": ", ": \n").splitlines()}
    spelled = "\n".join(path.read_text(encoding="utf-8") for path in
                        (ROOT / "src/slipwai/cli_prompts.py", ROOT / "src/slipwai/cli_generate.py",
                         ROOT / "src/slipwai/cli.py", ROOT / "catalog.json"))
    findings = []
    for line in documented:
        question = stem(line)
        if not question or question in asked:
            continue
        if any(word and word not in spelled for word in re.split(r"[^A-Za-z]+", question)):
            findings.append(f"start-here.md shows the interview asking {question!r}, which it did not ask "
                            "and which no prompt in the keel spells")
    return findings


# ──────────────────────────────────────────────────────────────────────────────────────────────────────
# The gate
# ──────────────────────────────────────────────────────────────────────────────────────────────────────

def slash_exists(name: str, project: Path, keel: str) -> bool:
    """Whether `/<name>` is something a reader can actually type.

    Three kinds answer to a slash and they live in three places: the toolkit's own commands, which are
    files in the project; the skills, which are directories in it; and Spec Kit's, which `./init` installs
    over the network and which no generation here has — so those are held against the keel's own source,
    which is where the ladder names the ones it runs. That last one is the weakest of the three and is
    still enough: `/speckit-model`, which this page shipped, is in none of them.
    """
    return ((project / "commands" / f"{name}.md").is_file()
            or (project / "skills" / name / "SKILL.md").is_file()
            or f"/{name}" in keel)


def check_arguments(page: str, command: str, written: str, project: Path) -> list[str]:
    """Every `key=` a page writes after a `/command`, against that command's own `argument-hint`.

    The hint is the one place a command says what it takes, so it is the one place to check a page against.
    A command with no file here is somebody else's — Spec Kit's — and `slash_exists` has already said so;
    there is nothing to read its arguments from and nothing is claimed about them.
    """
    file = project / "commands" / f"{command}.md"
    if not file.is_file():
        return []
    hint = next((line for line in file.read_text(encoding="utf-8").splitlines()
                 if line.startswith("argument-hint:")), "")
    return [f"{page}: `/{command} {key}=…` names an argument, and commands/{command}.md's argument-hint "
            f"does not have `{key}=`: {hint.removeprefix('argument-hint:').strip() or 'there is none'}"
            for key in re.findall(r"\s([a-z][a-z0-9-]*)=", written) if f"{key}=" not in hint]


def check_names(page: str, text: str, project: Path, targets: set[str], verbs: set[str]) -> list[str]:
    """Every name the page gives as a command, against what a generated project has."""
    keel = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                     for path in sorted((ROOT / "src/slipwai").rglob("*.py")))
    findings = []
    for name in sorted(set(names(text))):
        if (found := MAKE.match(name)) and found.group(1) not in targets:
            findings.append(f"{page}: `make {found.group(1)}` is not a target of a generated Makefile")
        if (found := VERB.match(name)) and found.group(1) not in verbs | {"generate"}:
            findings.append(f"{page}: `slipwai {found.group(1)}` is not a verb the command takes")
        if (found := SLASH.match(name)) and not slash_exists(found.group(1), project, keel):
            findings.append(f"{page}: `/{found.group(1)}` is not a command, a skill, or anything the keel "
                            "names — nothing a reader could type")
        if found := ARGUMENT.match(name):
            findings += check_arguments(page, found.group(1), found.group(2), project)
        for path in SCRIPT.findall(name):
            if not (project / path).is_file():
                findings.append(f"{page}: {path} is not in a generated project")
    for name in sorted(set(SKILL.findall(text))):
        if not (project / "skills" / name / "SKILL.md").is_file():
            findings.append(f"{page}: skills/{name}/SKILL.md is not a skill a generated project has")
    return findings


def check_chart_block(page: str, text: str, project: Path) -> list[str]:
    """A `yaml` block quoting the chart must quote the chart that is rendered."""
    chart = (project / "specs/booking/chart.yaml")
    if not chart.is_file():
        return []
    held = chart.read_text(encoding="utf-8")
    findings = []
    for info, body, line in blocks(text):
        if info != "yaml" or "owns:" not in body:
            continue
        for owned in re.findall(r'"([^"]+\*\*)"', body):
            if owned not in held:
                findings.append(f"{page}:{line}: the chart block says a fairway owns {owned!r}, and the "
                                "chart `make chart` renders does not")
    return findings


#: A command this gate cannot run on this machine, and what in its output says so. A *skip*, printed and
#: counted, never a pass: the whole point of the three tiers is that nothing is silently unchecked, and a
#: machine that could not run something has to say which something.
CANNOT = (
    ("make verify", ("npm", "not found"), "Node is not installed, and `check-drawio` needs it"),
    ("make model", ("Failed to launch", "browser"),
     "mermaid renders through a headless Chromium and none will start here; "
     "MERMAID_PUPPETEER_CONFIG with `--no-sandbox` is what a container or a runner needs"),
    ("make model", ("npm", "not found"), "Node is not installed, and the renderer runs on it"),
)


def refused_here(command: str, output: str) -> str | None:
    """Why this machine could not run that command, or None where it ran."""
    for named, markers, why in CANNOT:
        if named == command and all(marker in output for marker in markers):
            return why
    return None


def run(command: str, where: Path) -> str:
    argv = command.split()
    if argv[0] == "slipwai":
        argv = [sys.executable, "-m", "slipwai", *argv[1:]]
    elif argv[0] == "python3":
        argv = [sys.executable, *argv[1:]]
    done = subprocess.run(argv, cwd=where, env=keel_env(), capture_output=True, text=True)
    return done.stdout + done.stderr


def main(argv: list[str]) -> int:
    findings: list[str] = []
    done: list[str] = []
    skipped: list[str] = []
    pages = {page: (GUIDE / page).read_text(encoding="utf-8") for page in PAGES}
    shown = {page: said(text) for page, text in pages.items()}

    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary)
        fresh = generate(parent, "fresh")
        booking = generate(parent, PROJECT)
        where = {KEEL: ROOT, FRESH: fresh, BOOKING: booking}

        targets = set(re.findall(r"^([a-z][a-zA-Z0-9_-]*):", (booking / "Makefile").read_text(encoding="utf-8"), re.M))
        help_text = subprocess.run([sys.executable, "-m", "slipwai", "--help"], check=True, cwd=ROOT,
                                   env=keel_env(), capture_output=True, text=True).stdout
        verbs = set(re.search(r"\{([a-z0-9,-]+)\}", help_text).group(1).split(","))  # type: ignore[union-attr]

        for page, text in pages.items():
            findings += check_names(page, text, booking, targets, verbs)

        # The page's commands must be the programme's commands, in order. Checked before anything runs, so a
        # page that has grown past the gate says so rather than failing somewhere in the middle.
        for page in PAGES:
            planned = [step.command for step in PROGRAMME
                       if isinstance(step, Shown) and step.page == page]
            printed = [one.command for one in shown[page]]
            if planned != printed:
                findings.append(f"{page} runs {printed}, and scripts/test-docs.py has {planned}. A command "
                                "on a page that the programme does not have is one nothing checks.")
        if findings:
            print("\n".join(f"test-docs: {finding}" for finding in findings), file=sys.stderr)
            return 1

        at = {page: 0 for page in PAGES}
        for step in PROGRAMME:
            if isinstance(step, Seed):
                step.do(booking)
                done.append(f"seeded   {step.what}")
                continue
            page = step.page
            one = shown[page][at[page]]
            at[page] += 1
            if isinstance(step, Named):
                if one.output:
                    findings.append(f"{page}:{one.line}: `{one.command}` cannot be run here ({step.why}) and "
                                    "the page prints its output anyway, so nothing checks it")
                continue
            if isinstance(step, Captured):
                held = (CAPTURES / step.capture).read_text(encoding="utf-8")
                if gone := missing(one.output, held):
                    findings.append(f"{page}:{one.line}: the block quotes docs/captures/{step.capture}, "
                                    f"which does not have the line {gone.strip()!r}")
                done.append(f"captured {step.command} — docs/captures/{step.capture}")
                continue
            if isinstance(step, Pinned):
                source = (ROOT / step.source).read_text(encoding="utf-8")
                for value in re.findall(r"\b\d+\.\d+\.\d+\.\d+\b|\b\d{2,}\b", "\n".join(one.output)):
                    if value not in source:
                        findings.append(f"{page}:{one.line}: `{one.command}` is shown printing {value}, and "
                                        f"{step.source} does not have it")
                done.append(f"pinned   {step.command} — {step.source}")
                continue
            if isinstance(step, Interview):
                if step is next(one for one in PROGRAMME if isinstance(one, Interview)):
                    continue  # the `sh` block, which is the same command with nothing shown printing
                findings += check_interview(parent, one.output)
                done.append("ran      slipwai generate (the interview, question by question)")
                continue
            assert isinstance(step, Run)
            output = run(step.command, where[step.where])
            if (why := refused_here(step.command, output)) is not None:
                skipped.append(f"{step.command} — {why}")
                continue
            compare = same_release if step.command == "slipwai --version" else missing
            if gone := compare(one.output, output):
                findings.append(f"{page}:{one.line}: `{step.command}` does not print {gone.strip()!r}. It "
                                "printed:\n" + "\n".join("      " + line for line in output.splitlines()[-14:]))
            done.append(f"ran      {step.command}  ({step.where})")

        findings += check_chart_block("a-second-person.md", pages["a-second-person.md"], booking)

    print("\n".join("  " + line for line in done))
    for line in skipped:
        print(f"  skipped  {line}")
    if findings:
        print("\n".join(f"test-docs: {finding}" for finding in findings), file=sys.stderr)
        return 1
    print(f"test-docs: {len(PAGES)} pages, {sum(len(one) for one in shown.values())} commands, none unchecked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
