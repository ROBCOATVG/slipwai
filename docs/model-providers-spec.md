# Specification: any model, any provider, every harness

The specification for [model-providers-requirements.md](model-providers-requirements.md), written as the
`specification` skill asks: one story in its owner's words, rules in domain language, each with concrete
examples, open questions attached where they arise, acceptance criteria distilled from the examples, and
candidate vocabulary. The requirements say *what the keel must do*; this says *what a person sees happen*,
and every example below is either something a run on 2026-11-04 showed or a value a test can check.

**Round 1, agent-drafted, 2026-11-04.** The conversation that produced it was the session of 2026-11-03 and
2026-11-04 with the owner, whose answers are taken as given: support local and hybrid models; a router is the
way to go; open models are first-class; Microsoft Foundry is the provider in heavy use soon; and, asked
whether to ship the router-less part alone, *"no, I want all."* The questions it could not answer are parked
with the owner and a date. The map holds 34 rules and 63 examples, which the skill reads as too big for one
story, so it is split into seven child stories in the order they can be built. Round 2 is the owner's review.

## The story

> As a project owner, I choose which model — from any provider, local, hosted open, or cloud frontier — runs
> each stage of the ladder, on whichever harness my team uses, so that cheap stages run cheaply, judgement
> stays on the strongest model, code can stay inside our tenant or on our machines, and I can see on every
> run which model did what.

**What exists today.** `.specify/models.json` maps each stage to a role and each role to an identifier per
harness; nothing in the keel names a provider. The session inherits whatever provider the shell was set up
for, and a delegated stage reaches only models on that provider.

**What good looks like.** The owner opens the board's Models tab, picks a provider for the whole run and a
model per role, sees beside each pick whether the installed harness can carry it, and runs. Every stage line
names its model and provider, `check-agents` refuses what cannot work before anything is spent, preflight
proves each provider answers and calls a tool, and the benchmark records what actually ran.

## The map

