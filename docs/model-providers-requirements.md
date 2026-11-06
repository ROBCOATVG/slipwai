# Model providers and routing: requirements

A requirements document for letting a project run any stage of `/sail`'s ladder on any model from any
provider — Anthropic, OpenAI, a local Ollama or vLLM, a cloud model behind a gateway — with the choice
declared once in the project, projected into whatever harness is installed, and reported stage by stage the
way the model already is. Drawn on 2026-11-03 from the code as it stands at 2.0.2.dev0 and from the harness
documentation read that day; every external claim below carries the date it was read.

**The principle the document serves:** slipwai never calls a model. It drives a coding-agent harness and
hands it strings, and everything it says about what ran is read from the harness's own transcript rather
than asked. A provider is one more string to hand over and one more fact to read back. The keel owns how
each harness is pointed at an endpoint and what each stage asked for; a router owns which provider answers;
nothing in between is guessed, and a stage that could not switch says so in words.

## 1. The words this document uses

- **Provider** — where a request goes: Anthropic's API, OpenAI's, an Ollama on this machine, a vLLM on a
  tailnet, a cloud model behind a gateway. Today the keel has no word for it: the provider is whatever the
  harness's own environment says.
- **Endpoint** — a base URL a harness can be pointed at, in the one API format that harness speaks.
  Claude Code speaks the Anthropic Messages format; Codex speaks OpenAI's Responses format; opencode and
  most of the rest speak OpenAI's Chat Completions format.
- **Router** — one process exposing every format the installed harnesses speak, choosing a provider by the
  model name a request carries, with fallbacks and usage logging. LiteLLM and Bifrost are the two candidates
  read. The router is an **extension** in the keel's vocabulary: dev tooling elected into a project at
  `./init --extension`, the way the code index is, never a dependency of the keel.
- **Role** — `strong`, `fast`, `review`, `decide`: what `.specify/models.json` keys a stage by today.
- **Identifier** — what a role maps to for one harness: an alias for Claude Code, an OpenAI id for Codex,
  `provider/model` for opencode, `host` for the session's own model, `null` for not mapped. After this
  document an identifier may be **provider-qualified**: `local:qwen3.5`, naming a row of the new
  `providers` table.
- **Host** — the model the session running `/sail` or `/cruise` itself is on. `strong`, `review` and
  `decide` map to it by default.
- **Proven** — a harness a captain has driven through a feature end to end. Today a property of the harness
  row; after this document a property of the pair, harness and provider.

## 2. Where things stand today

A model is chosen in three places, and the provider in none of them.

| Where | What is chosen | How it reaches the harness |
|---|---|---|
| The captain's session | the model `/cruise` runs on | `cruise.json` `model`, through the registry row's `modelFlag` (`harness.py` `model_flags`) |
| Each delegated stage | the model for implement, mutation, review and the rest | `models.json` role, resolved by `models.py` before the stage; applied through the Agent tool's `model` on Claude Code, or written into the projected agent file by `project.py` on opencode, Codex, Cursor, Copilot and Gemini |
| Afterwards | which model ran | `message.model` and token usage read from the Claude Code or Codex transcript by `benchmark.py` |

The session inherits the parent environment minus every harness's session variable plus the row's
`headless.env` (`harness.py` `child_environment`). So a shell already pointed at Bedrock, Vertex or a gateway
carries the captain there, and the keel neither knows nor says.

Two consequences shape everything below:

- **opencode can already do a per-stage hybrid**, because its identifier is `provider/model` and its agent
  file carries one per type. The keel writes it without knowing a provider was chosen.
- **Claude Code and Codex cannot**, without a router. Every sub-agent in a Claude Code session shares the
  session's `ANTHROPIC_BASE_URL`; the Agent tool's `model` parameter changes the name, not the destination.
  Codex's `model_provider` is likewise per session.

## 3. Goals

1. A project owner declares providers once, in `.specify/models.json`, beside the roles that already exist,
   and maps any role on any harness to a model on any declared provider.
2. The two stages whose inputs are fully on paper, `implement-shipwright` and `mutation-shipworm`, can run
   on a local or cheaper model while `strong`, `review` and `decide` stay on the frontier model. This is the
   **hybrid**, and it is the cost case.
3. A whole ladder can run on a local provider with nothing leaving the machine. This is the **air-gapped**
   case, and it is the adoption case: a brownfield repository that cannot be sent out.
4. Every harness the registry records an endpoint mechanism for can be routed, through one projected router
   configuration, so adding a provider is a table row and adding a harness is a registry row.
5. Which model and provider ran each stage is read from the transcript and recorded by `benchmark.py`, so
   the hybrid is a measured hypothesis against the 2.0 target of a median at or below 64M input tokens per
   accepted slice, not a belief.
6. Open-weight models, served locally or by a hosted provider, are first-class: a role can name one on any
   routable harness, and what they bring that Claude does not — a different API format, a context window
   that has to be asked for, tool calling that varies by serving stack, no prompt cache — is handled in the
   table and the projection, never left to the person to discover mid-run.

## 4. Non-goals

- **No routing logic in the keel.** Fallback from a local model to Claude when the local one stalls is the
  router's `fallbacks`, projected from the table; the captain never decides it at run time.
