"""The catch-up page's section for a local trunk holding commits the forge's trunk has not got.

A stage once committed onto local `main` in the person's checkout and pushed nothing — the board's triage,
twice, while a fleet ran. Every merge after that went to the forge's `main`, which the harbourmaster could
not bring local `main` up to without discarding those two commits, so it did not; the checkout fell 1168
commits behind in a night, and the board drew the old project. The board names such commits now
(`checkout_level`, `trunk_card`); a migration names them too, because a migration is when a person is
looking at what this checkout holds.

Read before the merge, so the migration's own commit is never counted among them. Nothing here resets,
rebases, pushes or drops anything: it says which commits, and the safe way to land them.
"""
from __future__ import annotations

from pathlib import Path

from .checkout_level import level


def unpushed(root: Path) -> tuple[str, list[str]]:
    """(trunk's name, each `<short id> <subject>` local trunk holds and `origin/<trunk>` does not)."""
    try:
        found = level(root)
    except Exception:  # noqa: BLE001 — a reading the page can go without is never a failed migration
        return "", []
    return str(found.get("trunk") or ""), [str(one) for one in found.get("stranded") or []]


def section(name: str, commits: list[str]) -> list[str]:
    """The lines the catch-up page carries for them; none where local trunk is on the forge."""
    if not commits:
        return []
    listed = [f"- `{one.split(' ', 1)[0]}` {one.split(' ', 1)[1] if ' ' in one else ''}".rstrip()
              for one in commits[:20]]
    more = [f"- and {len(commits) - 20} more: `git log origin/{name}..{name}`"] if len(commits) > 20 else []
    return ["", f"## Local {name} has commits the forge's {name} has not got", "",
            f"Before this migration, local `{name}` held {len(commits)} commit(s) that are not on `origin/{name}`. "
            f"While they are only here, the harbourmaster cannot bring this checkout level with the forge "
            f"after a merge, and the board — which draws from this folder — shows an older project. This "
            f"migration did not move them, and nothing here resets, rebases or drops them:", "",
            *listed, *more, "",
            "Land them, then bring this checkout level:", "",
            f"1. `git branch keep-local {name}` and `git push origin keep-local`, and open a pull request "
            f"from `keep-local` into `{name}`.",
            f"2. Once it has merged, `git switch -C {name} origin/{name}` here. Not before: until the pull "
            f"request is in, these commits are only on `keep-local`, and that switch is what leaves them "
            f"behind."]
