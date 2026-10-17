MINOR

**A project opened in a different coding agent from the one `./init` chose now sets itself up there.** Before,
a project set up under Cursor and opened in Claude Code (or under any harness and opened in another) followed
none of its rules: Claude Code reads `CLAUDE.md`, which only existed where Claude had been installed, and the
commands, skills and delegate types are generated per harness and git ignores them. Now:

- every generated project commits `CLAUDE.md` with its `@AGENTS.md` include, whichever harness was chosen, and
  `make agents` keeps that include in step for every harness that reads one;
- `AGENTS.md` opens with one instruction: if `python3 scripts/agents/harness.py --can-delegate` says this
  harness is not set up, run `make agents` and start a new session;
- `make agents` adds the harness the session runs in where it is not installed, through `specify integration
  install <key>`, so Spec Kit's commands arrive with the project's own. Where Spec Kit will not install it
  beside the others, the line says so and leaves `--force` or `specify integration switch` to you. Either way
  the project's own material is projected into it. `make arrive` and `make preflight` do the same, but only
  where the harness is missing or unprojected. Which harness is running is read from its own session variable
  (Claude Code and Codex set one) and never guessed;
- `make agents` removes a projected command, skill or agent type whose canonical file has gone, but only files
  carrying its stamp. `check-agents` reports such a file as drift;
- `make agents` warns when the slipwai installed here is newer than the one that last wrote the project, and
  names `slipwai migrate`, which is what brings a newer ladder, command or agent type in;
- Cursor is recorded as reading `AGENTS.md` natively (its documentation, read 2026-10-17), so it no longer gets
  extension blocks copied into `.cursor/rules/specify-rules.mdc`.

**Catch-up:** `slipwai migrate`, then `make agents`. Migrate brings `CLAUDE.md`, the new `AGENTS.md` opening,
the projector and the `arrive`/`preflight` targets. Commit `CLAUDE.md`.
