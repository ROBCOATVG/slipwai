# The board on the Agent Client Protocol

A plan for phase 22, asked for on 2026-11-05 during the second live run of the brief's first page, when
the session behind it turned out to be `claude` by name: "we cant tie this to claude". Four ways to keep a
chat stateful over a coding agent were laid out — one headless run per turn with the folder as the state,
each harness's own session and resume flag recorded row by row, the Agent Client Protocol, or a model API
called directly — and the protocol was chosen, with the words "there are many ways to build a stateful
chat bot driven by a harness" against settling for the first. The work was then split in two: phase 21
stays the brief, with its record still to take; this is the port, done first, "and utilising its benefits,
so screen changes welcome".

**Status, 2026-11-05:** 22.1 to 22.5 built and green (2887 tests). 22.6, the live run, is half taken: the
keel's client has spoken to two real agents from a scratch folder, with no board involved — the Claude
adapter (handshake 0.4 s; options mode, model, effort, fast; a prompt answered in 2.2 s) and OpenCode
(1.7 s; options model and mode; 2.6 s, with thought chunks and a usage update); both advertise
`loadSession`. The page half waits on a board restart the user has not yet called for, since a
conversation is running on it. Found on the way: the first `npx` launch fetches the package, which a
60-second handshake would not survive on a slow line — the client now gives a package launch five
minutes, and 22.8 gains a "make ready" step. 22.7 is begun without the board: the draft runs over the
protocol where the board can launch the project's agent — `stage_session.py`, a step run in-process in
place of the `make draft` child, its words and tool calls as lines on the receipt, a permission and a
question as cards under it with a Stop, and every stage's prompt carrying the asking rule. The surfaces
and the assessment followed the same way through one `stage_step` helper; the model, triage and launch
through `stage_steps.py`, which does around the session what the toolkit's scripts do around theirs — the
model's prompt asked of the project's script, triage given the numbers nobody has routed, a launch going
on to enable `/cruise` and cast off — and says what a stage left undone; the adoption steps the same
way, with their prompt from `step.py --prompt`. The captain's drives and the skipper's rounds take the
protocol too, opt-in: the toolkit carries the keel's client (`make shared` writes `scripts/agents/acp.py`)
and `scripts/agents/drive.py` gives a session a process's face for the captain's watch; `SLIPWAI_ACP=1`
takes the initialised harness's launch row, any other value a command, unset is the print mode as it was.
The suite's stand-in drives a slice through the captain's gate on it. The board turning it on for a project
waits on a proven row (22.6 — now proven, so that switch is the next change).

**22.6, taken 2026-11-06** on a second board served from this tree on another port, so the conversation on the
first board was not dropped. The Claude adapter: *Make ready* 3.8 s; a brief drawn in 27 turns — a prototype,
`brief/prd.md` with 13 proposals and 2 open questions. OpenCode: *Make ready* 0.7 s; on its free model it thought
for minutes and was stopped; signed in to OpenAI by the person and set to GPT-6.1 Sol fast from the board, a brief
in 13 turns — a prototype, a brief with 22 proposals and 6 open questions, people, domain, look, surfaces. Neither
agent asked anything through `elicitation/create`: both wrote their questions under `## Open`, as the prompt
allows; the asking rule is the stages', not the first page's, and whether an agent takes it is the number 21.6d
still owes. Found on the way, and fixed the same day: a page script broken by a Python escape, *Auto* taking the
first `npx` row over the agents the machine had, thoughts drawn as turns, tool calls drawn raw, and nothing
saying which agent and model a conversation was on. Also proven: Amp installed from its archive by the board
answered its handshake in 0.9 s. 22.8 is built: *Make ready* on the Settings tab does the handshake through the client and keeps the
agent's name, version, time and sign-in methods on the row; *Sign in* is `authenticate`, or the line to run for a
terminal method; *Install* fetches the registry's archive for this platform, checks its sha256 and unpacks it
under `~/.slipwai/agents/`, which `acp_launch` then finds. Nothing in 22.8 has been exercised against a real
download yet; that goes with 22.6's live run.

