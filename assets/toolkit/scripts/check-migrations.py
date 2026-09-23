#!/usr/bin/env python3
"""Hold schema changes to expand/contract, whatever language wrote them.

A deploy rolls: for a minute or so the release before and the release after run against one database, and
a rollback is the release before, on its own, against whatever schema the release after left. So a
migration that removes or reshapes something the running release still uses — drops a table or column,
renames, changes a type, makes a column NOT NULL, adds a NOT NULL column with no default — breaks one of
them. The constitution's rule is expand, then contract, in separate deployments. This is the gate on it:

- A migration with a *contracting* statement must say which earlier, additive migration it completes, in a
  comment line: `-- contract: 202609151030_orders_add_status` (`//` or `#` in a JavaScript or Python migration).
- That migration must exist beside it, sort before it, and must not be new in the same change: where git
  history is available, "new" is anything not yet in the base branch (`main`), or uncommitted when on it.

Comments are stripped before anything is matched, and only the `up` half of a JavaScript migration is read.
Every migration file under every `apps/*/` and `packages/*/` is checked: `migrations/<n>_*.{sql,js,ts}` where
`<n>` is the shipped ones' zero-padded number or a new one's `YYYYMMDDHHMM` stamp, Flyway's
`db/migration/V<n>__*.sql`. Nothing else in this repository is a migration.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def project_root(script: Path, depth: int) -> Path:
    """The repository root: the nearest directory above this script holding `project.json`.

    This script's own tree is `<root>/scripts` in a generated project and `<root>/<layout.delivery>/scripts`
    where the method was installed beside an existing codebase (`project.json`'s `layout.delivery`), so how
    far below the root it sits is not something to count; `depth` is only the fallback for a tree with no
    manifest at all.
    """
    for candidate in script.parents:
        if (candidate / "project.json").is_file():
            return candidate
    return script.parents[depth]


ROOT = project_root(Path(__file__).resolve(), 1)
MIGRATION_DIRECTORIES = ("migrations", "migration")
MIGRATION_NAME = re.compile(r"^(?:\d+_|V\d+__)")
SUFFIXES = {".sql", ".js", ".ts", ".py"}
COMMENTS = re.compile(r"--[^\n]*|//[^\n]*|#[^\n]*|/\*.*?\*/", re.DOTALL)
DOWN = re.compile(r"\b(?:export\s+(?:const|async\s+function|function)\s+down|exports\.down)\b")
CONTRACT = re.compile(r"^\s*(?:--|//|#)\s*contract:\s*(\S+)\s*$", re.MULTILINE)

# Each is a statement the release still running cannot survive, with what to say about it.
CONTRACTING = (
    (re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE), "drops a table"),
    (re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE), "drops a column"),
    (re.compile(r"\bRENAME\s+(?:COLUMN\b|TO\b)", re.IGNORECASE), "renames what the running release addresses by name"),
    (re.compile(r"\bALTER\s+COLUMN\b[^;]*?\bTYPE\b", re.IGNORECASE), "changes a column's type"),
    (re.compile(r"\bSET\s+NOT\s+NULL\b", re.IGNORECASE), "makes a column NOT NULL under a release that may not set it"),
    (re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?(?!ON\b)\w+", re.IGNORECASE), "truncates a table"),
    (re.compile(r"\bpgm\.(?:dropTable|dropColumns?|renameTable|renameColumn)\b"), "drops or renames"),
    (re.compile(r"\bpgm\.alterColumn\b[^;]*?\b(?:type|notNull)\s*:"), "reshapes a column"),
)
# A new NOT NULL column with no default fails every INSERT the running release still makes.
ADDED_COLUMN = re.compile(r"\bADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?\w+[^,;]*", re.IGNORECASE)
NOT_NULL = re.compile(r"\bNOT\s+NULL\b", re.IGNORECASE)
DEFAULT = re.compile(r"\bDEFAULT\b", re.IGNORECASE)


def migrations() -> list[Path]:
    found = []
    for area in ("apps", "packages"):
        for path in sorted((ROOT / area).rglob("*")):
            if (
                path.is_file()
                and path.suffix in SUFFIXES
                and MIGRATION_NAME.match(path.name)
                and path.parent.name in MIGRATION_DIRECTORIES
                and "node_modules" not in path.parts
            ):
                found.append(path)
    return found


def statements(path: Path) -> str:
    """The text that runs when the migration is applied: comments out, and a JavaScript `down` cut off."""
    text = path.read_text(errors="ignore")
    if path.suffix in {".js", ".ts"}:
        down = DOWN.search(text)
        if down:
            text = text[: down.start()]
    return COMMENTS.sub(" ", text)


def contractions(text: str) -> list[str]:
    found = [reason for pattern, reason in CONTRACTING if pattern.search(text)]
    for clause in ADDED_COLUMN.finditer(text):
        if NOT_NULL.search(clause.group(0)) and not DEFAULT.search(clause.group(0)):
            found.append("adds a NOT NULL column with no default, which fails every INSERT the running release makes")
            break
    return found


def git(*arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout


def new_in_this_change() -> set[str] | None:
    """Paths (relative to the root) not yet in the base branch, or None where there is no history to ask.

    On a branch: everything added since it left `main`, plus whatever is uncommitted. On `main` itself, or
    without a `main` to compare with: only what is uncommitted. A shallow CI checkout has no base to
    compare with either, and is treated the same — the check then holds on the developer's machine and on
    a full clone, and says nothing false on a shallow one.
    """
    if git("rev-parse", "--is-inside-work-tree") is None:
        return None
    changed = git("status", "--porcelain", "--untracked-files=all") or ""
    new = {line[3:] for line in changed.splitlines() if line[:2].strip() in {"A", "??", "AM", "?"}}
    base = merge_base()
    if base is not None:
        added = git("diff", "--name-only", "--diff-filter=A", base, "HEAD") or ""
        new.update(added.splitlines())
    return new


def merge_base() -> str | None:
    """Where the branch left `main`, or last merged it in: the newest base among every `main` the checkout has
    — `origin/main` alone is stale where `main` moved locally and was not pushed, and would count `main`'s own
    migrations as new in this change. On `main` itself the base is `HEAD`, and nothing committed counts."""
    bases: list[str] = []
    for name in ("main", "origin/main", "master", "origin/master"):
        found = git("merge-base", "HEAD", name)
        if found and found.strip() not in bases:
            bases.append(found.strip())
    if not bases:
        return None
    newest = bases[0]
    for candidate in bases[1:]:
        if git("merge-base", "--is-ancestor", newest, candidate) is not None:
            newest = candidate
    return newest


def go_migrate_embeds() -> list[str]:
    """Go's migrate image is built by ko and carries only the binary.

    Without `migrations/embed.go` (`//go:embed *.sql`), cmd/migrate's filesystem glob matches
    nothing inside the container, exits 0, and a freshly created database stays empty behind a
    green deploy. Expand/contract checks on the repo files say nothing about whether they ship.
    """
    violations: list[str] = []
    apps = ROOT / "apps"
    if not apps.is_dir():
        return violations
    for app in sorted(apps.iterdir()):
        migrations_dir = app / "migrations"
        if not migrations_dir.is_dir():
            continue
        if not any(migrations_dir.glob("*.sql")):
            continue
        if not (app / "cmd" / "migrate").is_dir():
            continue
        if not (migrations_dir / "embed.go").is_file():
            relative = migrations_dir.relative_to(ROOT).as_posix()
            violations.append(
                f"{relative}: has .sql files and cmd/migrate but no embed.go. "
                "ko ships only the compiled binary, so without //go:embed the migrate image "
                "applies nothing and still exits 0."
            )
    return violations


def check() -> list[str]:
    violations: list[str] = []
    new = new_in_this_change()
    for path in migrations():
        relative = path.relative_to(ROOT).as_posix()
        text = statements(path)
        found = contractions(text)
        marker = CONTRACT.search(path.read_text(errors="ignore"))
        if not found:
            continue
        what = "; ".join(found)
        if marker is None:
            violations.append(
                f"{relative}: {what}. A contracting migration names the additive one it completes — "
                f"`contract: <migration>` in a comment line — and ships in a later change than it."
            )
            continue
        name = Path(marker.group(1)).stem
        expand = next((p for p in path.parent.iterdir() if p.stem == name and p != path), None)
        if expand is None:
            violations.append(f"{relative}: {what}, and names `{name}`, which is not a migration beside it.")
        elif expand.name >= path.name:
            violations.append(f"{relative}: {what}, and names `{name}`, which does not come before it.")
        elif new is not None and expand.relative_to(ROOT).as_posix() in new:
            violations.append(
                f"{relative}: {what}, and `{name}` is new in this same change. Expand and contract ship in "
                f"separate deployments: land `{name}` first, then this one."
            )
    violations.extend(go_migrate_embeds())
    return violations


def main() -> int:
    violations = check()
    if violations:
        print("check-migrations: a schema change does not follow expand/contract\n", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(file=sys.stderr)
        return 1
    print(
        "check-migrations: every migration is additive, or a marked contraction of an earlier one; "
        "Go migrate images embed their .sql files"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
