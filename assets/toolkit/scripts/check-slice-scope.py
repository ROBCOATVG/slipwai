#!/usr/bin/env python3
"""Hold a slice branch to the files one slice may touch — the shared-surface rule, held mechanically.

Once the event contract is settled, ready slices run concurrently: one delegate per slice, each on a
`slice/<id>` branch in its own worktree, merged back in split order (`commands/sail.md`, *Running ready
slices concurrently*). That works only because the files two slices could fight over are few and named.
This is the list, and the gate on it. On a branch that is not `slice/<id>` there is nothing to hold, and the
script says so and exits 0 — which is why `make verify` runs it everywhere.

What a slice's change may contain — everything since the branch left `main`, committed or not:

- **its own record**, `specs/<feature>/slices/<id>/**`, and the feature's cumulative artifacts — `spec.md`,
  `story-split.md`, `contracts/`, `checklists/`, `people/`, `slices/README.md` — which every slice amends and
  the host merges in split order. The decision and adversary records are among them, one file each under
  `decisions/` and `adversary-log/`, with the two logs `make decisions` renders from them: `/cruise` writes a
  decision where the ladder took it, which during a slice's stages is the slice's branch, and `check-decisions`
  wants every `Written to` path in the tree, which for a slice's artifacts is only true there;
- **its capability's record**, `specs/<feature>/capabilities/<capability>/**` — `gates.md` and the demo log —
  for the capability the chart puts the slice in, under the feature that capability's slices are under. The
  harbourmaster holds a capability's last merge until `gates.md` says `Cleared:` on that slice's branch;
- **its own block of `docs/event-model/model.yaml`**: every other slice's block reads exactly as on `main`,
  but for its `code` list where this branch moved or deleted a file it names — the list follows the file.
  Events, commands and read models are frames inside a slice's block, so the contract another slice builds
  against cannot move underneath it; `docs/event-model/mockups/` is per screen and open;
- **the committed canvas, `docs/event-model/model.drawio`**, because it is rendered from the model the slice
  just changed and `check-drawio` fails the branch until it is: that gate holds it to `model.yaml`, so it can
  carry nothing of the slice's own. The host regenerates it again after each merge. The chart,
  `specs/<feature>/chart.yaml`, is allowed on the same terms on that profile: `check-chart` holds it to what
  `make chart` renders from the model;
- **a new ADR under `docs/adr/`**: a decision taken during the slice whose reversal would be a migration is
  written there at `Proposed`, by `/cruise` or by the slice's own planning. New files only — an ADR that exists
  is never edited; superseding one is the host's, on `main`;
- **code and tests of the service that owns it** — `service` in its model block, or any service where the
  model names none — its own build manifest and lock among them: a dependency or a build step the slice
  needs is added where the service declares them, in the same change as the code that uses it, and is
  never handed back (lean-coffee-club's SI1 handed back a line of its own service's `pom.xml`, which this
  gate would have let it write, and nobody landed it). **A workspace's one lock at the root is the slice's
  too** (`package-lock.json`, `pnpm-lock.yaml`, `uv.lock`): it is derived from the manifests, and where two
  slices' locks conflict the harbourmaster takes trunk's and writes it again (`scripts/agents/lockfiles.py`) — and, where the block names a `context`, nothing under another context's directory in
  `domain/` or `application/`. A browser app is open to every slice: a white box is one screen;
- **the context's events module additively**: it may only grow. A line may be added, and so may a member of an
  enum or a union of literals and an optional field of a shape, in any language whose lists, unions and shapes
  read as such (TypeScript and zod, Python, Go, Java); a member or field removed or renamed, a field made
  required, a type changed, or anything the gate cannot read as one of these, is refused, naming which it saw.
  It is the contract, and events already written are read back through it (issue 168);
- **its own flag's declaration**, `infra/service/flags.auto.tfvars`, additively and seeded `off`: a key, a
  comment, a blank line may be added, nothing removed or changed. The method asks for the declaration in the
  same change as the code that reads it, and `check-flags` holds a branch to that — declared and never read is
  red on `main`, read and never declared is red on the branch — so a slice refused the file could pass on
  neither. lean-coffee-club's MT1 handed the line back, nothing could land it alone, and it parked for a
  person; SI1 before it stubbed sign-in round the flag it could not declare;
- **under keystone mode** (the product in pilot, `scripts/agents/release_state.py`), **nothing of a
  capability's entry point but in its last slice**: `specs/<feature>/keystones.yaml` names each capability's
  entry as globs, and the chart's split order names its last slice. Every slice before it lands unreachable,
  which is how a pilot product keeps an unfinished capability from its users without a flag;
- **new migration files only**, timestamped so two slices never mint the same name: `YYYYMMDDHHMM_<name>`,
  or `V<YYYYMMDDHHMM>__<name>` under Flyway. The shipped numbered ones keep working — the order is lexical
  either way, and every stamp sorts after every number;
- **the composition root** — one line per use case, the one code file every slice touches, resolved in
  split order at merge and allowed here for that reason;
- **under a fairway's careen slice, `slice/<fairway>-careen`, that fairway's `fairways/<fairway>/careen.md`**,
  whose rows it closes. Nothing else under `fairways/`, and no other slice anything there: a finding a stage
  stows is a row in the capability's `stowed.md`, and the harbourmaster carries it into the careen at the
  merge, because a file every slice of a stream wrote was a conflict on every merge (issue 154);
- **its own dispatch ledger file**, `.slipwai/dispatch/<feature>/<id>.jsonl`, which `dispatch.py` writes into
  the slice's worktree so the evidence of the slice's start rides in the pull request that lands it. Its own
  only: another slice's file, and the run's `.slipwai/dispatch/<feature>.jsonl`, are the host's.

Refused, each with what to do instead: the canonical slot at the feature root (`specs/<feature>/plan.md`,
`research.md`, `data-model.md`, `quickstart.md`, `tasks.md` — links into `slices/<id>/`, never committed;
a regular file there is a record about to be lost, on every branch), another slice's directory or model
block, another context's code, an edited or deleted migration, a numbered new migration, and anything else
in the repository — `Makefile`, `project.json`, the workspace's root manifests, `docker/`, `scripts/`, `skills/`,
`commands/`, `agents/`, CI, the docs other than the model and its canvas — which is the host's: landed on `main`
before the fan-out, or handed back as the question it is. A refusal is a hand-back, not something to work around.

The base the branch is compared with is where it left `main`, or last merged it in. Every `main` the checkout
knows is tried — `main`, `origin/main`, their `master` spellings — and the newest base wins: `origin/main` alone
goes stale the moment `main` moves locally and is not yet pushed (a migration run there, then merged into the
slice), and a stale base charges the slice with `main`'s own files.
"""

