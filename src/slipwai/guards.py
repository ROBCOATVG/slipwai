"""The second closed set: the moments an extension may *refuse* something, and the seven of them.

`hooks.py` is the first set, and its second rule is the reason this file exists: **a hook is never fatal to
the rung.** It is reported and the rung completes, because an extension that could fail a stage is an
extension that can stop a delivery loop it was added to help.

That rule left one thing unbuildable. `codegraph` wants to say *don't grep for that, ask the index* — which
is not a report after the fact, it is an answer to a tool call that has not happened yet. Version 1 reached
it through Claude Code's own `PreToolUse` hook, so it worked on one harness and silently did nothing on the
rest. Widening `hooks` to allow a refusal would have made every hook able to fail a rung, which is the
control plane the rule is there to prevent.

**So a guard is its own kind.** Three differences from a hook, and they are the whole design:

1. **A guard fires before a tool call, not around a rung.** What it can stop is that one call.
2. **A guard may refuse, by exiting 2.** The reason it printed goes back to the agent, which then does
   something else — usually the thing the guard suggested. Every other exit code is a hook's behaviour:
   reported, and the call goes ahead.
3. **The rung completes either way.** A refused tool call is not a failed stage. `hooks.py`'s rule is about
   rungs and it is untouched: no guard can end one.

The shape is the harnesses' own: Claude Code, Codex and Cursor all have a pre-tool event where a non-zero
exit blocks the call and the message reaches the model. This is the keel's name for that, so an extension
declares it once instead of once per harness.

**A guard is agreed to, not installed.** A hook runs where an extension is elected; a guard also refuses
things a person asked for, so election names the guards an extension declares and takes the person's word
once. An extension that declares a guard nobody agreed to fires none — `.slipwai/guards.json` is written
from the agreement, not from the manifest, and like `.slipwai/hooks.json` it is a controlled file.

**And once per quickstart, not once per project** (13.4). The agreement travels in the quickstart that
elected the extension, because a person who said yes when they wrote it has said yes; a project generated
from one is asked nothing it already carries. An extension that has *gained* a guard since is asked about
again, naming only the new point — which is why the agreement is recorded per guard rather than per
extension, here and in the project's own `guards.py`.

**Why there are seven and not three.** The set is closed, so widening it is a keel change, and a keel change
to add a point is the cost this file exists to avoid paying twice. The three it opened with were the three
`codegraph` needed. The four added on 2026-10-08 are the *shapes* the three leave out, and each was added
with something firing it rather than on the chance it would be wanted:

- `before-write` is a path about to be written. The captain's own control-file refusal lives here — a gate
  or a Makefile is not edited by an iteration — and it was a verb inside the runner before this, which is
  why it worked on one harness.
- `before-command` is a shell command about to run. It is the same refusal as `before-write` through the
  door `before-write` cannot see: `make verify` rewritten by a `sed` is rewritten all the same.
- `before-fetch` is a URL about to be read. Egress is its own shape — what a guard is handed is a host, not
  a path — and nothing else on this list can hold an opinion about it.
- `before-stop` is a session about to end. Refusing it carries the turn on, which is the cheap recovery for
  a delegate that stopped without finishing; the captain's gate is the dear one, and parks.

Three shapes are deliberately *not* here. There is no point around a rung — that is `hooks.py`, and a guard
there would make every extension able to end a stage. There is no point that can change what a tool call
does, only whether it happens: a guard that could rewrite the call would be a second author of the diff.
And there is no point after a write, because a refusal after the fact is a report, which is a hook.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Where the resolved registry is written. A controlled file, for the same reason the hook registry is: a
#: run that could register a guard on itself could also unregister one.
REGISTRY = ".slipwai/guards.json"
#: What an extension's manifest declares its guards under.
BLOCK = "guards"
#: How long one guard may take before it is ended, where its declaration does not say. Shorter than a
#: hook's: this one is in front of a tool call, and a tool call a person is waiting on cannot wait 30s.
DEFAULT_BUDGET = "5s"
#: The exit code that refuses the call. Every other code is a hook's behaviour — said, and the call goes on.
REFUSE = 2


@dataclass(frozen=True)
class Guard:
    """One moment a tool call may be refused, what the guard is handed, and what refusing it does."""

    name: str
    when: str
    given: tuple[str, ...]
    refusing: str


#: In the order a session meets them: `session` opens it, `before-stop` is the last thing it asks, and the
#: five between are the tool calls. `session` and `before-stop` are the two that are not about one call.
GUARDS: tuple[Guard, ...] = (
    Guard("session", "a delegate's session opens, before its first tool call",
          ("stage", "slice", "fairway", "berth"),
          "the session does not start, and the stage is dispatched again without this extension's guard"),
    Guard("before-search", "a delegate is about to search the tree — grep, find, a file read by glob",
          ("stage", "slice", "fairway", "query", "tool"),
          "that search does not run, and the agent is told what to ask instead"),
    Guard("before-write", "a delegate is about to write or edit a file",
          ("stage", "slice", "fairway", "path", "tool"),
          "that file is not written, and the agent is told why and writes something else"),
    Guard("before-command", "a delegate is about to run a shell command",
          ("stage", "slice", "fairway", "command", "tool"),
          "that command does not run, and the agent is told why"),
    Guard("before-fetch", "a delegate is about to read a URL",
          ("stage", "slice", "fairway", "url", "host", "tool"),
          "that fetch does not happen, and the agent is told where to look instead"),
    Guard("after-delegate", "a delegate has answered, before its answer is used",
          ("stage", "slice", "fairway", "tool"),
          "the answer is not used, and the agent is told why and asked again"),
    Guard("before-stop", "a delegate's session is about to end",
          ("stage", "slice", "fairway", "berth"),
          "the session does not end: the reason goes back as the next turn, and the delegate carries on"),
)
NAMES = tuple(guard.name for guard in GUARDS)


def guard(name: str) -> Guard:
    """One guard by name, or a refusal listing the set.

    Refused rather than ignored, exactly as a hook point is: an extension that declared a guard the keel has
    not got would be installed, valid, and silently never run — the failure that is hardest to notice.
    """
    for declared_guard in GUARDS:
        if declared_guard.name == name:
            return declared_guard
    raise KeyError(f"`{name}` is not a guard the keel fires. There are {len(GUARDS)}, in firing order: "
                   f"{', '.join(NAMES)}. A guard may refuse a tool call; a hook never can, and the two sets "
                   f"are separate for that reason")


def declared(manifest: dict) -> dict[str, dict]:
    """An extension's guards, normalised. The short and the long form read the same, as a hook's do."""
    block = manifest.get(BLOCK)
    if not isinstance(block, dict):
        return {}
    found: dict[str, dict] = {}
    for name, body in block.items():
        guard(name)
        if isinstance(body, str):
            found[name] = {"run": body, "budget": DEFAULT_BUDGET}
        elif isinstance(body, dict) and body.get("run"):
            found[name] = {"budget": DEFAULT_BUDGET, **body}
        else:
            raise ValueError(f"the `{name}` guard names no script to run. A guard is a path, or an object "
                             f"with `run` and optionally `stages` and `budget`")
    return found


def registry(manifests: dict[str, dict], agreed: set[str] | None = None) -> dict:
    """`.slipwai/guards.json`: every *agreed* extension's guards, by guard, in firing order.

    `agreed` is the set of extension keys a person has said yes to; None means none have been asked, which
    writes an empty registry rather than every manifest's guards. An extension is elected by installing it
    and agreed to by answering a question, and those are deliberately two things.
    """
    allowed = set() if agreed is None else agreed
    by_guard: dict[str, list[dict]] = {name: [] for name in NAMES}
    for extension in sorted(manifests):
        if extension not in allowed:
            continue
        for name, body in sorted(declared(manifests[extension]).items()):
            by_guard[name].append({"extension": extension, **body})
    return {"v": 1, "guards": {name: by_guard[name] for name in NAMES if by_guard[name]}}