- **No bundled router.** The keel elects one and writes its configuration. Running it is the team's.
- **No hidden hybrid.** On a harness whose sub-agents cannot name a destination, a provider-qualified
  identifier without the router extension elected is refused by `make check-agents`, with the reason.
- **No change to the language or frontend protocol.** Everything here is a generated file `slipwai migrate`
  merges, a registry row and an extension; it is an additive 2.x MINOR under `docs/backend-protocol.md`
  *Compatibility*.
- **No new harness rows invented.** An `endpoint` row is read from that harness's documentation and dated,
  or absent, exactly as `subagentModel` and `headless` are today.

## 5. Requirements

Numbered so a slice can name the ones it sets. *Must* is a requirement; *should* is a preference a slice may
trade with a reason in its plan.

### 5.1 The table: `.specify/models.json`

- **R1.** The table gains a `providers` object. Each row has `api` (`anthropic`, `openai-chat` or
  `openai-responses`, the format the provider itself speaks), `url`, `auth` (`api_key` with `token_env`
  naming the variable that carries it; `bearer`; or `entra`, a cloud identity's default credential chain,
  with no key anywhere), an optional `concurrency` (how many sessions it serves at once; absent means
  unbounded) and `rate` (the tokens and requests per minute a deployment is quota'd at), and `proven` with
  `provenWhy`, `false` and "no feature has been run end to end on it" as seeded. A provider that names its
  models by deployment carries `deployments`, model id to deployment name, and `check-agents` refuses a bare
  alias on it: a cloud provider has no startup model check, and an alias there resolves to a harness's
  built-in default, which can lag what the account has.
- **R2.** A role identifier may be provider-qualified, `<provider>:<identifier>`, where `<provider>` is a row
  of `providers`. A bare identifier keeps today's meaning: the harness's own provider.
- **R3.** `models.py --check` refuses a qualified identifier whose provider is not declared, and refuses one
  on a harness whose sub-agents cannot name a destination (section 5.2) unless the router extension is
  elected, saying which of the two it is. `make check-agents` runs it as it does today.
- **R4.** `models.py --set claude.fast=local:qwen3.5` writes a qualified identifier, and
  `--set providers.local.url=…` writes a provider field, so `/model-delegation-settings` remains the one
  answer to "which model runs implement".
- **R5.** `models.py <stage>` prints the provider beside the model in the line `/sail` reads before a stage,
  or the words for why no provider was chosen. The stamp a projected agent file carries says the same.
- **R6.** `slipwai migrate` merges a newer factory's `providers` seed over an edited table rather than
  replacing it, as it does for `roles` today. A table without `providers` is a table with none, not a
  finding, so every project written before this passes `check-agents` unchanged.
- **R7.** The seed declares no provider. A generated project behaves exactly as today until somebody adds
  one.

### 5.2 The registry: `scripts/agents/registry.json`

- **R8.** A harness row may carry `endpoint`: `format` (which API format it speaks: `anthropic`,
  `openai-chat`, `openai-responses`), `how` (the mechanism, in words), `where` (the variables or the file and
  key), `grain` (`session` or `subagent`: whether a sub-agent of one session can be sent to a different
  destination by the name it asks for), and `source` with the date read. Claude Code: `ANTHROPIC_BASE_URL`,
  `ANTHROPIC_AUTH_TOKEN` and the per-tier model variables, grain `session`. Codex: `model_provider` and a
  `model_providers.<key>` block with `base_url` and `wire_api`, grain `session`. opencode: a `provider`
  block in `opencode.json`, grain `subagent`. Grain describes destinations, not models: a provider hosting
  several models behind one endpoint allows per-sub-agent model choice on any harness, and R3 refuses only
  a mapping that needs a second destination.
- **R9.** A row without `endpoint` is a harness that cannot be routed. `models.py` says so, in words, where
  a qualified identifier is mapped on it; nothing falls through to a guess.
- **R10.** `proven` moves from the harness row alone to the pair. The registry keeps the harness's row; the
  provider's row in `models.json` carries its own; the unproven line (`harness.py` `unproven_line`) prints
  once per run for whichever of the two is unproven, naming it.
- **R11.** The registry does not record router products. Which router is elected is the extension's business
  (section 5.5); the registry records only how each harness reaches an endpoint.

### 5.3 Projection: `make agents`

- **R12.** `project.py` writes, per installed harness, what that harness's `endpoint` row says it needs for
  every provider a role on that harness names: for opencode, a `provider` block in `opencode.json` and
  `model: <provider>/<identifier>` in the agent file's frontmatter; for a `session`-grain harness, nothing
  per sub-agent, and the identifier passes through unchanged for the router to read.
- **R13.** Every projected provider block is stamped and gitignored, re-derived by `make agents` and
  `slipwai migrate`, and `check-agents` reports a drifted one, exactly as agent files are handled today.
- **R14.** A projection never carries a credential. `token_env` names a variable; the value is read at
  session start by the captain and by the router, never written to a file the keel generates.

### 5.4 The captain's session

- **R15.** `.specify/cruise.json` gains `provider`, free text or null, beside `model`: the row of
  `providers` the ladder's own session runs on. Null is the harness's own provider, which is a fact about
  the run and is said in the turn's line rather than inferred.
- **R16.** `harness.py` `child_environment` gains a third source after `headless.env`: what the installed
  harness's `endpoint` row says points it at the session's provider — for Claude Code the base URL, the
  auth token read from `token_env`, and the three tier variables so the harness's own background requests
  (Haiku-class by name) resolve to something the provider serves. For a harness whose `endpoint` is a flag
  rather than a variable, a `providerFlag` on its headless row, substituted the way `modelFlag` is.
- **R17.** The captain's turn line names model and provider for the session, and the stage line names both
  for each delegated stage, so a reader can tell "the harness's own default ran" from "routed to local" without
  opening a transcript.
- **R18.** The telegraph clamps `boilers` to the smallest `concurrency` among the providers the run can
  reach, and says so in the line that names the preset. A home GPU declared `concurrency: 1` gets one
  session under `full-ahead`. A provider's `rate` clamps the same way, and a fleet at `full-ahead` on a
  quota'd deployment is told, once, that provisioned throughput is what the preset assumes.

### 5.5 The router extension

- **R19.** A router is elected at `./init --extension <router>` and recorded as other extensions are. The
  keel ships the election for one router first (LiteLLM, the one whose Anthropic-format endpoint Anthropic's
  own gateway documentation names), with Bifrost as the second once proven. The elected router must
  translate between the formats the installed harnesses and the declared providers speak (R30); a
  passthrough-only splitter serves the Anthropic-plus-Ollama case and nothing hosted. For an Azure estate
  the election is API Management's AI gateway: it speaks OpenAI chat, Responses and, on v2 tiers, the
  Anthropic Messages API, under Entra, with per-developer token limits and quotas (`llm-token-limit`) and
  metrics to Azure Monitor — so the bunker is enforced server-side and the team runs nothing new. Its
  forwarding rules are still the team's to keep current with each harness release (R24).
- **R20.** `make agents` writes the router's configuration from `models.json`: one model entry per distinct
  identifier any role names, mapped to its provider's `api`, `url` and credential variable; one entry per
  tier name Claude Code asks for by itself; `fallbacks` from an optional `fallback` field on a provider row.
  Written to `.slipwai/router.yaml`, beside the project's other derived state, and the router is started
  with that path. Never under `.specify/`: every slipwai file there is committed and edited by a person, and
  a projection is neither. Stamped, gitignored, re-derived.
- **R21.** With the router elected, every installed `session`-grain harness is pointed at the router by
  `child_environment` (R16) in its own format, and the per-stage hybrid on Claude Code and Codex works
  through the same `models.py` line as on opencode.
- **R22.** The router must pass Anthropic-bound requests through with the caller's own credential and the
  `anthropic-beta` OAuth capability header forwarded, injecting a key only for other providers, so a
  claude.ai subscription keeps billing the Anthropic traffic. If the elected router cannot do that per route,
  the keel prints once per run that Anthropic traffic through the router is billed per token to the key the
  router holds. (Anthropic, *Other LLM gateways* and *Subscriptions and gateways*, read 2026-11-03.)
- **R23.** `make preflight` checks that the elected router is listening at its URL and serves every format
  the installed harnesses speak, and names the one it does not. For an open provider it also checks that
  the named model is present, that its context meets the role's minimum (R36), and that a one-call tool-use
  smoke test passes, and names the check that failed. For an `entra` provider it checks the credential
  chain resolves before the first stage, so a captain on a VM without a managed identity is refused at
  preflight rather than at its first request.
- **R24.** The keel prints, once at election, Anthropic's own position: it does not support routing Claude
  Code to non-Claude models through any gateway, and a gateway must forward each release's new capabilities
  or the corresponding features break. Said once, not refused.

### 5.6 Measurement and proof

- **R25.** `benchmark.py` records, per stage, the provider beside the model where the transcript's
  `message.model` carries the routed name, and `provider=` from the stage line only where no transcript can
  say — the same rule it applies to `model=` today.
- **R26.** The fleet board's token figures distinguish Anthropic-billed from other tokens where the record
  does, so the 64M target stays comparable and a run on a free local provider is not counted as a saving it
  did not make.
- **R27.** A pair becomes `proven` by the same act a harness does: a captain runs a feature end to end on it,
  and the row is edited with the date and the feature.

### 5.7 Prose and checks

- **R28.** `docs/agent-harnesses.md` gains a section *Providers and routing* saying the three cases
  (native on opencode, whole ladder on one provider, router), the `endpoint` row, and the subscription rule.
  `commands/sail.md` *Who runs each stage* names the provider in its example line. `GLOSSARY.md` gains the
  words of section 1 through the plan, as every word does.
- **R29.** Every number and claim about a harness or router in the registry and in prose carries a source
  and a date read, and `check-agents` fails a row that has `how` without `source`.
- **R42.** The board gains a **Models** tab, and the work must ship it, as the clickable prototype of
  2026-11-04 draws it (the *Models and providers prototype* canvas). It shows, for the installed harness:
  what a sub-agent can name, where its traffic goes, whose login travels and when that was tested; the
  whole run's provider (`cruise.json` `provider`, R15), the no-router lever, with a warning when the host
  itself becomes a small local model; each
  role's model with check-agents' verdict beside it, refusals before warnings; every stage with its role
  and resolved model, the delegated stages' roles changeable in place; each provider with its preflight
  checks run on demand; the router's election, its pinned version and the routes it would serve; and the
  files `make agents` would write, updating as the choices change. A choice made there writes
  `.specify/models.json` through `models.py --set`, so the page and the command cannot disagree.

### 5.8 Open models

Open-weight models are first-class, local or hosted. They differ from Claude in four ways the rest of this
document would otherwise leave to chance: format, context, tool calling and cache. A frontier model hosted on
a cloud provider keeps its cache and most of its features, so R33 and R37 apply to open-model deployments
and not to, for instance, Claude on Foundry (5.9).

- **R30.** A provider row says which `api` it serves natively, and the elected router translates where a
  harness and a provider disagree. Hosted open-model providers — OpenRouter, Together, Fireworks, Groq,
  DeepInfra, as read 2026-11-03 — speak OpenAI's format; Ollama, local and cloud, speaks both. So Claude
  Code reaches a hosted open model only through a translating router, and `check-agents` refuses the
  mapping where no such router is elected, naming the two formats.
- **R31.** A provider row may carry `context`: the window the projection must ask the serving stack for,
  because a locally served open model's default is often far below what a ladder stage needs. The
  projection writes it where the stack takes it — Ollama's per-model context length, vLLM's maximum model
  length — or says it cannot, and the stage line prints the model's context where the row records one.
  Ollama's guidance for Claude Code is at least 64k (read 2026-11-03).
- **R32.** Tool calling is the gate, not a benchmark score. A model that fumbles structured tool use stalls
  the ladder on its first delegate, and tool-call fidelity depends on the serving stack's parser as much as
  on the weights. So `proven` is read for the triple: harness, provider and model. R10 and R27 are read with
  the model as part of what is proven, and a provider row's `proven` names the model it was proven with.
  The provider row and `benchmark.py` record the model tag, quantization and serving-stack version, without
  which a proof says nothing six weeks later.
- **R33.** Open providers mostly have no prompt cache. Their input is re-sent whole every turn and lands in
  `benchmark.py`'s input figure with nothing under cache reads. R26's split by provider is therefore
  cache-aware: the board shows uncached input per provider and never adds an open provider's input to an
  Anthropic figure as though the two cost the same.
- **R34.** Claude Code's own tier requests are mapped to the open model in every open-provider
  configuration the keel writes, session (R16) and router (R20) alike, so a session on an open provider
  never silently asks for a Claude model it cannot reach.
- **R35.** The prose names example open models with the date read and the source, never as a seed:
  Ollama's Claude Code page recommends `qwen3.5` locally and `glm-5.3-flash`, `gemma4:cloud` and
  `kimi-k2.7-code:cloud` hosted (read 2026-11-03). A model's licence is the team's to check; a provider row
  may record `license` as a fact, and the keel reads it for nothing.
- **R36.** A role declares its minimum: `context` in tokens, `tools: true`, and optionally `reasoning`.
  `stages` keeps mapping to role names; the minimums sit under `requires.<role>` in the table, seeded from
  what the ladder's stages actually need — 64k and tool calling for every delegable stage. A model on a
  provider declares what it has, and `check-agents` refuses a mapping that falls short, naming the field.
- **R37.** A provider row may record `loses`: what a harness gives up through it — hosted web search,
  prompt caching, extended thinking, the larger context — read from the provider's documentation and dated.
  The captain's turn line prints it once per run, so a stage that reads documentation unattended is known
  to have lost its tool before it fails to.

### 5.9 Microsoft Foundry

One tenant serves all three model classes this document cares about — Claude through the Anthropic
Messages API, OpenAI models and Foundry's own model router through the Responses API, open-weight models
through an OpenAI-compatible endpoint — under one identity, one bill and private networking. It is the
provider the first real adoptions are most likely to run on, so it gets requirements of its own.

- **R38.** Foundry is three provider rows, by `api`. `anthropic`: Claude deployments, reached by Claude
  Code's own variables — `CLAUDE_CODE_USE_FOUNDRY=1`, `ANTHROPIC_FOUNDRY_RESOURCE`, the three tier variables
  carrying deployment names — with `modelOverrides` projected into `.claude/settings.json` where a deployment
  name differs from its model id, so the 1M window is recognised. `openai-responses`: Azure OpenAI and
  `model-router` deployments, reached by Codex's `model_providers.<key>` with `base_url` ending `/openai`,
  `query_params.api-version` and `wire_api = "responses"`, and by opencode's `azure` provider.
  `openai-chat`: open-weight deployments, whose endpoint shape experiment 4 confirms. The `endpoint` row
  (R8) therefore allows a provider-specific variable set beside the generic one, as Claude Code's
  `allowedProviders` already distinguishes them.
- **R39.** The same-resource hybrid: `strong`, `review` and `fast` as three deployments on one resource,
  no router, on any harness — the Agent tool's `model` parameter and an agent file's `model` are deployment
  names on the same destination. The stage line names the deployment. `ANTHROPIC_DEFAULT_HAIKU_MODEL` is
  always set on a Foundry row, because Claude Code otherwise sends its background requests to the primary
  model there (R34).
- **R40.** `model-router` is a legitimate `fast` identifier on a Responses-grain harness: provider-side
  routing in Cost, Balanced or Quality mode, with the configured subset doubling as the failover set, which
  keeps the keel's no-routing rule intact. `benchmark.py` reads the underlying model from the response's
  routing metadata where it carries one, and otherwise records `model-router` and says the underlying model
  was not read.
- **R41.** The in-tenant case is the air-gapped case's sibling and is said as such: private endpoints,
  data-zone deployments, and a Claude deployment's hosting option — inference on Azure or on Anthropic
  infrastructure — recorded as `hosting` on the row, a fact the turn line prints and the keel acts on
  nothing. `auth: entra` on every Foundry row by default; a captain on an Azure VM authenticates by managed
  identity, which is the unattended case Claude apps gateway cannot serve. `loses` for Claude on Foundry is
  `/logout` and whatever experiment 4 finds.

## 6. Constraints

- **Additive, a 2.x MINOR.** A project that never adds a provider sees no change in behaviour and no new
  finding from any check.
- **Nothing is guessed.** A harness without an `endpoint` row, a provider without `api`, a transcript
  without `message.model`: each is said in words, never defaulted.
- **The keel writes configuration; it runs nothing.** The router is a process the team operates. The keel
  checks it is there (R23) and never starts it.
- **Local inference does not fit the presets.** Ollama's own guidance for Claude Code is a tool-calling
  model with at least 64k context, more for a large repository (read 2026-11-03). A single GPU serves one
  session well. R18 is the only telegraph change; bunker arithmetic is unchanged and local tokens still count
  as work tokens, because the bunker is a throughput lever, not a bill.
- **Unattended runs punish weak tool calling.** The captain's controls (last line, controlled-file diff,
  Stop hook) depend on no model, but a model that fumbles structured tool use stalls the ladder on its first
  delegate. The default role mapping keeps `strong`, `review` and `decide` on the host; the seed moves
  nothing to a provider.