from __future__ import annotations

import difflib
import fnmatch
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
# Where the delivery material sits: the root, or `project.json`'s `layout.delivery` where the method was
# installed beside an existing codebase — this script's own tree is `<root>/<delivery>/scripts`. `specs/` stays
# at the root either way; the docs and the model checker move with the material.
DELIVERY = Path(__file__).resolve().parent.parent.relative_to(ROOT)
DOCS = (DELIVERY / "docs").as_posix() + "/"
MODEL = DELIVERY / "docs/event-model/model.yaml"
CANVAS = DELIVERY / "docs/event-model/model.drawio"
ADRS = (DELIVERY / "docs/adr").as_posix() + "/"
SLICE_BRANCH = re.compile(r"^slice/(?P<id>[A-Za-z0-9][A-Za-z0-9._-]*)$")
#: Where the chart is, on either profile. It names what each fairway owns, which is the boundary this gate
#: held from `model.yaml` alone before — and so held not at all on the standard profile, where any code in
#: any deployable passed. Slice 5.6.
SPECS = "specs"
CANONICAL_SLOTS = ("plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md")
FEATURE_SHARED = ("spec.md", "story-split.md", "adversary-log.md", "decisions.md")
#: `people/` is the story's: `commands/sail.md` rung 12 has a slice write the person its story signs in as there,
#: and game-club-manager's PE-01 was refused here for doing what the command said.
#: `decisions/` and `adversary-log/` are one file per decision and per slice's rows, which `make decisions` renders
#: the two logs from: a slice writes its own, and seven slices abreast never write one file.
FEATURE_SHARED_DIRECTORIES = ("contracts", "checklists", "people", "decisions", "adversary-log")
MIGRATION_DIRECTORIES = ("migrations", "migration")
MIGRATION_NAME = re.compile(r"^(?:\d+_|V\d+__)")
MIGRATION_SUFFIXES = {".sql", ".js", ".ts", ".py"}
#: A workspace's one lock at its root, by name: derived from the manifests, so the slice that changes a
#: manifest writes it. The names `scripts/agents/lockfiles.py` knows how to write again, and no others.
WORKSPACE_LOCKS = frozenset({"package-lock.json", "pnpm-lock.yaml", "uv.lock"})
STAMPED_MIGRATION = re.compile(r"^(?:\d{12}_|V\d{12}__)")
LAYERS_BY_CONTEXT = ("domain", "application")
#: What a run writes in any checkout, a slice's berth included: everything under `.slipwai/run/`, which the
#: generated `.gitignore` names in one line. Untracked, none of it is anything a slice did — `make preflight`
#: writes `preflight.json` in every berth, and a berth's `logs.unread-*` is lines kept aside when it was
#: linked — so in hr-test-2 every slice run abreast went red here on files the run itself had put there, and
#: in game-club-manager every berth did on the ACP session files a name-by-name list had not caught up with.
RUN_STATE = re.compile(r"^\.slipwai/run/.*$")
#: Where the release flags are declared (`check-flags.py`), and the one shape a slice may add there: a key
#: seeded `off`, with or without its comment. Blank lines and comments ride with it.
FLAGS = "infra/service/flags.auto.tfvars"
#: Every fairway's own files, which no slice writes, and what a fairway's careen slice is called: it alone
#: may change `fairways/<fairway>/careen.md`, to close the rows the harbourmaster carried there.
FAIRWAYS, CAREEN = "fairways/", "-careen"
FLAG_SEEDED_OFF = re.compile(r'^\s*[A-Za-z_][A-Za-z0-9_-]*\s*=\s*"off"\s*(#.*)?$')


