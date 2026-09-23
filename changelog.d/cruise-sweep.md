MINOR

**Seven things `/drive` does, or a person configures, no longer drop out under `/cruise`.** A sweep of the
autopilot against the ladder it runs found each of these, and each is now held by a test or a gate. A Codex
iteration can write: `codex exec` is read-only by default, so its registry row now runs `--sandbox
workspace-write`. The ladder's concurrent slices can edit their worktrees: a Claude Code print session under
`acceptEdits` is refused every edit outside its working directory, and the worktrees sit beside the checkout,
so the row's new `worktreeFlags` pass `--add-dir` for the directory the checkout sits in on every iteration.
The runner no longer drives a CLI that is on PATH but was never initialised here — nothing is projected for
it, so `/cruise` was unknown to it, and a run spent its stuck budget on that before parking for the wrong
reason; the refusal names the `./init --integration <key>` that adds the CLI beside what is installed. The
`hand` setting reaches the hand: the delegation brief names the rung the ladder starts at, the delegate's own
brief says it never climbs above it, and `http` and `cli` mean what the settings table says. A fetch that
could not run — no remote, or one the environment cannot reach — is what the ladder says it is, said in the
evidence line, and the run goes on; the first stop row used to park there, which parked a local-only project
on its first iteration for good. What a demo leaves running is stopped: the command stops the app once the
hand's verdict is recorded, since no person is coming to open it, and the runner ends the iteration's process
group after the session exits and says so in the feed, so the next slice's demo finds its port free. And a
refusal inside an iteration — `enabled` turned off mid-run, a missing specification — ends on a last line the
runner reads, `cruise: stopped: human` or `cruise: parked: …`, rather than a plain sentence the runner counted
as no progress. Along the way the runner now reads `.specify/cruise.json` before every iteration, which is
what `/cruise-settings` always promised: a budget, the stuck window, the poll and `enabled` change at the next
iteration, and a file a hand edit broke keeps the last good settings and says so. And the driver's own model
is a setting: `.specify/cruise.json` gains `model` (`/cruise-settings model=opus`; `null`, the default, is the
harness's own), which the runner passes through the registry row's new `modelFlag` — `--model` on Claude Code,
Codex and Gemini CLI — on every iteration, saying before the first which model the iteration runs on or that
the row has no flag for it. Under `/drive` a person chose that model when they opened the session; under
`/cruise` nobody did, and every stage `.specify/models.json` maps to `host` ran on an unchosen default.

**Catch-up.** `slipwai migrate` brings the runner, the registry rows, the command text and the hand's brief;
`make agents` re-projects the delegate types. A project driven by Codex needs nothing else. A project whose
`/cruise` was reaching the ladder through a CLI it never initialised now needs `./init --integration <key>`
for that CLI, which the refusal names.