- **Supply chain.** A June 2026 advisory concerned malware in two LiteLLM releases (1.82.7 and 1.82.8,
  per third-party reporting read 2026-11-03; the advisory itself was not read). The election pins a version
  and says which, as the keel pins Spec Kit.

### 6.1 What supporting open models implies

Open models are not one more provider row. The keel is harness-neutral by construction: one canonical set
of skills, commands and agents, projected into whichever of Spec Kit's harnesses `./init` names. What was
written against frontier models is the prose — the stage briefs, the skills, the ladder's instructions —
and open models test that prose, not the projection.

- **The gates become the quality floor.** Today a strong model writes decent code and the gates confirm it.
  With a 30B-class model on implementation, the tests, the mutation score, converge and the fresh-eyes
  review are what stops bad work merging. The design already leans this way; open models make it
  load-bearing. Expect more red-green cycles per example and more retries, which the telegraph's `attempts`
  already bounds.
- **A role says what it needs.** A name is not enough once the model behind it can be anything (R36).
- **Features the ladder relies on go missing.** Ollama's own page says hosted web search and advanced tool
  controls are not fully supported through its endpoint; prompt caching, extended thinking and the larger
  windows go with it. A provider row says what is lost (R37) rather than a stage finding out.
- **Prompts gain a compatibility matrix, held by proof rather than CI.** CI has no GPU. A prose change that
  breaks a smaller model's ability to follow a stage is seen when a captain runs it, and the proven triple
  with its recorded tag, quantization and stack version (R32) is what makes that sighting mean something.