```yaml
story: Choose which model, from any provider, runs each stage, on any harness, and see what ran.

children:

  - story: S1. Declare providers and map roles to them
    rules:
      - rule: A project declares a provider once, by the format it speaks, where it is, and how it signs in.
        examples:
          - "`providers.local` = api openai-chat, url http://127.0.0.1:11434, context 65536, concurrency 1, auth none."
          - "`providers.foundry` = api anthropic, auth entra, deployments {claude-haiku: <deployment name>}; no key anywhere in the file."
          - "A provider row with `token_env: OLLAMA_KEY` writes the variable's name, never its value, into every file it touches."
      - rule: A project that declares no provider behaves exactly as it does today.
        examples:
          - "A project generated before this change passes `make check-agents` unchanged after `slipwai migrate`."
          - "`make agents` on that project writes byte-identical projections before and after the upgrade."
      - rule: A role names a model in the spelling the installed harness can say; the keel refuses one it cannot.
        examples:
          - "Claude Code, `roles.claude.fast = haiku` is accepted; `roles.claude.fast = local-qwen` is refused: the Agent tool takes only opus, sonnet, haiku or fable (2.1.306, run 2026-11-04)."
          - "opencode, `roles.opencode.fast = local/qwen3.5:9b` is accepted as written."
          - "Cursor, any value but `host` is refused: Cursor chooses from its own catalogue and cannot be routed."
      - rule: A role declares the least it needs, and a model that falls short is refused before a run.
        examples:
          - "`requires.fast = {context: 64000, tools: true}`; a provider model with context 32768 is refused, naming `context`."
          - "The same model at context 65536 with tool calling is accepted."
      - rule: Every claim about a harness or provider carries a source and the date it was read.
        examples:
          - "A registry `endpoint` row without `source` fails `make check-agents`."
          - "Claude Code's `subagentModel.identifiers` reads `an alias: opus, sonnet, haiku, fable`, sourced to the 2026-11-04 run, not `or a model id`."
    questions:
      - "Licences: record only, act on nothing? (owner, 2026-11-11)"
    acceptance criteria:
      - "Given a project with no `providers`, when the keel is upgraded, then projections and `check-agents` are unchanged."
      - "Given a role mapped to a model the installed harness cannot name, when `make check-agents` runs, then it fails naming the role, the value and what the harness takes."
      - "Given a provider with a credential, when any projection is written, then no file contains the credential's value."

  - story: S2. Run the whole ladder on one provider, with no router
    rules:
      - rule: The run's own provider is a setting, and the captain points the harness at it with that harness's own variables or flags.
        examples:
          - "Claude Code, `cruise.json provider: foundry` sets CLAUDE_CODE_USE_FOUNDRY=1, ANTHROPIC_FOUNDRY_RESOURCE and the three tier variables to deployment names."
          - "Claude Code, `provider: local` sets ANTHROPIC_BASE_URL=http://127.0.0.1:11434, ANTHROPIC_AUTH_TOKEN=ollama, an empty ANTHROPIC_API_KEY, and every tier variable to qwen3.5:9b."
          - "Codex, `provider: local` runs `codex exec --oss --local-provider ollama -m qwen3.5:9b`."
      - rule: Several models on the run's provider need no router.
        examples:
          - "Foundry run, strong = host (Opus deployment), fast = haiku (Haiku deployment): accepted, no router, one resource."
          - "Anthropic run on a claude.ai login, fast = sonnet: accepted, as today."
      - rule: A cloud provider is addressed by pinned deployment names, never a bare alias.
        examples:
          - "Foundry row with `deployments` missing `haiku`, fast = haiku: refused; Claude Code would otherwise send it to its built-in default, which can lag the account."
          - "A deployment named team-opus-prod for claude-opus-4-8 projects `modelOverrides` so the 1M window is recognised."
      - rule: A provider signed in by cloud identity is checked before the first stage, not at the first request.
        examples:
          - "Foundry with auth entra on a machine with no `az login` and no managed identity: preflight fails, `credential chain does not resolve`, and nothing runs."
          - "A captain on an Azure VM with a managed identity passes the same check with no key in the environment."
      - rule: The run says, once, where it is running and what it gives up there.
        examples:
          - "`cruise: host on Microsoft Foundry · hosting Azure · loses /logout`."
          - "`cruise: host on Ollama on this machine · unproven: no feature run end to end · loses prompt cache, hosted web search`."
      - rule: A provider that can serve only so many sessions limits the fleet to that many.
        examples:
          - "full-ahead (5 boilers) on a provider with concurrency 1 runs one session, and the preset line says why."
          - "A Foundry deployment with a rate quota under the preset's throughput is told once that provisioned throughput is assumed."
    questions:
      - "Where does a Foundry deployment's rate come from: read from Azure, or typed into the row? (owner, 2026-11-11)"
      - "Experiment 4, needs a Foundry resource: does hosted web search work through Foundry? (owner, 2026-11-18)"
    acceptance criteria:
      - "Given `provider: foundry` and three pinned deployments, when /cruise runs one slice, then every stage line names a Foundry deployment and no request reaches api.anthropic.com."
      - "Given `provider: local`, when a feature runs, then the session transcript records no Anthropic request."
      - "Given an entra provider and no credential, when preflight runs, then it refuses before the first stage and names the check."

  - story: S3. Send each delegated stage to its own provider on opencode, with no router
    rules:
      - rule: On opencode the agent file names provider and model, so each delegated stage reaches its own provider directly.
        examples:
          - "Host on local/qwen3.5:9b; sail-fast-stub's file names stubprov/stub; the sub-agent's request landed on the stub (run 2026-11-04, 2a)."
          - "sail-fast-local's file names local/qwen3.5:9b; the sub-agent ran the allowed command and wrote the file (2b)."
      - rule: The captain closes standard input on an opencode run.
        examples:
          - "`opencode run …` with an open pipe for input sent no request for ten minutes; `< /dev/null` answered at once."
      - rule: An unattended opencode run gets an allowlist, never approve-everything.
        examples:
          - "`opencode.json permission = {\"*\": \"deny\", \"task\": \"allow\", \"bash\": {\"*\": \"deny\", \"<the stage's commands>\": \"allow\"}}`; the host's attempt at another command was refused as `Permission denied: shell`."
          - "`--auto` is never passed."
      - rule: A provider block is projected, stamped and never committed.
        examples:
          - "`make agents` writes `provider.local` into opencode.json from `providers.local`; editing it by hand is reported by `check-agents` as drift."
    acceptance criteria:
      - "Given opencode, host on Anthropic and fast = local/qwen3.5:9b, when one slice runs, then benchmark.md records implement-shipwright on local and specify on the host, with no router."
      - "Given an opencode run started by the captain, when it starts, then standard input is closed and permissions are the projected allowlist."

  - story: S4. Route across providers on Claude Code and Codex
    rules:
      - rule: A router is an extension the team elects and runs; the keel writes its configuration and checks it, and never starts it.
        examples:
          - "`./init --extension litellm` records the election; `make agents` writes `.slipwai/router.yaml`; `make preflight` fails with `router not listening on 127.0.0.1:4000` when it is down."
          - "LiteLLM is pinned to 1.106.2 (released 2026-10-21); 1.108.0, released the day of the test, was skipped."
      - rule: On Claude Code a role on another provider fills an alias slot, and the router sends that slot where it belongs.
        examples:
          - "fast = local:qwen3.5:9b fills the haiku slot: ANTHROPIC_DEFAULT_HAIKU_MODEL=local-qwen; a Sonnet host delegated with model haiku and the sub-agent ran on the local model (3b, 2026-11-04)."
          - "fast = local and review = Anthropic Haiku: review is refused, `the haiku slot already holds qwen3.5 9B. One model per alias`."
          - "With the haiku slot local, Claude Code's own background requests went local too, and the turn line says so once."
      - rule: The caller's own Anthropic login rides through to Anthropic and reaches no other provider.
        examples:
          - "Claude Code on a claude.ai Max login, only ANTHROPIC_BASE_URL set: `claude auth status` stayed claude.ai / max; requests succeeded; the router held no Anthropic key."
          - "Every request the stand-in local server received carried no Anthropic credential in any header."
      - rule: The client signs in to the router by its own header, never Authorization.
        examples:
          - "ANTHROPIC_CUSTOM_HEADERS=\"x-litellm-api-key: $SLIPWAI_ROUTER_KEY\"; Authorization carries the claude.ai login."
          - "With the router key in Authorization instead, Anthropic would receive the router key; that configuration is never projected."
      - rule: On Codex the stage brief names the model to spawn with; agent files cannot choose a provider.
        examples:
          - "Codex host on local-qwen called spawn_agent with model local-stub; the sub-agent's transcript records local-stub (5c)."
          - "A project agent file's model did not reach the spawned agent in 0.152.1 (5b); Codex's docs say model_provider cannot be set per agent."
      - rule: A route to a server that speaks only chat is declared with a prefix that translates.
        examples:
          - "ollama_chat/qwen3.5:9b answered Codex's Responses calls; hosted_vllm/stub received them untranslated and Codex retried about 30 times."
          - "Preflight sends one request in the harness's own format to each route and fails the one that cannot answer it."
    questions:
      - "Azure estates: elect API Management's AI gateway by default instead of LiteLLM? (owner, 2026-11-11)"
      - "Codex on a ChatGPT plan: accept a router that holds its own ChatGPT sign-in, or require an OpenAI API key? (owner, 2026-11-11)"
      - "Keep local in the haiku slot (background requests follow), or reserve another alias for routed models? (owner, 2026-11-11)"
      - "Codex agent files: re-test 5b with the user's own config loaded before relying on spawn-by-name alone? (owner, 2026-11-18)"
    acceptance criteria:
      - "Given Claude Code on a claude.ai login, strong = host and fast = local, and the router elected, when one slice runs, then the host's requests reach Anthropic on the subscription and implement-shipwright's reach Ollama, and benchmark.md names both models."
      - "Given the same mapping and no router, when check-agents runs, then it refuses fast, naming the run's provider and the router."
      - "Given Codex and the router, when the brief spawns implement-shipwright with model local-qwen, then the sub-agent's transcript records local-qwen."

  - story: S5. Treat open models as first-class, and keep their weaknesses visible
    rules:
      - rule: A delegated stage's brief says its tools must be called.
        examples:
          - "Plain brief: qwen3.5:9b answered `hybrid-ok` with 0 tool uses and wrote nothing; the host caught it on disk."
          - "Brief with `You must call the Bash tool; do not answer from memory`: 3 of 3 runs called the tool and wrote the file."
      - rule: Preflight's tool-use smoke test passes only when a tool was called, not when an answer came back.
        examples:
          - "A model that replies with the expected text and no tool call fails the smoke test."
      - rule: A local model is offered for fast, and warned against for judgement roles and the host.
        examples:
          - "Selecting qwen3.5:9b for review shows `small local models fumbled tool names in tests; keep judgement roles on the host`."
          - "The 9B host picked the wrong delegation tool or argument before succeeding: 3 tries in 2a, 6 in 2b."
      - rule: The serving stack is asked for the context a role needs.
        examples:
          - "Ollama started with OLLAMA_CONTEXT_LENGTH=65536 for a role requiring 64k; a stack that cannot be told is named in the stage line."
      - rule: What a provider gives up is said, not discovered.
        examples:
          - "Ollama row: `loses prompt cache, hosted web search`; printed once per run."
    questions:
      - "Experiment 1, not yet run: does a local model drive a whole ladder unattended? Gates advertising the air-gapped case. (owner, 2026-11-18)"
    acceptance criteria:
      - "Given a model that answers without calling a tool, when preflight runs, then the smoke test fails."
      - "Given every delegable stage's brief, when it is read, then it states that the stage's tools must be called."

  - story: S6. Record what ran, and prove each combination once
    rules:
      - rule: Every stage records the model and provider that actually ran, read from the transcript.
        examples:
          - "Claude Code modelUsage named claude-sonnet-5-5 and local-qwen in one session; benchmark.md records both against their stages."
          - "A Foundry model-router response without routing metadata records `model-router` and says the underlying model was not read."
      - rule: Proof is per harness, provider and model, with the exact build.
        examples:
          - "`proven: Claude Code 2.1.306 · Ollama 0.40.14 · qwen3.5:9b q4 · feature <name> · 2026-11-18`."
          - "A combination nobody has run end to end prints its unproven line once per run."
      - rule: Token figures are split by provider and by cache, so a local run is not counted as a saving it did not make.
        examples:
          - "Host 72,576 input tokens mostly cached, local sub-agent 8,318 uncached: the board shows the two separately."
    acceptance criteria:
      - "Given a hybrid slice, when it finishes, then benchmark.md records each stage's model and provider from the transcript."
      - "Given an unproven combination, when a run starts, then it prints the unproven line once, naming the combination."

  - story: S7. Choose it all on the board's Models tab
    rules:
      - rule: The Models tab shows what the installed harness can carry, before the owner chooses.
        examples:
          - "Claude Code: names four aliases, destination once per session, claude.ai login relayed, tested 2026-11-04."
          - "Cursor: models from Cursor's catalogue, destination not settable, every non-host choice disabled with the reason."
      - rule: Every choice shows check-agents' verdict beside it, refusals before warnings.
        examples:
          - "Claude Code, run on Anthropic, fast = qwen, no router: `refused: Claude Code sends every sub-agent to the session's endpoint… Elect the router`."
          - "Same, run on Ollama: accepted, with the warning that the host itself is now a 9B model."
      - rule: A choice on the page writes the same file the command writes.
        examples:
          - "Choosing fast = haiku on the page runs `models.py --set claude.fast=haiku`; the page and `make models` then agree."
      - rule: The page previews the files make agents would write, and updates as choices change.
        examples:
          - "Electing the router adds `.slipwai/router.yaml` with a route for local-qwen, and the captain's command gains ANTHROPIC_BASE_URL and ANTHROPIC_CUSTOM_HEADERS."
      - rule: Preflight runs from the page, per provider.
        examples:
          - "Foundry card: credential chain fails, deployments pinned passes, tool-use smoke test waits on the credential."
    acceptance criteria:
      - "Given the Models tab, when the owner picks a mapping check-agents would refuse, then the page shows the same refusal text before anything is saved."
      - "Given a choice saved on the page, when `make models` runs, then it prints the same mapping."

questions:
  - "Cursor: test the IDE's own override-base-URL setting, or declare Cursor unroutable? (owner, 2026-11-11)"
  - "When the router is elected, does `make arrive` offer to start it for a person at a laptop, given the keel never starts it unattended? (owner, 2026-11-11)"

candidate terms:
  - "provider: where a request goes; declared once in models.json by format, place and sign-in."
  - "run provider: the provider the whole run's session is pointed at (cruise.json `provider`); the no-router lever."
  - "router: an elected extension serving every format the installed harnesses speak and routing by model name."
  - "slot: one of Claude Code's four aliases, filled by a model on another provider through the router."
  - "nameable: what a harness lets a sub-agent ask for: aliases, any name, provider/model, or a catalogue."
  - "grain: whether a harness chooses a destination per session or per agent."
  - "login relay: the router passing the caller's own subscription login to that vendor and to no one else."
  - "proven combination: harness, provider and model, at exact versions, run end to end by a captain once."
  - "routed name: the model name a harness asks for that the router maps to a provider, such as local-qwen."
```

## Acceptance criteria for the whole

Distilled from the children; each is a check a run or a test can make.

1. A project that declares no provider sees no change after the upgrade: byte-identical projections, an
   unchanged `check-agents`.
2. A whole run can be pointed at Foundry or a local provider with no router, and its transcript shows no
   request to any other provider.
3. On opencode, each delegated stage reaches the provider its agent file names, with no router.
4. On Claude Code and Codex, a cross-provider hybrid works through the elected router, the caller's
   Anthropic login reaches Anthropic and nothing else, and without the router the same mapping is refused
   before a run.
5. Cursor's limits are said in words, on the page and by `check-agents`, and nothing is projected that would
   silently do nothing.
6. Every stage records the model and provider that ran, and every combination nobody has proven says so
   once per run.
7. Everything above can be chosen and seen on the board's Models tab, which writes through the same command
   a person would type.

## The split

| Child | Builds on | Requirements it sets |
|---|---|---|
| S1. Declare providers and map roles | none | R1–R7, R29, R36 |
| S2. One provider for the whole run | S1 | R15–R18, R34, R38, R39, R41 |
| S3. Per-stage provider on opencode | S1 | R8 (opencode), R12–R14, R31, R37 |
| S4. Route across providers | S2, S3 | R19–R24, R30 |
| S5. Open models first-class | S1 | R31–R35, R23's smoke test, the brief rule |
| S6. Record and prove | S2, S3 | R10, R25–R27, R32, R33, R40 |
| S7. The Models tab | S1–S4 | R42 |

S2, S3 and S5 can run in parallel fairways once S1 merges. S4 needs S2's per-session environment and S3's
projection. S7 goes last because it fronts all of them, and the prototype stands in for it until then.

## Round 2

The review page is generated from this map by the skill's template and sent to the owner. Feedback comes
back as answers and new questions, never as silent edits, and the page is regenerated until a round
changes nothing. Then each child goes to `story-splitting` and onto a chart under `docs/charts/`.
