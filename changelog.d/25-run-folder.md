MINOR

**Everything a run writes about itself now lives in one folder, `.slipwai/run/`, and the ignore file has one
line for it.** Deck and harbour logs, `running/` and its pid files, berth records, the ACP, console and stage
sessions, `activity/`, `try-it/`, `walks/`, the catch-up page and its archive, `run-state.json`,
`harbourmaster.json`, `preflight.json` and the merge and mend scratch worktrees all moved there. Before this,
the run's files were ignored one name at a time, and the list kept falling behind: `.slipwai/acp/`,
`console/`, `stages/` and two pid files were never ignored, so `check-slice-scope` failed every slice's berth
on files no slice wrote. What stays at `.slipwai/` is committed: `dispatch/`, `extensions.json`,
`hooks.json`, `guards.json`, `quickstart.json`, `packages/`, `migration.json` and `shape-transitions/`.

**A project that has not migrated keeps working.** The board and the toolkit read the layout from
`.gitignore`. Until the line `.slipwai/run/` is there, they read and write the old places. Log refs keep the
old path spelling, so a machine not migrated yet still receives every line from one that is.

**Catch-up:** stop the fleet first (`python3 scripts/agents/fleet.py stop`), then run `slipwai migrate`.
It moves the run's state from `.slipwai/<name>` into `.slipwai/run/<name>` and rewrites the ignore lines,
including an adopted repository's marked block. It refuses while any process under `running/` is still
alive. Running it a second time changes nothing. Restart the fleet afterwards.