- **The token target stops meaning one thing.** 64M input tokens per slice was a cost proxy for one
  provider with a cache. A local model has no cache and costs hardware time; a hosted open model costs a
  fraction per token and resends everything. The board shows uncached input per provider (R33) and, for a
  local provider, wall time per slice beside it. The bunker stays a throughput lever and stops approximating
  a bill.
- **Concurrency inverts.** Five boilers on one GPU thrash; vLLM batches, Ollama mostly does not. The hybrid
  is the practical shape for most teams: strong stages fanned out on a hosted frontier model, fast stages
  queued on the GPU (R18).
- **Silent failures need preflight rungs.** A model not pulled, a context smaller than the prompt, a
  tool-call parser that does not match the model's template, a quantization that broke tool use. The worst
  is a server truncating a prompt that exceeds its configured context without saying so. R23's three checks
  per open provider exist for these.
- **Privacy improves and shifts.** Local is air-gapped. A hosted open provider has its own retention terms,
  and a router logs every prompt by design. The no-credentials-in-projections rule (R14) extends to
  no-prompts-in-projections; the router's logging is the team's policy to set and the keel's to say once.
- **Licences are facts, not code.** Open-weight is not open-source. The keel records a licence if told one
  (R35) and acts on nothing; checking it is the team's job.

