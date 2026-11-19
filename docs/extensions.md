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
| What a project is given of a package | `src/slipwai/extension_given.py` | contract |
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
| `writes` | no | The paths that the extension writes in a project outside its own directory. See [Taking it back](#taking-it-back). |
| `withhold` | no | Paths of the package that a project is not given, beyond the conventional ones. See [Where the files land](#where-the-files-land). |

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
| `init` | `./init --extension <key>`, once per election | `root`, `guards_held` |
| `project` | every re-projection: `make agents`, `migrate`, `./init --integration` | `root`, `harnesses`, `guards_held` |
| `check` | `make check-extensions`, as one more gate | `root` |
| `remove` | un-electing the extension: `python3 scripts/extensions/hooks.py --remove <key>` | `root` |
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
    "after-stage": {"run": "hooks/sync.py", "stages": ["drive"], "budget": "30s"}
  }
}
```

**`stages` is matched against the name the captain fires the point with, and it fires two.** `before-stage`
and `after-stage` fire around a session, not around each rung inside it:

- `drive` is the session that takes one slice up the ladder.
- `decide` is the session that answers the questions a slice stopped on.

A hook that names no `stages` runs at both. A hook that names any other stage — `implement` or `converge`,
which this page once gave as its example — never runs, and nothing reports it.

**Every script a manifest names must be in the package.** A hook or a guard whose file is missing never
runs in any project. Conformance fails such a package and names the point and the path, and
`slipwai extension list` says so for an installed package in that state.

The hook receives the given values as environment variables: `SLIPWAI_STAGE`, `SLIPWAI_SLICE` and so on.
`SLIPWAI_POINT` names the point itself.

**A hook that names no `budget` gets 30 seconds, or ten minutes at `check`.** A `check` hook is a gate in
`make verify`, and a gate that renders or builds takes minutes. A hook over its budget is ended.

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
| `before-search` | just before a delegate searches the tree | [the search event](#what-a-before-search-guard-is-handed) | the search does not run, and the agent is told what to ask instead |
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

### How a guard is handed what it is given

A guard receives the given values as environment variables, in the same way as a hook: `SLIPWAI_STAGE`,
`SLIPWAI_QUERY`, `SLIPWAI_TOOL` and so on. `SLIPWAI_POINT` names the guard point. A variable is set only
where the value exists. For example, a person's own session has no stage, so `SLIPWAI_STAGE` is not set.

A guard runs with the project root as its working directory. Slipwai ends a guard that is over its budget,
and the call goes ahead. A guard that crashes, exits with any code except 2, or is not in the project also
lets the call go ahead. A guard can never keep a tool call waiting for longer than its budget.

### What a `before-search` guard is handed

A search guard must decide about *this* search: which tool made it, where it looks, and whose it is. So
`before-search` also hands the guard one JSON object on its stdin. This object is the contract. Write a
guard against it.

| Field | What it is |
|---|---|
| `v` | The version of this contract: `1`. A new field does not change it. A field whose meaning changes does. |
| `point` | `before-search`. |
| `tool` | The tool that makes the search, in the harness's own spelling: `Grep`, `Glob` or `Bash` on Claude Code. |
| `query` | The same string as `SLIPWAI_QUERY`: the pattern, or the command for a shell search. |
| `pattern` | What a search tool looks for: a regular expression for `Grep`, a file pattern for `Glob`. |
| `path` | Where a search tool looks, exactly as the agent wrote it. It can be relative to `cwd`. |
| `glob` | The file filter of a `Grep`, for example `*.md`. |
| `type` | The file type of a `Grep`, for example `py`. |
| `command` | The whole shell command, for a search that comes through the shell. Slipwai does not parse it. |
| `cwd` | The directory that the session is in. |
| `session` | The harness's identifier for the session. |
| `agent` | The harness's identifier for the sub-agent that made the call. It is absent for the session itself. |
| `agent_type` | The type of that sub-agent, for example `sail-implement-shipwright`. |
| `stage` | The rung, in a session that a captain dispatched. |
| `slice` | The slice, in a session that a captain dispatched. |
| `fairway` | The fairway, in a session that a captain dispatched. |

**A field that the search did not name is absent.** It is never an empty string. A `Grep` with no `path`
has no `path` key, and a call by the session itself has no `agent` key. Read a field with `.get()`.

Every shell command reaches `before-search`, and not only the commands that search. A `grep` in the shell
is the same search through another door, and slipwai cannot tell which commands search without parsing
the shell. So a guard receives `tool: "Bash"` and the `command`, and decides for itself.

**A guard is handed the search, not the session.** The harness's own event also names the transcript of
the conversation, the permission mode and the identifier of the call. Slipwai copies none of them.

`SLIPWAI_QUERY` is the only thing that a guard received before this event existed. It still carries the
same string, so a guard that reads only `SLIPWAI_QUERY` works as before. Slipwai cuts it at 16,000
characters, because a platform refuses a process whose arguments are too long. The event carries the
whole string.

The other guards receive no event on stdin. `tests/test_guard_event.py` holds this table to the code that
builds the event.

### A guard can see its extension's own tools used

Some rules depend on what a session did earlier. The rule for a code index is *refuse a symbol search
until this session has asked the index*. An ask over MCP is a tool call of its own, and no guard point
fires for it. So a guard can declare the tools whose use it wants to **see**:

```json
{
  "guards": {
    "before-search": {"run": "guards/ask-the-index.py", "sees": ["mcp__codegraph__.*"]}
  }
}
```

When a session is about to use one of those tools, slipwai runs the same script. It sets `SLIPWAI_POINT`
to `tool-use`, and `SLIPWAI_GUARD` to the guard that declared the tool. It hands the script this JSON
object on stdin:

| Field | What it is |
|---|---|
| `v` | The version of this contract: `1`. |
| `point` | `tool-use`. |
| `tool` | The tool that is being used, for example `mcp__codegraph__codegraph_explore`. |
| `cwd` | The directory that the session is in. |
| `session` | The harness's identifier for the session. |
| `agent` | The harness's identifier for the sub-agent that made the call. It is absent for the session itself. |
| `agent_type` | The type of that sub-agent. |
| `stage` | The rung, in a session that a captain dispatched. |
| `slice` | The slice, in a session that a captain dispatched. |
| `fairway` | The fairway, in a session that a captain dispatched. |

So one script reads `point`, records the session at `tool-use`, and decides at `before-search`. Three
rules apply:

- **Seeing is not judging.** `tool-use` is not a guard point. Slipwai discards the exit code, so a guard
  cannot refuse a tool that it is only told about. If the script exits 2 there, slipwai says so and the
  call goes ahead. This is why seeing is a separate moment and not one more `before-` point: a script
  written to refuse wherever it runs would otherwise stop its own extension's tool.
- **A guard is told which tool, and not what the tool was asked.** The event carries no arguments of the
  call. They are not a search, and they can hold anything.
- **`sees` is limited to one MCP server's tools.** Each entry is `mcp__<server>__<tool>` or
  `mcp__<server>__.*`. Slipwai also reads `mcp__<server>__*`, the spelling that `tools` uses, as the same
  thing. A guard can declare at most 8 entries. Slipwai refuses anything else when it reads the manifest,
  and ignores it in a registry that somebody edited by hand. No alternation and no other wildcard is
  accepted, so no extension can name a search tool, the shell or every MCP call, and no extension can put
  a guard in front of every tool call.

A person agrees to what a guard sees together with the guard, and the question names the tools. On Claude
Code, the pre-tool matcher for `tool-use` is exactly the entries of the agreed guards: slipwai writes that
one row into `.claude/settings.json` when an agreement changes and at every `make agents`, and removes it
when no agreed guard sees anything. [Which harness holds which guard](#which-harness-holds-which-guard)
says where this works. A shell command that belongs to an extension needs no `sees`: every shell command
reaches `before-search` already.

`tests/test_guard_seen.py` holds this table to the code, and is the proof that the rule above can be
written: a stand-in extension refuses a symbol `Grep` of the source, allows it after its tool was used in
that session, never refuses a `Grep` under `specs/` or a `Glob`, and still refuses another session.

**A person agrees to a guard. Installing the extension is not enough.** A hook runs wherever an extension
is elected. A guard can also refuse things that a person asked for. So `./init` asks once, and names in
plain words what each guard could stop. `./init` writes `.slipwai/guards.json` from the answer, not from
the manifests.

`./init` asks this question over the terminal. So a scripted or CI `./init` is never asked, and agrees to
nothing. No answer means *no*. That is the only safe default for a question about refusing somebody's tool
calls. If nobody agreed to an extension's guard, the guard never fires. To change the answer later:

- `python3 scripts/extensions/guards.py --elect <keys>` agrees to the guards of the extensions it names.
  It keeps every agreement that is already there.
- `python3 scripts/extensions/guards.py --remove <keys>` takes the agreement back for the extensions it
  names. It keeps the others.

**Either command leaves the gate green.** An extension's guidance can say whether its guard is agreed to,
so both commands bring what follows from the agreement up to date before they return:

1. the harness's row for the tools an agreed guard sees;
2. the guidance of each extension they named, by firing that extension's `project` hook alone, with what
   `make agents` hands it, and then writing its block from its `GUIDANCE` if it is still drifted;
3. where `AGENTS.md` changed, the copy of its extension guidance in the context file of a harness that
   reads a copy.

Each command prints what it brought up to date. `make check-extensions` then passes with nothing else run.
A `project` hook that crashes or goes over its budget does not undo the agreement and does not change the
exit code: the command prints the `hook <key> project` line, says whether the block is current, and names
`make agents` as the command that runs the hook again. A *yes* at the question `make agents` asks runs
`--elect`, so it does the same. `make agents` still asks last, after it has projected.

**A guard that arrives on an upgrade is said, and never agreed to for anybody.** A project can elect an
extension before the extension has a guard. `slipwai migrate` then brings the guard's files and refreshes
`available-guards.json` from the installed package, but nobody was asked. So:

- `slipwai migrate` prints one line for each such extension, and writes the same lines to the catch-up
  page under *Guards nobody has agreed to*.
- `make agents` prints the same line every time it runs. If it runs at a terminal, it asks the question
  that `./init` asks, and a `y` agrees. With no terminal it prints the line, changes nothing and exits 0.

Each line ends with the command that agrees: `python3 scripts/extensions/guards.py --elect <key>`. Neither
command writes `.slipwai/guards.json` unless a person answered. An extension must not write that file
either, from a hook or from anywhere else. The file *is* the agreement.

The registry holds each guard as it was when a person agreed to it. If an extension later changes that
guard's declaration, the agreed one still fires. `make agents` and `migrate` say that it changed, with the
same command, and `make agents` does not ask about it in passing.

**Where guards fire from.** All of a harness's own events arrive at one place: `scripts/agents/session.py`.
These events are the pre-tool event, the stop event and the compaction events. `session.py` runs the
keel's answer first, and then the extensions' answers.

So an extension declares `before-write` once. It does not have to learn the spelling of each of thirty-six
harnesses. For the same reason, the keel's own refusal of edits to controlled files is a guard like any
other. It is not a row that the keel writes into one harness's settings file.

## Which harness holds which guard

A guard holds on a harness only if that harness has a hook that can refuse at that moment, and somebody
read the shape of that hook. `scripts/agents/registry.json` records this for each harness, with the source
and the date. A harness that is not in this table holds no guard: an extension's guard is installed and
agreed to there, and it refuses nothing.

| Harness | `session` | `before-search` | `before-write` | `before-command` | `before-fetch` | `after-delegate` | `before-stop` | `tool-use` |
|---|---|---|---|---|---|---|---|---|
| Claude Code (`claude`) | yes | yes | yes | yes | yes | yes | yes | yes |
| Cursor (`cursor-agent`) | no | no | no | no | no | no | yes | no |
| Gemini CLI (`gemini`) | no | no | no | no | no | no | yes | no |

`tool-use` is not a guard point. It is the moment when a guard is told that a tool it `sees` was used.

**Cursor and Gemini CLI get no `before-search`, and slipwai does not pretend that they do.** The registry
records a stop hook for each of them, and slipwai projects that hook. The registry records no hook before
a tool call for either of them whose input and refusal were read. Slipwai writes a harness's hook file
only from a shape that somebody read, because a row written from a guess is a guard that looks installed
and never fires. When somebody reads such a hook, its row gains the event, slipwai projects it, and this
table changes.

**An extension is told, so that its guidance can be true.** At the `init` and `project` hook points, the
hook receives `SLIPWAI_GUARDS_HELD`. It is a JSON object: each harness that is installed in the project,
with the list of moments that hold there.

```json
{"claude": ["session", "before-search", "before-write", "before-command", "before-fetch", "after-delegate", "before-stop", "tool-use"], "gemini": ["before-stop"]}
```

`python3 scripts/extensions/guard_harness.py --held` prints the same object. So an extension that writes
"a guard refuses that search" into `AGENTS.md` can write it only where `before-search` is in the list, and
say that the rule is advice on the other harnesses. `tests/test_guard_harnesses.py` holds this table to
the registry, and the Claude Code row to the hook rows that slipwai writes.

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

Slipwai writes what a project runs or reads of the package into a generated project at
`scripts/extensions/<key>/`. Four files sit beside them:

- `scripts/extensions/available.json` carries each offered extension's hooks.
- `available-guards.json` carries what each extension can refuse.
- `available-tools.json` carries the tool names that each extension needs allowed.
- `available-writes.json` carries the paths that each extension says it writes outside its own directory.

**A project is not given the package's repository.** A package is a repository as well as a tool. These
paths at the package root stay in the package, for every extension, with no line in any manifest:

| Not given | Why |
|---|---|
| `.github/` | A workflow outside a project's own `.github/` is run by nobody. |
| `tests/` | Nothing in a project runs a package's tests. |
| `changelog.d/`, `CHANGELOG.md` | `VERSION` says which release the copy is. What earlier releases changed is the repository's history. |
| `.gitignore`, `.gitattributes` | They describe the package's checkout. A project ignores an extension's local state through `ignore` in the manifest. |
| `__pycache__/`, at any depth | What an interpreter left in the publisher's checkout. |

A manifest can add to that list with `withhold`, and cannot take anything off it:

```json
{"withhold": ["fixtures/", "MAINTAINING.md"]}
```

Each entry is a path from the package root, with `/` between its parts. An entry that ends in `/` is a
folder and everything in it.

Three things are always given, whatever either list says:

- **Every script the manifest declares** at a hook or a guard, wherever the script sits.
- **Every module of the package that such a script imports**, followed through. Slipwai reads the `import`
  statements, and looks beside the importing file and at the package root. Slipwai does not see a module
  that is loaded by a computed name, or a file that is opened as data. Keep those outside the paths above.
- **`README.md`, a licence and a notice.** The README is what a person or an agent in the project reads to
  learn what the folder is. A licence travels with the code that it covers, and a project holds a copy of
  that code.

`slipwai extension check <dir>` prints how many files a project is given, and names the ones it is not.
`slipwai conformance --extension` runs the entry point in a project that holds only what is given. So a
script that needs a withheld file fails on the publisher's machine, not in a project.

None of this changes what a release packs. The archive, its checksum and the installed package are still
the whole package.

**An existing project loses those files at its next `slipwai migrate`.** The merge removes each one that
the project left as it was given. A file that somebody changed in the project stays as it is, the merge
does not stop on it, and the catch-up page names it.

Slipwai does not copy the manifest. Nothing reads a manifest inside a project. A copy there would be a
decoy that nothing reads and everybody edits.

The project receives the files at **generation**, not at election. `./init` builds its menu from the
catalogue, and the election happens inside the project, where there is no keel to fetch anything. So the
menu offers exactly what `./init` can run. If you install an extension after a project was generated, the
extension reaches that project at the next `slipwai migrate`.

## Taking it back

An extension can write outside its own directory. For example, an entry point can write a command at
`scripts/<key>` that its `AGENTS.md` block names. Two declarations let a project take such a file back.

**`writes` names the paths.** The record is declared, not observed: slipwai does not watch what a hook
does.

```json
{
  "hooks": {"init": "init.py", "remove": "hooks/remove.py"},
  "writes": ["scripts/indexer"]
}
```

Each entry is a path from the project root, with `/` between its parts, and outside
`scripts/extensions/<key>/`. Declare the files that are wholly the extension's. Do not declare a file that
the extension shares, such as `AGENTS.md` or a harness's MCP file. The extension holds one entry in such a
file, and the `remove` hook takes that entry back.

An election records the paths in `.slipwai/hooks.json`, under `writes`.

**`remove` is the point where the extension takes them back.** It has no default declaration, because an
entry point installs. Slipwai fires it for one extension, when a person un-elects that extension:

```sh
python3 scripts/extensions/hooks.py --remove <key>
```

The un-election does these things, in this order:

1. It fires the extension's `remove` hook, if the extension declares one.
2. It names each recorded path that is still in the project. It removes no file itself. A file that an
   extension wrote can since have become a file that somebody depends on, so a person decides.
3. It takes the extension out of `.slipwai/hooks.json`, out of `.slipwai/extensions.json`, and takes its
   block out of `AGENTS.md`.

A `remove` hook that fails never blocks the un-election. Slipwai reports it as a `hook` line, and
continues. The extension's copy under `scripts/extensions/<key>/` stays, because the extension is still
offered. The un-election does not withdraw a guard that somebody agreed to. `.slipwai/guards.json` holds
that agreement.

**`slipwai extension remove <key>` runs the un-election first** when you run it in a project that elected
the extension. Then it removes the package from the machine. It changes no other project. Run anywhere
else, it prints the un-election command to run in each project that elected the extension. Run that
command before the project's next `slipwai migrate`, because the migration takes the copy away, and the
`remove` hook is in the copy.

## Keeping one current

`slipwai upgrade` moves an installed extension as it moves an installed language. Its `extensions:` section
has one line for each:

| The line says | What happens |
|---|---|
| `<key> 1.0.0 → 1.0.1 available` | A newer release that this keel can load is published. `upgrade` installs it. With `--check`, it prints `would run: slipwai extension upgrade <key>` and installs nothing. |
| `<key> 1.0.0 (newest compatible)` | Nothing moves. |
| `<key> 1.0.0 held back: 2.0.0 needs another core schema than 9.0 — slipwai upgrade, once a slipwai that speaks it is published` | Nothing moves. The newer release is for another keel. |

`slipwai extension upgrade <key>` is the same move for the extensions that you name. With no name, it moves
every installed extension.

An upgrade agrees to nothing for you:

- If the release comes from a publisher that this machine has not accepted, `upgrade` refuses it and names
  the command that accepts the publisher. The upgrade then exits non-zero. An upgrade that left an
  extension behind did not succeed.
- A guard is agreed to in a project, at election. If a newer package declares a guard, no project's
  agreement changes.

The newer release is admitted as an install admits it. Slipwai stages the release, reads its manifest
under this keel's schema, and only then renames it into place. A release that does not load never replaces
one that does.

Moving the installed package does not move a project's copy. A project takes the installed package at its
next `slipwai migrate`.

## Writing one

```sh
slipwai package new <key>                  # a whole package that already loads
slipwai package check <dir>                # the conformance suite for whichever kind it is
slipwai package release <dir>              # the release file, its digest and its index entry
slipwai package register <dir> --channel <checkout>   # both of those, into a channel
slipwai extension check <dir>              # just the manifest, and the six it is held to
slipwai extension install <key>            # into the package directory
slipwai extension upgrade [<key>...]       # each installed one to its newest compatible release
slipwai extension list                     # what is installed, and what each attaches to
slipwai hooks                              # every point, and what is on it
python3 scripts/extensions/guards.py --elect <keys>   # in a project: one more may refuse a tool call
python3 scripts/extensions/guards.py --remove <keys>  # in a project: it may not any more
```

The scaffold ships a `Makefile` with `check`, `release` and `register`. It also ships a CI workflow that
calls the keel's reusable workflow. So inside the package, you run `make check` and
`make register CHANNEL=...`.

**A release is what the tag holds.** In a git repository, the release file holds the files that `HEAD`
tracks under the package and nothing else: no untracked file, no ignored file and no empty directory. So
two clones of one commit build the same bytes. `package release` and `package register` refuse while the
package's working tree differs from `HEAD`, and they name what differs; commit it or stash it. Outside a
repository, the directory is read as it stands.

A package's CI builds the release from its tag and attaches the file and its entry to the tag. If you
finish that publication by hand, register the entry that CI wrote, so that nothing is built a second time:

```sh
gh release download v<version> -R <owner>/<repo> -p '<name>-<version>.json'
slipwai package register . --entry <name>-<version>.json --channel <checkout>
```

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

Version 1 carried its extensions in its own `catalog.json`. They are packages now, and the keel names
none of them: [the index](https://robcoatvg.github.io/slipwai-index/) lists every published extension,
and `slipwai search` prints the same list. If an extension lived in the keel, every project would carry
its description, whether anybody wanted it or not, and every new package would be a keel release.