**The principle the plan serves:** the board is the face a non-technical person sees, and what runs behind
it must be whichever coding agent that person has — not one named in the keel's source. The protocol is
how editors already do this: one client, any agent. Taking it gives the board more than neutrality: events
as they happen on every agent instead of two, a permission the board answers by policy or puts to the
person, a question the agent can ask on the page instead of writing an assumption, and a stop that is a
real cancel. Each of those is a screen change, and each is welcome.

## 1. What is wrong, in the words of the code

**The two sessions name their harness.** `brief_session.Sketch.argv` and `console.Console.argv` look up
the `claude` binary and write its flags by hand — `-p`, `--output-format stream-json`, `--tools`,
`--session-id`, `--resume`, the no-MCP pair — and say "there is no `claude` on this machine's path" when
it is missing. The prototyping plan's own words under 21.6: "not harness-neutral in its first version".

**The stages have a seam the sessions do not use.** `assets/toolkit/scripts/agents/harness.py` chooses a
harness and builds its headless command from the registry's `headless` row; `draft`, `assess`, `model`,
`triage`, the adoption steps and the captain run through it. It is one prompt in, a stream read on two
harnesses, a kill to stop, and no way for the stage to ask anybody anything — which is why the draft
writes assumptions, and why the number this phase's predecessor keeps is *assumptions after the draft*.

**The registry knows 36 harnesses and can run 27 headless, 2 with events, 1 with resume.** A conversation
needs a session: state across turns, events as they happen, a way to be asked, a way to be stopped.

## 2. What the protocol is, as far as this plan needs it

The Agent Client Protocol (agentclientprotocol.com; wire version 1 stable; v2 in draft since July 2026) is
JSON-RPC 2.0 over the agent's stdin and stdout, one JSON object per line, the agent a subprocess of the
client. Read on 2026-11-05 from the v1 schema and the prompt-turn and tool-call pages.

| The client sends | What it does |
|---|---|
| `initialize` | `protocolVersion: 1` and `clientCapabilities` (`fs.readTextFile`, `fs.writeTextFile`, `terminal`, all false here); the agent answers with `agentCapabilities` — `loadSession`, `promptCapabilities`, `sessionCapabilities` — and `authMethods` |
| `authenticate` | where `authMethods` is not empty; a `terminal` method names a command to run, which is the sign-in |
| `session/new` | `cwd` (absolute) and `mcpServers` (none here); answers `sessionId`, and may carry `configOptions` (category `model` among them) and `modes` |
| `session/load` | the same with a `sessionId`, only where the agent advertised `loadSession`; the agent replays the history as updates before answering |
| `session/prompt` | `sessionId` and `prompt`, a list of content blocks, `{"type": "text", "text": ...}` here; answers `stopReason`: `end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled` |
| `session/cancel` | a notification; the agent stops and still answers the prompt, with `cancelled` |
| `session/set_config_option` | a config option's new value, the model among them, where the agent offered one |

| The agent sends | What it is |
|---|---|
| `session/update` | a notification: `sessionUpdate` is `agent_message_chunk`, `agent_thought_chunk`, `user_message_chunk` (each a `content` block), `tool_call` (`toolCallId`, `title`, `kind` in read/edit/delete/move/search/execute/think/fetch/switch_mode/other, `status` in pending/in_progress/completed/failed, `locations`, `content`, `rawInput`), `tool_call_update` (the changed fields), `plan` (`entries` of `content`, `priority`, `status`), `available_commands_update`, `current_mode_update`, `config_option_update`, `session_info_update`, `usage_update`, `notice`, `compaction_update`, `compaction_summary_chunk` |
| `session/request_permission` | a request: `sessionId`, `toolCall` (a tool-call update), `options` of `optionId`, `name`, `kind` in `allow_once`, `allow_always`, `reject_once`, `reject_always`; the client answers `outcome: {outcome: "selected", optionId}` or `{outcome: "cancelled"}`, and must answer every outstanding one with `cancelled` on a cancel |
| `elicitation/create` | a request: `message`, with a form (`requestedSchema`) or a URL; the client answers `action` `accept` with `content`, `decline` or `cancel` |
| `fs/read_text_file`, `fs/write_text_file`, `terminal/*` | only where the client said it could; the board does not |