## 7. What is proven first, before anything is built

Three experiments, each a day or less, each answerable with the tooling that exists today.

1. **Whole ladder on Ollama, Claude Code, no keel change.** `ollama launch claude` or the three variables
   by hand, `cruise.json` `model` set to the local name, one generated project, one small feature.
   Question: does any local model drive fourteen stages unattended, and what does `benchmark.md` say ran?
   Answers whether goal 3 is reachable at all and which open models to name in the prose (R35).
2. **Hybrid on opencode, no router.** `roles.opencode.fast = "ollama/<model>"`, host on Anthropic, the same
   feature. Question: does `project.py`'s agent-file model reach the sub-agent, and does the stage line say
   so? Answers goal 2 on the one harness where it is native, and proves the shape of R12.
3. **Subscription through LiteLLM.** Claude Code pointed at a local LiteLLM with one Anthropic passthrough
   route and no Anthropic key, one session. Question: does `/status` show the claude.ai login as the active
   credential, and does the request succeed? Answers R22, and with it whether the cost case holds for a
   subscription user or only for an API-key one.

4. **Claude Code on Foundry, three deployments, one slice.** `CLAUDE_CODE_USE_FOUNDRY=1`, Entra sign-in,
   Opus, Sonnet and Haiku deployments named as the three tier variables, `claude.fast=haiku`. Questions:
   does hosted web search work through Foundry, so the documentation-reading stages keep their tool; does
   a `model-router` response name the model that answered; and what is the endpoint shape of an open-weight
   deployment. Answers R38 to R41 and the `loses` row for Claude on Foundry.

