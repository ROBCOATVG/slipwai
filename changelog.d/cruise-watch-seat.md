MINOR

**The session that types `/cruise` now watches the run, and a run can no longer park on its first command.**
`/cruise` used to start the runner and end its turn, so a run that parked thirty seconds in — as every run in a
TypeScript or Go project did, because the generated `.claude/settings.json` allowed no `python3` and the headless
iteration under `acceptEdits` cannot ask — was found only by someone typing `make cruise-status`. Three things
change. `python3 scripts/agents/cruise.py watch` is the watch seat: it prints the feed from where the last watch
left off and returns at the iteration's end, a park, the run's end, once the feed has gone quiet for twenty
seconds, or after a minute and a half with nothing new, saying which — on quiet, because a harness shows a
command's output when it returns, and the feed has to reach a person as it happens; the command runs it after `start`, again while the run continues, and ends the turn when
it says parked or ended, and a person typing into that session is answered — the feed, the settings, the status,
the decision log, a setting changed through `/cruise-settings` — and then watched for again; every line `watch`
printed goes into the reply unchanged, because a harness folds a command's output and the feed has to reach the
person. `make cruise-watch` is the same seat from a terminal, and two commands sit beside it in every session:
`/cruise-status` (the runner's state and the feed's tail) and `/cruise-stop` (after the iteration in flight, or
`now`). The feed is the harness's own event stream rendered one line per command, file,
and delegate out and back: the registry's `headless` row for Claude Code now runs `--output-format stream-json
--verbose` and Codex's `exec --json`, each row saying so with its `stream`, the runner keeps the raw stream in
`.specify/cruise-stream.jsonl` beside the log, and a refused permission is in the feed the moment it happens.
And an iteration is no longer refused its own commands: Claude Code's headless row runs with `--allowedTools
Bash`, the shell allowed wholesale because no list names the compound commands an agent writes, while the
project's new `deny` rules — a plain force-push, `reset --hard`, `clean` — still refuse what they name; the
allowlist every project's `.claude/settings.json` carries now includes the toolkit's own scripts
(`python3 scripts/*`) and the Git a slice is made of, whatever the language, so a person's own session stops
prompting at every hook and gate, and a test holds it to every command `commands/cruise.md` and the hooks
issue. Which tools a whole build needs is measured rather than guessed: `python3 scripts/agents/cruise.py
denials` lists every refusal in the raw stream by tool and command with the iterations it happened in, and
`status` says when there are any. What is typed
after `/cruise` is the kick-off — what the run is for, where the PRD is — and reaches the first iteration only;
every later one runs bare and derives from disk, so the first iteration writes down what must outlive it. Every
setting keeps its meaning.

**Catch-up.** `slipwai migrate` brings the runner, the command text, the Make target, the registry rows and the
allowlist; `make agents` re-projects the hook files. The raw stream and the watch cursor are gitignored.
