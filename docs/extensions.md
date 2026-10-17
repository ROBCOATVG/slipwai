# Contract — an extension package

An **extension** is an optional development tool that a project elects at `./init`. An extension never
changes generated code. So it is not a product-architecture choice, and `slipwai generate` does not ask
about it.

The life of an extension has three steps:

1. You install it into the package directory, beside the languages.
2. `./init`'s menu then offers it in every project that is generated after that.
3. You elect it in that menu, or later with `./init --extension <key>`.

This page is the whole contract. It says what the manifest declares, what the entry point must do, where
the files land, and what the keel refuses. Two files hold this page to the code:

- `src/slipwai/extension_shape.py` holds the manifest half.
- `tests/test_extension_package.py` holds the loader and installer half.

If this page and the code disagree, the gate is red.

## Where it lives

| Thing | Module | Tier (`scripts/check-structure.py`) |
|---|---|---|
| What a manifest declares, and the six obligations | `src/slipwai/extension_shape.py` | contract |
| Reading a package from disk | `src/slipwai/extension_directory.py` | contract |
| Adding a package to the catalogue | `src/slipwai/extensions.py` | contract |
| The points that a hook can attach to | `src/slipwai/hooks.py` | contract |
| Installing and removing a package | `src/slipwai/extension_install.py` | edge |
| Writing a new package | `src/slipwai/package_new.py`, `slipwai package new` | edge |
| Firing a point inside a project | `assets/toolkit/scripts/extensions/hooks.py` | the toolkit's, not the keel's |

The last row shows a rule that slipwai has learned twice: **anything that a generated project runs is a
toolkit script.** A generated project has no slipwai to import. The keel decides what an extension *is*.
The toolkit runs it.

## The manifest

The manifest is `extension.json`, at the root of the package directory.