A *no* on the first narrows goal 3 to the cloud-behind-gateway case. A *no* on the third changes R22 from a
requirement to a printed warning and moves the hybrid's economics to API billing. Neither blocks goal 1 or 2.

**Experiment 3, run 2026-11-04: yes, for a passthrough route.** LiteLLM 1.106.2 (released 2026-10-21) on
localhost, Claude Code 2.1.306 signed in with a claude.ai Max subscription, only `ANTHROPIC_BASE_URL` set,
no Anthropic key anywhere. `claude auth status` reported `authMethod: claude.ai`, `subscriptionType: max`
through the proxy; a one-line request and a two-turn request that ran a Bash tool both returned 200 from
`/v1/messages?beta=true`. Three findings for R19 to R23:

- **LiteLLM refuses to start without a master key** in this release. The proxy keeps one; the Anthropic
  routes are marked `auth: false` so the caller sends only its own login.
- **`auth: false` is honoured only on an exact path match.** With one route and `include_subpath`, every
  request fell through to LiteLLM's key lookup with the claude.ai token and failed (`400 No connected db`).
  The projection (R20) must therefore write one route per Anthropic path — `/v1/messages` and
  `/v1/messages/count_tokens` — never a prefix.
- **A passthrough route chooses by path, not by model**, so it proves the subscription survives but not the
  hybrid. Splitting Claude Code's traffic between Anthropic and a local model by model name needs LiteLLM's
  unified `/v1/messages` with a `model_list`, and whether an Anthropic entry there can relay the caller's
  OAuth credential is untested. That is experiment 3b, and R22 stays open on it.

