PATCH

**A merge no longer fails on an extension that installs a skill.** The harbourmaster runs the gate in a
scratch worktree and links into it what Git ignores under `tools/`. An extension that is a skill, such as
unslop or UI/UX Pro Max, installs under `skills/`, which was not linked, so `check-extensions` failed at
every merge while passing in the slice's own berth, and no slice of a project with one elected could reach
trunk. Both folders are linked now.

**Catch-up:** `slipwai upgrade` carries the new `scripts/agents/harbourmaster.py` into the project. Stop
the fleet and cast off again so the harbourmaster starts from it.