| Field | Required | What it is |
|---|---|---|
| `key` | yes | What a person types, as in `./init --extension <key>`. It is also the name of the installed directory. A lower-case slug. |
| `name` | yes | What `./init`'s menu shows. Use the product's own name. "UI/UX Pro Max" is correct here, and nowhere else. |
| `description` | yes | One sentence that the menu shows under the name. For most people, this is the only thing they will read about the extension. |
| `kind` | yes | `extension`. The loader tells this file and `language.json` apart by the file name. This field lets the loader refuse a manifest in the wrong file, with the correct advice. |
| `core` | yes | The keel schema range that the extension is built for, for example `>=9.0,<10`. Outside that range, the refusal names the command that updates whichever of the two is older. |
| `ignore` | no | gitignore text for any local state that the extension leaves. |
| `publisher` | no | Who published the extension. The chandlery's index shows this. |
| `tags` | no | The words that `slipwai search` matches. |
| `hooks` | no | The points that the extension attaches to. See [The hook points](#the-hook-points). |
| `guards` | no | What the extension can refuse, and with what message. See [The guards](#the-guards). |
| `tools` | no | The tool names that a headless session must be allowed to call to reach the extension. See [The tools](#the-tools). |

`key` and `name` are separate fields because they are different things. In a language's manifest, one
name is both. This is the only way that an extension's manifest differs from a language's. The catalogue
entry that a project receives carries `name`, `description` and `ignore`. The other fields are for the
keel only.

## The six obligations

Each obligation exists because somebody had that failure.

- `slipwai extension check <dir>` prints the six obligations.
- `python -m slipwai.conformance --extension <dir>` tests them. It builds a temporary project, runs the
  tests against it, and then deletes it.

The suite tests the obligations in three ways:

- `idempotent`, `non-fatal`, `projects` and `merges` are facts about what the entry point did. So the
  suite runs the entry point twice, and then once more with nothing on `PATH`.
- `gated` is a fact about what the package ships.
- `recovers` is tested against what the entry point printed. If a line reports a problem and names no
  command, that is the failure the obligation exists to stop.

If the suite cannot reach a check, it reports `not run`, with the reason. It does not pass that check
silently.

1. **Idempotent.** Running `./init --extension <key>` twice has the same result as running it once.
   Otherwise the question "did it work?" becomes "how many times has it run?".
2. **Non-fatal.** If a development tool is not on this machine, that is not a reason for the project
   setup to fail. The extension says what is missing, and the project still works.
3. **Projects.** The extension's `AGENTS.md` block sits between markers. So the next projection replaces
   exactly that block, and keeps what a person wrote around it.
4. **Gated.** If an extension writes an index, a cache or a lock, it ships a `check-<key>.py`. If nothing
   checks old state, nobody trusts it, and everybody rebuilds it.
5. **Recovers.** Every failure path names the command that fixes it. A message that says what is wrong,
   but not what to do, costs the reader a search.
6. **Merges.** If a person edited a file by hand, the extension merges into that file. It never
   overwrites it. Otherwise an install for an unrelated reason loses the edit, and people start to avoid
   running the tool.

## The hook points

A hook attaches to an existing point. A hook cannot create a new point. The set of points is closed, like
the axes. Each point is a promise by the keel about when something runs and what it receives. If an
extension could add a point, that would be a promise that nobody made. `slipwai hooks` prints the set,
with what is attached to each point.

| Point | Fires | Given |
|---|---|---|
| `init` | `./init --extension <key>`, once per election | `root` |
| `project` | every re-projection: `make agents`, `migrate`, `./init --integration` | `root`, `harnesses` |
| `check` | `make check-extensions`, as one more gate | `root` |
| `before-stage` | before each rung of the ladder | `stage`, `slice`, `fairway`, `berth` |
| `after-stage` | after each rung of the ladder | `stage`, `slice`, `fairway`, `berth` |
| `boundary` | every captain boundary, after the captain reads the inbox | `slice`, `fairway`, `lines` |
| `before-merge` | on the rebased branch, before the full gate | `slice`, `fairway`, `diff` |
| `after-merge` | after the slice is on trunk and pushed | `slice`, `fairway`, `commit` |
| `before-compact` | just before a delegate's context is compacted | `stage`, `slice`, `fairway` |
| `after-compact` | after a delegate's session resumes from a compacted context | `stage`, `slice`, `fairway` |

You can declare a hook in a short form, `"hooks": {"init": "init.py"}`, or in a long form with `run`,
`stages` and `budget`:

```json
{
  "hooks": {
    "after-stage": {"run": "hooks/sync.py", "stages": ["implement", "converge"], "budget": "30s"}
  }
}
```

The hook receives the given values as environment variables: `SLIPWAI_STAGE`, `SLIPWAI_SLICE` and so on.
`SLIPWAI_POINT` names the point itself.

**`init` and `project` have a default declaration, and the default is the entry point.** If a manifest
names neither point, the extension is attached to both, and `init.py` fires at each. Every extension
installs something, and every extension tells the agent that it is there. So these two points cost no
manifest line. If you name another script at either point, that script fires instead.

One script can answer both points by reading `SLIPWAI_POINT`:

- At `init`, the script installs and projects.
- At `project`, the script projects and installs nothing. A re-projection happens on every `make agents`,
  and it is not an election.

Until slice 6.1e, this was only a *convention*. `./init` ran a file called `init.py`. `make agents`
imported that file and called a function called `project_guidance()`. So if an extension declared a
different script at either point, slipwai read the declaration, ignored it, and never ran the script. Now
the registry is the only way that a hook fires.

Three rules stop a hook from becoming a second control plane:

- **The captain depends on no hook.** The captain's controls all work with every hook removed: the last
  line, the controlled-files diff, the bounded waits and the inbox receipt. A hook is extra protection
  only.
- **A hook never fails the rung.** Slipwai reports a hook's result as a `hook` line. The line names the
  extension, the point and the last thing that the hook printed. The rung then completes. If an extension
  could fail a stage, it could stop the delivery loop that it was added to help. The one exception is the
  `check` point, and `make check-extensions` is its only caller. That point *is* a gate, and a gate that
  cannot fail is not a gate.
- **The resolved registry is a controlled file.** Slipwai writes `.slipwai/hooks.json` from the elected
  extensions. If an iteration edits that file, slipwai refuses the iteration, the same as an edit to a
  gate. So a run cannot register a hook on itself.

## The guards

A guard is the second closed set. It exists because of the rule above: **a hook never fails the rung.**
That rule made one thing impossible to build. Some extensions want to say *do not search for that, ask the
index*. That is not a report after the event. It is an answer to a tool call that has not happened yet.

If `hooks` could refuse, every hook could fail a rung. That is the control plane that the rule prevents.
So a guard is a separate kind. It has three differences from a hook, and they are the whole design:

1. **A guard fires before a tool call, not around a rung.** It can stop only that one call.
2. **A guard can refuse, by exiting with code 2.** Everything that the guard printed goes back to the
   agent. The agent then does something else, usually what the guard suggested. Any other exit code
   behaves like a hook: slipwai reports it, and the call goes ahead.
3. **The rung completes in both cases.** A refused tool call is not a failed stage. No guard can end a
   stage.

| Guard | Fires | Given | If the guard refuses |
|---|---|---|---|
| `session` | when a delegate's session opens, before its first tool call | `stage`, `slice`, `fairway`, `berth` | the session does not start |
| `before-search` | just before a delegate searches the tree | `stage`, `slice`, `fairway`, `query`, `tool` | the search does not run, and the agent is told what to ask instead |
| `before-write` | just before a delegate writes or edits a file | `stage`, `slice`, `fairway`, `path`, `tool` | the file is not written |
| `before-command` | just before a delegate runs a shell command | `stage`, `slice`, `fairway`, `command`, `tool` | the command does not run |
| `before-fetch` | just before a delegate reads a URL | `stage`, `slice`, `fairway`, `url`, `host`, `tool` | the fetch does not happen |
| `after-delegate` | after a delegate answers, before slipwai uses the answer | `stage`, `slice`, `fairway`, `tool` | the answer is not used, and the agent is asked again |
| `before-stop` | just before a delegate's session ends | `stage`, `slice`, `fairway`, `berth` | the session does not end: the reason becomes the next turn |

Declare a guard in the same way as a hook, but under `guards` instead of `hooks`. The default budget for a
guard is 5s, not 30s, because somebody is waiting for the tool call.

```json
{
  "guards": {
    "before-search": {"run": "guards/ask-the-index.py", "budget": "3s"}
  }
}
```

**A person agrees to a guard. Installing the extension is not enough.** A hook runs wherever an extension
is elected. A guard can also refuse things that a person asked for. So `./init` asks once, and names in
plain words what each guard could stop. `./init` writes `.slipwai/guards.json` from the answer, not from
the manifests.

`./init` asks this question over the terminal. So a scripted or CI `./init` is never asked, and agrees to
nothing. No answer means *no*. That is the only safe default for a question about refusing somebody's tool
calls. If nobody agreed to an extension's guard, the guard never fires. To change the answer later, run
`python3 scripts/extensions/guards.py --elect <keys>`.

**Where guards fire from.** All of a harness's own events arrive at one place: `scripts/agents/session.py`.
These events are the pre-tool event, the stop event and the compaction events. `session.py` runs the
keel's answer first, and then the extensions' answers.

So an extension declares `before-write` once. It does not have to learn the spelling of each of thirty-six
harnesses. For the same reason, the keel's own refusal of edits to controlled files is a guard like any
other. It is not a row that the keel writes into one harness's settings file.

## The tools

A hook is something that the extension runs. A guard is something that the extension can refuse. The
third thing is neither. It is a tool that *the agent* calls, and that belongs to the extension. An example
is `codegraph`'s MCP server, which the agent sees as `mcp__codegraph__*`. If a headless session starts
under an allow-list that does not name the tool, the session cannot reach the extension at all.

```json
{
  "tools": ["mcp__codegraph__*"]
}
```

`tools` is a list of strings, in the order that the extension wrote them. Slipwai does not validate the
strings against a harness. Each pattern is a string in the harness's own spelling. If the keel checked
the patterns, an extension could not use a new tool until the keel had a new release.

**Why this is a declaration, and not a row in the registry.** It was a row in the registry before.
`scripts/agents/registry.json` is the keel's catalogue of coding agents, and it goes into every generated
project. So `mcp__codegraph__*` was in Claude Code's headless allow-list in every project, whether the
project had elected the index or not. A reader who found it there had every reason to think that the keel
brought the index.

Now a harness row says where an elected extension's names go. It does this with a `{tools}` placeholder
inside the allow-list that the row already has. If a row has no placeholder, slipwai leaves it exactly as
recorded. It does not add a flag that nobody has checked the harness accepts.
`tests/test_extension_reach.py` checks that no value a session runs under carries an extension's name.

The keel still *reads* what an extension built. For example, `slipwai survey` opens
`.codegraph/codegraph.db` if it exists, in the same way that it reads `.git`. The keel still names the
product where it names that file's format, or where it quotes dated evidence about it. But the keel does
not carry a live configuration value that belongs to an extension.

## Where the files land

Slipwai writes every file of the package except `extension.json` into a generated project at
`scripts/extensions/<key>/`. Three files sit beside them:

- `scripts/extensions/available.json` carries each offered extension's hooks.
- `available-guards.json` carries what each extension can refuse.
- `available-tools.json` carries the tool names that each extension needs allowed.

Slipwai does not copy the manifest. Nothing reads a manifest inside a project. A copy there would be a
decoy that nothing reads and everybody edits.

The project receives the files at **generation**, not at election. `./init` builds its menu from the
catalogue, and the election happens inside the project, where there is no keel to fetch anything. So the
menu offers exactly what `./init` can run. If you install an extension after a project was generated, the
extension reaches that project at the next `slipwai migrate`.

## Writing one

```sh
slipwai package new <key>                  # a whole package that already loads
slipwai package check <dir>                # the conformance suite for whichever kind it is
slipwai package release <dir>              # the release file, its digest and its index entry
slipwai package register <dir> --channel <checkout>   # both of those, into a channel
slipwai extension check <dir>              # just the manifest, and the six it is held to
slipwai extension install <key>            # into the package directory
slipwai extension list                     # what is installed, and what each attaches to
slipwai hooks                              # every point, and what is on it
python3 scripts/extensions/guards.py --elect <keys>   # in a project: who may refuse a tool call
```

The scaffold ships a `Makefile` with `check`, `release` and `register`. It also ships a CI workflow that
calls the keel's reusable workflow. So inside the package, you run `make check` and
`make register CHANNEL=...`.

A channel is a directory. It holds `entries/<name>-<version>.json`, one file per release, and
`slipwai-languages/index.json`, which is built from those files. If two publishers release on the same
afternoon, they change two different files and never conflict. The index is regenerated, not merged. This
is the same shape as `changelog.d`.

A channel refuses a version that it already lists with different bytes. A release cannot change once
anybody has installed it. If a release could be replaced silently, a digest that somebody checked would
stop meaning anything.

`package new` writes a manifest that declares the schema that *this* keel uses. It also writes an entry
point that already meets obligations 1, 3 and 6, with the others marked `TODO`. If a scaffold did not
load, its first lesson would be that the tool is broken.

An install takes a name, a package directory, a release file or a git URL:

- A name with no path separator is looked up in the chandlery.
- Anything with a separator is a path. So a mistyped path is a refusal, never a silent network call.

A clone is shallow, and slipwai drops its `.git` during the install. What is installed is the package,
not its history.

## Channels

`SLIPWAI_CHANDLERY` names the channels to ask, separated by commas, in order. Usually an organisation's
own channel is first and the public channel is after it.

The order is the whole policy: **if an earlier channel lists a name, that name belongs to that channel**,
with all its versions. So an organisation can publish its own `python` package, and that package wins with
nothing else configured. If slipwai merged the version lists instead, one install could fetch from
whichever channel published most recently.

Slipwai still reads `SLIPWAI_INDEX`, and asks it last. It is the keel's own upgrade index as well as a
package channel. A person who set it to a mirror meant "fetch from here". That person did not mean "and
never ask anywhere else".

If one channel is unreachable, slipwai says so and still lists the other channels. If every channel is
unreachable, slipwai refuses. "Nothing is available" and "slipwai could not ask" are different answers,
and a person acts differently on each.

## What is refused, and where

A manifest is either correct or incorrect on its publisher's machine. So `extension check` refuses every
problem with the manifest's shape before anything is published.

Two problems are only visible on the machine that installs the extension, so that machine refuses them:

- a `key` that another package already holds
- a `core` range that this keel does not satisfy

Slipwai refuses only the faulty extension. An extension is an optional development tool. If a project
could not be generated because an optional extension was malformed, the dependency would point the wrong
way.

## Who you install from

When you install a package, you run somebody else's code. The keel imports a language's Python code, and
an extension's entry point edits the project. The digest that the index publishes proves that the file is
the file the index listed. It says nothing about who listed it.

So if a package's index entry names a publisher, slipwai asks you about that publisher **once**. When you
accept a publisher, all their later releases install without a question.

- `slipwai trust list` shows who is accepted.
- `slipwai trust add <publisher>` accepts a publisher in advance. A container image or a CI runner needs
  this.
- `slipwai trust remove` removes a publisher.

`ROBCOATVG` is seeded as a row like any other, and you can remove it. That is the difference between a
default and a rule.

A release is in one of four states, and `slipwai show` tells you which:

| State | What it means |
|---|---|
| `verified` | slipwai checked a signature, and it matched |
| `unverified` | the release carries a signature, and this copy has no verifier for it |
| `unsigned` | the index carries no signature, or names no publisher to attribute one to |
| `untrusted` | this machine has not accepted the publisher |

`unverified` is deliberately separate from `verified`. A signature must never be used to say "signed"
about a signature that nobody checked.

There are two verifiers, one for each kind of channel. This was decided on 2026-10-08 (plan 6.5):

- **A private channel** signs with an Ed25519 key that its organisation holds. Every machine verifies
  that signature completely, with the keel's own `ed25519.py`. The signature starts with `ed25519:`. It
  reaches `verified` only if the publisher is accepted and this machine holds the publisher's key.
- **The public channel** signs without a key, from CI, as a Sigstore bundle. Python's standard library
  has no X.509 and no ECDSA, so a keel with no dependencies cannot check that bundle. A machine that
  installed `slipwai[verify]` checks the bundle with the Sigstore library. A machine without it still has
  the digest, TLS to the channel, and the identity that the channel's CI recorded, and it reports
  `unverified`.

## The keel ships none

Version 1 carried three extensions in its own `catalog.json`. They are packages now:
`ROBCOATVG/slipwai-extension-codegraph`, `-uipro` and `-ux-gates`. If an extension lived in the keel,
every project would carry its description, whether anybody wanted it or not.