def git(*arguments: str) -> str | None:
    try:
        completed = subprocess.run(["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout


def current_branch() -> str | None:
    """The branch under check: the checkout's, or the pull request's head where CI checks out a detached
    merge commit (`GITHUB_HEAD_REF`, which Gitea Actions sets the same way)."""
    for variable in ("GITHUB_HEAD_REF", "CI_COMMIT_REF_NAME"):
        if os.environ.get(variable):
            return os.environ[variable]
    name = git("rev-parse", "--abbrev-ref", "HEAD")
    if name is None:
        return None
    name = name.strip()
    return None if name == "HEAD" else name


def merge_base() -> str | None:
    """Where the branch left `main`, or last merged it in: the newest base among every `main` the checkout has.
    Trying `origin/main` alone is wrong on a machine where `main` has moved and not been pushed — the base is then
    older than the merge the slice took, and `main`'s own files land in the slice's diff."""
    bases: list[str] = []
    for name in ("main", "origin/main", "master", "origin/master"):
        found = git("merge-base", "HEAD", name)
        if found and found.strip() not in bases:
            bases.append(found.strip())
    if not bases:
        return None
    newest = bases[0]
    for candidate in bases[1:]:
        # `--is-ancestor` exits 0, with nothing printed, when the first commit is an ancestor of the second.
        if git("merge-base", "--is-ancestor", newest, candidate) is not None:
            newest = candidate
    return newest


def changed_files(base: str) -> dict[str, str]:
    """Every path that differs from the base, with its status: `A` added, `M` modified, `D` deleted. The working
    tree is compared, not the last commit, so an uncommitted edit is held the same as a committed one."""
    changes: dict[str, str] = {}
    for line in (git("diff", "--name-status", "--no-renames", base) or "").splitlines():
        status, _, path = line.partition("\t")
        if path:
            changes[path] = status[:1]
    for path in (git("ls-files", "--others", "--exclude-standard") or "").splitlines():
        if path and not RUN_STATE.match(path):
            changes[path] = "A"
    return changes


def deletions(base: str, path: str) -> int:
    numstat = git("diff", "--numstat", base, "--", path) or ""
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    return 0


# The events module may only grow.
#
# It used to be held by line: a line may be added and none removed (`deletions`). Widening an enum is the most
# ordinary change an events module gets, and by line it is a removed line — manda's S115 needed
# `z.enum(['alert', 'reminder', 'digest'])` to gain `'invite'`, was refused here, and parked for good, with
# nothing on the board able to land it (issue 168). So the change is judged and not the line: the module is
# read as tokens, comments and layout dropped, and every place it differs from the base must be a line added
# or an insertion that only widens what an event may carry. Where it cannot tell, it refuses, as it always did,
# and says what it saw.

#: A token: a string (triple-quoted first), a number, a name, or one character of punctuation. Comments are
#: matched so they can be dropped — `//` and `/* */` everywhere but Python, `#` in Python, where `//` divides.
TRIPLE = r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\''
STRINGS = TRIPLE + r'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`'
SLASH_COMMENT = r"//[^\n]*|/\*[\s\S]*?\*/"
HASH_COMMENT = r"#[^\n]*"
WORDS = r"\d+(?:\.\d+)?|[A-Za-z_$][\w$]*|\S"
TOKENS = {
    "slash": re.compile(f"(?P<comment>{SLASH_COMMENT})|(?P<token>{STRINGS}|{WORDS})"),
    # A triple-quoted string in Python is a docstring far more often than a value, so it goes with the comments.
    "hash": re.compile(f"(?P<comment>{HASH_COMMENT}|{TRIPLE})|(?P<token>{STRINGS}|{WORDS})"),
}
#: What separates the members of a list, a union or a shape.
SEPARATORS = {",", "|", ";"}
OPENING, CLOSING = {"(": ")", "[": "]", "{": "}"}, {")", "]", "}"}
NAME = re.compile(r"^[A-Za-z_$][\w$]*$")
LITERAL = re.compile(r"^(?:\"[\s\S]*\"|'[\s\S]*'|`[\s\S]*`|\d+(?:\.\d+)?)$")
#: Names that make a growing list *narrow* what it allows — `.exclude([...])`, `Omit<T, 'a' | 'b'>`, a JSON
#: schema's `required` — so a member added near one is not read as a widening.
NARROWING = {"exclude", "omit", "pick", "required", "not", "except", "without"}
#: What says a field may be absent. Taken away, the field became required.
OPTIONAL_MARKS = {"optional", "nullish", "nullable", "Optional", "NotRequired", "None", "undefined", "null", "?"}


def comment_style(path: str) -> str:
    return "hash" if Path(path).suffix in (".py", ".pyi") else "slash"


def code_lines(text: str, style: str) -> list[list[str]]:
    """The module as lines of tokens, comments and blank lines dropped, so neither a comment nor a reflow is a
    change. A token that spans lines belongs to the line it starts on."""
    lines: dict[int, list[str]] = {}
    line = 1
    at = 0
    for found in TOKENS[style].finditer(text):
        line += text.count("\n", at, found.start())
        at = found.start()
        if found.group("token") is not None:
            lines.setdefault(line, []).append(found.group("token"))
    return [lines[number] for number in sorted(lines)]


def split_members(run: list[str]) -> list[list[str]] | None:
    """A run of tokens split at the separators outside any bracket, or None where its brackets do not balance —
    an insertion that opens what it does not close is not a member."""
    pieces: list[list[str]] = [[]]
    depth: list[str] = []
    for token in run:
        if token in OPENING:
            depth.append(OPENING[token])
        elif token in CLOSING and (not depth or depth.pop() != token):
            return None
        if token in SEPARATORS and not depth:
            pieces.append([])
        else:
            pieces[-1].append(token)
    return None if depth else pieces


def dotted(tokens: list[str]) -> bool:
    """`Kind`, `z.literal`, `Kinds.INVITE`."""
    return bool(tokens) and len(tokens) % 2 == 1 and all(
        NAME.match(token) if index % 2 == 0 else token == "." for index, token in enumerate(tokens))


def a_member(piece: list[str]) -> bool:
    """A member of an enum or a union: `'invite'`, `z.literal('invite')`, `INVITE`, `INVITE("invite")` (Java),
    `Invite = 'invite'` (a TypeScript enum), `InviteSent` (a schema in a union)."""
    if len(piece) == 1:
        return bool(LITERAL.match(piece[0]) or NAME.match(piece[0]))
    if len(piece) >= 4 and piece[-3] == "(" and piece[-1] == ")" and LITERAL.match(piece[-2]):
        return dotted(piece[:-3])
    return len(piece) == 3 and bool(NAME.match(piece[0])) and piece[1] == "=" and bool(LITERAL.match(piece[2]))


def a_key(token: str) -> bool:
    return bool(NAME.match(token) or LITERAL.match(token))


def an_optional_field(piece: list[str]) -> bool:
    """A field a reader of an old event finds absent and is fine: `invitedBy?: string` (TypeScript),
    `invitedBy: z.string().optional()` or `.nullish()` (zod). A Python or Go field is a line of its own, and a
    line added is the module growing already."""
    if len(piece) >= 4 and a_key(piece[0]) and piece[1] == "?" and piece[2] == ":":
        return True
    if len(piece) < 3 or not a_key(piece[0]) or piece[1] != ":":
        return False
    rest = piece[2:]
    return len(rest) >= 4 and rest[-4:-2] in ([".", "optional"], [".", "nullish"]) and rest[-2:] == ["(", ")"]


def a_field(piece: list[str]) -> bool:
    return len(piece) >= 3 and a_key(piece[0]) and (piece[1] == ":" or piece[1:3] == ["?", ":"])


def widening(run: list[str], after: list[str], end: int) -> str | None:
    """Why an inserted run of tokens is not a widening, or None where it is: one or more members, or optional
    fields, each with the separator that joins it to its neighbours — or a separator alone, a trailing comma."""
    pieces = split_members(run)
    if pieces is None:
        return f"an insertion that does not close what it opens (`{' '.join(run)}`)"
    if len(pieces) == 1:
        if run == ["?"] and end < len(after) and after[end] == ":":
            return (f"a field made optional (`{' '.join(run)}`), which a slice may not do to a field events "
                    f"already carry")
        return f"an insertion the gate cannot read as a new member or an optional field (`{' '.join(run)}`)"
    inner = pieces[1:-1]
    if any(not piece for piece in inner):
        return f"an insertion the gate cannot read as a new member or an optional field (`{' '.join(run)}`)"
    for piece in [piece for piece in pieces if piece]:
        if a_member(piece) or an_optional_field(piece):
            continue
        if a_field(piece):
            return f"a required field added to a shape events already carry (`{' '.join(piece)}`)"
        return f"an insertion the gate cannot read as a new member or an optional field (`{' '.join(piece)}`)"
    return None


def words_of_name(token: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", token)}


def taken_away(removed: list[str], added: list[str], before: str = "", following: str = "") -> str:
    """What a deletion or a replacement did, in the words of the rule: a member removed or renamed, a field
    removed, renamed or made required, a type changed — or that it cannot tell which. `before` and `following`
    are the tokens either side of it, which say whether a name swapped is a key or a member, or a type."""
    shown = " ".join(removed)
    if (OPTIONAL_MARKS & set(removed)) - set(added):
        return f"a field made required (`{shown}` taken away)"
    if not added:
        pieces = split_members(removed) or [removed]
        if any(a_field(piece) for piece in pieces):
            return f"a field removed (`{shown}`)"
        if all(a_member(piece) for piece in pieces if piece):
            return f"a member removed (`{shown}`)"
        return f"something removed (`{shown}`)"
    typed = before in (".", ":") and following != ":"
    if len(removed) == len(added) == 1 and a_key(removed[0]) and a_key(added[0]) and not typed:
        return f"a member or a field renamed (`{removed[0]}` became `{added[0]}`)"
    return f"a type changed (`{shown}` became `{' '.join(added)}`)"


def chunk_violation(before: list[str], after: list[str]) -> str | None:
    """Why one changed stretch of the module is not a widening, or None where it is."""
    narrowing = sorted({word for token in after if NAME.match(token) for word in words_of_name(token)} & NARROWING)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag != "insert":
            return taken_away(before[i1:i2], after[j1:j2], before[i1 - 1] if i1 else "",
                              before[i2] if i2 < len(before) else "")
        if why := widening(after[j1:j2], after, j2):
            return why
        if narrowing:
            return (f"a member added beside `{narrowing[0]}`, where a longer list may allow less "
                    f"(`{' '.join(after[j1:j2])}`)")
    return None


def events_violation(base_text: str, text: str, path: str) -> str | None:
    """What the events module's change did that a slice may not do, or None where it only grows: lines added,
    members added to an enum or a union of literals, optional fields added to a shape."""
    style = comment_style(path)
    old, new = code_lines(base_text, style), code_lines(text, style)
    flat_old, flat_new = [" ".join(line) for line in old], [" ".join(line) for line in new]
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, flat_old, flat_new, autojunk=False).get_opcodes():
        if tag in ("equal", "insert"):
            continue  # a line added is the module growing, as it always was
        before = [token for line in old[i1:i2] for token in line]
        after = [token for line in new[j1:j2] for token in line]
        if why := chunk_violation(before, after):
            return why
    return None


def deployables() -> dict[str, dict]:
    try:
        document = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    listed = document.get("deployables") if isinstance(document, dict) else None
    return {name: record for name, record in listed.items() if isinstance(record, dict)} if isinstance(listed, dict) else {}


def load_model(text: str) -> object:
    """Parse the model with the loader `check-model` uses, so the two agree on how it reads."""
    checker = ROOT / DELIVERY / "scripts/event-model/check.py"
    if not checker.is_file():
        return None
    spec = importlib.util.spec_from_file_location("event_model_check", checker)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Loading the checker must not leave a `__pycache__` beside it: that would be an untracked file outside every
    # deployable, and this very gate would then refuse the branch for something it did itself.
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    sys.path.insert(0, str(module.TOOLS))
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        module.load_yaml()  # installs the parser beside the checker's other tools
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def slices_of(model: object) -> dict[str, dict]:
    if not isinstance(model, dict) or not isinstance(model.get("slices"), list):
        return {}
    return {str(item["id"]): item for item in model["slices"] if isinstance(item, dict) and "id" in item}


class Scope:
    """What one slice may touch, read off the branch, the model and the manifest."""

    def __init__(self, slice_id: str, base: str) -> None:
        self.slice_id = slice_id
        self.base = base
        self.apps = deployables()
        model_text = (ROOT / MODEL).read_text(encoding="utf-8") if (ROOT / MODEL).is_file() else None
        self.model = load_model(model_text) if model_text is not None else None
        own = slices_of(self.model).get(slice_id, {})
        self.service = own.get("service") if isinstance(own.get("service"), str) else None
        self.context = own.get("context") if isinstance(own.get("context"), str) else None
        try:
            self.fairway, self.owns = chart_fairways(slice_id)
            self.unreadable: str | None = None
        except ChartUnreadable as unreadable:
            self.fairway, self.owns, self.unreadable = None, {}, str(unreadable)

    def fairway_violation(self, path: str) -> str | None:
        """A path another fairway owns. The chart says who owns what, on both profiles.

        Where this slice is not on a chart, or the chart claims nothing, there is nothing to hold and the
        other rules still apply — the same reading as a branch that is not a slice branch. A path no
        fairway claims is nobody's to refuse: `owns` is a statement about what is divided, not about
        everything that exists.
        """
        if self.fairway is None:
            return None
        for fairway, patterns in sorted(self.owns.items()):
            if fairway == self.fairway or not owned_by(path, patterns):
                continue
            if owned_by(path, self.owns.get(self.fairway, [])):
                continue
            return (
                f"{path}: owned by fairway `{fairway}`, and this slice is in `{self.fairway}`. "
                f"Two fairways share nothing but marks; if `{fairway}` has to change, that is a mark "
                f"it sets and this slice steers by, not a file this slice edits."
            )
        return None

    def service_path(self, name: str) -> str | None:
        record = self.apps.get(name)
        path = record.get("path") if record else None
        return path.strip("/") if isinstance(path, str) else None

    def other_contexts(self) -> list[str]:
        if self.service is None or self.context is None:
            return []
        record = self.apps.get(self.service, {})
        contexts = record.get("contexts") if isinstance(record.get("contexts"), list) else []
        return [str(context) for context in contexts if str(context) != self.context]

    def owning_app(self, path: str) -> str | None:
        """The deployable a path sits under, by its recorded `path`, or None for a path outside every app."""
        for name in self.apps:
            app_path = self.service_path(name)
            if app_path and (path == app_path or path.startswith(app_path + "/")):
                return name
        return None

    def spec_violation(self, path: str) -> str | None:
        parts = path.split("/")
        if len(parts) < 3:
            return f"{path}: a slice writes under a feature directory, `specs/<feature>/`, never beside one."
        feature, rest = parts[1], parts[2:]
        if rest[0] in CANONICAL_SLOTS and len(rest) == 1:
            return (
                f"{path}: the canonical slot is a link into `specs/{feature}/slices/{self.slice_id}/`, where the "
                f"record lives, and is never committed. Move the file there, `ln -s slices/{self.slice_id}/{rest[0]} "
                f"specs/{feature}/{rest[0]}`, and leave the link unstaged."
            )
        if rest[0] == "slices":
            if len(rest) == 2 and rest[1] == "README.md":
                return None
            if len(rest) >= 2 and rest[1] == self.slice_id:
                return None
            other = rest[1] if len(rest) >= 2 else "?"
            return (
                f"{path}: slice `{other}`'s record. A slice writes `slices/{self.slice_id}/` only; if `{other}` "
                f"needs a change, that is a question for the host."
            )
        if rest[0] in FEATURE_SHARED or rest[0] in FEATURE_SHARED_DIRECTORIES:
            return None
        if rest[0] == "capabilities":
            return self.capability_violation(path, feature, rest[1] if len(rest) > 2 else "")
        if rest == ["chart.yaml"] and self.model is not None:
            # On the event profile `make chart` renders it from the model and `check-chart` holds it there, as
            # `check-drawio` holds the canvas: a slice that changed its own block has to re-render it to pass
            # `verify`, and can put nothing else in it. DS-03 was refused by one gate or the other whichever it
            # did. On the standard profile it is written by `/chart`, held to nothing, and stays the host's.
            return None
        return (
            f"{path}: not a slice's to write. A slice amends `spec.md`, `story-split.md`, `contracts/`, "
            f"`checklists/`, `people/`, its records under `decisions/` and `adversary-log/` with the two logs "
            f"`make decisions` renders from them, its capability's record under "
            f"`capabilities/` and its own `slices/{self.slice_id}/`."
        )

    def capability_violation(self, path: str, feature: str, capability: str) -> str | None:
        """A capability's record — `gates.md`, the demo log — is its own slices' to write, where it is read.

        The harbourmaster refuses the merge that makes a capability whole until `gates.md` says `Cleared:` on
        that slice's branch, and this refused the file to every slice: manda's S63, S50, S49, S92, S95 and
        four more each cleared their gates, could not commit the record, handed it back, and were refused
        until the mender had landed it on trunk — sixteen refusals, and S92 parked on its fourth.
        """
        held_feature, own = capability_of(self.slice_id)
        if own and capability == own and feature == held_feature:
            return None
        if own and capability == own:
            return (f"{path}: `{own}`'s record is read at `specs/{held_feature}/capabilities/{own}/`, the "
                    f"feature its slices are under. Write it there.")
        return (f"{path}: the record of a capability slice `{self.slice_id}` is not part of"
                f"{f' — its own is `{own}`' if own else ''}. A capability's `gates.md` and demo log are written "
                f"by that capability's slices.")

    def model_violations(self) -> list[str]:
        """Every other slice's block must read as it does on the base."""
        if self.model is None:
            return []
        base_text = git("show", f"{self.base}:{MODEL.as_posix()}")
        if base_text is None:
            return []
        base_slices, head_slices = slices_of(load_model(base_text)), slices_of(self.model)
        violations = []
        for slice_id, block in base_slices.items():
            if slice_id == self.slice_id:
                continue
            if slice_id not in head_slices:
                violations.append(
                    f"{MODEL}: slice `{slice_id}` is gone. A slice branch edits its own block of the model and "
                    f"removes nothing; removing a slice is the host's, on `main`."
                )
            elif head_slices[slice_id] != block and not code_moved(block, head_slices[slice_id]):
                violations.append(
                    f"{MODEL}: slice `{slice_id}`'s block changed on `{self.slice_id}`'s branch. The contract "
                    f"another slice builds against does not move under it: hand the change back to the host."
                )
        return violations

    def migration_violation(self, path: str, status: str) -> str | None:
        name = Path(path).name
        if status != "A":
            return (
                f"{path}: an existing migration was {'deleted' if status == 'D' else 'edited'}. A slice adds "
                f"migrations and never changes one that shipped — the release running against the database "
                f"already applied it. Add a new, timestamped migration instead."
            )
        if not STAMPED_MIGRATION.match(name):
            stamp = "202609151030"
            return (
                f"{path}: a new migration on a slice branch is timestamped — `{stamp}_{name.split('_', 1)[-1]}` "
                f"(`V{stamp}__…` under Flyway), `date -u +%Y%m%d%H%M` for the stamp — so two slices never mint "
                f"the same name. A number is what the sibling branch is also about to take."
            )
        return None

    def code_violation(self, path: str, status: str) -> str | None:
        app = self.owning_app(path)
        if app is None and Path(path).name in WORKSPACE_LOCKS:
            # Derived from the manifests, so nobody's to choose: the slice writes it with its own service's
            # manifest line, and the harbourmaster writes it again where two slices' locks meet (`lockfiles.py`).
            return None
        if app is None:
            return (
                f"{path}: outside every deployable and not a slice's to write — shared configuration, tooling and "
                f"docs are the host's. Land it on `main` before the fan-out, or hand it back as the question it is."
            )
        record = self.apps.get(app, {})
        if record.get("kind") == "service" and self.service is not None and app != self.service:
            return (
                f"{path}: service `{app}` is not slice `{self.slice_id}`'s (`service: {self.service}` in the model). "
                f"A slice's code lives in the service that owns it; a change another service needs is a slice of "
                f"its own."
            )
        parts = Path(path).parts
        for layer in LAYERS_BY_CONTEXT:
            if layer in parts:
                index = parts.index(layer)
                if index + 1 < len(parts) and parts[index + 1] in self.other_contexts():
                    return (
                        f"{path}: bounded context `{parts[index + 1]}` is not slice `{self.slice_id}`'s "
                        f"(`context: {self.context}`). One context per slice; a change there is another slice's."
                    )
        stem = Path(path).stem
        if "domain" in parts and stem.lower().endswith("events") and status != "A" and deletions(self.base, path):
            return self.events_violation(path)
        return None

    def events_violation(self, path: str) -> str | None:
        """The events module changed with lines taken away: a widening, or what it did that only trunk may do."""
        base_text = git("show", f"{self.base}:{path}")
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        if base_text is not None and text is not None:
            saw = events_violation(base_text, text, path)
            if saw is None:
                return None
        else:
            saw = "the module deleted" if text is None else "a change it could not read against the base"
        return (
            f"{path}: the events module may only grow on a slice branch, and this change reads as {saw}. Events "
            f"already written are read back through it, so a slice may add lines, members of an enum or a union of "
            f"literals, and optional fields — never remove, rename or retype what is there, or make a field "
            f"required. Add the new shape beside the old one; where none can be added, the change is trunk's, "
            f"landed on `main` as a commit of its own, and this slice merges trunk after it. Then "
            f"`python3 scripts/check-slice-scope.py` again."
        )

    def ledger_violation(self, path: str) -> str | None:
        """A slice branch carries its own dispatch ledger file and nothing else under `.slipwai/dispatch/`."""
        parts = path.split("/")
        if len(parts) == 4 and parts[3] == f"{self.slice_id}.jsonl":
            return None
        return (
            f"{path}: a dispatch ledger line that is not `{self.slice_id}`'s. A slice branch commits "
            f"`.slipwai/dispatch/<feature>/{self.slice_id}.jsonl` and no other; the rest are the host's."
        )

    def flags_violation(self, path: str, status: str) -> str | None:
        """The flags file grows by a declaration seeded `off`, and by nothing else, on a slice branch."""
        if status == "D" or deletions(self.base, path):
            return (
                f"{path}: a line was removed or changed. A slice declares its own flag here, seeded `off`, and "
                f"touches no other key; turning one on or striking one is the host's."
            )
        diff = git("diff", "--unified=0", self.base, "--", path) or ""
        added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
        wrong = [line for line in added
                 if line.strip() and not line.lstrip().startswith("#") and not FLAG_SEEDED_OFF.match(line)]
        if wrong:
            return (
                f"{path}: `{wrong[0].strip()}` is not a declaration seeded `off`. A flag a slice introduces is "
                f"seeded `off`, as `key = \"off\"`, in the same change as the code that reads it."
            )
        return None

    def careen_violation(self, path: str) -> str | None:
        """`fairways/` is every slice of a stream's, so no slice writes it — but a fairway's careen slice
        closes the careen's rows, and the careen is the one file of it that slice may change."""
        closes = self.slice_id[:-len(CAREEN)] if self.slice_id.endswith(CAREEN) else ""
        if closes and path == f"{FAIRWAYS}{closes}/careen.md":
            return None
        return (
            f"{path}: `fairways/` is shared by every slice of a stream, so it is the host's. A finding a stage "
            f"stows is a row in the capability's own record, `specs/<feature>/capabilities/<capability>/"
            f"stowed.md`, which the harbourmaster carries into `fairways/<fairway>/careen.md` when this slice "
            f"merges."
        )

    def violation(self, path: str, status: str) -> str | None:
        if path.startswith(FAIRWAYS):
            return self.careen_violation(path)
        if path == FLAGS:
            return self.flags_violation(path, status)
        if path.startswith(".slipwai/dispatch/"):
            return self.ledger_violation(path)
        if path.startswith("specs/"):
            return self.spec_violation(path)
        if path == MODEL.as_posix():
            return None
        if path == CANVAS.as_posix():
            # Rendered from the model, and `check-drawio` holds it to the model: a slice that advanced its own
            # block has to regenerate it to pass `verify`, and can put nothing else in it.
            return None
        if path.startswith(DOCS + "event-model/mockups/"):
            return None
        if path.startswith(ADRS) and path.endswith(".md"):
            if status == "A":
                return None
            return (
                f"{path}: an ADR that exists was {'deleted' if status == 'D' else 'edited'} on a slice branch. A "
                f"slice adds an ADR at `Proposed`; superseding or accepting one that stands is the host's, on `main`."
            )
        if path.startswith(DOCS):
            return f"{path}: the docs are the host's; a slice writes its record under `specs/` and the model."
        parent = Path(path).parent.name
        if parent in MIGRATION_DIRECTORIES and Path(path).suffix in MIGRATION_SUFFIXES and MIGRATION_NAME.match(
            Path(path).name
        ):
            return self.migration_violation(path, status)
        return self.code_violation(path, status)


def lost_records() -> list[str]:
    """A regular, untracked file at a canonical slot, on any branch: the Spec Kit command wrote through the link
    and something replaced it, and `.gitignore` would now hide the only copy of the record."""
    findings = []
    specs = ROOT / "specs"
    if not specs.is_dir():
        return findings
    tracked = set((git("ls-files", "specs") or "").splitlines())
    for feature in sorted(specs.iterdir()):
        for slot in CANONICAL_SLOTS:
            candidate = feature / slot
            relative = candidate.relative_to(ROOT).as_posix()
            if candidate.is_file() and not candidate.is_symlink() and relative not in tracked:
                findings.append(
                    f"{relative}: a regular file at the canonical slot, untracked and ignored — the record is "
                    f"about to be lost. Move it under `specs/{feature.name}/slices/<id>/` and link the slot to it."
                )
    return findings


class ChartUnreadable(Exception):
    """A chart is there and no parser is. The boundary is not held, and the gate says so rather than passing."""


def spanning(pattern: str) -> re.Pattern[str]:
    """A pattern holding `**` in the middle of it, as the expression that matches a path.

    `**` spans zero or more whole segments and `*` stays inside one, which is what every tool that reads a
    glob means by them. Zero is the case this exists for: `apps/orders/**/billing/**` has to match
    `apps/orders/billing/x.go` as well as `apps/orders/src/billing/x.ts`, because where a context's
    directory sits is the language's business and a chart is not written per language.
    """
    tail = ""
    if pattern.endswith("/**"):
        pattern, tail = pattern[:-3], "(?:/.*)?"
    parts = ["(?:[^/]+/)*" if part == "**" else re.escape(part).replace(r"\*", "[^/]*") + "/"
             for part in pattern.split("/")]
    body = "".join(parts).rstrip("/")
    return re.compile(f"^{body}{tail}$")


def owned_by(path: str, patterns: list[str]) -> bool:
    """Whether a path falls inside one of a fairway's `owns` entries.

    `apps/orders/**` is a prefix, which is what every chart writes for a service that holds one context and
    what a reader expects it to mean. A `**` anywhere else is read as segments: the renderer writes one for
    a service holding several, because the directory a context lives in sits at a different depth in every
    language. Anything else falls through to `fnmatch`, so a chart may name one file if it has reason to.
    """
    for pattern in patterns:
        if "**" in pattern.removesuffix("/**"):
            if spanning(pattern).match(path):
                return True
        elif pattern.endswith("/**"):
            root = pattern[:-3]
            if path == root or path.startswith(root + "/"):
                return True
        elif fnmatch.fnmatch(path, pattern):
            return True
    return False


#: Returned where a chart is there and cannot be parsed. Distinct from `None`, which means "no chart".
UNREADABLE = object()


def load_chart(text: str) -> object:
    """Parse a chart.

    Deliberately not `load_model`. That one borrows the event-model checker's parser so the two agree on
    how the model reads, and returns `None` where the checker is absent — which is every standard-profile
    project, and the standard profile is the one this boundary never held on. A chart reader that needed
    the event profile's checker would hold nothing exactly where there was nothing holding it before.
    """
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        checker = ROOT / DELIVERY / "scripts/event-model/check.py"
        if not checker.is_file():
            # Standard profile, no parser. The first version of this fell back to the event-model checker's
            # bundled one, which is excluded on exactly this profile — so the boundary silently held nothing
            # on the profile it was built for, while the gate still printed that the branch was fine.
            # Saying so is the only honest answer; a quiet pass reads identical to a held boundary.
            return UNREADABLE
        spec = importlib.util.spec_from_file_location("event_model_check", checker)
        if spec is None or spec.loader is None:
            return UNREADABLE
        module = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
        sys.path.insert(0, str(module.TOOLS))
        module.load_yaml()
        import yaml  # type: ignore[import-not-found]
    return yaml.safe_load(text)


def chart_fairways(slice_id: str) -> tuple[str | None, dict[str, list[str]]]:
    """This slice's fairway, and what every fairway owns, from the first chart that names the slice."""
    for chart_path in sorted((ROOT / SPECS).glob("*/chart.yaml")) if (ROOT / SPECS).is_dir() else []:
        chart = load_chart(chart_path.read_text(encoding="utf-8"))
        if chart is UNREADABLE:
            raise ChartUnreadable(chart_path.relative_to(ROOT).as_posix())
        if not isinstance(chart, dict):
            continue
        slices = chart.get("slices") if isinstance(chart.get("slices"), dict) else {}
        entry = slices.get(slice_id)
        if not isinstance(entry, dict):
            continue
        owns = {}
        for name, body in (chart.get("fairways") or {}).items():
            paths = body.get("owns") if isinstance(body, dict) else None
            owns[str(name)] = [str(pattern) for pattern in paths] if isinstance(paths, list) else []
        return (str(entry.get("fairway")) if entry.get("fairway") else None), owns
    return None, {}


def code_moved(was: dict, now: dict) -> bool:
    """Whether another slice's block changed only by its `code` list following files this branch moved:
    every path gone from the list is gone from the tree, and every path added to it is there.

    `check-model` wants every path a block's `code` names to exist. A slice that renames or deletes a file
    an earlier slice lists made trunk's model wrong the moment it merged, and could not correct the list: it
    is another slice's block. Nor could the fleet land the correction first, because the new file is not on
    trunk until the slice is. manda's S49 was finished and refused on exactly that until a person stepped in.
    """
    if {**was, "code": None} != {**now, "code": None}:
        return False
    before, after = (held.get("code") if isinstance(held.get("code"), list) else [] for held in (was, now))
    gone, came = [path for path in before if path not in after], [path for path in after if path not in before]
    return bool(gone) and not any((ROOT / str(path)).exists() for path in gone) \
        and all((ROOT / str(path)).is_file() for path in came)


def capability_of(slice_id: str) -> tuple[str, str]:
    """The feature this slice's capability keeps its record under, and the capability, from the first chart
    that names the slice; `("", "")` where none does or it cannot be read. The feature is the capability's
    first slice's — a row's own `feature:`, else the chart's — which is where `capabilities.py` reads it."""
    for chart_path in sorted((ROOT / SPECS).glob("*/chart.yaml")) if (ROOT / SPECS).is_dir() else []:
        chart = load_chart(chart_path.read_text(encoding="utf-8"))
        slices = chart.get("slices") if isinstance(chart, dict) else None
        entry = slices.get(slice_id) if isinstance(slices, dict) else None
        if not isinstance(entry, dict) or not entry.get("capability"):
            continue
        first = next(body for body in slices.values()
                     if isinstance(body, dict) and body.get("capability") == entry["capability"])
        return str(first.get("feature") or chart.get("feature") or chart_path.parent.name), str(entry["capability"])
    return "", ""


def product_mode() -> str:
    """How dark a merge is here, from `scripts/agents/release_state.py` — `flagged` where it cannot be read,
    which is how every project merged before the product's state was recorded."""
    module_path = ROOT / DELIVERY / "scripts/agents/release_state.py"
    if not module_path.is_file():
        return "flagged"
    spec = importlib.util.spec_from_file_location("release_state", module_path)
    if spec is None or spec.loader is None:
        return "flagged"
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return str(module.mode_of(module.read(ROOT)))


def keystones(slice_id: str) -> dict[str, tuple[str, list[str]]]:
    """Under keystone mode: each capability's entry point and the slice that may wire it — the capability's
    last slice in the chart, which is split order. Read from `specs/<feature>/keystones.yaml`, beside the
    chart that names this slice: `<capability>: [<glob>, …]`. Beside it rather than in it, because on the
    event profile the chart is rendered from the model and compared whole."""
    found: dict[str, tuple[str, list[str]]] = {}
    for chart_path in sorted((ROOT / SPECS).glob("*/chart.yaml")) if (ROOT / SPECS).is_dir() else []:
        listed = chart_path.parent / "keystones.yaml"
        if not listed.is_file():
            continue
        chart, entries = load_chart(chart_path.read_text(encoding="utf-8")), load_chart(listed.read_text(encoding="utf-8"))
        if not isinstance(chart, dict) or not isinstance(entries, dict):
            continue
        slices = chart.get("slices") if isinstance(chart.get("slices"), dict) else {}
        if slice_id not in slices:
            continue
        for capability, globs in entries.items():
            members = [name for name, body in slices.items()
                       if isinstance(body, dict) and body.get("capability") == capability]
            if members and isinstance(globs, list):
                found[str(capability)] = (str(members[-1]), [str(glob) for glob in globs])
    return found


def keystone_violation(slice_id: str, path: str, held: dict[str, tuple[str, list[str]]]) -> str | None:
    """A capability's entry point touched by a slice that is not the capability's last."""
    for capability, (last, globs) in sorted(held.items()):
        if slice_id != last and owned_by(path, globs):
            return (
                f"{path}: the entry point of capability `{capability}`. The product is in pilot, so a capability "
                f"lands dark by omission: its entry is wired by its last slice, `{last}`, and every slice before "
                f"it lands unreachable. Leave the entry out and demo this slice at the `http` or `cli` rung."
            )
    return None


def check(branch: str | None) -> tuple[list[str], str]:
    """The violations, and the one line to print when there are none."""
    violations = lost_records()
    match = SLICE_BRANCH.match(branch or "")
    if match is None:
        where = f"on `{branch}`" if branch else "on a detached checkout"
        return violations, f"check-slice-scope: {where}, not a `slice/<id>` branch — nothing to hold"
    slice_id = match.group("id")
    base = merge_base()
    if base is None:
        return violations, f"check-slice-scope: slice/{slice_id} has no `main` to compare with — nothing to hold"
    scope = Scope(slice_id, base)
    held = keystones(slice_id) if product_mode() == "keystone" else {}
    for path, status in sorted(changed_files(base).items()):
        found = (scope.violation(path, status) or scope.fairway_violation(path)
                 or keystone_violation(slice_id, path, held))
        if found:
            violations.append(found)
    if scope.unreadable is not None:
        violations.append(
            f"{scope.unreadable}: there is a chart and no YAML parser to read it, so the fairway boundary "
            f"is not held on this branch. Install PyYAML (`python3 -m pip install PyYAML`) and run again; "
            f"a pass with the chart unread would read exactly like a pass with it held."
        )
    violations.extend(scope.model_violations())
    return violations, f"check-slice-scope: slice/{slice_id} touches only what one slice may"


def main() -> int:
    violations, report = check(current_branch())
    if violations:
        print("check-slice-scope: a slice branch reaches outside what one slice may touch\n", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(file=sys.stderr)
        return 1
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