**Which harnesses.** The protocol's own registry (github.com/agentclientprotocol/registry, read 2026-11-05)
holds a manifest per agent with how it is launched: an `npx` package and arguments, or a binary archive
per platform with a sha256 and arguments. Crossed with the keel's 36:

| Keel key | ACP agent | Launch, from its manifest |
|---|---|---|
| claude | Claude Agent, adapter | `npx @agentclientprotocol/claude-agent-acp` |
| codex | Codex, adapter | `npx @agentclientprotocol/codex-acp` |
| gemini | Gemini CLI | `npx @google/gemini-cli --acp` |
| opencode | OpenCode | `opencode acp` |
| cursor-agent | Cursor | `agent acp` (the manifest's binary is `cursor-agent acp`) |
| copilot | GitHub Copilot | `npx @github/copilot --acp` |
| qwen | Qwen Code | `npx @qwen-code/qwen-code --acp --experimental-skills` |
| goose | goose | `goose acp` |
| kimi | Kimi CLI | `kimi acp` |
| kiro-cli | Kiro CLI | `kiro-cli acp --agent-engine=v3` |
| junie | Junie | `junie --acp=true` |
| droid | Factory Droid | `npx droid exec --output-format acp-daemon` |
| cline | Cline | `npx cline --acp` |
| auggie | Auggie CLI | `npx @augmentcode/auggie --acp` |
| qodercli, lingma | Qoder CLI | `npx @qoder-ai/qodercli --acp` |
| kilocode | Kilo | `kilo acp` or `npx @kilocode/cli acp` |
| vibe | Mistral Vibe | `vibe-acp` |
| amp | Amp, third-party adapter | `amp-acp` |
| codebuddy | Codebuddy Code | `npx @tencent-ai/codebuddy-code --acp` |
| devin | Devin | `devin acp` |
| pi | pi, adapter | `npx pi-acp` |
| grok | Grok Build | `npx @xai-official/grok agent stdio` |
| bob | Bob | in the registry; launch to be read |
| hermes | Hermes Agent | on the protocol's agents page, not in its registry |

Twenty-four of the keel's 36 are in the protocol's registry and a twenty-fifth on its agents page; Junie
and Kiro among them, which the keel has no headless row for. Not on either list: agy, alquimia, firebender,
forge, omp, rovodev, shai, tabnine, trae, zcode, and zed, which is a client. On the machine this was planned
on: Claude Code and Codex through their adapters over `npx`, and OpenCode and Cursor natively.

## 3. The decisions

1. **The keel speaks the client half itself.** It ships with no dependencies, and the half it needs is
   small: spawn, seven methods, two callbacks, a line reader. `acp.py` in the edge tier, with `json`,
   `subprocess` and a thread. The Python SDK (`agent-client-protocol` on PyPI) is the reference it is
   checked against and is not vendored.
2. **The board offers no file system and no terminal.** An agent's own tools write the folder; the
   permission request is where the board holds the line. A write under the session's working directory
   is allowed by policy without a word; a request for anything else, and any request the policy cannot
   read, is a card on the page with the agent's own options, and the turn waits on it. On a cancel every
   outstanding request is answered `cancelled`, as the protocol requires.
3. **A question from the agent is a question on the page.** `elicitation/create` becomes a card the
   person answers in the same session. That is the change the draft has been waiting for: a stage that can
   ask does not have to assume.
4. **The role goes at the head of the first prompt.** The protocol has no system prompt. The eight steps
   of the brief's session, and the console's brief, are the first prompt's opening text, set off from what
   the person said; `session/load` brings them back with the rest of the history.
5. **The session outlives the board.** The session id is written beside the brief (`<workspace>/.acp`)
   and the console's beside the project's board state; where the agent advertises `loadSession`, a board
   restart loads it and the page shows the history the agent replays. Where it does not, the board starts
   a new session and says so on the page; the folder is still the state.
6. **The model is the agent's to offer.** `session/new` may answer with config options, one of them of
   category `model`; the settings page shows those, and sets one with `session/set_config_option`. The
   board names no model of its own.
7. **The registry gains an `acp` row per harness**, copied from the protocol's registry with the date it
   was read: the launch, the kind (native or through which adapter), and `proven: false` until a session
   has run on it from the board. The `headless` row stays for the stages until 22.7, and for any harness
   with no `acp` row after.
8. **One settings page, `/settings`, last on the tab bar.** *Runs on*: every registry harness with an
   `acp` row whose launch this machine can make — the binary on PATH, or `npx` present for a package —
   with where it was found, and *Auto*, the first found, as the default. Remembered in
   `~/.slipwai/board.json`. A project's recorded harness in `.specify/integration.json` outranks the
   board's for its console, because it is the person's answer to `./init`; the first page, with no
   project, has only the board's. The theme stays in the corner.
9. **Optional, as everything in phase 21 is.** A board with no settings file and no agent it can launch
   runs the first page and the console as it does today, on `claude`, and says so. The start page,
   `slipwai generate` and the toolkit's headless path are untouched.
10. **Screens change where the protocol gives something to show.** A tool call is a card with its kind,
    title and status, not a grey monospace line; a plan is a list that ticks; a permission and a question
    are cards with buttons; a turn has a Stop. The log keeps its shape — turns behind a lock, a poll with
    `since` — and grows kinds.

## 4. The slices

Each on its own branch stacked on the last, one commit with a fragment and a `Slice-done: 22.x` trailer,
the gates inside. The main plan's phase 22 table is the one `make progress` ticks.

| Slice | What | Size | Status |
|---|---|---|---|
| 22.1 | `acp.py`: the client half — spawn, initialize, new and load, prompt, cancel, updates to a callback, permissions and questions to callbacks — over a stand-in agent that speaks the protocol from a script | M | todo |
| 22.2 | The registry's `acp` rows, dated, and `harness.acp_launch(key)`: the argv this machine can make for a harness, or why not | S | todo |
| 22.3 | `/settings`: *Runs on* and the agent's own model options, remembered in `~/.slipwai/board.json`; a project's init answer wins for its console | M | todo |
| 22.4 | The first page over the protocol: `Sketch` on an `acp.Session`, the role at the head of the first prompt, tool cards, a plan, permission and question cards, Stop, the session loaded across a restart | L | todo |
| 22.5 | The console over the protocol: the same on the Voyage page | M | todo |
| 22.6 | The live run: one brief through the first page on Claude's adapter and one on a native agent, recorded here | S | done 2026-11-06; the rows carry the proof |
| 22.7 | The stages over the protocol: draft first, then the surfaces, assess, the event model, triage, the adoption steps and the captain's drives; each shows its progress, asks the person instead of assuming, and stops on a cancel; the headless path kept where a harness has no `acp` row | L | done 2026-11-05; the captain's path opt-in by `SLIPWAI_ACP` until a row is proven |
| 22.8 | Install from the settings page: an agent put on this machine from its manifest — `npx` needs only Node, a binary archive is fetched and its sha256 checked — and its sign-in started through `authenticate`; the one line to run shown where the machine lacks what the manifest needs | M | done 2026-11-05: `agent_ready.py`, `agent_install.py`; three manifests give no checksum and get the link |
| 22.9 | The captain's protocol path turned on per project from the board: `sessions: protocol` in `.specify/cruise.json`, set on the *Who answers* card and read by the captain's switch; `SLIPWAI_ACP` still says first | S | done 2026-11-06 |

### 22.1 `acp.py` — M

- `Session(argv, cwd, on_update, on_permission, on_question)`: spawns the agent with its stdin and stdout
  as pipes and stderr to a log in `cwd/.acp/`, sends `initialize` with every capability false, reads one
  JSON object per line on a thread, routes responses to the waiting call by id, `session/update` to
  `on_update`, `session/request_permission` to `on_permission` (which returns an option id or `None` for
  cancelled) and `elicitation/create` to `on_question` (which returns an action and content). `new()`,
  `load(session_id)`, `prompt(text) -> stop_reason` (blocking; one at a time, a second is a refusal),
  `cancel()` (the notification, then every outstanding permission answered `cancelled`), `set_option(id,
  value)`, `close()`. `agent` carries what `initialize` answered: `load_session`, `auth_methods`,
  `config_options` after `new`.
- Errors are values: an agent that exits, a line that is not JSON, a response with `error`, a call that
  outlives its timeout, each a `Refusal` with the agent's stderr tail. Nothing here raises past the session.
- `tests/fixtures/acp_agent.py`: a stand-in agent in forty lines that answers `initialize`, `session/new`
  and `session/load`, streams a message chunk, a tool call and its update, asks permission for a write
  outside `cwd` and a question when the prompt says so, honours `session/cancel`, and writes a file so the
  folder changes. `tests/test_acp.py` drives the session over it: the handshake, a turn's updates in order,
  a permission inside and outside the working directory, a question answered, a cancel while a permission
  is outstanding, a load, an agent that dies mid-turn. Budget 320. Fragment `22.1-acp-client.md`, MINOR.

### 22.2 The registry's `acp` rows — S

- `assets/toolkit/scripts/agents/registry.json`: an `acp` object on each of the 24 rows the protocol's
  registry has — `npx: {package, args}` or `binary: {cmd, args}` as the manifest says, `via` (`native` or
  the adapter's name), `source` (the manifest's URL and the date), `proven: false`. `harness.acp_launch`
  in `src/slipwai/harness.py`: the argv, resolving `npx` on PATH for a package and the binary for a
  command, or a sentence saying what is missing. `tests/test_harness.py` grows the lookup. Fragment, PATCH.

### 22.3 `/settings` — M

- `settings_page.py` on the tab bar; `board_settings.py` for `~/.slipwai/board.json` (`runs_on`, `model`
  per harness). *Runs on* lists each harness with an `acp` row and whether this machine can launch it;
  *Auto* first. The model list is what the chosen agent offered as config options of category `model` the
  last time a session began, with "the agent's own" first; the board never invents one. `tests/test_settings_page.py`
  with the board fixture. Fragment, MINOR.

### 22.4 The first page over the protocol — L

- `brief_session.Sketch` keeps `say`, `said`, `ask`, `reset` and the lock, and holds an `acp.Session` in
  place of a process: `ask` is `prompt` on a thread, every update a turn with a kind the page knows —
  `text`, `thought`, `tool` (with `kind`, `title`, `status`, `path`), `plan`, `permission`, `question`,
  `error` — and the brief read back when the prompt returns. The role goes at the head of the first prompt.
  The session id is written to `<workspace>/.acp/session`; `for_slug` loads it where the agent can.
- `brief_page.py`: tool cards, the plan, a permission card and a question card with their buttons posting
  to `/brief/answer`, a Stop that posts `/brief/cancel`, and the text that said "there is no `claude`"
  saying what the settings page says instead. The listing shows which agent a sketch runs on.
- A board with no agent it can launch keeps the command of today, so `tests/test_brief_page.py` keeps its
  stand-in; `tests/test_brief_session.py` runs over the 22.1 stand-in agent. Fragment, MINOR.

### 22.5 The console over the protocol — M

- `console.Console` the same way, `console_page` the same cards; the project's harness from
  `.specify/integration.json` first, the board's where it has none. Fragment, MINOR.

### 22.6 The live run — S

- One brief through the first page on Claude's adapter and one on OpenCode or Cursor, whichever this
  machine signs into first; the registry rows marked proven with the date; the two runs recorded in this
  file's status line with what each showed that the stand-in could not.

### 22.7 The stages over the protocol — L

- As built: the stages the board runs take the protocol in the keel — `stage_session.py` is a step run
  in-process in place of the `make` child, `stage_steps.py` does around the session what the toolkit's
  scripts do around theirs (the model's prompt from `model.py --prompt`, triage's numbers, launch going on
  to cast off; the adoption step's prompt from `step.py --prompt`) — so the toolkit's scripts are untouched
  but for the `--prompt` flags, and a terminal runs them as it did. The captain's drives take it in the
  toolkit: `acp.py` carried by `make shared`, `drive.py` a session with a process's face. The draft first,
  because it is where the number is taken: a draft that asks on the page instead of assuming, and the
  count after it against 21.6d's ten. One fragment per stage, MINOR.

### 22.9 The captain's switch, from the board — S

- `sessions` joins `.specify/cruise.json`'s one list of settings, `print` or `protocol`, default `print`,
  a later key so a project written before it still passes `make check-agents`. The *Who answers* card on
  the Voyage sets it through the project's own `/cruise-settings` script, as it sets every other answer,
  and the captain's `drive.protocol()` reads it where `SLIPWAI_ACP` is unset. Nothing else changes: a
  project that never flips it runs its captains in the print mode it always did. Fragment, MINOR.

### 22.8 Install from the settings page — M

- An agent whose manifest says `npx` needs only Node on PATH, and is launched, not installed. One whose
  manifest is a binary archive is fetched for this platform, its sha256 checked, unpacked under
  `~/.slipwai/agents/<key>/` and launched from there. Sign-in is `initialize` answering `authMethods` and
  the board calling `authenticate`, or running the `terminal` method's command as a board step with its
  output on the page. Where the machine lacks Node for an `npx` package, or the platform has no archive,
  the page shows the one line to run and says why. Nothing here installs the board, Python, Docker or a
  cloud target; section 6 of the prototyping plan stands. Fragment, MINOR.
- **Pulled down without a word asked.** Asked on 2026-11-05, when the first `npx` launch had to fetch its
  package: "can we ensure dependencies like this are pulled down automatically?" They are — `npx --yes`
  fetches with no prompt and caches — and two things make it unfelt: a *Make ready* step on the settings
  page that does the fetch ahead of the first conversation with its output shown, so the first turn is
  not also a download; and the client's handshake ceiling of five minutes for a package launch
  (`acp.FETCHING`), the floor under a slow line. Where Node is absent the page prefers an agent
  distributed as a binary over one that needs it, and says why.

## 5. What this plan does not do

- It does not change the brief contract, the start page, `slipwai generate`, or the toolkit's headless
  path. A project with a harness that has no `acp` row runs every stage as it does today.
- It does not route models: the agent offers what it offers, and the board sets one of those. The
  model-providers requirements stand beside this, untouched.
- It does not make the board reachable without a terminal. 22.8 is the first step toward that and no more.
- It does not vendor the protocol's SDK or any package.

## 6. Open points

- **Whether the Claude adapter honours `loadSession`.** Its manifest is read, its capabilities are not
  until 22.6; where it does not, the first page on Claude starts a new session after a restart and says so.
- **Permission option ids are the agent's.** The policy picks by `kind`, `allow_once` for a write inside
  the working directory; an agent whose options carry no `allow_*` kind gets the card.
- **The toolkit's `harness.py` and the keel's share a name and not a file.** 22.2 and 22.7 touch both; the
  registry is the one source they read.
