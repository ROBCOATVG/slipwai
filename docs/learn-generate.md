# Learning path: generate a new project

Four sessions: install the command, scaffold a repository, keep the command current, then migrate an
older project **and run `/catch-up`**. You do **not** clone this factory to scaffold a product — the
installed `slipwai` carries everything it needs. Full reference: [Scaffold a new project](generating.md),
[Install the command](executable.md), [Bring a generated project forward](upgrading.md).

---

## 1. Install the command

Needs **Python 3.11+** and **Git**. **`uv` is the recommended installer** — a
generated project's `./init` uses it too:

```sh
uv tool install slipwai
slipwai --version
```

```text
slipwai 1.0.0
```

Alternatives — `pip`, or a standalone executable that needs only Git — are in
[Install the command](executable.md).

---

## 2. Generate a project

From wherever the new repository should appear:

```sh
slipwai generate
```

In a terminal each fixed list is an arrow-key menu (↑/↓ or `j`/`k`; Enter chooses). The transcript below
is the typed form of the same questions — what you see when stdin is not a terminal, and on Windows.
Press Enter to accept a shown default:

```text
Create a new product monorepo. Press Enter to accept a shown default.
Project name: ledger

Delivery foundation:
  event-modelling — Event Modeling — everything above, plus events as the source of truth, …
  standard — Standard — walking skeleton, executable test and the CD gate, …
Use Event Modeling? [Y/n]: Y

Production target:
  none — Local only — nothing is deployed anywhere; `make verify` is the end of the road
  aws — AWS — …
  azure — Azure — …
  existing — Existing — … (experimental, with brownfield adoption)
Choose (none/aws/azure/existing) [none]:

Language (typescript/python/go/java) [typescript]:
Service name [service]:
What does service own? (a sentence or two; Enter to decide later):
Bounded contexts service holds, comma-separated [service]:
Frontend (none/react-vite) [react-vite]:

Event store:
  memory — In-memory — …
  sqlite — SQLite — …
  postgres — Postgres — …
Choose (memory/sqlite/postgres) [postgres]:

HTTP transport:
  none — None — library or worker only, no inbound HTTP
  fastify — Fastify — …
Choose (none/fastify) [fastify]:

Staff authentication:
  none — None — …
  keycloak — Keycloak — …
Choose (none/keycloak) [none]:

Customer authentication:
  none — None — …
  keycloak — Keycloak — …
Choose (none/keycloak) [none]:
Output parent [/Users/you/dev]:
created: /Users/you/dev/ledger
```

Or pass the answers in one shot (scripts and CI):

```sh
slipwai generate ledger \
  --profile event-modelling \
  --target none \
  --language typescript \
  --frontend react-vite \
  --event-store postgres \
  --http fastify
```

```text
created: /Users/you/dev/ledger
```

That directory is a fresh Git repository on `main` with one commit. The target must not already exist;
`--output` names a different **parent** directory if you want one.

### Bootstrap and prove the gate

```sh
cd ledger
./init                        # Spec Kit; it asks which coding agent, then which extensions
make verify                   # the same gate CI runs
```

```text
$ ./init
… Spec Kit installed; choose an agent integration …

Optional dev tooling — check any to adopt now, or none;
`./init --extension <key>` adds one later just the same.

  ❯ [ ] CodeGraph — Indexes the codebase into a local knowledge graph your
        coding agent can query over MCP, so it can trace callers, dependencies,
        and the blast radius of a change across files.

    [ Confirm ]

  ↑/↓ move · Enter or Space checks · Enter on Confirm finishes · Esc skips
```

Space or Enter on a row checks it; Confirm finishes with whatever is checked; Escape skips. Nothing is
adopted by default. `--extension <key>` skips the menu and names one; the same flag adds one later.
[Extensions](extensions.md).

Then open an agent session and type `/drive` — it walks the delivery ladder from the first missing
artifact. [The delivery loop](delivery-loop.md) is the full picture; [What you get](what-you-get.md) is the
tour of the tree.

---

## 3. Update the command

When a newer release is out, upgrade the *installed* `slipwai` — not a checkout of this factory:

```sh
slipwai upgrade --check   # say what is installed and what is published; change nothing
slipwai upgrade           # replace this copy with the newest release
slipwai upgrade --pre     # count the snapshot of main as well
```

```text
$ slipwai upgrade --check
slipwai 1.0.0, installed as: uv tool
newest published: 1.1.0
this is not the newest published version.
would run: uv tool upgrade slipwai
```

```text
$ slipwai upgrade
slipwai 1.0.0, installed as: uv tool
newest published: 1.1.0
running: uv tool upgrade slipwai
```

An installation configured for a private mirror may still need that mirror's
credentials. Public PyPI installs need none. Detail:
[Upgrade it](executable.md#upgrade-it).

---

## 4. Migrate, then catch up

`upgrade` moves the command on your PATH. `migrate`, run **inside** a generated project on a clean tree,
brings that project's files forward to match the factory you just upgraded to. **The merge is not the end
of the upgrade:** anything a merge cannot do — a gate that now judges older code, an answer the project
still has to give — is left as notes. `/catch-up` is that work.

```sh
cd /Users/you/dev/ledger
slipwai migrate
```

```text
$ slipwai migrate
migrated ledger from 1.0.0 to slipwai 1.1.0: 47 files
One merge commit. The files this project had changed itself were kept; the rest are what the
factory now generates for its answers.
Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.
What the versions crossed ask of code already here — which no merge can do — is written to
.slipwai/catch-up.md, git-ignored and disposable.
Next: /catch-up, which reads .slipwai/catch-up.md — what these versions ask of code already here — and
runs make verify against it.
```

Clean merges are one commit (two when harness projections had to be re-derived). Conflicts leave the
merge in progress with each file named — you decide, `git add`, `git commit`, or `git merge --abort`.

Then, in an agent session from the project root, **do this before considering the upgrade done:**

```sh
/catch-up
```

It reads `.slipwai/catch-up.md` and runs `make verify` against those notes. Skipping it leaves the
repository on a newer factory with obligations nobody has worked through.

`slipwai replay` is the same offer written *beside* the project instead of merged, to look at first.
Full recipe: [Bring a generated project forward](upgrading.md).

---

## Next

| | |
|---|---|
| [Scaffold a new project](generating.md) | Every flag, the interactive form in full, layout, adding a second service |
| [Project shape](axes.md) | What each answer brings, and which combinations are refused |
| [The delivery loop](delivery-loop.md) | `/drive` and the fifteen workflow commands |
| [Adopt an existing repository](learn-adopt.md) | The other learning path — method around code that already exists |