**Experiment 3b, run 2026-11-04: yes. The per-stage hybrid works on Claude Code through one LiteLLM
endpoint, on a subscription.** Same LiteLLM and Claude Code as experiment 3. The proxy's `model_list` sent
`claude-*` to `anthropic/claude-*` with no Anthropic key, and `local-stub` to an OpenAI-chat stub on
localhost standing in for a local model (Ollama is not installed on the test machine, so a real model's
tool calling is still experiment 1's question). Claude Code sent its claude.ai login in `Authorization` and
the proxy's key in `x-litellm-api-key` through `ANTHROPIC_CUSTOM_HEADERS`.

- A Claude request and a two-turn Bash tool turn on the routed endpoint both succeeded; `claude auth status`
  still reported `claude.ai` and `max`.
- A session on `--model local-stub` was answered by the stub.
- A Sonnet host that delegated one sub-task with the Agent tool's `model: haiku`, with
  `ANTHROPIC_DEFAULT_HAIKU_MODEL=local-stub`, ran the host on Anthropic and the sub-agent on the stub, in one
  session. The session's `modelUsage` named both models, so `benchmark.py` can read what ran (R25).
- In every request the stub received, no Anthropic credential arrived in any header. LiteLLM forwards the
  OAuth token only to the Anthropic provider.

Four findings that change the requirements:

- **The Agent tool accepts only the aliases** — sonnet, opus, haiku, fable — in Claude Code 2.1.306. It
  refused `model: "local-stub"`. `registry.json`'s `subagentModel.identifiers` for Claude Code says "or a
  model id", which this build contradicts. So on Claude Code a role's identifier must be an alias, and the
  provider is chosen by mapping that alias's tier variable (R16, R20, R34): `fast` = `haiku` with
  `ANTHROPIC_DEFAULT_HAIKU_MODEL` set to the routed name. The consequence is that one session has at most
  four routable destinations, one per alias, and Claude Code's own background requests follow the haiku
  mapping.
- **The client authenticates to the proxy by `x-litellm-api-key`, never `Authorization`.** That header
  belongs to the caller's Anthropic login. `child_environment` (R16) sets `ANTHROPIC_CUSTOM_HEADERS` from
  the proxy key's variable, and the key is never written to a projected file (R14).
- **A generic `openai/` provider is translated to OpenAI's Responses API**, not chat completions. A local
  server that speaks only chat — vLLM, and Ollama's OpenAI endpoint — must be declared with a chat-format
  provider prefix (`hosted_vllm/`, `ollama_chat/`). The provider row's `api` (R1) decides the prefix the
  projection writes (R20).
- **Credential isolation holds by LiteLLM's design** and is a preflight check worth keeping (R23): the stub
  logged the kind of credential it received on every request, and preflight can do the same with a probe.

R22 is met for LiteLLM 1.106.2, pinned.

**Experiment 3b again with a real local model, run 2026-11-04.** Ollama 0.40.14 (Homebrew), `qwen3.5:9b`
(7.6 GB), served with `OLLAMA_CONTEXT_LENGTH=65536` on a 36 GB Apple-silicon machine; LiteLLM routed
`local-qwen` to `ollama_chat/qwen3.5:9b`. Everything else as above.

| Run | Result |
| --- | --- |
| Whole session on `local-qwen`, one Bash tool task | Ran the command and wrote the file. 2 turns, 15 s. |
| Sonnet host, sub-agent on `local-qwen` via `haiku`, plain brief | Routed correctly, but the sub-agent reported `hybrid-ok` with 0 tool uses and wrote nothing. The host caught it by checking the file. |
| Same, brief saying "you must call the Bash tool; do not answer from memory", 3 runs | 3 of 3 ran the command and wrote the file. |

What it adds:

- **The hybrid works with a real local model** on a subscription, routing and credentials as experiment 3b
  found. The local sub-agent's input was about 8k tokens per call against the host's 73k, with no cache.
- **A small local model will fabricate a tool result** when the brief leaves room to answer from memory.
  It is R32's risk observed on the first try. Two things caught or prevented it: the host verifying the
  result on disk, which is what the ladder's gates do, and a brief that says the tool must be called. The
  delegable stages' briefs (`agents/`) should say so explicitly; that is a prose change the keel owns, and
  R23's tool-use smoke test should check that a tool was called, not only that an answer came back.
- **Background requests follow the haiku mapping**, as predicted: with `ANTHROPIC_DEFAULT_HAIKU_MODEL`
  pointed at the local model, Claude Code's own small requests went there too.

### Experiments 2, 5 and 6: the other harnesses, run 2026-11-04

Same machine, Ollama and `qwen3.5:9b` as above, the stub standing in for a second destination. Each
harness ran in a scratch project with the user's own configuration left untouched.

| # | Harness | Question | Result |
| --- | --- | --- | --- |
| 2a | opencode 2.2.5 | Does an agent file's `provider/model` choose a sub-agent's destination with no router? | **Yes.** Host on `local/qwen3.5:9b`; the sub-agent's file named `stubprov/stub` and its request landed on the stub. |
| 2b | opencode | Does a sub-agent on a local provider do real tool work? | **Yes.** It ran the one allowed command and wrote the file; the host's own attempt at a different command was refused by the allowlist. |
| 5a | Codex 0.152.1 | Does a whole session run through LiteLLM's Responses endpoint on a local model? | **Yes.** Two shell calls, file written, three `/v1/responses` requests. |
| 5b | Codex | Does a project agent file's `model` reach a sub-agent? | **Not shown.** The spawned agent had no role and inherited the host's model. Codex's docs say an agent file cannot set `model_provider` at all. |
| 5c | Codex | Can the host choose a sub-agent's model per spawn? | **Yes.** `spawn_agent` takes `model`, offered from the provider's own model list; the transcripts show host on `local-qwen` and sub-agent on `local-stub`. |
| 5d | Codex | Does a ChatGPT-plan login survive a router? | **No, by code.** LiteLLM 1.106.2 relays a caller's own login for Anthropic only; its ChatGPT provider holds a login of its own from a one-time device sign-in. Not run: it needs a person to sign in. |
| 6 | Cursor CLI 2026.10.22 | Can it be pointed at a router? | **No.** `--endpoint` is Cursor's own RPC service; pointed at a local server it refused a JSON reply (`unsupported content type application/json`). Models come only from Cursor's catalogue. |

Findings that change the requirements:

- **opencode is the one fully native hybrid.** The registry row (`grain: subagent`) is confirmed. Two
  operational facts join it: `opencode run` waits on standard input when it is not a terminal, so the
  captain closes it (a ten-minute hang without); and permissions should be an allowlist in `opencode.json`
  (`"*": "deny"` plus what the stage needs) rather than `--auto`, which approves everything.
- **Codex chooses a model per spawn, not per agent file**, in this build: `spawn_agent`'s `model` takes any
  name the provider lists, so through a router every routed model is offered. The keel's lever on Codex is
  therefore the stage brief naming the model to spawn with, and `[agents].default_subagent_model` for the
  default — not a projected agent file's `model`, which 5b could not show applied. The registry's Codex
  `agentFile.model` claim is unverified and should say so.
- **Codex's own login does not ride a router.** A Codex hybrid with an OpenAI host on a ChatGPT plan needs
  the router to hold its own ChatGPT sign-in, or an OpenAI API key. Either way the router, not the harness,
  carries the credential — a different trust shape from Claude Code's relay, and the turn line says which.
- **A Responses-format harness needs a translating route to a chat-only server.** LiteLLM translated
  Codex's Responses calls for `ollama_chat/` but passed them straight through for `hosted_vllm/`, which the
  chat-only stub could not answer; Codex then retried about 30 times. R20 writes, per provider, the prefix
  that translates for the harness's format, and R23's preflight sends one request in that format.
- **Cursor is `nameable: catalogue`, `endpoint: none`.** The keel cannot route it and says so in words; the
  per-agent model choice it does have is within Cursor's catalogue. The IDE's own "override OpenAI base URL"
  is a different product surface and was not tested.
- **Small local hosts fumble tool names.** The 9B model used the wrong delegation tool or argument before
  getting it right in 2a (three tries), 2b (six) and 5b. A local model is a candidate for `fast`, not for
  the host; the seed keeps `strong`, `review` and `decide` on the host for this reason.

## 8. Acceptance

The work is done when, on a generated project:

- `python3 scripts/agents/models.py --set providers.local.url=http://localhost:11434 opencode.fast=local:qwen3.5`
  followed by `make agents` writes the provider block and agent frontmatter, `make check-agents` passes, and
  `/sail` on one slice records in `benchmark.md` that `implement-shipwright` ran on `local` and `specify`
  on the host — with no router.
- The same `--set` for `claude.fast` is refused by `check-agents` with the reason, then accepted once the
  router extension is elected, and a `/cruise` run on one slice records the same split, with the Anthropic
  stages billed as R22 says and the line printed as R22 says.
- `cruise.json` `provider: local` runs a feature with no request leaving the machine, which the router's
  log (or, without a router, the absence of any Anthropic request in the session's transcript) shows.
- A project that adds no provider produces byte-identical projections and an unchanged `check-agents`
  before and after the keel upgrade.

## 9. Sequence

Five slices, in the order their marks allow. The second is first in value and proves the shape with no
router at all.

| Slice | Sets | Steers by |
|---|---|---|
| 1. The table | R1–R7, R29, R36 | — |
| 2. opencode, native | R8 (opencode row), R12–R14, R25, R28, R31, R32, R35, R37 | 1 |
| 3. One provider per session | R8 (Claude Code and Codex rows), R15–R18, R34, R38, R39, R41 | 1 |
| 4. The router extension | R19–R24, R30 | 2, 3 |
| 5. Proof and the board | R10, R26, R27, R33, R40 | 2, 3 |

Slices 2 and 3 are independent and can run in parallel fairways; 4 needs both because it is the one that
makes a `session`-grain harness do what a `subagent`-grain one does natively.

## 10. Sources

- Anthropic, *Other LLM gateways* (code.claude.com/docs/en/llm-gateway): the unsupported-non-Claude
  statement, the forward-new-capabilities obligation, `allowedProviders`, and *Subscriptions and gateways*
  on which credential is active. Read 2026-11-03.
- Ollama, *Claude Code* integration page (docs.ollama.com/integrations/claude-code): `ollama launch
  claude`, the three variables, tool-calling models, the 64k context guidance. Read 2026-11-03.
- opencode: custom providers through a `provider` block with `@ai-sdk/openai-compatible` and a `baseURL`,
  from third-party guides and anomalyco/opencode issue #6231 on manual model lists. Read 2026-11-03; the
  project's own docs to be re-read when slice 2 opens.
- Codex CLI: `model_provider`, `model_providers.<key>` with `base_url` and `wire_api`, `--oss` with
  `oss_provider`, from third-party guides. Read 2026-11-03. A later guide says that since February 2026
  `wire_api` accepts only `responses`, which settles the dispute between the earlier guides and matches
  Azure's endpoint; to be confirmed from the installed CLI when slice 3 opens.
- Anthropic, *Claude Code on Microsoft Foundry* (code.claude.com/docs/en/microsoft-foundry): the Foundry
  variables, the three authentication methods and the default credential chain, deployment names as tier
  variables, the pinning warning, automatic prompt caching, the 1M window and `modelOverrides`, `/logout`
  unavailable. Read 2026-11-03.
- Microsoft Learn, *Model router in the Responses API* and the Foundry blog on cost-aware workloads:
  `model-router` as a deployment name, Cost/Balanced/Quality, the subset as failover set, routing metadata
  in preview (October 2026). Read 2026-11-03.
- Microsoft Learn, *AI gateway capabilities in API Management*: OpenAI chat and Responses, Anthropic
  Messages on v2 tiers, `llm-token-limit`, Foundry integration. Read 2026-11-03.
- Open-weight models on Foundry — gpt-oss-120b, DeepSeek V3.2, Kimi K2.5, MiniMax M2.5 via Fireworks,
  Llama 4, Mistral Large 3, bring-your-own weights — from the Azure blog and third-party roundups. Read
  2026-11-03; the endpoint shape is unconfirmed and is experiment 4's third question.
- claude-code-router: scenario routing (default, background, think, longContext, webSearch) and
  provider list, from third-party guides. Read 2026-11-03. Not elected: Anthropic format only, one harness.
- LiteLLM and Claude Code: the two-variable setup and a community `fallbacks` example; the 1.82.7/1.82.8
  advisory as reported. Read 2026-11-03.
- This repository: `assets/toolkit/scripts/agents/{harness,models,project,captain,benchmark,telegraph}.py`,
  `registry.json`, `src/slipwai/project/stage_models.py`, `src/slipwai/harness.py`, `docs/slipwai-2-plan.md`
  sections 9 and 11, at 2.0.2.dev0.
