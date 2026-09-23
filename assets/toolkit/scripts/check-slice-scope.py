#!/usr/bin/env python3
"""Hold a slice branch to the files one slice may touch — the shared-surface rule, held mechanically.

Once the event contract is settled, ready slices run concurrently: one delegate per slice, each on a
`slice/<id>` branch in its own worktree, merged back in split order (`commands/drive.md`, *Running ready
slices concurrently*). That works only because the files two slices could fight over are few and named.
This is the list, and the gate on it. On a branch that is not `slice/<id>` there is nothing to hold, and the
script says so and exits 0 — which is why `make verify` runs it everywhere.

What a slice's change may contain — everything since the branch left `main`, committed or not:

- **its own record**, `specs/<feature>/slices/<id>/**`, and the feature's cumulative artifacts — `spec.md`,
  `story-split.md`, `contracts/`, `checklists/`, `adversary-log.md`, `decisions.md`, `slices/README.md` — which
  every slice amends and the host merges in split order. `decisions.md` is among them because `/cruise` writes
  a decision where the ladder took it, which during a slice's stages is the slice's branch, and `check-decisions`
  wants every `Written to` path in the tree, which for a slice's artifacts is only true there;
- **its own block of `docs/event-model/model.yaml`**: every other slice's block reads exactly as on `main`.
  Events, commands and read models are frames inside a slice's block, so the contract another slice builds
  against cannot move underneath it; `docs/event-model/mockups/` is per screen and open;
- **the committed canvas, `docs/event-model/model.drawio`**, because it is rendered from the model the slice
  just changed and `check-drawio` fails the branch until it is: that gate holds it to `model.yaml`, so it can
  carry nothing of the slice's own. The host regenerates it again after each merge;
- **a new ADR under `docs/adr/`**: a decision taken during the slice whose reversal would be a migration is
  written there at `Proposed`, by `/cruise` or by the slice's own planning. New files only — an ADR that exists
  is never edited; superseding one is the host's, on `main`;
- **code and tests of the service that owns it** — `service` in its model block, or any service where the
  model names none — and, where the block names a `context`, nothing under another context's directory in
  `domain/` or `application/`. A browser app is open to every slice: a white box is one screen;
- **the context's events module additively**: a line may be added, none removed. It is the contract;
- **new migration files only**, timestamped so two slices never mint the same name: `YYYYMMDDHHMM_<name>`,
  or `V<YYYYMMDDHHMM>__<name>` under Flyway. The shipped numbered ones keep working — the order is lexical
  either way, and every stamp sorts after every number;
- **the composition root** — one line per use case, the one code file every slice touches, resolved in
  split order at merge and allowed here for that reason.

Refused, each with what to do instead: the canonical slot at the feature root (`specs/<feature>/plan.md`,
`research.md`, `data-model.md`, `quickstart.md`, `tasks.md` — links into `slices/<id>/`, never committed;
a regular file there is a record about to be lost, on every branch), another slice's directory or model
block, another context's code, an edited or deleted migration, a numbered new migration, and anything else
in the repository — `Makefile`, `project.json`, package manifests and locks, `scripts/`, `skills/`,
`commands/`, `agents/`, CI, the docs other than the model and its canvas — which is the host's: landed on `main`
before the fan-out, or handed back as the question it is. A refusal is a hand-back, not something to work around.

The base the branch is compared with is where it left `main`, or last merged it in. Every `main` the checkout
knows is tried — `main`, `origin/main`, their `master` spellings — and the newest base wins: `origin/main` alone
goes stale the moment `main` moves locally and is not yet pushed (a migration run there, then merged into the
slice), and a stale base charges the slice with `main`'s own files.
"""

from __future__ import annotations

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
CANONICAL_SLOTS = ("plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md")
FEATURE_SHARED = ("spec.md", "story-split.md", "adversary-log.md", "decisions.md")
FEATURE_SHARED_DIRECTORIES = ("contracts", "checklists")
MIGRATION_DIRECTORIES = ("migrations", "migration")
MIGRATION_NAME = re.compile(r"^(?:\d+_|V\d+__)")
MIGRATION_SUFFIXES = {".sql", ".js", ".ts", ".py"}
STAMPED_MIGRATION = re.compile(r"^(?:\d{12}_|V\d{12}__)")
LAYERS_BY_CONTEXT = ("domain", "application")


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
        if path:
            changes[path] = "A"
    return changes


def deletions(base: str, path: str) -> int:
    numstat = git("diff", "--numstat", base, "--", path) or ""
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    return 0


def deployables() -> dict[str, dict]:
    try:
        document = json.loads((ROOT / "project.json").read_text())
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
        model_text = (ROOT / MODEL).read_text() if (ROOT / MODEL).is_file() else None
        self.model = load_model(model_text) if model_text is not None else None
        own = slices_of(self.model).get(slice_id, {})
        self.service = own.get("service") if isinstance(own.get("service"), str) else None
        self.context = own.get("context") if isinstance(own.get("context"), str) else None

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
        return (
            f"{path}: not a slice's to write. A slice amends `spec.md`, `story-split.md`, `contracts/`, "
            f"`checklists/`, `adversary-log.md`, `decisions.md` and its own `slices/{self.slice_id}/`."
        )

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
            elif head_slices[slice_id] != block:
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
            return (
                f"{path}: the events module is the contract and grows additively — a line was removed. Add the new "
                f"shape beside the old; retiring one is the host's, once nothing folds it."
            )
        return None

    def violation(self, path: str, status: str) -> str | None:
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
    for path, status in sorted(changed_files(base).items()):
        found = scope.violation(path, status)
        if found:
            violations.append(found)
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
