# Learning path: adopt an existing repository

> **Experimental.** As [AGENTS.md](../AGENTS.md#versioning-is-not-optional) defines the word: the files
> `adopt` writes, the facts `project.json` records and the questions it asks may change in a MINOR release.
> Every place this reaches you says so until it stops being true. Surprises belong on the public issue tracker.

Four sessions: install the command, wrap an existing tree with the delivery method, keep the command
current, then migrate **and run `/catch-up`**. This is **adopt the method**, not **generate the skeleton**
— nothing about strangler-versus-rewrite has to be decided first. Full reference:
[Adopt an existing repository](adopting.md), [Install the command](executable.md), [Bring a generated
project forward](upgrading.md) (the same merge path).

---

## 1. Install the command

Needs **Python 3.11+** and **Git**. **`uv` is the recommended installer**:

```sh
uv tool install slipwai
slipwai --version
```

```text
slipwai 1.0.0
```

Alternatives are in [Install the command](executable.md).

---

## 2. Adopt the repository

Start at the **root** of a repository the factory did not make. The tree must be clean — `adopt` leaves
one factory commit, and `git reset --hard HEAD^` undoes exactly that:

```sh
cd /Users/you/dev/legacy-worker
git status   # nothing to commit
slipwai adopt
```

It surveys the tree, then asks with each finding as the default. Enter accepts; another answer overrides;
`project.json` records which. In a list, ↑/↓ move and Enter chooses:

```text
Adopt the delivery method here (experimental). Each question shows what the survey found as its default:
Enter accepts it, another answer replaces it, and project.json records which. In a list, ↑/↓ move and
Enter chooses.

Found a python build at the repository root (.): python.
Wrap it as the application `legacy-worker`? (its build joins the gate; n leaves it out entirely) [Y/n]:
Language [python]:
What is `legacy-worker`? (the survey could not tell; Enter keeps that)
    service — runs somewhere and serves requests or jobs
    library — code other applications import; ships as a package, not a process
    tool — run by hand or in CI — a CLI, a build helper, a migration runner
    tests — a test suite of its own, against something else here
  ❯ application — not established — leave it open rather than guess; the record says so
Kind: tool
`make verify` would run these for `legacy-worker`, one per Make target:
  install      python3 -m pip install -r requirements.txt
  typecheck    (none recorded)
  lint         (none recorded)
  test         python3 -m pytest
  integration  (none recorded)
  adversarial  (none recorded)
  audit        pip-audit -r requirements.txt
  mutation     (none recorded)
  A target with none recorded is a written no: verify passes it with a line saying so.
Keep these commands? (n asks about each target in turn) [Y/n]:
What does `legacy-worker` own? (a sentence or two, for the docs and the agent; Enter leaves it blank): batch jobs

Database schema: …
Deployment infrastructure: …
Where does this repository's CI run? …
How does a change reach production today? …
Why is this work happening? …
```

`--yes` takes every survey proposal without asking (recorded as `detected`). A flag overrides one answer
either way. Outside a terminal without `--yes`, `adopt` refuses rather than guessing.

When it finishes:

```text
adopted legacy-worker with slipwai 1.1.0 — experimental: this path is new, its shape may change in a MINOR,
and what surprised you belongs on the public issue tracker
261 files written under delivery/ and beside it; nothing of the repository's own was written over.
One commit by the factory; `git reset --hard HEAD^` undoes all of it.
  legacy-worker: . (python; a tool), 3 of 8 targets have a command; the rest are written no's
…
Next: ./delivery/init — installs Spec Kit and asks which coding agent gets the skills and commands
Then: /ground, in the agent — it asks what the tree could not say, one row of the map at a time
Then: make verify — the gate. Its first run records the lint and typecheck findings as the baseline
```

Your `README.md` is left alone. `AGENTS.md` and `.gitignore` each get a marked block, appended once. The
method lives under `delivery/` by default (`--delivery` names another directory).

### Bootstrap and prove the gate

```sh
./delivery/init
make verify
```

`./delivery/init` is the same prompt as generate: agent first, then optional extensions as a checkbox
menu (Escape skips; `--extension <key>` names one or adds one later).

A red test suite stops that first run and says so: read the failures, then `make ratchet-tighten`
quarantines it deliberately. Commit `delivery/baseline.json` with what init wrote. Next in the agent:
`/ground` (what the tree could not say), then `/drive`. [The two workflows](two-workflows.md) places this
beside generate.

---

## 3. Update the command

Same as the generate path — upgrade the installed `slipwai`:

```sh
slipwai upgrade --check
slipwai upgrade
slipwai upgrade --pre      # count the snapshot of main as well
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

Adoption writes factory material under `delivery/` the same way generate writes it at the root. When a
newer factory changes that material — or the experimental contract — bring it forward from the repository
root on a clean tree. **The merge is not the end of the upgrade:** `/catch-up` is the work a merge cannot
finish.

```sh
cd /Users/you/dev/legacy-worker
slipwai migrate
```

```text
$ slipwai migrate
migrated legacy-worker from 1.0.0 to slipwai 1.1.0: 32 files
One merge commit. The files this project had changed itself were kept; the rest are what the
factory now generates for its answers.
Nothing pushed; `git reset --hard ORIG_HEAD` undoes all of it.
What the versions crossed ask of code already here — which no merge can do — is written to
.slipwai/catch-up.md, git-ignored and disposable.
Next: /catch-up, which reads .slipwai/catch-up.md — what these versions ask of code already here — and
runs make verify against it.
```

Your product code stays yours; conflicts land where both you and the factory edited the same lines of
method material. `/survey` re-reads the tree when detection, not the factory's files, is what moved.

Then, in an agent session from the repository root, **do this before considering the upgrade done:**

```sh
/catch-up
```

It reads `.slipwai/catch-up.md` and runs `make verify` against those notes — including catch-up the
experimental adoption contract left. Skipping it leaves the method on a newer factory with obligations
nobody has worked through.

Full recipe: [Bring a generated project forward](upgrading.md); adoption-specific notes stay in
[Adopt an existing repository](adopting.md).

---

## Next

| | |
|---|---|
| [Adopt an existing repository](adopting.md) | Survey, flags, convergence map, ratchet, what it forfeits |
| [The two workflows](two-workflows.md) | Generated and adopted side by side |
| [Gates](verification.md) | The ratchet and day-one green |
| [Generate a new project](learn-generate.md) | The other learning path — a fresh skeleton from answers |
